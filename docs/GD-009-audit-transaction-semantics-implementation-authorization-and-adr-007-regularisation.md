# GD-009 — Audit Transaction Semantics Implementation Authorization and ADR-007 Regularisation

**Status:** **ACCEPTED — 2026-09-11, on explicit Governance Authority ratification. IN FORCE.** This
Decision authorizes exactly Batch 1 implementation, as described below — the same category of
authorization `docs/adr/ADR-026-evidence-domain-model.md` gave its own "B5.2" implementation. It does
**not** authorize `ADR-028`'s HTTP exposure, or anything beyond Batch 1's own bounded scope; see
"Explicit exclusions" under "Approval Gate" below.

**Date drafted:** 2026-09-11. **Ratified:** 2026-09-11.

**Operative authority:** **Article XVI §2** — this is a later numbered decision that explicitly
names and qualifies the governing texts it touches (`docs/adr/ADR-007-audit-trail-evidence-model.md`
Decision 1, per the mechanism `docs/adr/ADR-029-audit-transaction-semantics-and-outcome-integrity.md`
already established; `docs/adr/ADR-028-evidence-actor-and-commissioning-provenance.md`'s HTTP
exposure gate). It is not proposed under Article XIV and does not amend this Constitution. It
follows the precedent `GD-006`/`GD-007` already set for regularising a discovered
implementation/documentation divergence after ratification, and the precedent `docs/adr/
ADR-026-evidence-domain-model.md` set for separating architecture acceptance from implementation
authorization (its own "B5.2 — Evidence Domain Model Implementation" authorization).

## Ratification Record

Ratified by Governance Authority for AquaSavannah LandVault, **2026-09-11**, following a formal
Governance review (`GD-009 GOVERNANCE REVIEW PASS WITH REQUIRED TEXTUAL REMEDIATION`) and the three
required textual remediations that review identified — kernel-capability isolation (§5), the
concurrency/hash-chain finding and its mandatory test (§11, §15), and the PR-boundary exclusion list
(§19) — applied before ratification. This record does not alter the draft; it identifies what
ratification covers:

- **ADR-007 historical regularisation** (§3): the historical eager-independent audit kernel diverged
  from Decision 1's literal atomicity text; `ADR-029` now governs the corrected split semantics;
  historical audit rows are unchanged and not retrospectively granted guarantees they lacked.
- **ADR-029 = architecture authority; GD-009 = implementation authority, Batch 1 only** (§20).
- **Explicit per-call transactional opt-in required** — no ambient, global, or default rebinding may
  alter any un-migrated `audit()` call's behavior (§5).
- **The remaining 52 call sites, and both ambiguous sites, are not authorized for migration** (§6,
  §18).
- **Audit-chain concurrency hard stop**: a proven fork, duplicate predecessor, or invalid lineage
  under Batch 1's mandatory concurrency tests halts implementation and returns to Governance — no
  locking/sequencing/outbox workaround is pre-authorized (§11, §15).
- **No schema migration by default; no new runtime dependency** — either requires a stop-and-return to
  Governance, the latter under Engineering Rule #5 (§12, §19.1).
- **ADR-028 HTTP hard gate remains in force** — ratification alone does not authorize Evidence
  Attribution HTTP exposure (§14).

## 1. Governance baseline verified for this drafting

Read directly against the current repository, not assumed or carried over from any prior document:

- `origin/main` SHA: **`e4a8da9ab2d7c40f01a52eba0997a9001b76582d`** (the ADR-029 ratification squash
  commit, PR #29).
- `docs/adr/ADR-007-audit-trail-evidence-model.md`: **Accepted**.
- `docs/adr/ADR-029-audit-transaction-semantics-and-outcome-integrity.md`: **ACCEPTED — 2026-09-11,
  on explicit Governance Authority ratification. IN FORCE.**
- `docs/adr/ADR-028-evidence-actor-and-commissioning-provenance.md`: **ACCEPTED — 2026-09-10, on
  explicit Governance Authority ratification. IN FORCE.**
- `docs/adr/ADR-026-evidence-domain-model.md`: **Accepted** — Governance Authority authorization,
  "B5.2 — Evidence Domain Model Implementation."
- `docs/GD-008-surveyor-network-phase-0-principles-and-authorization-boundary.md`: **ACCEPTED —
  2026-09-08, on explicit Governance Authority ratification. IN FORCE.**
- Article XVI Governance Decision Log (`docs/LV-000-constitution.md`): entries **GD-001 through
  GD-008** exist, each following the same numbered, dated, "later decision qualifies only by naming
  it" (§2) discipline. No `GD-009` or higher entry exists anywhere in the repository (checked by
  direct search, not assumed).
