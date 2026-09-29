# GD-014 — GD-013 ORM Rollback Exception Authorization

**Status:** **ACCEPTED — 23 September 2026, on explicit Governance Authority ratification. IN FORCE.**
This Decision authorizes exactly the narrow rollback exception in §5 below; ratification does not
itself certify that any implementation relying on it has satisfied the seven mandatory proof obligations
in §5, and does not authorize a Git commit, push, pull request, or merge of any kind.

**Date drafted:** 2026-09-21. **Ratification date:** **23 September 2026.**

**Ratification Record.** The Governance Authority expressly ratified this exact text — the remediated
draft that passed the final ratification-readiness verification against `origin/main` baseline
`0bcc18eae463ec30e8f846357858529686d16747` — on 23 September 2026, declaring GD-014 ACCEPTED and IN
FORCE. That governance act is distinct from three further acts, none of which the ratification itself
performs or authorizes: (1) the local documentation transcription recorded in this file and in the
Article XVI Log entry it authorizes, performed here under separate, bounded execution authority; (2) any
subsequent Git commit, push, pull request, or merge of this documentation change, not authorized by
either the ratification or this transcription; and (3) implementation acceptance under §5's seven
mandatory proof obligations, which remains outstanding and is not certified, in whole or in part, by
this ratification.

**Operative authority:** **Article XVI §2** — this is a later numbered decision that explicitly names
`docs/GD-013-gd012-commit-boundary-and-concurrent-correction-exception-authorization.md` (to grant one
narrow, additional implementation-mechanism exception its own text explicitly foreclosed, and to
correct one factual assumption in its own drafting) and amends nothing else. It is not proposed under
Article XIV and does not amend this Constitution. It follows the exact precedent `GD-013` itself set
for narrowly qualifying an earlier decision's execution mechanics without reopening its substantive
scope.

## 1. Governance baseline verified for this drafting

Read directly against the current repository, not assumed or carried over from any prior document:

