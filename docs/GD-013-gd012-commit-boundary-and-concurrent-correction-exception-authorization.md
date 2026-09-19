# GD-013 — GD-012 Commit-Boundary and Concurrent-Correction Exception Authorization

**Status:** **ACCEPTED — 2026-09-19, on explicit Governance Authority ratification. IN FORCE.** This
Decision authorizes exactly the two narrow, additional implementation-mechanism exceptions to `GD-012`
described below — the same category of narrowly-scoped qualification `GD-011` gave its own lifting of
`GD-009` §11. It does **not** authorize implementation execution, a Git commit, push, pull request, or
merge; those remain separate, subsequent authorizations. It does **not** authorize anything beyond the
two exceptions named below; see "Explicit exclusions" under "Approval Gate" below.

**Date drafted:** 2026-09-18. **Ratified:** 2026-09-19.

**Operative authority:** **Article XVI §2** — this is a later numbered decision that explicitly names
`docs/GD-012-evidence-actor-attribution-http-implementation-authorization.md` (to grant two narrow,
additional implementation-mechanism exceptions its own text did not anticipate) and amends nothing
else. It is not proposed under Article XIV and does not amend this Constitution. It follows the exact
precedent `GD-011` set for narrowly qualifying an earlier decision's execution mechanics without
reopening its substantive scope, and the precedent `GD-012` §9 itself already set — the
`_verify_actor_reference` message-normalization clause — for granting one narrowly bounded exception
to an otherwise-unchanged-reuse rule.

## Ratification Record

Ratified by Governance Authority for AquaSavannah LandVault, **2026-09-19**, following the formal
Governance review (`GD-013 GOVERNANCE REVIEW PASS WITH REQUIRED TEXTUAL REMEDIATION`), the required
textual remediation that review identified (the constraint-identity precision in §4 condition 1,
requiring both SQLSTATE `23505` and the exact constraint name — verified achievable via structured
driver diagnostics, not message-parsing), and a final transaction-wording verification pass (correcting
§4's explanation of which `get_db_session` branch actually executes once `HTTPException(409)` is
raised, and confirming no claim of guaranteed rollback is made) — all applied and independently
re-verified before ratification. This record does not alter the draft; it identifies what ratification
covers:

- **Two exceptions only, both narrowly bounded** (§3, §4): endpoint-local, function-scoped dependency
  wiring for the commit-boundary fix, and constraint-specific `HTTP 409` translation for the
  concurrent-correction race — nothing broader.
- **One shared session, one commit point, commit before response transmission** (§3): proven by
  direct execution against the actual `app.kernel.uow.get_db_session` function and a real, throwaway
  PostgreSQL database — not asserted.
- **`dependencies.py` and `uow.py` remain untouched** (§3 conditions 3–4, §6): every other route's
  dependency wiring is unaffected.
- **The 409 translation requires both SQLSTATE `23505` and the exact constraint name
  `uq_evidence_actor_attributions_supersedes_once`** (§4 condition 1), confirmed achievable via
  structured diagnostic attributes SQLAlchemy/asyncpg expose directly — never by parsing a
  human-readable message — so the self-supersession `CHECK` constraint (sharing `IntegrityError`'s
  exception class) cannot be misclassified as this exception's intended case.
- **No guarantee of rollback is claimed for the 409 path** (§4): the Decision states precisely which
  `get_db_session` branch executes (`HTTPException` → `commit`, not the generic-exception → `rollback`
  branch) and grounds the path's actual safety in PostgreSQL's own aborted-transaction semantics,
  verified directly — not in an internal branch name.
- **All other `GD-012` provisions remain in force, unaffected and unamended** (§5) — scope,
  authorization reuse, response-contract narrowness, the existing `_verify_actor_reference` exception,
  audit-transaction integrity, and the full exclusion list.
- **This ratification does not authorize implementation, commit, push, PR, or merge** — those require
  their own, separate, subsequent authorization, exactly as this Decision's own Status line states.

## 1. Governance baseline verified for this drafting

Read directly against the current repository, not assumed or carried over from any prior document:

