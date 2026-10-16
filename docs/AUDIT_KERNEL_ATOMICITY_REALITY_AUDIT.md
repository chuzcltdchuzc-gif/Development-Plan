# LandVault Audit Kernel Atomicity — Reality Audit

**Type:** Governance reality audit and architecture assessment. Read-only — no code, migration, or
document other than this one was touched. Produced against `main` at
`edbc4283005e86f5068de4014bedc8407ac5f61d` (ADR-028 Evidence Attribution Foundation, post-merge
verified).

**Date:** 2026-09-10

## Executive conclusion

The audit kernel's independent-commit design is **real, universal across every bounded context,
and deliberate** — not an oversight. It was arrived at after a live-Postgres finding that the
alternative (binding audit writes to the caller's own request session) silently discarded exactly
the deny/failure audit entries a real audit trail most needs to keep, and separately broke RLS
tenant-scoping. That trade-off is sound as far as it goes.

But the trade-off has a real, reproducible cost this document reproduces directly: **an audit
entry can durably reference a business mutation that never commits.** This was previously named
and explicitly disclaimed as untested in `tests/live/test_registry_history_rollback_live.py`'s own
docstring ("this test does NOT cover" that scenario). This audit ran that exact scenario against a
real Postgres database and confirmed it: the audit entry persists, the row it describes does not.

More consequentially: `docs/adr/ADR-007-audit-trail-evidence-model.md`, **Accepted**, Decision 1,
states explicitly that "every domain event across every bounded context is written atomically with
the state change that produced it." The implementation does not do this, by deliberate design, for
a documented and defensible reason — but that departure from an Accepted ADR's literal decision
text has never been reconciled at the governance level. This is the repository's own established
pattern for exactly this situation (see GD-006, GD-007): an implementation finding diverged from
what was written, discovered after the fact, requiring regularisation — not a silent patch, and not
"no ADR governs this."

**AUDIT ATOMICITY DEFECT CONFIRMED — ARCHITECTURE DECISION REQUIRED.**

## 1. Baseline verified

- `origin/main` SHA: `edbc4283005e86f5068de4014bedc8407ac5f61d`. Working tree clean.
- `docs/adr/ADR-028-evidence-actor-and-commissioning-provenance.md`: `ACCEPTED — 2026-09-10 ... IN
  FORCE`.
- ADR-028 foundation present: `backend/app/contexts/evidence/{domain,application}/attribution*.py`,
  `backend/migrations/versions/0014_evidence_actor_attributions.py`, associated tests — all
  confirmed on disk.
- `docs/adr/ADR-026-evidence-domain-model.md`: Accepted.
- `docs/adr/ADR-027-supabase-storage-authorization-and-tenant-isolation.md`: `ACCEPTED — 2026-09-06`.
- `docs/GD-008-surveyor-network-phase-0-principles-and-authorization-boundary.md`: `ACCEPTED —
  2026-09-08 ... IN FORCE`.
- Migration head: `0014_evidence_actor_attributions.py` (follows `0013`).
- Audit kernel implementation read directly: `backend/app/kernel/audit.py`,
  `backend/app/kernel/audit_postgres.py`, `backend/app/kernel/uow.py`, `backend/app/main.py`. Not
  inferred from the prior PR #27 report — re-read fresh for this audit.

## 2. Complete audit-call inventory

Every call site was found with `grep -rn "await audit(" app/`. **55 call sites**, across every
bounded context that mutates state:

| Context | File | Call count |
|---|---|---|
| Evidence | `application/evidence_service.py` | 8 |
| Evidence (ADR-028) | `application/attribution_service.py` | 2 |
| Identity | `application/admin_service.py` | 13 |
| Identity | `application/auth_service.py` | 12 |
| Registry | `application/parcel_service.py` | 7 |
| Spatial | `application/spatial_service.py` | 2 |
| Kernel | `authorization/pep.py` (PDP/PEP deny audits) | 2 |

All 55 call sites use the **same** `app.kernel.audit.audit()` function, which resolves to the
**same** store at runtime (see §3). There is no context-specific variation — the atomicity
characteristic is platform-wide, not patchy. Confirmed by reading every call site: **none** wraps
its `await audit(...)` call in a `try`/`except` that would swallow an audit failure — the one
`except Exception` found near an audit call (`auth_service.py` line ~553) guards a *different*,
preceding statement (`self.users.update(...)`, an explicitly best-effort `last_login` stamp), not
the audit call itself.

## 3. The actual transaction model — proven, not inferred

`app/kernel/uow.py`'s own docstring states directly: *"Deliberately does NOT bind this session as
the audit store... `audit()` always writes through the eager, independently-committing store
instead... confirmed against a live Postgres that binding the per-request session caused a second
bug on top of the one it fixed."*

`app/main.py` confirms this is what's actually wired in production:

```python
configure_eager_fallback(EagerPostgresAuditStore(session_factory))
```

`configure_audit_store` (the per-request `ContextVar`) is **never called in production code** —
only in test fixtures, to bind an in-memory fake. Every real `audit()` call in production resolves
to `_eager_fallback`, i.e. `EagerPostgresAuditStore`, whose `append()` opens a **brand-new session**
via `session_factory()`, adds the row, and calls `PostgresAuditStore.append()`, whose own comment
states plainly: *"Commits immediately — NOT just flush()... whatever the caller does next in the
same session is unaffected."*

**Precise statement of the mechanism:** audit writes use **a separate session and a separate,
independently-committed transaction** — never the caller's own Unit-of-Work session. Because this
separate commit happens synchronously, mid-request, and the caller's own business-mutation commit
happens only when the request's `get_db_session` generator resumes after the route handler returns,
**the audit entry for a given mutation almost always commits to disk before the business row that
mutation describes does.** This is the opposite of "persist first, audit as an afterthought" — in
terms of what actually reaches durable storage first, audit wins the race, every time, by
construction.

`get_db_session` (`app/kernel/uow.py`) also confirms: a raised `HTTPException` (a deliberate
rejection — 401/403/409) is **committed**, not rolled back — specifically so that a side effect
performed before the raise (e.g. `AuthService.refresh()`'s revoke-all-active-sessions-then-401 for
detected token-replay) survives. Only a genuinely unexpected exception triggers
`session.rollback()`.

## 4. Live failure-mode reproduction

### Case A — business mutation succeeds, audit fails

**Not independently reproduced as a live fault-injection; excluded by structural proof from the
exhaustive call-site review in §2.** Every audit() call is unguarded. If `audit()` raises (its own
store failing), the exception propagates unhandled up through the calling service method to
`get_db_session`'s `except Exception: await session.rollback(); raise` — which rolls back the
business mutation's own flushed-but-uncommitted row in the same request. A silently-persisted,
unaudited mutation caused by *this specific* failure ordering therefore cannot occur through the
platform's actual, universal call pattern (flush business row → call audit() unguarded → later,
final commit). This is a structural conclusion from code, not a live-tested one; see §17 for the
distinction this draws in confidence level.