- `origin/main` SHA: **`0bcc18eae463ec30e8f846357858529686d16747`** — the GD-013 ratification squash
  commit (PR #37), confirmed the current tip of `main`.
- `docs/GD-012-evidence-actor-attribution-http-implementation-authorization.md`: **ACCEPTED —
  2026-09-17, IN FORCE.**
- `docs/GD-013-gd012-commit-boundary-and-concurrent-correction-exception-authorization.md`: **ACCEPTED
  — 2026-09-19, IN FORCE.** No implementation has yet been merged under GD-012/GD-013 — the two
  authorized endpoints exist only as an uncommitted local implementation, on branch
  `feat/gd012-evidence-attribution-http`, that has not been committed, pushed, reviewed, or merged.
- Article XVI Governance Decision Log (`docs/LV-000-constitution.md`): entries **GD-001 through
  GD-013** exist. No `GD-014` or higher entry exists anywhere in the repository (checked by direct
  search of every `docs/GD-0*.md` file and of the Log itself).
- **Next available Governance Decision number, confirmed by repository reality: GD-014.**
- **The finding this Decision addresses was established by a formal, independent Governance review of
  the uncommitted GD-012/GD-013 implementation** — not by the implementing engineer's own report,
  which that review explicitly declined to accept at face value. The review traced the actual
  execution path against the actual source and actual observed `sqlalchemy` behavior. The formal
  GD-012/GD-013 HTTP implementation governance review concluded that the implementation, as written,
  is not authorised because the correction endpoint's exception-translation code introduces an
  explicit session rollback that `GD-013` §4 expressly forecloses. This implementation has never been
  committed or pushed and carries no pull-request number of its own — it remains local, uncommitted
  work on branch `feat/gd012-evidence-attribution-http`.

## 2. Purpose

This Decision does exactly one thing: **grants one narrow, additional implementation-mechanism
exception to `GD-013`** — authorizing the specific `session.rollback()` call the formal implementation
review found unauthorized — and **corrects one factual assumption in `GD-013`'s own drafting** about
SQLAlchemy ORM `Session` behavior that the review's independent verification disproved. It does **not**
reopen, expand, or narrow any other part of `GD-012` or `GD-013`'s scope, does not authorize any
additional HTTP operation, endpoint, role, or architecture change, and does not amend `ADR-028`,
`GD-009`, `GD-010`, or `GD-011`.

## 3. The exact GD-013 §4 wording this Decision modifies

`GD-013` §4 states, in its "What actually happens to the session once the router raises
`HTTPException(409)`" subsection:

> Raising `HTTPException(409)` is therefore safe in practice, but not because doing so is guaranteed to
> trigger a rollback — no code path in this exception guarantees that, **and none is authorized to add
> one**.

This Decision amends that clause only, replacing the categorical prohibition on adding any rollback
call with the single, narrowly bounded authorization in §5 below. No other sentence in `GD-013` §4, and
no other section of `GD-013`, is touched.

## 4. The finding, and the correction to GD-013's own factual assumption

`GD-013` §4's own safety theory rested on one true fact stated too broadly: PostgreSQL discards an
aborted transaction's work regardless of whether the client subsequently requests `COMMIT` or
`ROLLBACK` on the *database connection*. This is correct as a statement about PostgreSQL's own wire
protocol. It is **not**, however, a complete description of what happens when the caller is a
SQLAlchemy **ORM `Session`** (as `PostgresEvidenceActorAttributionRepository.record()` actually is —
`self._session.add(model)` followed by `await self._session.flush()`) rather than a raw Core
`Connection`. `GD-013`'s own drafting-time verification (its "Verified directly instead, against a real
PostgreSQL database, instrumenting `AsyncSession.commit`/`.rollback`" passage) used a simplified
harness that issued its INSERT via a raw Core connection, not via `Session.add()`/`flush()` — and so
never exercised the specific guard now found to matter.

**Established by the formal implementation review, using this session's own actual, observed
`sqlalchemy` behavior, not assumed:** once `Session.flush()` raises (as it does for the losing
concurrent `INSERT`), SQLAlchemy marks that `Session`'s transaction "must rollback" at the ORM layer —
*above* the database connection itself. Any further use of that same `Session` — including
`get_db_session`'s own, unmodified `except HTTPException: await session.commit()` branch — raises
`sqlalchemy.exc.PendingRollbackError` instead of completing, because the ORM refuses to proceed without
an explicit `rollback()` first. Confirmed directly: with no rollback call, the losing request's actual
observed HTTP outcome was **500** (`PendingRollbackError`, unhandled), not the **409** `GD-012` §7/§10
item 16 and `GD-013` §4 itself require. `GD-013`'s own assumption that PostgreSQL's connection-level
behavior alone would suffice was incomplete for this reason — a fact only established once a real ORM
`Session`-based repository call was exercised, which `GD-013`'s own verification did not do.

## 5. The exception granted

The router `backend/app/contexts/evidence/api/attribution_router.py`'s existing, `GD-013`
§4-authorized `IntegrityError` handler for `correct_evidence_attribution` may additionally call
`await service.session.rollback()` — **if and only if**:

1. the call occurs **only** inside the branch already gated by `_is_supersedes_once_violation(exc)`
   returning `True` — i.e., only after both structured diagnostics `GD-013` §4 condition 1 already
   requires (SQLSTATE exactly `23505`; constraint name exactly
   `uq_evidence_actor_attributions_supersedes_once`) have independently matched. No other exception
   path — including the commit-boundary failure `GD-013` §3 addresses, which must continue to surface
   as a 5xx — may reach this rollback call;
2. the call targets `service.session` **only** — the identical, single, function-scoped `AsyncSession`
   instance every one of the five providers `GD-013` §3 already authorizes shares for the whole
   request (`GD-013` §3 condition 2's "exactly one session instance" requirement is unaffected and
   restated here, not relaxed: this exception does not authorize introducing a second session, an
   independent transaction, or any connection this Decision's own five-provider graph does not already
   own);
3. no general rollback policy, retry mechanism, or additional database mutation accompanies the call —
   this Decision authorizes exactly one `rollback()` invocation in exactly one already-identified
   branch, nothing broader;
4. **a failure of the `rollback()` call itself must not be hidden behind a misleading `HTTPException
   (409)`.** The call must not be wrapped in a `try/except` that swallows its own exception and
   proceeds to raise 409 regardless — if `rollback()` itself raises, that exception must propagate
   as-is (surfacing, ultimately, as a 5xx), never as a false 409 implying the conflict was cleanly
   resolved when the session's own state could not be verified clean;
5. no change is made to `EvidenceActorAttributionService.correct_attribution`,
   `_resolve_active_head`, `PostgresEvidenceActorAttributionRepository.record`, `app/kernel/uow.py`,
   `backend/app/contexts/evidence/dependencies.py`, or any other application-service, repository-
   adapter, or shared-dependency code — the rollback call, like the exception-translation logic it
   extends, occurs entirely in the new router module, around an unmodified call to the unmodified
   service method, exactly as `GD-013` §4 condition 2 already required for the surrounding
   translation.

**Required proof — mandatory implementation-acceptance obligations, not a claim that any of the
following has already passed.** Ratification of this Decision authorizes the mechanism in §5 above; it
does not itself constitute proof that an implementation using it is complete. Before an implementation
relying on this exception may be considered acceptance-ready, it must include tests establishing each
of the following, restated here with the same specificity `GD-012` §10 and `GD-013` §4's own required-
proof paragraph already use:

1. **Forced final-commit failure, on both the record and correction endpoints**, produces a non-2xx
   response and leaves neither a durable attribution row nor a durable successful-mutation audit event
   — **real PostgreSQL required** (a forced commit failure is a database-level event that cannot be
   established hermetically).
2. **Commit completion precedes successful HTTP response transmission, on both endpoints** — **real
   PostgreSQL required** (timing relative to an actual commit cannot be established against an
   in-memory fake).
3. **Exactly one shared session serves each endpoint's own five-provider dependency graph** — **real
   PostgreSQL required** (session identity is only meaningful against a real session factory; an
   in-memory fake session cannot demonstrate this property).
4. **A matched concurrent-correction conflict** (both structured diagnostics from §5.1 above) **produces
   HTTP 409 without leaving the losing attribution row or its successful-mutation audit event durable**
   — **real PostgreSQL required** (genuine concurrency and the real `UNIQUE` constraint are both
   necessary to this proof).
5. **A failure of the `rollback()` call itself (§5.4) is not suppressed or converted into a misleading
   HTTP 409** — **hermetic testing is sufficient** (a fake session whose `rollback()` method raises can
   establish this without a real database).
6. **An `IntegrityError` arising from any constraint other than
   `uq_evidence_actor_attributions_supersedes_once` remains outside this narrowly authorized
   translation** — **hermetic testing is sufficient** for the predicate itself (synthetic diagnostics);
   **real PostgreSQL** is additionally required to confirm the self-supersession `CHECK`/cycle-trigger
   interaction this Decision does not alter.
7. **Rejected mutation attempts leave no unauthorized attribution row or successful-mutation audit
   event durable**, across the relevant `400`, `401`, `403`, `404`, and `422` cases on both endpoints —
   **hermetic testing is sufficient** (checking the fake repository's contents after each rejected
   attempt).

None of items 1–7 authorizes, or may be read to authorize, any broadening of the rollback mechanism
itself beyond what §5 above already bounds — they are proof obligations for the exception already
granted, not additional grants of authority.

## 6. Everything else in GD-012 and GD-013 remains unamended

This Decision modifies exactly the one `GD-013` §4 clause quoted in §3 above. **All other provisions of
`GD-012` and `GD-013` remain in force, unaffected and unamended**, restated for the avoidance of doubt:

- `GD-012`'s two-endpoint scope (§4), authorization reuse (§5), response-contract narrowness (§6,
  including the §6.4 `actor_principal_id` message-normalization exception), audit transaction
  integrity (§8), and full exclusion list (§11) — untouched.