- `origin/main` SHA: **`81daeba11407558571eb82674abd727655d17d11`** — the GD-012 ratification squash
  commit (PR #36), confirmed the current tip of `main`.
- `docs/GD-012-evidence-actor-attribution-http-implementation-authorization.md`: **ACCEPTED —
  2026-09-17, on explicit Governance Authority ratification. IN FORCE.** No implementation has yet
  been merged under it — the two authorized endpoints do not yet exist in any branch merged to `main`.
- Article XVI Governance Decision Log (`docs/LV-000-constitution.md`): entries **GD-001 through
  GD-012** exist. No `GD-013` or higher entry exists anywhere in the repository (checked by direct
  search of every `docs/GD-0*.md` file and of the Log itself).
- **Next available Governance Decision number, confirmed by repository reality: GD-013.**
- **Two technical findings, established this session by direct, reproducible investigation against
  the actual installed framework versions and a real, throwaway PostgreSQL database — not assumed,
  not inferred from documentation alone** — are the entire basis for this Decision. Both are
  restated precisely in §3–§4 below.

## 2. Purpose

This Decision does exactly one thing: **grants two narrow, additional implementation-mechanism
exceptions to `GD-012`**, each addressing a technical finding discovered during preflight
investigation of `GD-012`'s own authorized scope that `GD-012`'s text did not anticipate. It does
**not** reopen, expand, or narrow any other part of `GD-012`'s scope, does not authorize any
additional HTTP operation, endpoint, role, or architecture change beyond the two exceptions named
below, and does not amend `ADR-028`, `GD-009`, `GD-010`, or `GD-011`.

## 3. First finding and exception — commit-boundary timing

**The finding, established by direct, reproducible proof (real `uvicorn` server, real TCP socket, real
`httpx` client, the actual `app.kernel.uow.get_db_session` function, no simulation):** FastAPI
0.139.0's default dependency scope (`"request"`, the implicit value for every `yield`-based dependency
when no `scope=` is specified) exits its cleanup — including `get_db_session`'s own final
`await session.commit()` — **after** the HTTP response has already been transmitted to the client.
Reproduced three times, with increasing rigor, ending in a proof against the literal, unmodified
`app.kernel.uow.get_db_session` function: a client received **HTTP 200** with a fabricated success
body even though the injected final commit failed with an unhandled `RuntimeError`, logged server-side
only, never reaching the client. This is a pre-existing property of `get_db_session` — the single
shared dependency every mutating endpoint in this codebase already uses — not something `GD-012`
introduces; it has simply never been tested for any endpoint before, and `GD-012`'s two endpoints are
the first work for which it becomes squarely load-bearing, because their entire purpose is a
transaction-coupled guarantee between a business mutation and its audit event that the caller must be
able to trust the HTTP response accurately reflects.

**The proven fix, established by an equally rigorous, three-case proof (success, commit-failure, and
`HTTPException`-path, all against a real throwaway PostgreSQL database migrated to head):** FastAPI
0.139.0 provides a second, explicitly documented dependency scope, `"function"`, under which a
`yield`-dependency's post-yield cleanup runs **before** the response is transmitted. Applying it
requires **five new, endpoint-local dependency-provider functions**, mirroring
`get_evidence_repository`, `get_evidence_actor_attribution_repository`,
`get_evidence_parcel_existence_port`, `get_principal_tenant_port`, and
`get_evidence_actor_attribution_service` (`backend/app/contexts/evidence/dependencies.py`)
field-for-field, except that every `Depends(get_db_session)` in the five is declared
`Depends(get_db_session, scope="function")` instead. Verified directly (via `id()` comparison across
every provider in the graph, against real Postgres): **exactly one** session instance serves the
whole request when all five declarations share the identical scope — the mutation and its staged
audit event remain on the same session and the same transaction, exactly as `GD-009` Batch 1 requires.
Verified further: the success case produces an independently-durable row and audit event; the
commit-failure case produces a genuine **500**, not a false 200, with the database correctly rolled
back to zero new rows; and `get_db_session`'s existing `HTTPException → commit` branch (the mechanism
protecting, e.g., a revoke-then-reject sequence elsewhere in this codebase) fires unchanged, because
`get_db_session`'s own source code is never edited by this fix — only how it is *declared* as a
dependency, at five new call sites, changes.

