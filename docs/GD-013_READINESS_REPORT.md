# GD-013 READINESS REPORT

**Type:** Point-in-time governance readiness review, produced against `origin/main` at commit
`81daeba11407558571eb82674abd727655d17d11`, preserved as the pre-ratification readiness record
alongside the draft `docs/GD-013-gd012-commit-boundary-and-concurrent-correction-exception-
authorization.md`.

## 1. Baseline and Numbering

- `origin/main`: `81daeba11407558571eb82674abd727655d17d11` — the GD-012 ratification squash commit
  (PR #36), fetched fresh for this drafting.
- GD-013 availability: confirmed by direct search of every `docs/GD-0*.md` file and the Article XVI
  Log — highest existing entry is GD-012; no `GD-013` reference exists anywhere in the repository.

## 2. Why This Decision Exists

`GD-012` (Accepted 2026-09-17) authorized the minimum HTTP interface for Evidence actor attribution.
Before any implementation was written, a mandatory preflight investigation (required by the
implementation task itself, independent of `GD-012`'s own text) tested `GD-012`'s implicit assumption
that reusing the existing, unmodified `get_evidence_actor_attribution_service` dependency would
produce an HTTP response accurately reflecting whether the underlying database transaction actually
succeeded. It does not. This report and the accompanying draft exist because that finding, and a
second related finding about concurrent-correction error handling, surfaced only during
implementation-preflight — genuinely new information `GD-012`'s own drafting could not have
anticipated, not a drafting oversight discovered by re-reading the same evidence.

## 3. Sources Inspected

- `docs/GD-012-evidence-actor-attribution-http-implementation-authorization.md` — full text, current
  ratified version, §§4–11 re-read in full for this drafting.
- `backend/app/kernel/uow.py` — `get_db_session`, read in full.
- `backend/app/contexts/evidence/dependencies.py` — all five relevant provider functions, read in
  full.
- `backend/app/contexts/evidence/adapters/postgres_repositories.py` —
  `PostgresEvidenceActorAttributionRepository.record`, read in full.
- `backend/migrations/versions/0014_evidence_actor_attributions.py` — the supersession-uniqueness
  constraint definition, confirmed non-deferrable.
- `fastapi/params.py`, `fastapi/dependencies/models.py`, `fastapi/dependencies/utils.py`,
  `fastapi/routing.py` (installed package, version 0.139.0) — read directly to confirm the `scope`
  parameter's real, documented, and source-verified behavior, not assumed from external documentation
  alone.

## 4. Finding 1 — Commit-Boundary Timing (Full Technical Basis)

**Method:** three escalating empirical proofs, each against the actual installed FastAPI/Starlette
versions:
1. An isolated harness reproducing `get_db_session`'s exact try/yield/commit shape, via `TestClient`.
2. The same shape, against a real `uvicorn` server on a real TCP socket, hit with a real `httpx`
   client — ruling out any `TestClient` in-process-transport artifact.
3. The actual, unmodified `app.kernel.uow.get_db_session` function, imported directly (not
   reproduced), with only its session factory swapped for one whose `commit()` raises, run through a
   real server and real socket.

**Result, all three:** the client received **HTTP 200** with the endpoint's original success body
even though the injected commit failed. Traceback confirms the failure occurs inside FastAPI's
request-scoped `AsyncExitStack` (`fastapi/routing.py` line 132), which the traceback shows exits
*after* the response has already been constructed and returned along the success path — the
exception only ever reaches a server-side log line.

**Fix, proven with equal rigor:** FastAPI 0.139.0's `Depends(..., scope="function")` — confirmed via
direct source inspection to use a *separate* `AsyncExitStack` (`fastapi/routing.py` line 134,
`function_stack`) that closes before response transmission. Applying it consistently to all five
`Depends(get_db_session)` occurrences in the attribution dependency graph (via five new,
endpoint-local provider functions) was proven, against a real, migrated, throwaway PostgreSQL
database:
- Success case: HTTP 200, exactly one session (`id()` identical across every one of the five
  providers), attribution row and audit row both independently verified durable via a separate
  connection after the response.
- Commit-failure case: HTTP **500** (not 200), independently verified — zero new rows, matching the
  pre-failure count exactly.
- `HTTPException`-path case: a route raising `HTTPException(403)` still correctly returned 403, and
  `get_db_session`'s existing "HTTPException → commit, not rollback" branch (protecting scenarios like
  a revoke-then-reject sequence elsewhere in this codebase) fired exactly once, unchanged — because
  `get_db_session`'s own source was never edited, only how it is declared as a dependency.

**Why this cannot be achieved by literally reusing `Depends(get_evidence_actor_attribution_service)`
as `GD-012` §9 currently requires:** confirmed via `fastapi/dependencies/models.py`:
`Dependant.cache_key` includes `computed_scope`, and `computed_scope` derives from the `scope` value
fixed at each `Depends()` call's own declaration site — the four provider functions and the service
provider itself all declare their own `Depends(get_db_session)` internally, in `dependencies.py`, at
default scope. Nothing available to a caller of `get_evidence_actor_attribution_service` can alter
those internal declarations' scope without either editing that file (a shared-UoW-adjacent change
touching unrelated routes) or substituting a different callable entirely (which is not "the existing
dependency — unchanged," regardless of the substitution mechanism).

## 5. Finding 2 — Concurrent-Correction Status Code (Full Technical Basis)

**Method:** direct code tracing, not live-tested in this drafting (the underlying mechanism — a plain
Postgres unique-constraint violation surfacing as an unhandled `IntegrityError` — is deterministic and
does not require a live race to characterize; `GD-012` §10 item 16 already requires the actual
concurrent-race test at implementation time).

**Chain of evidence:**
1. `uq_evidence_actor_attributions_supersedes_once` (migration `0014`) — `UNIQUE (supersedes_id)`,
   not `DEFERRABLE`. Postgres default: checked immediately at statement execution.
2. `PostgresEvidenceActorAttributionRepository.record()` — `self._session.add(model)` immediately
   followed by `await self._session.flush()`. The INSERT, and any unique-violation, therefore fires
   synchronously inside `correct_attribution()`'s own call stack — mid-request, not at final commit.
3. `EvidenceActorAttributionService.correct_attribution` — catches only `ValueError` (→ 400). No
   `sqlalchemy.exc.IntegrityError` handling exists anywhere in this method or its callees.
4. Consequence: an unhandled `IntegrityError` propagates to `get_db_session`'s generic
   `except Exception: rollback(); raise` (correct rollback, no phantom row — data integrity is fine),
   then to Starlette's default exception-handling middleware, which converts any unhandled exception
   into a generic **500** — not the "coherent 4xx" `GD-012` §7/§10 item 16 explicitly requires.

**Fix proposed:** router-level (not service-level) exception translation, scoped to the one named
constraint, converting its `IntegrityError` into `HTTPException(409)` — chosen deliberately narrow (a
named-constraint check, not a blanket database-exception handler) so that an unrelated, genuinely
unexpected database failure — including Finding 1's own commit-boundary failure — continues to
surface as a 5xx rather than being masked behind a misleadingly specific 409.

## 6. Why a New Governance Decision, Not Silent Implementation

Both fixes are, in isolation, small and mechanically unremarkable — an extra `scope=` keyword and a
try/except block. Neither, however, is literally what `GD-012` §9 authorizes: §9 names a specific
existing callable "unchanged," and says nothing about exception translation for the correction route.
Constitution Article XVI §2 states plainly that "a decision in this Log is amended only by a later
numbered decision that names it" — `GD-012` itself relies on this exact discipline to bound its own
authority over `GD-009`. Treating a technically-sound fix as self-evidently authorized because it is
"obviously what GD-012 must have meant" would be exactly the kind of silent expansion this repository's
governance discipline (visible throughout `GD-009`'s, `GD-010`'s, and `GD-011`'s own stop-and-return
clauses) exists to prevent. GD-013 exists to make the two exceptions explicit, narrow, and reviewable,
rather than assumed.

## 7. Scope Discipline

Both exceptions are drawn as narrowly as the underlying finding requires:
- Finding 1's exception names the exact five functions, requires them to mirror their originals
  field-for-field, requires identical scope across all five (closing off any possibility of a
  two-session split), and explicitly forbids editing `dependencies.py` or `uow.py`.
- Finding 2's exception names the exact constraint, forbids a general exception-handler, and forbids
  any service/repository-layer change.
- §5 of the draft explicitly restates that every other `GD-012` provision — scope, authorization,
  response contract, the `_verify_actor_reference` exception, audit integrity, the full exclusion
  list — is unamended and unaffected.

Neither exception authorizes a platform-wide fix for the same commit-boundary defect at any of this
codebase's other existing mutating endpoints (upload, parcel mutation, admin, auth) — all of which
share the identical property, since they all still use the default-scope providers. That broader
question is deliberately left to its own, future, separate governance act, exactly as `GD-012` itself
left the remaining 52 audit call sites and any Batch-2-style expansion to their own future acts.

## 8. Required Validation, Restated as Mandatory

The draft (§3, §4) requires — not merely suggests — that the eventual implementation's tracked test
suite include:
- a real-PostgreSQL test proving a forced final-commit failure on either attribution endpoint yields a
  non-2xx response with zero rows persisted (generalizing this drafting's own proof into permanent,
  re-runnable evidence);
- the real-PostgreSQL concurrent-correction test `GD-012` §10 item 16 already requires, extended to
  assert the specific status code (409, or whichever single code is chosen and documented) rather than
  merely "some 4xx."

## 9. Unresolved Questions for Governance

1. **409 vs. another 4xx code for the concurrent-correction race.** The draft proposes 409 (Conflict)
   as the conventional HTTP status for a losing optimistic-concurrency race, consistent with common
   REST practice, but this repository has no prior precedent endpoint returning 409 to compare
   against (`evidence_router.py`'s existing endpoints use 400/403/404/413 only). Governance should
   confirm 409 is acceptable, or specify an alternative.
2. **The platform-wide commit-boundary defect** (§7 above) is disclosed here as context but
   deliberately left unaddressed — Governance may wish to open a separate, future investigation into
   whether the same fix should eventually apply to the platform's other mutating endpoints, but this
   draft does not propose that work and recommends against bundling it here.

Neither question blocks this draft's own two narrow exceptions from being ready for review.

## 10. Exact Files Created

Exactly two, both uncommitted, both new (no existing file modified):
- `docs/GD-013-gd012-commit-boundary-and-concurrent-correction-exception-authorization.md`
- `docs/GD-013_READINESS_REPORT.md`

Created in a fresh, detached worktree (`Development-Plan-gd013-draft`, checked out at `origin/main`'s
`81daeba...`), consistent with the pattern already used for `GD-012`'s own drafting, to avoid placing
uncommitted material inside the GD-012 implementation worktree
(`Development-Plan-gd012-http`, branch `feat/gd012-evidence-attribution-http`, left clean and
untouched) or the governance-protected preserved-prototype worktree
(`feat/gd009-batch1-transactional-audit`, likewise untouched).

## 11. Working-Tree State

The drafting worktree contains only the two new files above, untracked, unstaged, uncommitted. No
existing governance document, ADR, LV-000, backend code, frontend code, or migration was modified,
staged, or committed. No branch was created; the worktree is in a detached-HEAD state at `origin/main`.
No push, commit, or PR was made.

## 12. Recommendation for Governance Review

The draft is internally consistent with `GD-012`'s own text and structure, grounded in reproducible,
real-Postgres/real-HTTP evidence rather than assertion, drawn as narrowly as each finding allows, and
explicitly restates every `GD-012` provision it does not touch. The two open questions in §9 are
disclosed for Governance's attention, not defects requiring textual remediation before review. On that
basis:

**GD-013 READY FOR FORMAL GOVERNANCE REVIEW**