- `GD-013` §3's commit-boundary exception (the five endpoint-local, function-scoped providers) —
  untouched; this Decision does not add, remove, or alter any of the five providers, and the
  "exactly one session" requirement is restated, not relaxed, in §5.2 above.
- `GD-013` §4's dual-diagnostic predicate itself (SQLSTATE `23505` + exact constraint name, via
  structured driver attributes only) — untouched; this Decision authorizes one additional action
  *inside* the branch that predicate already gates, not a change to the predicate.
- `GD-013` §4 condition 3 (no new database constraint, trigger, retry mechanism, or transaction-
  isolation change) — untouched and restated: `rollback()` is an existing `AsyncSession` method, not a
  new mechanism of that kind.

## 7. No unauthorized architecture expansion

Restated, because this exception is a narrow addition to `GD-013`'s existing boundary, not a reopening
of it: this Decision does not authorize, and no implementation under it may introduce, any of the items
`GD-012` §11 or `GD-013` §6 already exclude, nor:

- any change to `app/kernel/uow.py` or `get_db_session`'s own definition;
- any change to `backend/app/contexts/evidence/dependencies.py`'s existing five provider functions;
- any database migration;
- any change to `verify_chain()`, `_compute_hash`, `GENESIS_HASH`, or any other audit-kernel internal;
- any change to tenant-isolation architecture or authentication/authorization mechanism;
- any frontend work of any kind;
- any broadening of the two-endpoint scope `GD-012` §4 authorizes;
- a second `AsyncSession`, an independent transaction, or any connection outside the five-provider
  graph `GD-013` §3 already authorizes;
