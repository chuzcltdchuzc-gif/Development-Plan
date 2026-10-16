# ADR-029 — Audit Transaction Semantics and Outcome Integrity

**Status:** **ACCEPTED — 2026-09-11, on explicit Governance Authority ratification. IN FORCE.**
This ADR authorizes exactly the architecture described below — the split audit transaction
semantics, the two invariants, and the taxonomy — the same category of authorization ADR-028
received for its own domain model. It does **not** authorize implementation of any of it: no code,
migration, audit-kernel modification, API, or frontend change is authorized by this ratification;
see "Explicit exclusions" under "Approval Gate" below. Drafted at Governance Authority's direction
following `docs/AUDIT_KERNEL_ATOMICITY_REALITY_AUDIT.md`'s finding:
`docs/adr/ADR-007-audit-trail-evidence-model.md` Decision 1 ("every domain event... is written
atomically with the state change that produced it") is contradicted, today, by the production audit
kernel — proven directly against a real Postgres database, not asserted.

**Date:** 2026-09-10 (drafted); **ratified 2026-09-11**.

## Ratification Record

Ratified by Governance Authority for AquaSavannah LandVault, **2026-09-11**, as: "ADR-029 — Audit
Transaction Semantics and Outcome Integrity," following a formal Governance review (`ADR-029
GOVERNANCE REVIEW PASS WITH REQUIRED TEXTUAL REMEDIATION`) and the one required remediation that
review identified — the audit-call-site inventory, corrected from a miscounted 55 to a verified 54
(§"Audit-call-site migration matrix" below; `docs/AUDIT_KERNEL_ATOMICITY_REALITY_AUDIT_CORRECTION_2026-09-11.md`)
— applied before ratification. This record does not alter the architectural substance drafted
below; it identifies what acceptance covers:

- **Architecture-only acceptance.** Ratification accepts the taxonomy, the two invariants, and the
  selected split-transaction design (§"Decision", §"Alternatives considered" below) — nothing else.
  No code, migration, audit-kernel modification, API, or frontend change is authorized by this
  ratification (see "Explicit exclusions" under "Approval Gate" below).
- **ADR-007 Decision 1 refinement.** This ADR explicitly refines, not supersedes, ADR-007 Decision
  1: the atomicity principle remains applicable to successful domain-state mutation events;
  denial/failure auditing is governed by separate durability semantics, since no successful state
  mutation exists for those events to atomically commit with. ADR-007 Decisions 2–5, and ADR-007
  itself, are unchanged and not rewritten (see "Governance treatment of ADR-007" below).
- **Separate implementation-GD requirement.** Acceptance of this ADR does not authorize
  implementation. A separate, numbered Governance Decision is required before any code, migration,
  or audit-kernel change is written, on this repository's own ADR-026 precedent (architecture
  acceptance ≠ implementation authorization; see "Governance Decision question" below).
- **ADR-028 HTTP hard gate.** Ratification does not authorize ADR-028's Evidence Attribution HTTP
  endpoints. `evidence.actor_attribution.recorded`/`corrected` must first be migrated to the
  accepted successful-mutation semantics, implemented, merged, and post-merge verified before that
  API may be exposed (see "API exposure gate" and "Implementation hard gates" below).

**Scope:** Decides the transaction semantics audit writes require, distinguishes the classes of
audit information LandVault actually produces, and states which class needs which guarantee. Does
**not** implement anything — no code, migration, or outbox is created by this ADR. Does **not**
authorize ADR-028's HTTP API exposure or any other new endpoint.

**Constitutional anchors:** LV-000 v1.8 Article VIII §1 (attributable actor), §2 (RLS in the
database), §3 (audit chain, resolvable reference), §4 (audited overrides); Article IV
(non-adjudication — an audit event is a recorded assertion about what happened, never a legal
determination).

## Context

### Governed architecture — what ADR-007 actually promises

`docs/adr/ADR-007-audit-trail-evidence-model.md`, **Accepted**, Decision 1: *"Event sourcing with a
transactional outbox at the kernel level... every domain event across every bounded context is
written atomically with the state change that produced it."* No later ADR, Governance Decision, or
constitutional amendment revises this sentence. Read literally and in full, Decision 1 also commits
to publishing every event to downstream subscribers ("Trust Engine, Knowledge Graph,
notifications") — that half was never built either, and is not this ADR's concern (§13).

### Implemented architecture — what actually runs today

Re-verified directly against current `main` for this ADR, not carried over from the prior audit:

- `app/kernel/audit.py`'s `audit()` resolves a store via a `ContextVar` (`_store_var`) or, if unset,
  a module-level `_eager_fallback`.
- `app/main.py` calls `configure_eager_fallback(EagerPostgresAuditStore(session_factory))` at
  startup. **`configure_audit_store` (the per-request `ContextVar`) is never called anywhere in
  production code** — confirmed by search; it is used only in test fixtures to bind an in-memory
  fake. Every real `audit()` call therefore resolves to `_eager_fallback`.
- `EagerPostgresAuditStore.append()` (`app/kernel/audit_postgres.py`) opens a **brand-new session**
  from `session_factory()` per call and delegates to `PostgresAuditStore.append()`, whose own
  comment states: *"Commits immediately — NOT just flush()."*
- `app/kernel/uow.py`'s `get_db_session` — the request's own Unit-of-Work — never binds this
  session as the audit store, by its own docstring's explicit statement, and separately: an
  `HTTPException` propagating out of the generator is **committed**, not rolled back; only a
  genuinely unexpected `Exception` triggers `await session.rollback()`.
- `audit_log`'s own RLS (`migrations/versions/0001_identity_and_audit.py`, re-read directly for
  this ADR): `FOR SELECT USING (true)` and `FOR INSERT WITH CHECK (true)` — **no tenant predicate
  at all**. `audit_log` relies on `REVOKE UPDATE, DELETE ON audit_log FROM PUBLIC` plus the hash
  chain for its integrity, not on RLS for tenant isolation. This is a materially different fact than
  the prior reality audit stated in passing ("broke RLS tenant-scoping") and is corrected precisely
  here (§ "RLS treatment").

### Reason implementation diverged — verified, not merely reported

`app/kernel/uow.py`'s docstring states the shared-session attempt was tried and reverted because it
*"silently discarded exactly the deny/failure audit entries... e.g. `identity.refresh.
replay_detected`"* and separately *"audit()'s own commit ends the transaction `is_local=true` was
scoped to, silently clearing the RLS bypass/tenant-scope for everything the same request does
afterward."*

Verified precisely, by reading both mechanisms end to end:

1. **The RLS/`is_local` mechanism, exactly**: `get_db_session` sets `app.tenant_id` (or
   `app.is_super_admin`) via `set_config(name, value, is_local := true)` — a Postgres GUC scoped to
   the *current transaction only*, cleared automatically the instant that transaction commits. If
   `audit()` had shared the request's session **and kept its own eager `commit()`**, that
   intermediate commit would silently clear the tenant scope for every *later* query in the same
   logical request (e.g. Evidence upload's own sequence: audit "uploaded", read back from Storage,
   `mark_hashed`, audit "hashed" again — the second half would run unscoped). This is not a claim
   about `audit_log`'s own RLS (it has none to break); it is a claim about collateral damage to
   *every other table's* RLS scoping for the remainder of that request.
2. **The deny/failure-audit-loss mechanism**: at the time this was found, `get_db_session` rolled
   back on *any* propagating exception, including an expected `HTTPException` (401/403/409). A
   deny audit staged into that same session, followed by the deliberate `raise HTTPException(...)`
   that expresses the denial, was rolled back along with everything else — discarding precisely the
   record a denial most needs. **The fix applied two changes together**: (a) route `audit()`
   through an independent, eagerly-committing store, and (b) separately harden `get_db_session`
   itself to commit — not roll back — on `HTTPException` specifically (preserving, e.g., a
   detected-replay session revocation that must survive the 401 that reports it).
3. **A structural constraint independent of either bug**: `require_role`'s deny audit and
   `enforce()`'s permit/deny audit (`app/kernel/authorization/pep.py`) run as **FastAPI dependency
   resolution**, which does not depend on `get_db_session` at all. Confirmed by reading the
   dependency graph directly: no request-scoped session is guaranteed to exist yet when these fire.
   An independent store is not merely the safer choice here — for this specific caller, it is the
   *only* structurally available one.

**Net finding**: fix (b) above (`HTTPException` commits, not rolls back) already independently
closes part of the original problem. A denial audit raised via `HTTPException` from *inside* an
existing session (e.g. `AuthService.redeem_invitation`'s `identity.invitation.redemption_denied`,
re-read directly for this ADR) would, if staged into that session today, now survive — because the
generator's `except HTTPException: await session.commit(); raise` branch would commit it. The
genuinely irreducible cases for an independent path are: (i) PEP-layer audits with no session in
scope at all, and (ii) any audit whose surrounding code path can raise a plain `Exception` (not an
`HTTPException`) and still needs the audit to survive that rollback.

## Decision

### 1. Audit is not one undifferentiated concept

LandVault produces (and ADR-007 improperly folded into one transaction-semantics requirement) at
least four semantically distinct classes of audit information:

- **Successful-mutation audit** — a durable claim that a state transition *committed*. Example:
  `evidence.actor_attribution.recorded`. This class's entire value depends on the event and the
  state change being the same fact; it is precisely this class ADR-007 Decision 1's "atomically"
  language is actually about, and precisely this class the reality audit proved is not atomic
  today.
- **Denial/security audit** — a durable claim that an unauthorized or rejected action was
  *attempted*. No successful domain mutation exists or is claimed. Its entire value depends on
  surviving exactly the rollback its own denial triggers — the opposite requirement from the class
  above.
- **Failure audit** — a record that an attempted operation failed before completing (e.g. a
  read-back hash mismatch, a validation error). Shares denial's need to survive a rollback, but
  describes an operational fact, not a security decision.
- **Operational/application logging** — diagnostic telemetry never treated as authoritative
  evidence. LandVault's `audit_log` table does not currently carry this class at all (every
  existing call site records one of the first three); named here only to exclude it explicitly from
  this ADR's scope.

ADR-007 Decision 1 does not distinguish these. That is the root of the contradiction: a single
transaction-semantics rule cannot correctly serve both "must commit exactly when the mutation
does" (successful-mutation) and "must survive exactly when the mutation does not" (denial/failure)
at once.

### 2. Required invariants — two, not one

- **Successful-mutation invariant**: *A successful-mutation audit event must not become durable
  unless the state change it describes becomes durable, and a committed, audit-required state
  change must not exist without its corresponding successful-mutation audit record becoming durable
  in the same act.* (Adopted from the task's candidate wording, verified consistent with ADR-007
  Decision 1's own literal intent for this class specifically — not adopted automatically, but
  found, on inspection, to be the correct statement of what Decision 1 was actually trying to say
  for this one class.)
- **Denial/failure invariant**: *A denial or failure audit event's durability must not depend on
  whether the surrounding business transaction commits, because by definition the transaction it
  concerns is expected not to.* This is the opposite requirement, and is why a single shared rule
  across all four classes was always going to be wrong for at least one of them.

### 3. Selected architecture — Alternative C, split transaction semantics

- **Successful-mutation audit rows are staged into the same session and the same transaction as
  the business mutation they describe, and are never independently committed.** No intermediate
  `session.commit()` is introduced anywhere in this path — the row is added (`session.add(...)`,
  flushed) exactly like any other row in that Unit of Work, and becomes durable only when
  `get_db_session`'s own single, final `await session.commit()` runs. This is what makes the
  successful-mutation invariant true by construction: there is exactly one commit point, and both
  the business row and its audit row pass through it together or neither does.
- **Denial and failure audits keep the existing independent, eagerly-committing path**
  (`EagerPostgresAuditStore`, unchanged), because their entire value is surviving a rollback the
  successful-mutation path is specifically designed *not* to survive.
- **No transactional outbox, no background worker, no new runtime dependency** — the split above
  is achieved entirely by choosing, per call site, which of two *already-existing* mechanisms to
  use (a session already in scope versus the existing independent store), not by building a third.

### 4. RLS treatment — the actual mechanism, solved

`audit_log` itself needs no tenant predicate — confirmed above, it has none today and none is
proposed. The risk the historical shared-session attempt actually created was **collateral**: an
intermediate commit clearing `app.tenant_id`'s `is_local` scoping for the rest of the request. The
selected architecture avoids this by construction, not by adding a new safeguard: because a staged
successful-mutation audit row is never independently committed, **no intermediate commit is ever
introduced**, so the GUC is never cleared before the request's natural, single commit point. Cross-
tenant audit insertion cannot occur because the audit row's `tenant_id` field (in its `payload`, as
today) is sourced from the same `ExecutionContext` the business mutation itself was already
authorized against — no new input path is introduced. Privileged/system activity remains
representable exactly as today (`ctx.principal_id`, `app.is_super_admin` for super-admin/anonymous
paths, unchanged). Denied requests remain safely recordable because their path is unchanged — they
keep using the independent store, which was never the source of the RLS risk in the first place.

### 5. Successful-mutation semantics

Events such as `evidence.uploaded`, `evidence.hashed`, `evidence.actor_attribution.recorded`,
`evidence.actor_attribution.corrected`, and Registry's parcel-mutation events must mean **the
corresponding state change committed** — not "the application reached the audit call before the
transaction later failed." Under the selected architecture this becomes true by construction for
every event in this class, because the audit row and the business row share one commit. No new
outcome field or terminology is introduced by this ADR (a later implementation phase may find one
useful for a reader distinguishing pre- and post-remediation history — see §12 — but this ADR does
not create schema).

### 6. Denial/failure semantics

- **Authorization denied**: independent audit, as today (`authz.deny`, `*.replay_detected`, etc.) —
  unchanged.
- **Validation failed**: if raised as an `HTTPException` from inside an existing session before any
  business row was ever added, either path (independent, or staged-and-committed via the
  `HTTPException`-commits branch) is now safe, per the finding in Context point 3 above; this ADR
  does not mandate migrating these to the shared path merely because it has become possible — see
  §15 for why the minimum-change classification leaves most of these where they already work.
- **Persistence failed / transaction rolled back**: must be represented, if at all, as an
  independent failure audit — by definition, nothing in the business transaction is available to
  share a commit with.
- **External Storage failed**: see §10 — this is not a database-transaction question at all.
- **Unexpected server exception**: independent audit only, since the business transaction rolls
  back unconditionally in this case (`get_db_session`'s `except Exception` branch) and nothing else
  is safe to assume.

A failure/attempt event must never reuse a successful-mutation action name (e.g.
`evidence.actor_attribution.recorded` must never be emitted for an attempt that did not commit) —
this is already true of every existing call site reviewed for this ADR; no renaming is required.

### 7. External Storage boundary — no distributed atomicity is claimed

PostgreSQL and Supabase Storage cannot participate in one ACID transaction, and this ADR does not
pretend otherwise. For Evidence upload's sequence (Storage write → DB persistence → read-back →
hashing → audit → request commit):

- **Database transactional atomicity** (this ADR's actual subject) covers only the DB-internal
  half: the `EvidenceRecord` row and its `evidence.uploaded`/`evidence.hashed` audit rows share one
  commit, under the selected architecture.
- **External-side-effect compensation** remains exactly what ADR-026 already named and deferred: an
  orphaned Storage object with no committed `EvidenceRecord` is a housekeeping/garbage-collection
  concern, not solved by this ADR and not claimed to be.
- **Audit of the attempt** (that a Storage write was tried) is not currently emitted as its own
  event and this ADR does not require adding one.
- **Audit of successful, committed state** is what `evidence.uploaded`/`evidence.hashed` become,
  precisely, once staged into the same transaction as the row they describe.

### 8. ADR-028 attribution impact

`evidence.actor_attribution.recorded` and `evidence.actor_attribution.corrected` are
successful-mutation events under this taxonomy and move to the staged/shared-transaction path.
After remediation, neither can be emitted without the attribution row it describes also having
committed, by construction. A denied or failed attribution attempt (e.g. the authorization or
same-tenant checks in `EvidenceActorAttributionService`) would be recorded, if Governance requires
it at all beyond the current `HTTPException`-only signal, via the independent path — unchanged from
every other denial in the platform.

### 9. Historical audit records — no retrospective action

Records created before any remediation lived entirely under the eager-independent architecture and
must not be assumed to correspond to a committed state transition merely because they exist. **No
destructive rewriting of audit history is proposed or acceptable** — the hash chain forbids it
structurally in any case (`app.kernel.audit`, append-only, no update/delete path). This ADR
recommends a **documentation qualification** (a note in this ADR and, if Governance later ratifies
a remediation, in the eventual implementation record) stating the date/commit after which
successful-mutation events carry the stronger guarantee, rather than any reconciliation tooling or
metadata migration — a metadata column distinguishing "legacy" from "post-remediation" semantics
would itself be a schema change this ADR does not authorize, and is not necessary: the chain's own
`created_at` ordering already lets a reader place any entry relative to whichever commit eventually
implements this decision.

## Alternatives considered

| | A — All audit shares the caller's transaction | B — All audit remains eager/independent (status quo) | C — Split by class (selected) | D — Transactional outbox |
|---|---|---|---|---|
| Success atomicity | True, if the historical `is_local`/rollback bugs are avoided | False (the proven defect) | True, by construction, for the class it matters to | True for the outbox row; the eventual `audit_log` materialization is itself only eventually consistent |
| Denial auditing | Regresses to the exact, already-found-and-fixed bug unless done very carefully | Correct today | Correct — unchanged | Correct, if the outbox row commits with whatever denial-recording transaction exists |
| Failure auditing | Same regression risk as denial | Correct today | Correct — unchanged | Same as denial |
| RLS | Must re-solve the `is_local`-clearing risk from scratch | Not at risk (no shared commit exists to clear it) | Not at risk — no intermediate commit is ever introduced | Not at risk — outbox row uses the business transaction's own scope |
| Transaction boundaries | One, shared — simplest in principle, historically mishandled | Two, per mutation (business + audit), by design | One for successful-mutation calls; two remain for denial/failure, matching each class's actual need | Two: business+outbox now, materialization later |
| Concurrency | Unaffected by this axis | Unaffected | Unaffected | New concern: outbox-worker concurrency, idempotent redelivery |
| Retries | N/A | N/A | N/A | Outbox delivery must be idempotent — new design surface |
| Operational complexity | Low, but carries known regression risk | Low (already running) | Low — reuses two mechanisms that already exist correctly, applied per class | Moderate–high: new worker, new failure modes for the worker itself |
| Schema impact | None | None | None | New outbox table |
| Dependencies | None | None | None | A worker/scheduler this codebase has never had (Engineering Rule #5 territory) |
| External side effects (Storage) | Unaffected — none of these alternatives touch it | Unaffected | Unaffected | Unaffected |
| Future WORM/archive compatibility | Neutral | Neutral | Neutral | Composes well, if a real event-sourcing effort is ever separately chartered |
| Background-job compatibility | N/A | N/A | N/A | Would be the platform's first such infrastructure |
| Testability | Requires re-proving the historical bugs are actually avoided | Already proven (existing tests) | Straightforward — reuses two already-tested mechanisms; one new test proves the shared-commit case | Requires testing worker crash/retry semantics — materially larger surface |

**Alternative A is rejected**: applying the shared-session approach to *every* audit call, including
denial/failure, reintroduces the exact, already-discovered, already-reverted regression — it is not
a step forward merely because it looks simpler.

**Alternative B (status quo) is rejected** for the successful-mutation class specifically: it is the
proven defect this ADR exists to close.

**Alternative D (transactional outbox) is not selected**, per the task's own instruction not to
default to it: it requires a new background-worker component (a genuinely new runtime dependency,
Engineering Rule #5 territory) and produces only *eventual* consistency for the materialized
`audit_log` row, not the strict, immediate atomicity the successful-mutation invariant actually
requires and that Alternative C achieves for free by reusing an already-open transaction. It remains
worth naming as the eventual direction if LandVault ever builds real cross-context event
publishing (the other half of ADR-007 Decision 1 that was never built) — but adopting it now, for
this narrower problem, is disproportionate.

**Alternative C is selected.**

## Governance treatment of ADR-007

This ADR **refines ADR-007's meaning for audit transaction semantics specifically; it does not
supersede ADR-007 as a whole.** ADR-007's other four decisions (real S3-compatible Object Lock
storage; legal hold as a shared guard; hash-recomputation-based verification; dual-authorized
break-glass) are entirely unaffected and remain exactly as accepted. Decision 1's "atomically"
language is refined, not deleted: this ADR states precisely which class of audit event that
language governs (successful-mutation) and which class it was never correctly describing
(denial/failure), and resolves the ambiguity in favor of the two-invariant statement in §2 above.
ADR-007 Decision 1's further ambition — full event sourcing with downstream publication — is
neither adopted nor rejected here; it remains unbuilt and out of this ADR's scope (§13 of the
originating task; not re-litigated).

## Governance Decision question

- **Is this ADR sufficient on its own?** For the *architecture* decision, yes — an ADR is exactly
  the instrument this repository uses to decide and record an architecture question, and this one
  explicitly names and refines the prior ADR it touches, per this repository's own citation
  discipline.
- **Is a later Governance Decision required for historical reconciliation?** No — §9 above already
  determined no reconciliation tooling or retrospective action is needed; a documentation
  qualification is sufficient, and that qualification lives in this ADR's own text, not in a
  separate instrument.
- **Is a Governance Decision required to authorize eventual remediation implementation?** This is
  the one place a GD is more likely than not needed, on this repository's own precedent: **ADR-026
  is the closest analogy** — an accepted domain-model ADR that itself required a later, separate
  Governance authorization event (Decision 8/9's own re-derivation shows exactly this shape: "B5.2
  — Evidence Domain Model Implementation" authorization) before any migration could be written
  against it. This ADR, if accepted, should be read the same way: acceptance authorizes the
  *decision*, and a later, explicit Governance act — plausibly a GD in the GD-006/GD-007 style,
  since this also regularizes a documented divergence discovered after ratification — authorizes
  the *implementation*. This ADR does not create that GD; it names the need for one before code is
  written.

## Minimum implementation consequence (future work — not authorized here)

- **Conceptual API shape**: rather than fixing names now, this ADR describes the shape a future
  implementation phase would need: a way for a caller that already holds an open Unit-of-Work
  session to stage a successful-mutation audit row into it (e.g. a session-aware variant or
  parameter on the existing `audit()` call), left entirely distinct from the existing, unchanged
  `audit()` behavior for denial/failure calls. The two must remain textually and behaviorally
  distinguishable at each call site — a future reviewer must be able to tell, from the call itself,
  which invariant applies.
- **Call sites needing classification**: all 54 (§16 below; corrected from an original miscount of
  55 — see `docs/AUDIT_KERNEL_ATOMICITY_REALITY_AUDIT_CORRECTION_2026-09-11.md`) — every one must be
  assigned to successful-mutation, denial, or failure before any code changes; none may be migrated
  to the shared path by default.
- **New runtime dependency**: none.
- **Schema migration**: none — `audit_log`'s existing shape needs no change to support being
  written from either session.

## Audit-call-site migration matrix

**Corrected 2026-09-11** — the original draft of this section, and the reality audit it was drawn
from, stated 55 total call sites with approximate per-class buckets; both the total and the buckets
were arithmetic errors, not a change in the underlying code. A fresh, individually-verified count
against the confirmed baseline (`edbc4283005e86f5068de4014bedc8407ac5f61d`; `grep -rn "await
audit(" app/` from `backend/`) found **54** call sites. Full detail, including the two ambiguous
sites named individually, is in
`docs/AUDIT_KERNEL_ATOMICITY_REALITY_AUDIT_CORRECTION_2026-09-11.md`; this table restates the
reconciled result. **This correction changes no target transaction semantics and no architectural
conclusion** — only the count and its classification totals.

| Class | Representative call sites | Count (of 54) | Target transaction semantics |
|---|---|---|---|
| Successful mutation | `evidence.uploaded`, `evidence.hashed`, `evidence.sealed`, `evidence.legal_hold.applied`/`released`, `evidence.actor_attribution.recorded`/`corrected`, `registry.parcel.created`/`updated`/`archived`/`geometry_attached`/`geometry_detached`, `registry.parcel_ownership.recorded`/`changed`, `registry.parcel_status.changed`, `spatial.parcel_geometry.created`, Identity provisioning/invitation/tenant/delegation-success and login/logout events | 31 | Staged into the caller's existing session; committed only at that session's own single commit point |
| Denial | `authz.deny` (`pep.py`, both `require_role` and `enforce`), `identity.role.assign_denied`, `identity.invitation.denied`, `identity.delegation.denied`, `identity.login.failed`, `identity.refresh.unknown_token`/`replay_detected`, `identity.invitation.redemption_denied` (the clean cases), `evidence.upload_denied`, `registry.parcel.mutation_denied`, `spatial.parcel_geometry.mutation_denied` | 20 | Independent, eagerly-committing store — unchanged |
| Failure | `evidence.integrity_check_failed` | 1 | Independent, eagerly-committing store — unchanged |
| Ambiguous / requires implementation-time governance | Two specific call sites, named individually in the correction note: `AdminService.get_delegation`'s `identity.delegation.invalidated` (fired during a read, no mutation attempted); `AuthService._authorize_invitation_redemption`'s `authority_lost_reason` branch of `identity.invitation.redemption_denied` (a real invitation-revoke mutation and a denial audit share one call) | 2 | Not resolved by this ADR — an implementing engineer must classify each individually against the two invariants in §2 before writing any code; each currently defaults to the independent path (the class this ADR changes nothing about) rather than being guessed into successful-mutation |

Row total: 31 + 20 + 1 + 2 = 54, matching the verified inventory exactly. Every one of the 54 sites
was read individually for this classification, not sampled or estimated; the correction note's own
table cross-reconciles this classification against each file's independently verified count.

## Failure matrix under the selected architecture

| Scenario | Truthful final outcome |
|---|---|
| Mutation flush succeeds, success-audit staging fails (e.g. a constraint violation on the audit row itself) | Both roll back together at the shared commit point — no orphan of either kind, by construction |
| Mutation succeeds, final transaction commit fails (DB connectivity, deferred constraint) | Both fail to commit together — no orphan; the caller sees the failure |
| Denial audit insert fails | The independent store's own commit fails; the audit failure itself propagates as an unguarded exception (unchanged from today, per the reality audit's Case A structural finding) — the request fails visibly, it does not silently proceed |
| Transaction rolls back after successful-mutation audit staging | Both roll back together — this is precisely what closes the proven defect; no orphan audit remains |
| Request crashes after transaction commit but before response | Both the mutation and its audit are already durable; only the HTTP response to the caller is uncertain, not the durable state — acceptable, matches every other at-least-once-delivery web API |
| Duplicate request/retry | Unaffected by this ADR — a retried request produces a new, independent attempt with its own audit trail either way; idempotency of the underlying mutation, if required, is a separate, pre-existing concern this ADR does not change |
| Database unavailable | Every audit() call fails, which (per the unguarded-call-site finding) fails every mutation request platform-wide — fail-closed, unchanged from today |
| Storage succeeds, DB transaction fails | Storage object orphaned (ADR-026's already-accepted risk, unchanged); DB-side audit and business row both absent together — no *new* orphan-audit risk added on top of the pre-existing Storage-orphan one |
| Storage fails before DB mutation | No DB row, no audit row of either kind attempted yet in the current code order — unaffected |

## Security and constitutional analysis

- **Tenant isolation**: preserved — no new cross-tenant read/write path is introduced; see "RLS
  treatment" above.
- **Actor identity**: unaffected — `ctx.principal_id` sourcing is unchanged.
- **Deny-attempt traceability**: preserved exactly as today for the class that needs it.
- **No fabricated successful mutation**: this is the specific guarantee this ADR restores for the
  successful-mutation class.
- **Append-only audit history**: unaffected — no update/delete path is introduced or removed by
  either the current architecture or this ADR's proposed refinement.
- **Non-adjudication doctrine**: unaffected — this ADR governs *when* an audit record becomes
  durable relative to a state change, never *what legal weight* that record carries. An audit event
  remains a recorded assertion that a state change happened (or was denied/failed), never a
  determination of ownership, title, or any other adjudicated fact, before or after this decision.

## API exposure gate

**Recommendation: B — the architecture decision (this ADR) should complete before ADR-028's HTTP
API ships, but implementation remediation may proceed in parallel with, not strictly before,
that API's build-out, provided the API's own audit calls are classified and migrated (§16) before
the API itself is exposed to real traffic.**

Reasoning: the reality audit's own recommendation ("B — correct in parallel, do not block") was
made before this architecture decision existed and reasonably treated the gap as an already-shipped,
platform-wide characteristic no worse for one more feature to inherit. That reasoning still holds
for the *existing* 52 non-ADR-028 call sites (54 total, corrected 2026-09-11 — see
`docs/AUDIT_KERNEL_ATOMICITY_REALITY_AUDIT_CORRECTION_2026-09-11.md` — minus the 2
attribution-service calls) — Governance is not required to halt them. But *knowingly* shipping a
**new** mutating HTTP surface whose two audit calls are proven capable of lying about a committed
mutation, after Governance has just confirmed that mechanism and drafted its fix, is a different
posture than tolerating a pre-existing condition. The narrow, correct answer is: this ADR must be
accepted (or Governance must otherwise formally decide the invariant) before
`evidence.actor_attribution.recorded`/`corrected` specifically are exposed over HTTP; the other 52
call sites are not newly gated by this ADR's existence.

## Implementation hard gates

- This ADR is now **Accepted** (2026-09-11), but acceptance alone does not lift this gate: no
  migration, code, audit-kernel modification, or outbox may be written against it until the
  separate Governance Decision named in "Governance Decision question" above is also ratified, on
  this repository's own ADR-026 precedent (architecture acceptance ≠ implementation authorization).
- ADR-028's HTTP API must not expose `record_attribution`/`correct_attribution` until their two
  audit calls have been classified and migrated to the staged/shared path, implemented, merged, and
  post-merge verified.

## Consequences

- The successful-mutation audit invariant becomes true by construction, for every call site
  eventually migrated, without a new runtime dependency, schema change, or background-job
  infrastructure.
- Denial/failure auditing is unchanged and remains correct.
- The RLS/`is_local` risk that motivated the original eager-everywhere design is understood
  precisely enough to be certain the selected architecture does not reintroduce it.
- ADR-007 Decision 1's "atomically" language is refined into two class-specific invariants rather
  than one universal (and, for one class, incorrect) rule.
- No historical audit record is rewritten or specially flagged; a documentation qualification is
  the extent of retrospective treatment.

## Approval Gate

This ADR is **ACCEPTED**, per the Ratification Record above. Acceptance authorizes only the
architecture described above — the taxonomy, the two invariants, and the selected split-transaction
design (Alternative C) — the same category of authorization ADR-028 received for its own domain
model, never the implementation, migration, or API-exposure steps this ADR and its ratification
both explicitly exclude.

**Explicit exclusions.** Acceptance of this ADR does not authorize: any code, migration, or
audit-kernel modification implementing the staged/shared successful-mutation path; any change to
`app/kernel/audit.py`, `app/kernel/audit_postgres.py`, or `app/kernel/uow.py`; classification or
migration of any of the 54 call sites named in §"Audit-call-site migration matrix"; a transactional
outbox or any new background-worker infrastructure; or exposure of ADR-028's
`record_attribution`/`correct_attribution` HTTP endpoints. Implementation of this ADR's accepted
architecture — exactly as much as this document decides, no more — requires its own, separate
Governance Decision before any code, migration, or audit-kernel change is written, exactly as every
prior ADR in this codebase has required (per "Governance Decision question" above, on the ADR-026
precedent).

**ADR-028 API dependency, restated.** `evidence.actor_attribution.recorded`/`corrected` must be
migrated to the successful-mutation transaction semantics accepted here, implemented, merged, and
post-merge verified, before ADR-028's mutating HTTP attribution endpoints may be exposed. Acceptance
of this ADR's architecture does not, by itself, satisfy that condition.