- **Next available Governance Decision number, confirmed by repository reality: GD-009.** Not
  assumed in advance of this check — GD-001–008 all exist as either full Article XVI entries or
  (GD-008) a full standalone instrument with a condensed Article XVI entry; GD-009 is the first
  unused number.

## 2. Purpose

This Governance Decision does two things, and no more:

1. **Regularises** the historical divergence between `ADR-007` Decision 1's literal "atomically"
   text and the production audit kernel's actual, deliberate eager-independent-commit design —
   proven directly against a real Postgres database by
   `docs/AUDIT_KERNEL_ATOMICITY_REALITY_AUDIT.md`, and resolved at the architecture level by
   `ADR-029`, now Accepted. This Decision does not itself resolve that divergence a second time; it
   records that `ADR-029`'s acceptance is the resolution, and authorizes the bounded first step of
   implementing it.
2. **Authorizes Batch 1 implementation** of `ADR-029`'s accepted split-transaction architecture,
   strictly bounded to the scope in §5 below — the two `ADR-028` attribution audit events and the
   internal capability needed to stage them into the caller's existing transaction. Nothing beyond
   that scope is authorized by this Decision.

This Decision explicitly names `ADR-007`, `ADR-029`, and `ADR-028` (its HTTP gate specifically), per
Article XVI §2's requirement that a later decision qualify an earlier one only by naming it.

## 3. Historical regularisation — the record, stated once, precisely

- `docs/adr/ADR-007-audit-trail-evidence-model.md`, Accepted, Decision 1, states: "every domain event
  across every bounded context is written atomically with the state change that produced it."