### Case B — audit succeeds, business transaction later fails and rolls back

**Reproduced directly against a real, throwaway Postgres database.** Method: drove
`app.kernel.uow.get_db_session` exactly as `tests/live/test_registry_history_rollback_live.py`
already does, but — unlike that test, which explicitly documents injecting its fault *before* any
`audit()` call specifically to avoid this scenario — this audit injected the fault *after* a real
`audit()` call had already run and committed.

Steps: created a real `Parcel` via `PostgresParcelRepository.add()` (flushed, not committed) →
called the real `audit()` function with `action="registry.parcel.created"`, `resource_id=parcel_id`
→ confirmed the entry committed independently → threw a simulated fault into the still-open
generator (`agen.athrow(...)`), forcing `get_db_session`'s rollback path.

**Result, queried on a fresh connection afterward:**

```
[result] parcel row persisted: False
[result] audit_log entry persisted: True
CONFIRMED: orphan audit_log entry references a parcel mutation that never committed (Case B reproduced)
```

An `audit_log` row exists, permanently, hash-chained into the tamper-evident log, asserting
`registry.parcel.created` / `decision=PERMIT` for a `parcel_id` that **does not and never did
exist** in `parcels`.

### Case C — request crashes after audit commit

Not separately live-tested (crashing a real process mid-request is impractical to stage safely and
reliably in this environment). **Structurally identical to Case B**: a crashed process's
uncommitted transaction is discarded by PostgreSQL when the connection drops, regardless of whether
the client disappeared via an exception or a hard crash. The audit entry, already durably committed
via its own separate connection before the crash, is unaffected either way. No new mechanism is
introduced by a crash versus a raised exception; the same orphan-audit outcome results.