- any general exception-to-rollback policy applicable to exceptions other than the one specifically
  gated `IntegrityError` branch named in §5.1 above.

**Stop-and-return condition, restated from `GD-013` §6 in identical form:** if implementation reality
proves this exception insufficient, or reveals that achieving the required properties needs a change to
`dependencies.py`, `uow.py`, a new database constraint, or any other item this section excludes, the
implementing engineer must stop and return exactly:

**`GD-014 BLOCKED — [DEPENDENCY-GRAPH | UOW | CONSTRAINT | AUTHORIZATION] AUTHORITY REQUIRED`**

rather than improvise a workaround inside this Decision's own authority.

## 8. Article XVI entry (ratified — inserted into LV-000 under separate transcription authority)

The Governance Authority ratified this Decision, including the following text, on 23 September 2026.
The text below is inserted into `docs/LV-000-constitution.md`'s Article XVI Log as a distinct,
separately-authorized local documentation transcription of that ratification (not performed by the act
of ratification itself, and not, by that transcription alone, a Git commit, push, pull request, or
merge):

> **GD-014 — GD-013 ORM Rollback Exception Authorization.** *(Ratified 23 September 2026; full operative
> text at `docs/GD-014-gd013-orm-rollback-exception-authorization.md`.)* Operative authority:
> **Article XVI §2** — GD-014 is a later numbered decision that explicitly names `docs/
> GD-013-gd012-commit-boundary-and-concurrent-correction-exception-authorization.md` to grant one
> narrow, additional implementation-mechanism exception its own text explicitly foreclosed, and to
> correct one factual assumption in its own drafting about SQLAlchemy ORM `Session` behavior; it is not
> proposed under Article XIV and does not amend this Constitution.
>
> **Decision.** `GD-013` §4's statement that no rollback mechanism "is authorized to add" is amended
> solely to permit the correction endpoint's existing, `GD-013`-authorized `IntegrityError` handler to
> call `await service.session.rollback()` — on the single, function-scoped session `GD-013` §3 already
> authorizes, only inside the branch already gated by the existing dual-diagnostic predicate (SQLSTATE
> `23505` and constraint name `uq_evidence_actor_attributions_supersedes_once`), with no general
> rollback policy, no second session, no additional mutation, and no concealment of a rollback failure
> behind a false 409. This corrects `GD-013`'s own incomplete verification, which exercised a raw Core
> connection rather than the ORM `Session` the actual repository code uses, and did not discover that a
> failed `Session.flush()` requires an explicit `rollback()` before any further use — including
> `get_db_session`'s own subsequent commit — can succeed.
>
> **Scope excluded — no retroactive expansion.** This decision does not authorise any change to
> `dependencies.py`, `uow.py`, any database migration, any audit-kernel or verifier change, any
> authentication/authorization/tenant-isolation change, any frontend work, any broadening of `GD-012`'s
> two-endpoint scope, or any of the programmes `GD-008`/`ADR-026`/`ADR-028`/`GD-009`/`GD-011` already
> exclude. All other `GD-012` and `GD-013` provisions remain in force, unaffected and unamended.

## Approval Gate

This Governance Decision is **ACCEPTED and IN FORCE**, ratified by the Governance Authority on 23
September 2026. It authorizes exactly the narrow rollback exception in §5 above — nothing more.

**Explicit exclusions, restated.** This ratification does not authorize: any change to
`backend/app/contexts/evidence/dependencies.py` or `app/kernel/uow.py`; any database migration; any
change to the audit kernel or `verify_chain()`/`_compute_hash`/`GENESIS_HASH`; any change to
authentication, authorization, or tenant-isolation architecture; any frontend work; any broadening of
the two-endpoint scope `GD-012` §4 authorizes; a second session or independent transaction; a general
exception-to-rollback policy beyond the one specifically gated branch named in §5.1; or any of the
programmes named in `GD-009`/`GD-012`/`GD-013`'s own exclusion lists.

See the companion readiness report, `docs/GD-014_READINESS_REPORT.md`, for the independent challenge of
this draft that preceded this ratification, and for the seven mandatory proof obligations that remain
outstanding implementation-acceptance requirements notwithstanding ratification.