**The conflict with `GD-012` §9's literal text, and why it requires this Decision rather than silent
implementation:** `GD-012` §9 states, without qualification, "Application-service invocation:
`Depends(get_evidence_actor_attribution_service)` — the existing, already-wired dependency —
unchanged." `scope` is a property fixed at a `Depends()` call's own point of declaration (confirmed
directly against FastAPI's `Dependant.cache_key`/`computed_scope` implementation, which includes scope
in the dependency-cache key) — there is no supported mechanism by which a router can invoke the
literal, named `get_evidence_actor_attribution_service` callable "unchanged" while also causing its
internal, already-written `Depends(get_db_session)` calls to run at `scope="function"`. The two
requirements are mutually exclusive as `GD-012` §9 is presently worded. Proceeding with the five-
provider fix without this Decision would mean deviating from `GD-012`'s own literal dependency-
invocation clause without Governance authority to do so — precisely the outcome Article XVI §2's
amend-only-by-a-later-named-decision discipline exists to prevent.

**The exception granted:**

The router `backend/app/contexts/evidence/api/attribution_router.py` (`GD-012` §9) may construct
`EvidenceActorAttributionService` via five new, endpoint-local dependency-provider functions — not
via `Depends(get_evidence_actor_attribution_service)` — **if and only if**:

1. each of the five mirrors its corresponding existing provider in `dependencies.py` field-for-field,
   with no behavioral difference other than the `scope` argument on its own `Depends(get_db_session)`
   call;
2. every one of the five declares the identical scope, `"function"`, so that exactly one session
   instance serves the entire request — this Decision does not authorize, and no implementation under
   it may introduce, any configuration in which the mutation and its staged audit event could be
   served by two different sessions;
3. `backend/app/contexts/evidence/dependencies.py` itself is not edited — `get_evidence_repository`,
   `get_evidence_actor_attribution_repository`, `get_evidence_parcel_existence_port`,
   `get_principal_tenant_port`, and `get_evidence_actor_attribution_service` remain exactly as they
   are, at their existing (implicit "request") scope, for every other route that already depends on
   them (`upload_parcel_evidence`, `list_parcel_evidence`, and any future consumer);
4. `app/kernel/uow.py` and `get_db_session`'s own definition are not edited;
5. the five new provider functions live only in the attribution router's own module (or a
   sibling module used only by it) — never imported by, or wired into, any other router.