### Case D — concurrent mutations, audit ordering

**Not empirically reproduced in this audit — flagged as a distinct, narrower, unproven concern,
not folded into the atomicity conclusion above.** Structural observation: `audit()` computes
`prev_hash` from `store.last_hash()` (an `ORDER BY created_at DESC LIMIT 1` query) and a
client-side `created_at` timestamp, then commits via a fresh, independent transaction per call —
there is no locking or serialization between the read of `last_hash()` and the eventual `INSERT`.
Two genuinely concurrent `audit()` calls could both read the same `prev_hash` before either
commits, and both attempt to chain onto it. Whether Postgres's own transaction isolation (default
`READ COMMITTED`) permits both inserts to succeed with the same `prev_hash` value (breaking the
intended one-successor-per-hash chain shape) was not tested here. This is a *plausible* additional
integrity question about the hash chain's linearizability under real concurrency, separate from the
atomicity question this task was scoped to, and is named here as **requiring its own dedicated
testing if pursued** — not asserted as proven.

## 5. Evidence upload special case

`EvidenceService.upload_evidence` (read directly, `application/evidence_service.py`) sequences:
`StoragePort.put()` (external, real object storage) → `EvidenceRecord` row added + flushed (not
committed) → `audit("evidence.uploaded")` (commits independently, immediately) → independent
read-back re-hash against Storage → `mark_hashed()` flushed → `audit("evidence.hashed")` (commits
independently, immediately) → return.