- The production audit kernel's actual, historical implementation (`app/kernel/audit.py`,
  `app/kernel/audit_postgres.py`, `app/kernel/uow.py`) instead committed every audit entry through an
  independent session and an independent, immediately-committing transaction
  (`EagerPostgresAuditStore`), never the caller's own request transaction — a deliberate design,
  arrived at after a live-Postgres finding that the alternative (binding audit writes to the
  caller's session) silently discarded deny/failure audit entries on rollback and separately
  disturbed transaction-scoped RLS context (`app/kernel/uow.py`'s own docstring).
- This divergence was proven, not merely suspected, by `docs/AUDIT_KERNEL_ATOMICITY_REALITY_AUDIT.md`
  (Case B: a business mutation flushed, its audit entry committed independently, the surrounding
  transaction was then forced to roll back, and the audit entry survived — reproduced directly
  against a real Postgres database).
- `docs/adr/ADR-029-audit-transaction-semantics-and-outcome-integrity.md`, now Accepted, refines
  `ADR-007` Decision 1's governing semantics into two class-specific invariants: successful-mutation
  audit must commit or roll back together with the mutation it describes; denial/failure audit may
  remain independently durable because no successful mutation exists for it to coherently commit
  with. `ADR-007` Decisions 2–5, and `ADR-007` itself, are unaffected and are **not** rewritten,
  amended, or historically erased by this Decision.
- **Historical audit records remain untouched.** This Decision does not authorize, and no future
  implementation under it may perform, any destructive rewriting, deletion, or retroactive
  fabrication of existing `audit_log` rows. It does **not** claim that historical eager-committed
  audit rows retrospectively acquired a transactional guarantee they did not possess at the time
  they were written — `ADR-029`'s own "Historical audit records" section already states this, and
  this Decision restates it rather than weakening it: a documentation qualification (already present
  in `ADR-029`'s text) is the entire extent of retrospective treatment. No metadata migration, no
  reconciliation sweep, and no "legacy" flag column are authorized here.

## 4. Implementation architecture authorized — bounded to ADR-029's selected design, nothing else

This Decision authorizes implementation of, and only of, `ADR-029`'s selected Alternative C:

- **Successful-mutation audits** stage inside the caller's existing SQLAlchemy session/transaction
  and commit or roll back together with the corresponding state mutation, via that transaction's own
  single, final commit point — no new, independent commit is introduced for this class.
- **Denial/failure audits** remain on the existing independent, eagerly-committing path
  (`EagerPostgresAuditStore`), unmodified, unless a future, separate Governance act explicitly
  reclassifies a specific call site.

**This Decision does not authorize**, and no implementation under it may introduce:

- an all-audit shared-transaction design (Alternative A — the already-once-reverted regression);
- eager-independent commits for any call site newly classified as successful-mutation;
- a transactional outbox, Kafka, event sourcing, or CQRS (Alternative D, and `ADR-007` Decision 1's
  further, never-built ambition);
- any new background-worker infrastructure;
- any new runtime dependency.

## 5. Batch 1 — mandatory, and the only implementation scope this Decision authorizes

Batch 1 consists of exactly:

1. **A transaction-coupled successful-mutation audit capability** using the caller's existing
   Unit-of-Work session — the minimum internal abstraction needed to let a caller that already holds
   an open session stage a successful-mutation audit row into it, distinct in code and at each call
   site from the existing, unchanged `audit()` behavior used for denial/failure calls (per `ADR-029`
   §"Minimum implementation consequence"). This Decision authorizes the **capability, semantics, and
   boundary** — not a specific method name or signature; repository convention at implementation time
   (matching the shape of the existing `audit()`/`AuditStore` abstractions) governs the exact form,
   and no premature freezing of names is required by this Decision.
2. **Preservation, unmodified, of the existing independent path** for every denial/failure audit call
   site.
3. **Migration of exactly two call sites** to the transaction-coupled successful-mutation path:
   - `evidence.actor_attribution.recorded` (`app/contexts/evidence/application/attribution_service.py`,
     `EvidenceActorAttributionService.record_attribution`)
   - `evidence.actor_attribution.corrected` (same file,
     `EvidenceActorAttributionService.correct_attribution`)

These two are the immediate priority because they, and only they, gate `ADR-028`'s future minimal
HTTP surface (§14 below).

**Explicit opt-in required — no ambient or default rebinding.** The new transaction-coupled
successful-mutation audit capability **must be selected explicitly, in code, at each authorized call
site** — `record_attribution` and `correct_attribution`, and no other. Batch 1 must not implement the
capability through any of the following, each of which could cause an unedited call site among the
remaining 52 to change transaction semantics implicitly, without its own source being touched:

- default replacement of the existing `audit()` path;
- global audit-store replacement;
- request-scoped rebinding;
- session-scoped rebinding;
- ambient `ContextVar` configuration (the pattern `configure_audit_store` already uses for test
  fixtures is not to be repurposed this way in production);
- dependency-container rebinding;
- any other mechanism by which an `audit()` call whose own source line was not edited could begin
  exhibiting transaction-coupled behavior.

The implementation may share internal primitives (e.g., a common `AuditStore`-shaped interface) with
the existing `audit()`/`EagerPostgresAuditStore` machinery, but the semantic opt-in into the new,
transaction-coupled path must remain explicit and local to the two authorized call sites only. Every
one of the other 52 call sites must retain its current, unmodified behavior unless separately
authorized by a future Governance act.

## 6. Batch 1 must not migrate the other 52 call sites

The verified, repository-confirmed inventory (`docs/AUDIT_KERNEL_ATOMICITY_REALITY_AUDIT_CORRECTION_2026-09-11.md`;
re-derived independently again for this drafting, see §"Readiness challenge required" in the
companion readiness report) is:

| Class | Count | Batch 1 disposition |
|---|---|---|
| Successful mutation | 31 | **2 authorized** (the ADR-028 attribution pair, §5.3); **29 remain unauthorized**, unchanged, on the existing eager-independent path, pending a later, separately governed batch |
| Denial | 20 | Unchanged — independent path, not touched by this Decision |
| Failure | 1 | Unchanged — independent path, not touched by this Decision |
| Ambiguous | 2 | Unchanged — remain on current semantics; **not** classified by this Decision (§18) |
| **Total** | **54** | **2 migrated; 52 unchanged** |

The 29 unauthorized successful-mutation sites, by file, for the avoidance of doubt: `admin_service.py`
9, `auth_service.py` 5, `evidence_service.py` 7, `parcel_service.py` 7, `spatial_service.py` 1. **No
implementation under this Decision may migrate any of these 29**, silently or otherwise. Migrating
any of them requires either a separately governed future batch (§17) or an explicit extension of this
Decision's own authority by a later, numbered Governance Decision that names this one.

## 7. API/abstraction design consequence

The implementation this Decision authorizes may introduce the minimum internal audit abstraction
required to make a call site's transaction semantics textually and behaviorally distinguishable —
i.e., a future reviewer must be able to tell, from the call itself, whether it is transaction-coupled
(successful-mutation) or independent (denial/failure) — without this Decision prescribing the exact
method name, parameter shape, or module layout. Implementation-time engineering judgment, consistent
with this codebase's existing `AuditStore`/`audit()` conventions, governs that detail; this Decision
authorizes capability, semantics, and boundary only.

## 8. Transaction invariant — the one property Batch 1 must prove, not merely implement

Batch 1's implementation must prove, with real transaction-level tests (§15), that for
`record_attribution`/`correct_attribution`:

- attribution mutation + success audit → **commit together**, or
- attribution mutation + success audit → **roll back together**,

and that it is structurally impossible, under the implemented design, for:

- a committed attribution mutation to exist without its required successful-mutation audit row
  (transaction separation must not be able to produce this), or
- a successful-mutation audit row to remain durable when the attribution mutation it describes rolls
  back.

## 9. Denial/failure preservation — must not regress the already-once-fixed bug

Batch 1 must not touch the independent path's behavior. The future implementation must include tests
proving that representative denied/failed actions (at minimum: a `pep.py` role-gate denial and an
`identity.refresh.replay_detected`-shaped case) still produce independently durable audit records even
when the surrounding business operation does not commit — i.e., must not recreate the exact
regression `EagerPostgresAuditStore` was originally built to fix (deny/failure audits silently
discarded on rollback).

## 10. RLS / transaction-scoped context — verified against actual code, not ADR text alone

Batch 1 must introduce **no intermediate `commit()`** into the request's Unit-of-Work session for the
successful-mutation path. This is not merely an architectural preference restated from `ADR-029`; it
is verified here directly against `app/kernel/uow.py`'s actual mechanism (re-read for this drafting,
`origin/main` at the baseline SHA above): `get_db_session` sets `app.tenant_id`/`app.is_super_admin`
via `set_config(..., is_local := true)`, scoped to the current transaction only and cleared the
instant that transaction commits. Any intermediate commit on the shared session during
`record_attribution`/`correct_attribution` would silently clear that scoping for the remainder of the
request — the exact collateral mechanism the original eager-everywhere design was built to avoid.
Batch 1's implementation must be verified, live, against this exact mechanism (§15) — not assumed
safe merely because `ADR-029`'s text says so.

## 11. Audit append-only/hash-chain behavior — preserved, and its concurrency exposure proven, not assumed

**Transaction atomicity and audit-chain linearity/concurrency integrity are two distinct properties,
and this Decision does not conflate them.** `ADR-029` decides the former — that a successful-mutation
audit row and the mutation it describes commit or roll back together. It does **not** decide, and
this Decision does not assume, that the audit chain's `prev_hash` linkage remains a strictly linear,
fork-free sequence under concurrent writers; that is a separate property Batch 1 must independently
prove, not one `ADR-029`'s acceptance already establishes.

**The concurrency exposure, stated accurately.** The existing audit kernel computes each entry's
predecessor relationship through a **read-before-append pattern**: `audit()` reads
`prev_hash = await store.last_hash()`, then later calls `store.append(entry)`, with no locking or
serialization between the two, and no database-level uniqueness constraint on `prev_hash` (confirmed
directly against `app/kernel/audit.py` and the `audit_log` schema). **The existing eager-independent
audit path already contains a non-zero concurrency race window** — bounded, today, to a single,
freshly-opened, immediately-committing transaction (`EagerPostgresAuditStore`), and named, unresolved,
as "Case D" in `docs/AUDIT_KERNEL_ATOMICITY_REALITY_AUDIT.md` §4. **Batch 1 may widen that window for
the two migrated successful-mutation call sites specifically**, because a transaction-coupled audit
row's `last_hash()` read and its eventual durable commit are now separated by however long the rest
of the caller's request takes, rather than by a single, near-instantaneous eager commit — under
Postgres's default `READ COMMITTED` isolation, a concurrent write cannot see this row until it
commits, so two genuinely concurrent writes could compute and durably commit the same `prev_hash`.
**This is not automatically an architectural failure** — it is an implementation-time invariant that
must be proven, with the executable evidence required by §15 below, before Batch 1 may be considered
complete. This Decision does not claim, and no implementation report under it may claim, that the
existing chain is concurrency-safe absent that proof.

Subject to that proof obligation, Batch 1 must preserve every existing ADR-007 integrity control that
remains applicable to the successful-mutation class once staged into the caller's session:

- **Append-only audit history** — no `UPDATE`/`DELETE` path on `audit_log` is introduced or weakened;
  the existing `REVOKE UPDATE, DELETE` grant-level protection is unaffected by which session writes
  a row.
- **Existing hash computation** — Batch 1 must not change `_compute_hash`'s inputs.
- **Predecessor relationship** — `prev_hash` resolution semantics are not redefined by Batch 1; only
  the session/transaction that performs the read-then-append is different.
- **Actor identity** (`ctx.principal_id` sourcing) and **tenant metadata** (the audit row's
  `payload.tenant_id`, sourced from the same already-authorized `ExecutionContext` the business
  mutation itself used) — unchanged.
- **Event ordering semantics** — `last_hash()`'s read-before-insert *pattern* is unaffected by session
  choice; the *effective concurrency window* around that pattern is not — see above.
- **Integrity under rollback** — a rolled-back transaction-coupled attempt must leave neither the
  mutation nor its audit row durable (§8).
- **Integrity under concurrent writers** — proven, not assumed, per §15's concurrency tests below.

**If sharing the caller's transaction is found, during implementation, to require any change that
would undermine one of the above properties, the implementing engineer must stop and return an
architectural blocker to Governance — not improvise a workaround.** This Decision does not pre-clear
any such change. **This stop-and-return requirement explicitly extends to a positive finding from
§15's concurrency tests**: if Batch 1 testing proves that transaction-coupled successful auditing can
create a fork, a duplicate predecessor relationship, an invalid chain, or any other violation of
ADR-007's audit-chain integrity under realistic concurrent writes, implementation must stop. In that
event, the implementing engineer must **not**, unless separately authorized by Governance:

- add an advisory lock;
- add `SERIALIZABLE` isolation;
- introduce a chain-head table;
- create a sequence allocator;
- add a uniqueness constraint;
- redesign hashing;
- introduce an outbox;
- implement retry/serialization infrastructure.

The implementing engineer must instead return exactly: **`GD-009 BATCH 1 BLOCKED — AUDIT CHAIN
CONCURRENCY ARCHITECTURE REQUIRED`**. A proven concurrency defect is a Governance return condition,
not permission for an engineer to invent a fix inside Batch 1's own authority.

## 12. No schema migration by default

`ADR-029` found no schema migration necessary for this architecture; `audit_log`'s existing shape
already supports being written from either session. **Batch 1 requires no migration under this
Decision.** If implementation reality proves a schema change is unavoidable, the implementing
engineer must stop and return to Governance before creating one — this Decision does not authorize a
migration in advance of that determination.

## 13. No external Storage redesign

Batch 1 must not redesign Supabase Storage, `ADR-026`'s already-accepted orphaned-storage-object
compensation semantics, or Evidence upload's storage-then-database sequencing. PostgreSQL↔Storage
distributed atomicity remains outside this Decision's scope, exactly as `ADR-029` itself already
scoped it.

## 14. ADR-028 HTTP hard gate — restated, not loosened

Ratifying this Decision does **not**, by itself, lift `ADR-028`'s HTTP exposure gate. The gate remains
in force until, in sequence:

1. Batch 1 is **implemented**;
2. **tested** per §15 below, against real PostgreSQL where transaction behavior requires it;
3. **formally reviewed** (human review, per this repository's standing discipline);
4. **squash merged** to `main`;
5. **post-merge verified** — the transaction invariant (§8) and the denial/failure non-regression
   (§9) re-proven fresh against the merged `main` state, not carried over from pre-merge testing.

Only after all five steps are satisfied for `evidence.actor_attribution.recorded` and
`evidence.actor_attribution.corrected` specifically may Governance **consider** authorizing the
minimal `ADR-028` HTTP API — a separate, future, explicit Governance act, not an automatic
consequence of Batch 1's merge.

## 15. Testing requirements for the future Batch 1 implementation

The implementation this Decision authorizes must include real transaction-level tests proving, at
minimum:

1. Successful attribution record + audit commit together.
2. Successful attribution correction + audit commit together.
3. A forced rollback after audit staging leaves **neither** the attribution row **nor** the audit row
   durable.
4. A forced audit-stage failure (e.g., a constraint violation on the staged audit row) prevents the
   business mutation from committing.
5. Denial audit remains durable when the surrounding business transaction does not commit
   (regression guard for §9).
6. Failure audit remains independently durable where applicable (regression guard for §9).
7. No intermediate commit clears request-scoped RLS/`is_local` context for the remainder of the
   request (direct verification of §10, against real PostgreSQL).
8. Existing audit hash-chain behavior (`verify_chain()`) remains correct across a mix of
   transaction-coupled and independent entries.
9. No cross-tenant regression — `evidence_actor_attributions.tenant_id` binding and RLS scoping remain
   exactly as `ADR-028`'s own migration (`0014`) already established.
10. **Concurrent-chain integrity (real PostgreSQL, mandatory — see §11)**, at minimum:
    - **Case A — transactional vs. transactional.** Two concurrent successful attribution mutations
      each stage a transaction-coupled audit event before either commits. Determine whether both can
      produce an invalid fork or a duplicate predecessor relationship.
    - **Case B — transactional vs. eager-independent.** A transaction-coupled attribution
      success-audit races a representative eager-independent audit write (e.g., a `pep.py` deny
      audit or another mutation's eager success audit). Determine whether the chain remains valid.
    - **Case C — repeated execution.** Execute the concurrency scenario enough times to expose
      timing-sensitive behavior, rather than relying on one interleaving that happened to succeed.

    The implementation report for item 10 must record, for each run: the predecessor/hash
    relationships produced; the commit results; whether a fork occurred; whether any audit row became
    invalid; and whether ordering remained consistent with the existing audit-chain invariants. A
    positive finding of a fork, duplicate predecessor, or invalid chain triggers §11's hard-stop
    requirement — it is not a defect for the implementing engineer to work around inside Batch 1.

Tests requiring real transaction/commit/rollback behavior (items 1–4, 7, 10) must run against real
PostgreSQL, not an in-memory fake, per this repository's own established discipline
(`docs/ENGINEERING_RULES.md` rule 7 — "never mark complete without having observed it pass against
real infrastructure").

## 16. Failure handling — governed explicitly, not left implicit

- If transactional success-audit staging fails, the attribution mutation must fail/roll back with it
  (no partial success).
- If the final session commit fails (connectivity, deferred constraint), neither the mutation nor the
  success audit becomes durable.
- If the request process crashes after the database commit but before the HTTP response is sent, the
  already-committed mutation and success audit both legitimately remain durable — this is expected,
  matches every other at-least-once-delivery web API in this platform, and is not itself a defect.
- **Request replay/idempotency remains a separate, pre-existing concern**, unaffected and unaddressed
  by this Decision — a retried request produces a new, independent attempt with its own audit trail
  either way.
- **Storage side-effect compensation remains separately governed** by `ADR-026`'s already-accepted,
  unsolved orphaned-object risk — not touched, redesigned, or newly claimed to be solved by anything
  in this Decision (consistent with §13).

## 17. Batch sequencing

- **Batch 1** (this Decision): the split-path capability plus the two `ADR-028` attribution events,
  exactly as scoped in §5.
- **Later batches**: the remaining 29 successful-mutation call sites (§6), grouped by bounded context
  (a plausible, non-binding grouping: Registry `parcel_service.py`, Identity `admin_service.py` and
  `auth_service.py`, Evidence `evidence_service.py`, Spatial `spatial_service.py`) and independently
  verified — each batch proven against the same transaction invariant (§8) and non-regression
  guarantee (§9) as Batch 1 — before migration. **This Decision establishes these sequencing
  principles but does not itself authorize migration of any call site beyond the two named in §5.**
  Each later batch requires its own separate governance act (a future numbered Governance Decision
  naming this one, or an ADR-level revisit if a later batch's context reveals a genuinely new
  architectural question `ADR-029`'s existing invariants do not already answer).

## 18. Ambiguous calls — remain unclassified, not guessed

The two ambiguous sites `ADR-029` identified —
`AdminService.get_delegation`'s `identity.delegation.invalidated` (fired during a read, no mutation
attempted) and `AuthService._authorize_invitation_redemption`'s `authority_lost_reason` branch of
`identity.invitation.redemption_denied` (a real invitation-revoke mutation and a denial audit sharing
one call) — **must remain on their current, independent, eager-commit semantics** through Batch 1 and
until a future, separate governance act classifies each individually. Batch 1's implementation must
not guess a classification for either.

## 19. Implementation PR boundary

The eventual Batch 1 implementation must be **one bounded feature branch/PR**, containing only:

- the audit-kernel/internal abstraction changes strictly required for the split successful-mutation
  path (§7);
- `attribution_service.py`'s migration of its two success events (§5.3);
- the tests required by §15;
- minimal supporting documentation, if required (e.g., updating `ADR-029`'s own migration-matrix
  status for these two call sites once actually migrated).

**The following are explicitly excluded from that PR** — the HTTP gate (§14) remains independent of,
and later than, Batch 1's own merge, and none of the following may appear in it, individually or in
combination:

- the `ADR-028` HTTP router;
- HTTP request/response DTOs created solely in preparation for future attribution exposure;
- OpenAPI specification changes;
- generated API clients;
- generated schema clients;
- frontend components or pages;
- Surveyor Dashboard functionality.

The implementation PR authorized by this Decision is audit-semantics infrastructure, the two
attribution-call migrations named in §5, and their tests — nothing else.

## 19.1 Dependency stop-gate (Engineering Rule #5)

No new runtime dependency is authorized by this Decision. If implementation reality indicates one is
required, **Engineering Rule #5 applies**, and implementation must stop and return to Governance
before introducing it — this Decision does not pre-authorize any dependency, named or unnamed.

## 19.2 Constitutional / non-adjudication safeguard

Audit transaction semantics, as decided by `ADR-029` and implemented under this Decision, establish
only the durability relationship between a recorded platform event and its corresponding state
transition. An audit event does not determine land ownership, title validity, professional
certification, government approval, or legal truth.

## 19.3 Explicit programme exclusions

For auditability and consistency with `docs/GD-008-surveyor-network-phase-0-principles-and-authorization-boundary.md`,
`docs/adr/ADR-026-evidence-domain-model.md`, and `docs/adr/ADR-028-evidence-actor-and-commissioning-provenance.md`'s
own out-of-scope conventions: this Decision does not authorize Marketplace; the Partner programme;
Job; Assignment; Customer; accreditation; payments; SECI; EQF; the Professional Performance Index;
Rights or licensing; Legacy Vault; `ADR-021` functionality; or general Background Jobs
infrastructure. None of these is touched, implied, or brought closer to authorization by this
Decision's subject matter.

## 20. Decision effect — three distinct authorities, not one

- **Architecture authority:** `ADR-029` (Accepted, 2026-09-11). Decides *what* the correct transaction
  semantics are.
- **Implementation authority:** *this Decision*, once ratified. Decides *that* Batch 1, and only
  Batch 1, may now be built.
- **HTTP/API authority:** **still not granted, by anything.** Neither `ADR-029`'s acceptance nor this
  Decision's ratification authorizes `ADR-028`'s HTTP exposure — that remains a distinct, later,
  explicit Governance act, gated as stated in §14.

Ratification of this Decision authorizes **Batch 1 implementation only** — nothing broader is granted
by implication.

## 21. Article XVI entry

The following text is inserted into `docs/LV-000-constitution.md`'s Article XVI Log as part of this
ratification (a separate edit to that file, not by this document itself):

> **GD-009 — Audit Transaction Semantics Implementation Authorization and ADR-007 Regularisation.**
> *(Ratified 11 September 2026.)* Operative authority: **Article XVI §2** — GD-009 is a later
> numbered decision that explicitly names and qualifies `docs/adr/ADR-007-audit-trail-evidence-model.md`
> Decision 1 and relies on `docs/adr/ADR-029-audit-transaction-semantics-and-outcome-integrity.md`
> (Accepted, 2026-09-11) as its governing architecture; it is not proposed under Article XIV and does
> not amend this Constitution.
>
> `ADR-007` Decision 1's literal "written atomically" text was contradicted, in production, by the
> audit kernel's deliberate eager-independent-commit design — proven directly against real Postgres
> by `docs/AUDIT_KERNEL_ATOMICITY_REALITY_AUDIT.md` and resolved at the architecture level by
> `ADR-029`'s two class-specific invariants (successful-mutation audit commits/rolls back with its
> mutation; denial/failure audit remains independently durable). `ADR-007` Decisions 2–5, and
> `ADR-007` itself, are unaffected; no historical audit record is rewritten, and no historical record
> is newly claimed to have possessed a transactional guarantee it did not have at the time it was
> written.
>
> **Decision.** Implementation of `ADR-029`'s accepted split-transaction architecture is authorized,
> strictly bounded to Batch 1: a transaction-coupled successful-mutation audit capability using the
> caller's existing session, selected **explicitly, per call, at each authorized site only** — never
> through ambient, default, or global rebinding of the existing `audit()` path — and migration of
> exactly `evidence.actor_attribution.recorded` and `evidence.actor_attribution.corrected` (the two
> call sites gating `docs/adr/ADR-028`'s future HTTP surface) to that path. Denial/failure auditing,
> and every other successful-mutation call site (29 of 31 total, per the verified 54-call-site
> inventory), remain unchanged pending their own, separately governed batches. Batch 1 must
> additionally prove, against real PostgreSQL, that this capability does not introduce a fork,
> duplicate predecessor reference, or other audit-chain integrity violation under concurrent writers;
> a proven violation halts implementation and returns to Governance rather than being engineered
> around within Batch 1's own authority.
>
> **Scope excluded — no retroactive expansion.** This decision does not authorise migration of any
> call site beyond the two named above; a transactional outbox, Kafka, CQRS, or event sourcing; any
> new background-worker infrastructure or runtime dependency; any schema migration (none is required);
> any redesign of Supabase Storage or `ADR-026`'s orphaned-object compensation semantics; or exposure
> of any `ADR-028` HTTP endpoint (including its router, DTOs, OpenAPI surface, generated clients, or
> frontend). `ADR-028`'s HTTP gate remains independently conditioned on Batch 1's full implementation,
> test, review, merge, and post-merge verification (§14 of this Decision's own operative text) — this
> Log entry does not itself lift that gate.

## Approval Gate

This Governance Decision is **ACCEPTED**, per the Ratification Record above. Acceptance authorizes
only Batch 1 as described in §5 — the same category of authorization `docs/adr/
ADR-026-evidence-domain-model.md` gave its own "B5.2" implementation — never anything broader.

**Explicit exclusions.** Ratification does not authorize: migration of any of the 52 call sites
excluded by §6; classification of either ambiguous site (§18); any implementation shape prohibited by
§5's anti-ambient-rebinding rule; any concurrency-architecture response prohibited by §11's hard stop;
any schema migration (§12) or new runtime dependency (§19.1) absent a further stop-and-return to
Governance; the `ADR-028` HTTP router, DTOs prepared for future exposure, OpenAPI changes, generated
clients, frontend, or Surveyor Dashboard work (§19); or any of the programmes named in §19.3.

**ADR-028 API dependency, restated.** `evidence.actor_attribution.recorded`/`corrected` must be
implemented, tested, formally human-reviewed, squash merged, and post-merge verified under Batch 1
before `ADR-028`'s mutating HTTP attribution endpoints may be exposed (§14). Ratification of this
Decision does not, by itself, satisfy that condition.

See the companion readiness report, `docs/GD-009_READINESS_REPORT.md`, preserved as the point-in-time
pre-ratification readiness record, and the subsequent Governance review and textual-remediation
verification that preceded this ratification.