**Required proof, restated as a mandatory implementation obligation, not merely a drafting-time
finding:** the implementation authorized under this exception must include, in the tracked test
suite (extending `GD-012` §10's already-required real-PostgreSQL tests, items 16–19), a test
demonstrating that a forced final-commit failure on either attribution endpoint produces a non-2xx
response and leaves no attribution row or audit row durable — generalizing this Decision's own
drafting-time proof into permanent, re-runnable evidence, not relying on this document's narrative
alone.

## 4. Second finding and exception — concurrent-correction exception translation

**The finding, established by direct code tracing, not assumed:** `GD-012` §7 and §10 item 16 both
require that the losing request in a concurrent-correction race against the same lineage head receive
"a coherent 4xx response... not a 500." Traced directly: the database-level enforcement of "at most
one row may supersede any given attribution row" is
`uq_evidence_actor_attributions_supersedes_once`, a plain `UNIQUE (supersedes_id)` constraint
(`migrations/versions/0014_evidence_actor_attributions.py`), **not** declared `DEFERRABLE` — Postgres
therefore enforces it immediately, at statement-execution time. `PostgresEvidenceActorAttributionRepository.record()`
(`backend/app/contexts/evidence/adapters/postgres_repositories.py`) calls `self._session.add(model)`
immediately followed by `await self._session.flush()` — meaning a losing concurrent INSERT's
uniqueness violation fires **inside** `EvidenceActorAttributionService.correct_attribution`'s own call
stack, mid-request, not deferred to the final commit. `correct_attribution` catches only `ValueError`
(from domain construction, mapped to 400) — it does not catch `sqlalchemy.exc.IntegrityError` or any
database-level exception.

**With no router-level translation at all** (the true "as-is" baseline, before any exception handling
is added), the raw `IntegrityError` propagates as an ordinary `Exception` all the way to
`get_db_session`, correctly reaching its `except Exception: await session.rollback(); raise` branch —
`get_db_session`'s own generic-exception branch genuinely does perform the rollback in *this*
scenario — but is then converted by Starlette's default exception-handling middleware into a
**generic HTTP 500**, not the coherent 4xx `GD-012` explicitly requires. This "as-is" description does
**not** describe what happens once the router-level translation this Decision authorizes is applied —
that is a materially different code path, addressed precisely below.

**The exception granted:**

The router `backend/app/contexts/evidence/api/attribution_router.py` may catch
`sqlalchemy.exc.IntegrityError` raised specifically by a violation of the
`uq_evidence_actor_attributions_supersedes_once` constraint, arising from its own call to
`EvidenceActorAttributionService.correct_attribution`, and translate it into
`HTTPException(status_code=409, ...)` — **if and only if**:

1. the translation is scoped to this one, specifically named constraint — it must not become a
   general "catch any database error and return 409" handler, which would risk masking genuinely
   unexpected failures (including the commit-boundary failure §3 addresses, which must continue to
   surface as a 5xx) behind a misleadingly specific client-error status. **Catching the exception
   class alone is not sufficient**: `sqlalchemy.exc.IntegrityError` also wraps the unrelated
   `ck_evidence_actor_attributions_no_self_supersede` `CHECK` constraint (Postgres places both
   `UNIQUE` and `CHECK` violations in the same SQLSTATE class, 23), so a bare
   `except IntegrityError` would also — incorrectly — translate a self-supersession violation into a
   409. **The translation must check both of the following structured diagnostic fields — never a
   parsed, human-readable exception message — before translating to 409**:
   - the driver-reported SQLSTATE equals exactly `23505` (`unique_violation`), distinguishing it from
     `23514` (`check_violation`, the self-supersession `CHECK`'s own SQLSTATE) and every other class-23
     member; and
   - the driver-reported constraint name equals exactly `uq_evidence_actor_attributions_supersedes_once`.

     Both fields are confirmed, by direct inspection of the installed `sqlalchemy`/`asyncpg` versions
     against a real PostgreSQL unique-constraint violation, to be exposed as structured attributes on
     the underlying driver exception — `sqlalchemy.exc.IntegrityError.orig.__cause__.sqlstate` and
     `...__cause__.constraint_name` (asyncpg's own `UniqueViolationError`/`CheckViolationError`
     surface both directly, sourced from PostgreSQL's own wire-protocol error-response fields, not
     from string-parsing the error's message text) — so this requirement is achievable exactly as
     stated, not aspirational.

   Only when **both** conditions hold may the router translate to 409; any other `IntegrityError` —
   including the self-supersession `CHECK`, which the domain layer's own
   `EvidenceActorAttribution.new` treats as structurally unreachable in practice but which must not be
   silently misclassified if it is ever reached — must continue to propagate unhandled, as a 5xx;
2. no change is made to `EvidenceActorAttributionService.correct_attribution`, `_resolve_active_head`,
   `PostgresEvidenceActorAttributionRepository.record`, or any other application-service or
   repository-adapter code — the translation occurs entirely in the new router module, around an
   unmodified call to the unmodified service method;
3. no new database constraint, trigger, retry mechanism, locking strategy, or transaction-isolation
   change is introduced — the existing `UNIQUE (supersedes_id)` constraint remains the sole
   enforcement mechanism; this Decision authorizes only recognizing and translating its failure mode,
   never altering it.

**What actually happens to the session once the router raises `HTTPException(409)` — stated precisely,
not assumed.** `get_db_session` has two distinct branches, and they are not interchangeable:
`except HTTPException: await session.commit(); raise` and `except Exception: await session.rollback();
raise`. Because the router's translation replaces the original `IntegrityError` with an
`HTTPException` before it reaches `get_db_session`, **the `HTTPException` branch runs — `commit()`,
not `rollback()`** — not the generic-exception branch the "as-is" paragraph above describes. This
Decision does **not** rely on, and does not claim, that `get_db_session`'s generic-exception rollback
branch is what keeps the failed correction from becoming durable; that branch does not execute in this
path. Verified directly instead, against a real PostgreSQL database, instrumenting
`AsyncSession.commit`/`.rollback` to confirm which is actually called: `commit()` is called, completes
without raising a second exception, and — checked independently, via a separate connection, after the
response — the colliding row is **not** persisted. This holds for a reason external to
`get_db_session`'s own branching logic: the failed `flush()` already left the underlying PostgreSQL
transaction in an aborted state, and PostgreSQL discards an aborted transaction's work regardless of
whether the client subsequently requests `COMMIT` or `ROLLBACK` on it — a `COMMIT` sent to an aborted
transaction cannot make its failed statement durable. **Raising `HTTPException(409)` is therefore safe
in practice, but not because doing so is guaranteed to trigger a rollback** — no code path in this
exception guarantees that, and none is authorized to add one. The safety property this Decision
actually relies on, and requires proof of (per the mandatory test below), is the *externally observable
outcome* — no phantom row, no phantom audit event, a coherent 409 — not the specific internal
branch name that produces it.

**Required proof, restated as a mandatory implementation obligation:** the implementation must include
the real-PostgreSQL concurrent-correction test `GD-012` §10 item 16 already requires, and that test
must assert, against real PostgreSQL and independently of the HTTP status code alone: (a) the losing
request's status code is specifically the 409 this exception authorizes (or whichever single,
documented 4xx code the implementation settles on, provided it is used consistently and disclosed in
the endpoint's own API documentation) — not merely "some 4xx," to keep the ratified contract precise;
and (b) **no attribution row and no successful-mutation audit event was left durable for the losing
request specifically**, checked via a query independent of the request's own session — proving the
externally observable safety property the preceding paragraph describes, not merely inferring it from
the status code. The implementation must additionally include a hermetic or real-Postgres test
confirming that an `IntegrityError` arising from a constraint other than
`uq_evidence_actor_attributions_supersedes_once` is **not** translated to 409 — i.e., that condition
1's constraint-identity check is exercised, not merely present in the code as untested dead logic.

## 5. Everything else in GD-012 remains unamended

This Decision modifies `GD-012` §9 solely by adding the two narrowly bounded exceptions above,
alongside its existing `_verify_actor_reference` message-normalization exception. **All other GD-012
provisions remain in force, unaffected and unamended**, restated for the avoidance of doubt:

- §4's two-endpoint scope (nothing broader is authorized by this Decision);
- §5's authorization reuse (`_can_mutate`, `require_role(*PARCEL_REGISTRANT_ROLES)`) — untouched;
- §6's response-contract narrowness, including the §6.4 `actor_principal_id` message-normalization
  exception — untouched, and unrelated to either exception this Decision grants;
- §7's append-only correction semantics — untouched; this Decision only supplies the missing HTTP-
  status translation for an already-described race, never a new correction mechanism;
- §8's audit transaction integrity — reinforced, not altered: the whole purpose of §3's exception is
  to make the HTTP-visible outcome accurately reflect the transaction-coupling §8 already requires;
- §10's required validation — extended, per §3 and §4 above, never relaxed;
- §11's exclusion list (no migration, no dependency, no audit-kernel change, no new tenant type, no
  authorization broadening) — fully in force; neither exception touches any item on that list;
- §12's non-adjudication language, §13's programme exclusions — untouched.

## 6. No unauthorized architecture expansion

Restated, because both exceptions above are narrow additions to `GD-012`'s existing boundary, not a
reopening of it: this Decision does not authorize, and no implementation under it may introduce, any
of the items `GD-012` §11 already excludes, nor:

- any change to `app/kernel/uow.py` or `get_db_session`'s own definition;
- any change to `backend/app/contexts/evidence/dependencies.py`'s existing five provider functions;
- any change to the scope of any dependency used by any route other than the two `GD-012` authorizes;
- any general exception-translation middleware, error-handling framework, or retry/backoff mechanism
  beyond the one specifically named constraint in §4;
- any authorization, tenant-membership, or audit-transaction logic change beyond what `GD-012` §9's
  existing `_verify_actor_reference` exception already authorizes.

**Stop-and-return condition, restated from `GD-012` §11 in identical form:** if implementation reality
proves either exception insufficient, or reveals that achieving the required properties needs a
change to `dependencies.py`, `uow.py`, a new database constraint, or any other item this section
excludes, the implementing engineer must stop and return exactly:

**`GD-013 BLOCKED — [DEPENDENCY-GRAPH | UOW | CONSTRAINT] AUTHORITY REQUIRED`**

rather than improvise a workaround inside this Decision's own authority.

## 7. Article XVI entry

The following text is inserted into `docs/LV-000-constitution.md`'s Article XVI Log as part of this
ratification (a separate edit to that file, not by this document itself, and not performed by this
draft):

> **GD-013 — GD-012 Commit-Boundary and Concurrent-Correction Exception Authorization.** *(Ratified 19
> September 2026.)* Operative authority: **Article XVI §2** — GD-013 is a later numbered decision that
> explicitly names `docs/GD-012-evidence-actor-attribution-http-implementation-authorization.md` to
> grant two narrow, additional implementation-mechanism exceptions its own text did not anticipate; it
> is not proposed under Article XIV and does not amend this Constitution.
>
> **Decision.** `GD-012`'s two authorized attribution endpoints may (1) construct
> `EvidenceActorAttributionService` via five new, endpoint-local dependency-provider functions
> declaring `Depends(get_db_session, scope="function")` in place of `GD-012` §9's literal
> `Depends(get_evidence_actor_attribution_service)` clause — provided all five share identical scope
> (exactly one session per request), and neither `backend/app/contexts/evidence/dependencies.py` nor
> `app/kernel/uow.py` is edited — closing a proven, pre-existing framework-level defect under which a
> final commit failure could otherwise reach the client as a false HTTP success; and (2) catch a
> violation of the specifically named `uq_evidence_actor_attributions_supersedes_once` database
> constraint and translate it to `HTTPException(409)`, entirely within the new router module, with no
> change to the application service or repository adapter — supplying the coherent 4xx `GD-012` §7/§10
> already required for a losing concurrent correction but did not itself make achievable.
>
> **Scope excluded — no retroactive expansion.** This decision does not authorise any change to
> `dependencies.py`'s five existing provider functions, `get_db_session`'s own definition, any
> unrelated route's dependency scope, any general database-exception-translation mechanism beyond the
> one named constraint, or anything `GD-012` §4/§5/§6/§9/§11/§13 already exclude. All other `GD-012`
> provisions remain in force, unaffected and unamended.

## Approval Gate

This Governance Decision is **ACCEPTED**, per the Ratification Record above. Acceptance authorizes
only the two narrowly bounded exceptions to `GD-012` described in §3 and §4 — never anything broader.

**Explicit exclusions.** Ratification does not authorize: any change to
`backend/app/contexts/evidence/dependencies.py`'s existing provider functions or `app/kernel/uow.py`;
any change to the dependency scope of any route other than the two `GD-012` authorizes; any general
exception-translation mechanism beyond the one specifically named constraint in §4; any new database
constraint, trigger, or transaction-isolation change; any authorization, tenant, or audit-transaction
logic change beyond `GD-012` §9's existing `_verify_actor_reference` exception; or any of the
programmes or endpoints `GD-012` §4/§9/§11/§13 already exclude.

**Implementation process, restated.** Ratification of this Decision authorizes drafting and building
the implementation described in §3–§4; it does not itself constitute implementation, testing, review,
merge, a Git commit, push, pull request, or merge — every one of those remains a separate, subsequent
authorization, exactly as this Decision's own Status line states. The eventual implementation must
still satisfy `GD-012` §14's own five-step sequence (implement, test, formally review, squash merge,
post-merge verify) before either endpoint may be considered complete.

See the companion readiness report, `docs/GD-013_READINESS_REPORT.md`, preserved as the point-in-time
pre-ratification readiness record, and the subsequent formal Governance review and textual-remediation
verification that preceded ratification.