Failure-window analysis, building on ADR-026's own already-accepted residual risk (`docs/adr/
ADR-026-evidence-domain-model.md`, "Transaction boundaries": *"a storage write that succeeds,
followed by a database write that then fails or rolls back, can leave an orphaned object in storage
with no `EvidenceRecord` referencing it"* — accepted as a housekeeping concern, not a defect):

| Failure point | Storage | EvidenceRecord row | Audit entry |
|---|---|---|---|
| After Storage write, before DB flush | Object exists (orphaned; already accepted) | Never created | Never called; none exists |
| After DB flush, before first `audit()` | Object exists | Rolled back on any later failure | Never called for this attempt |
| After first `audit()`, before final commit | Object exists | **Rolled back** — Case B applies | **Persists**, referencing a row that never existed |
| After both audits and final commit, before response | Object exists | Persists | Persists — consistent; only the HTTP response to the caller is uncertain, not the durable state |

The third row is the compounded case this audit is most concerned with for Evidence specifically:
an *already-accepted* orphaned-Storage-object risk can now co-occur with a *newly reproduced*
orphaned-audit-entry risk, both pointing at an `EvidenceRecord` that was never durably created. This
is worse, in combination, than either risk considered alone — though each half was independently
already known or now proven, not a new mechanism.

## 6. ADR-028 attribution special case

`EvidenceActorAttributionService.record_attribution`/`correct_attribution` (read directly,
`application/attribution_service.py`) follow the identical shape: authorize → validate → construct
→ `attributions.record()` (flush, not commit) → `audit("evidence.actor_attribution.recorded"/
"...corrected")` (commits independently, immediately) → return.

- **Persisted attribution with no audit**: excluded by the same structural argument as Case A — the
  audit call is unguarded and precedes the method's return; a failure there aborts the request and
  rolls back the just-flushed attribution row via the same `get_db_session` path.
- **Audit for an attribution that never commits**: **possible, by the same Case B mechanism just
  reproduced** — no code-level difference exists between this path and the Registry path just
  tested live.
- **Correction audit whose successor row rolls back**: same mechanism, applied to
  `correct_attribution` specifically — the `supersedes_id`-carrying row could be audited as
  recorded while never actually landing in `evidence_actor_attributions`.
- **Misleading audit ordering**: no evidence found beyond the general Case D concern (§4); nothing
  specific to attribution's two action names introduces a new ordering risk.

**Would HTTP API exposure materially increase operational risk?** It would increase *frequency of
exposure* — more real network traffic means more genuine chances for a mid-request failure between
the audit call and the final commit (client disconnects, timeouts, transient DB issues) — but it
introduces **no new category of risk**: every other mutation endpoint already live in production
(Registry parcel creation, Identity admin actions, Spatial mutations) already carries the identical
risk profile today, unblocked. Treating this one feature's exposure differently from everything
already shipped would be inconsistent with how the platform already operates.

## 7. The required invariant

The task's candidate wording — *"the business mutation and its audit record must commit or roll
back as one logical transaction unless an explicitly governed exception applies"* — is not
automatically adopted here; it is tested against what governance has actually said:

- **`docs/adr/ADR-007-audit-trail-evidence-model.md`, Decision 1 (Accepted)**: *"every domain event
  across every bounded context is written atomically with the state change that produced it."*
  This is a stronger, unconditional statement — no "unless governed exception" clause exists in the
  ADR's own text.
- **LV-000 v1.8 Article VIII §3**: *"Every state change writes to the audit chain, and every record
  that a change occurred carries a resolvable reference to its audit entry."* This is a *weaker*
  requirement, phrased in the direction of "the mutated row must resolve to a real audit entry,"
  which the current implementation satisfies when a mutation succeeds — the article is silent on
  whether the reverse (an audit entry resolving to a real mutation) must also hold, and does not use
  the word "atomically."

These two governing texts are not in agreement with each other, and the implementation matches
neither exactly: it satisfies Article VIII §3's literal direction (a committed row's `audit_ref`
does resolve), while contradicting ADR-007 Decision 1's literal "atomically" requirement. **The
correct invariant is therefore not determinable from documentation alone — it requires a Governance
decision to state which of these two already-governed positions is authoritative**, or to adopt a
third, reconciled wording (see §9's alternatives).

## 8. Audit semantics — what is claimed versus what exists

- **Transactional audit** (business change and its record commit/rollback together): **not what
  exists**, contrary to ADR-007 Decision 1's literal text.
- **Eventual audit** (the record will exist soon after, with a bounded but nonzero window where it
  might not, or might wrongly claim something that then doesn't happen): **this is what actually
  exists** — not named as such anywhere in the codebase or governance documents.
- **External immutable audit** (a separate, tamper-evident system of record, deliberately decoupled
  from the business database's own transactions, by design, with reconciliation as a first-class
  concept): **closer to what exists in mechanism** (a genuinely separate, hash-chained, append-only
  store), but reconciliation against orphan entries is not implemented, tested (until this audit),
  or governed.
- **Application logging** (best-effort, not treated as a source of truth): **not what this claims
  to be** — `verify_chain()`'s tamper-evidence machinery and Article VIII §3's constitutional
  status both treat `audit_log` as authoritative, load-bearing evidence, not disposable logging.

**The word "immutable" is used carefully in the existing docstrings** (`audit.py`: "Append-only,
hash-chained audit log" — a claim about *tamper-evidence*, i.e. nobody can alter an entry
undetected) and this claim **is** actually supported by the implementation (`verify_chain()`
genuinely recomputes hashes). What is *not* supported, and *is* implicitly assumed by a casual
reader in several places (see §18), is that an existing, tamper-evident entry also implies the
event it describes durably happened. Those are two different guarantees, and only the first is
actually delivered today.

## 9. Architecture alternatives

| | A — Shared transaction | B — Transactional outbox | C — Retain, formally accept | D — Reconciliation sweep (additive to C) |
|---|---|---|---|---|
| Atomicity | True atomicity | True atomicity for the *outbox row*; a separate worker then materializes the audit-log entry, itself eventually-consistent | None — the current gap remains, but *named* and *bounded* by policy | None fixed; detects and flags drift after the fact |
| Failure behavior | Deny/failure audits lost on rollback (the exact regression already found and reverted once) | Deny/failure audits preserved (outbox row commits with whatever transaction recorded the denial) | Unchanged from today | Unchanged from today; adds visibility |
| Implementation complexity | Low (revert `uow.py`'s deliberate choice) — but reintroduces a previously-found, previously-fixed bug | Moderate–high: new table, new worker/poller, at-least-once delivery semantics, idempotency handling | None | Low–moderate: a scheduled job comparing `audit_log` resource references against source tables |
| FastAPI compatibility | Native | Requires a background worker (Celery/APScheduler/etc. — a new runtime dependency this audit does not authorize) | Native | Native, if built from existing scheduling primitives already in the platform |
| Storage-side-effect compatibility | Does not help Evidence's Storage-orphan case at all — Storage is external, never inside any DB transaction | Same limitation — outbox atomicity is a DB-only guarantee, doesn't extend to Storage | Same as today; ADR-026 already accepts the Storage half of this | Could detect Storage-orphan-plus-audit-orphan co-occurrence, at least after the fact |
| Testability | Straightforward, but the RLS-scoping bug already found must be solved simultaneously | Requires testing outbox-worker crash/retry semantics — a materially larger test surface | Straightforward — document and test the *accepted* gap, exactly as this audit's live tests now do | Straightforward |
| Tenant isolation | Must re-solve the `is_local=true` RLS-scoping conflict `uow.py` already found and fixed once | Unaffected — outbox row uses the same session as the business mutation, same RLS scope | Unaffected | Unaffected |
| Audit integrity for denials | **Regresses** — the exact bug this design was built to avoid | Preserved | Preserved (unchanged) | Preserved; adds detection |
| Future background jobs | N/A | Would be the platform's *first* background-job infrastructure — a genuinely new architectural commitment | N/A | Could reuse whatever scheduling mechanism, if any, the platform eventually adopts for other reasons |
| Future WORM/immutable archive | Unaffected | Outbox pattern composes well with an eventual real event-sourcing/WORM archive, if one is ever built | Unaffected | Unaffected |
| Migration impact | None | New `audit_outbox` (or similar) table + migration | None | Possibly a small table to track known-reconciled entries; optional |

**Alternative A is rejected outright**: it is not a forward step, it is a reversion to a
configuration this codebase already tried and found strictly worse (losing deny-audit entries is a
more severe defect than an orphan-audit entry, since it hides that access control worked instead of
merely mis-timestamping a business fact).

**Alternative B (transactional outbox) is not automatically superior**, per the task's own
instruction, and is not recommended as the default here: it requires a new background-worker
runtime component this codebase has never had (Engineering Rule #5 territory — a new dependency
requiring explicit human approval), and it does not solve the Evidence/Storage half of the problem
at all, since Storage is external to any database transaction regardless of outbox design. It is
the architecturally "correct" answer to the *pure database* half of ADR-007 Decision 1's stated
ambition, and is worth naming as the long-term direction ADR-007 itself already pointed at — but
adopting it now, for this narrow problem, would be disproportionate.

**Alternative C (retain, formally accept) plus D (a lightweight reconciliation sweep) is the
recommended direction**, elaborated in §14.

## 10. Governance/ADR authority

**This is already explicitly governed — by an Accepted ADR whose literal decision text the current
implementation does not satisfy.** `docs/adr/ADR-007-audit-trail-evidence-model.md` Decision 1 is
unambiguous: "written atomically with the state change." No later ADR, Governance Decision, or
constitutional amendment revises, qualifies, or supersedes that sentence. The divergence exists
only in code-level documentation (`app/kernel/uow.py`'s docstring, `app/kernel/audit_postgres.py`'s
comments) — a real, well-reasoned engineering rationale, but never elevated to a governance
instrument.

This repository has an established, named mechanism for exactly this situation: **GD-006**
("Regularisation of post-ratification factual observations") and **GD-007** ("IMVP-5 Sequencing
Exception... qualification of GD-004") both exist specifically to reconcile a discovered
implementation/documentation divergence after the fact, without treating it as an unrecorded
edit or a silent bug fix. Correcting the audit-atomicity gap should follow that same pattern: either
a new ADR that formally revises ADR-007 Decision 1's "atomically" language to the reconciled
invariant chosen from §9, or a Governance Decision that qualifies Decision 1 the way GD-007 qualified
GD-004 — **not** a defect correction merged without governance review, and **not** silence.

## 11. Scope of impact

| Mutation path | Classification |
|---|---|
| Registry (`parcel_service.py`, all 7 audit calls) | NON-ATOMIC TODAY (Case B directly reproduced against this exact context) |
| Evidence upload (`evidence_service.py`) | NON-ATOMIC TODAY + EXTERNAL-SIDE-EFFECT COMPLICATED (Storage) |
| Evidence attribution — ADR-028 (`attribution_service.py`) | NON-ATOMIC TODAY (identical mechanism to Registry; not independently live-tested, but no code-level difference exists) |
| Identity admin (`admin_service.py`) | NON-ATOMIC TODAY (same mechanism; not independently live-tested) |
| Identity auth (`auth_service.py`) | NON-ATOMIC TODAY, and in this one context the current design is *specifically correct* — the replay-detection revoke-then-401 case this design was built to preserve |
| Spatial (`spatial_service.py`) | NON-ATOMIC TODAY (same mechanism; not independently live-tested) |
| PDP/PEP deny audits (`pep.py`) | NON-ATOMIC TODAY, and here the "eager, independent" design is again specifically load-bearing (a 403 must be recorded even though nothing else in that request commits) |
| Audit chain linearizability under concurrency | UNKNOWN / NEEDS MORE PROOF (§4 Case D) |

**100% of state-changing, audited mutation paths across every bounded context share the identical
non-atomic characteristic.** This is not a localized defect in one context; it is a single,
platform-wide architectural property, currently undocumented at the governance level.

## 12. Security and compliance red-team

| Risk | Classification |
|---|---|
| Orphan audit entries (proven, §4 Case B) | **Integrity defect** — the audit chain can assert something that did not durably happen |
| Unaudited committed mutations | Excluded by structural proof (§4 Case A) — not a live risk given the current call pattern |
| Misleading chronology | **Integrity defect**, mild — audit timestamps generally *precede* the business commit they describe, the reverse of naive intuition; not itself dangerous once understood, but easy to misread |
| Duplicate audit entries | Not found; `entry_id` is caller-supplied or UUID4-generated per call, no retry-without-idempotency-key path identified in the 55 call sites reviewed |
| Retry behavior | Not separately tested; a caller-level retry after a failed request could, in principle, produce two audit entries for what the caller experienced as one logical attempt — flagged as **UNKNOWN**, not proven either way |
| Request replay | Out of scope for this audit — a distinct concern from transaction atomicity, already addressed by session/token replay detection (`auth_service.py`), unaffected by this finding |
| Tenant mismatch | Not found — `audit_log`'s own migration grants unconditional `SELECT`/`INSERT` (no RLS predicate keyed on tenant), and every observed payload's `tenant_id` is sourced from the caller's own already-authorized `ExecutionContext`/mutation, not independently verified against anything cross-tenant |
| Actor mismatch | Not found — `ctx.principal_id` is read from `current_context()` at the moment of the call, consistent with the authenticated caller |
| Audit entry committed for a denied mutation | **This is intentional and correct**, not a defect — it is precisely the guarantee the "eager, independent" design exists to provide (a 403 must be recorded even when everything else rolls back) |
| Audit failure hidden from caller | Excluded — an audit-store failure is unguarded and propagates as a request failure (§4 Case A reasoning); the caller sees the failure, it is not swallowed |
| Audit database outage | Not tested; structurally, an outage would make every `audit()` call fail, which (per the unguarded-call-site finding) would fail every mutation request platform-wide, fail-closed rather than fail-open — a reasonable posture, but the resulting full-platform unavailability is itself worth naming as an operational (not security) consideration |
| Storage side effect without matching audit | Not found in isolation; the compounded Evidence case (§5) is a genuine additional finding, but always co-occurs with an already-accepted Storage-orphan risk, not a new independent one |

**Overall classification: an integrity defect, not a security vulnerability.** No path was found
by which this gap grants unauthorized access, discloses cross-tenant data, or lets an unauthorized
mutation persist unaudited. It is, however, a **compliance/governance risk**: a tamper-evident log
that can assert a false positive (an action that did not durably happen) undermines the specific
claim Article VIII §3 and ADR-007 exist to support, and it currently exists without any governance
instrument acknowledging it.

## 13. Not Event Sourcing

This audit deliberately does not recommend, and this report does not require, aggregate
reconstruction from events, a generic event bus, Kafka, background-job infrastructure, or a
distributed-saga/CQRS framework. ADR-007 Decision 1's own text *did* originally reach for something
in that direction ("event sourcing... published for downstream subscribers... Trust Engine,
Knowledge Graph, notifications") — none of that was ever built, and this audit found no repository
evidence that it needs to be, to close the specific atomicity gap identified here. The minimum
remediation in §14 is deliberately much smaller than that original ambition.

## 14. Minimum viable correction

- **Can `audit()` accept/use the caller's existing database session?** Yes, mechanically — but
  doing so as the *default*, unconditionally, is exactly the change `uow.py`'s own history already
  shows fails for deny/failure audits and RLS scoping. Any shared-session approach must preserve
  those two specific properties (denial audits survive a rollback; RLS session variables are not
  disturbed by an intermediate commit), which the current design achieves precisely by *not*
  sharing the session.
- **Can callers stage audit rows in the same transaction, for the success-path calls only?** This is
  the more promising direction: a caller could pass an explicit flag or a distinct
  `audit_with_session(session, ...)` variant for calls that are *only* ever reached after a
  mutation that is about to commit in the same transaction anyway (e.g. `evidence.hashed`,
  `evidence.actor_attribution.recorded` on the success path) — leaving the existing eager/
  independent path for deny/failure audits, which must keep their current behavior. This is a
  targeted, dual-path change, not a wholesale reversal.
- **Which call sites would change?** Only success-path audits that immediately follow a flush that
  will commit in the same request — a minority of the 55 call sites; every deny/failure audit
  (`pep.py`, the `*_denied`/`*_replay_detected` actions across `auth_service.py`/
  `admin_service.py`) must keep the current eager, independent path unconditionally.
- **Would this break audit visibility or existing tests?** `verify_chain()`'s hash-chain logic is
  agnostic to which session wrote a row; no break expected there. Tests that assert "no orphan audit
  entry after a fault before commit" (already passing) would be unaffected; a new test proving "no
  orphan entry after a fault *following* a shared-transaction audit call" would need to be added and
  would be expected to newly pass.
- **Would external Storage workflows require compensation rather than pure DB atomicity?** Yes,
  unconditionally — Storage is never inside any database transaction, for any of the alternatives in
  §9. ADR-026's already-accepted orphaned-storage-object risk is not solved by any audit-transaction
  change; it would need its own, separately-governed garbage-collection mechanism, exactly as
  ADR-026 already named and deferred.
- **New runtime dependency?** None required for the dual-path minimum correction. A transactional
  outbox (Alternative B) would require one (a worker/scheduler); this minimum correction does not.

## 15. Migration implications

The minimum correction in §14 requires **no schema change** — `audit_log`'s existing shape already
supports being written from either session. A future transactional-outbox design (Alternative B, if
ever chosen) would require a new outbox table and its own migration; that is not proposed here, and
no migration was created by this audit.

## 16. Compatibility with future architecture

- **ADR-028 attribution API**: whichever remediation is eventually chosen should be applied to
  `attribution_service.py`'s two audit calls before or alongside its first HTTP exposure, but per
  §17 this is not a hard blocker on exposure itself.
- **Future Evidence HTTP surface, Partner workflows, Marketplace, payments**: all inherit the same
  platform-wide characteristic until a Governance decision changes it; none of them make the
  underlying gap worse or better, and none require their own, separate resolution of this issue.
- **Future background jobs / WORM archive**: an eventual real WORM/immutable-archive or
  event-sourcing effort (which `docs/adr/ADR-007` itself already gestured at) would most naturally
  absorb the transactional-outbox alternative as part of that larger, later, separately governed
  build — not as a prerequisite for it.

## 17. API exposure gate

**Recommendation: B — correct in parallel, do not block the upcoming minimal Evidence Attribution
HTTP API.**

Reasoning: the gap is real, proven, and platform-wide — but it is not new, not specific to ADR-028,
and every mutation endpoint already in production today (Registry, Identity, Spatial) carries the
identical characteristic, unblocked, without incident report or known exploitation. Singling out
ADR-028's still-unbuilt HTTP surface for a platform-wide, pre-existing property would be
inconsistent, would not reduce the platform's actual risk (the other 53 call sites remain exactly
as exposed), and would delay a bounded, already-governed feature over a problem whose fix (§14) is
independent of whether that feature ships. The correct sequencing is: raise this to Governance now
(this document), let Governance choose and schedule a remediation path, and let that remediation
apply platform-wide — including to ADR-028's attribution calls — on its own timeline, not gated
behind this one feature.

## 18. Documentation debt

- `backend/tests/live/test_registry_history_rollback_live.py`'s own docstring **already
  correctly discloses** this exact gap, in detail, as an explicitly named "Known limitation." No
  correction needed there — it is accurate and was the single most useful piece of pre-existing
  documentation this audit relied on.
- `backend/app/kernel/audit_postgres.py`'s and `backend/app/kernel/uow.py`'s docstrings are
  accurate about *why* the current design exists, but neither states the atomicity trade-off's
  *cost* (the orphan-entry possibility) as plainly as the rollback-test's docstring does — a reader
  of only those two files, without also finding the test docstring, could reasonably come away
  believing the design has no downside. Not edited in this task, per its read-only scope.
- `docs/adr/ADR-007-audit-trail-evidence-model.md` Decision 1's "written atomically" text is the one
  document that actively **misstates current reality** — not through carelessness, but because
  nothing has ever formally revised it to match the deliberate departure the implementation later
  took. This is the specific documentation debt this audit's recommended next governance action
  (§19) exists to close.

## Summary of what was directly proven versus reasoned

| Claim | Basis |
|---|---|
| Audit writes use a separate, independently-committed session/transaction | Direct code reading, three files, plus the codebase's own docstring account of a live-tested prior finding |
| Case B (orphan audit entry after a later rollback) | **Directly reproduced against a real Postgres database in this audit** |
| Case A (unaudited committed mutation) excluded | Structural proof from exhaustive review of all 55 call sites; not independently live-tested |
| Case C (crash) reduces to Case B | Structural reasoning from PostgreSQL's own connection-loss/rollback behavior; not separately staged |
| Case D (concurrent ordering) | Named as a plausible, unproven, separate concern — not tested |
| ADR-007 Decision 1 contradicted | Direct reading of the Accepted ADR's own text |
| Article VIII §3 technically satisfied on the literal wording | Direct reading of the Constitution |
| Evidence upload compounding risk | Direct code reading plus the already-accepted ADR-026 Storage-orphan precedent |

## Recommended next governance action

Raise this document to Governance Authority as the basis for one of: (a) a new ADR revising
ADR-007 Decision 1's atomicity language to match a reconciled invariant (recommended shape:
"eager, independent commit for deny/failure and cross-cutting audits; same-transaction audit for
success-path business mutations where the caller already holds an open, about-to-commit
transaction; Storage side effects remain a named, separate, already-accepted reconciliation
concern"), or (b) a Governance Decision in the GD-006/GD-007 pattern that regularises the existing
divergence and authorizes the §14 minimum correction without a full ADR rewrite. This document
does not choose between those two instruments — that choice belongs to Governance, not to this
audit.

**AUDIT ATOMICITY DEFECT CONFIRMED — ARCHITECTURE DECISION REQUIRED**
