# GD-011 — GD-009 Batch 1 Resumption Authorization

**Status:** **ACCEPTED — 2026-09-15, on explicit Governance Authority ratification. IN FORCE.** This
Decision authorizes exactly one thing — lifting `GD-009` §11's concurrency-related execution
suspension on Batch 1 — the same category of narrowly-scoped resumption authorization `GD-007`
already gave its own qualification of `GD-004`. It does **not** re-authorize, expand, or narrow Batch
1 beyond `GD-009` §5's original scope, and does not itself authorize `ADR-028`'s HTTP exposure; see
"Explicit exclusions" under "Approval Gate" below.

**Date drafted:** 2026-09-15. **Ratified:** 2026-09-15.

**Operative authority:** **Article XVI §2** — this is a later numbered decision that explicitly names
`docs/GD-009-audit-transaction-semantics-implementation-authorization-and-adr-007-regularisation.md`
(to lift its concurrency-related execution suspension only) and relies on `docs/adr/
ADR-030-audit-chain-concurrency-ordering-and-linearization.md` (Accepted, 2026-09-13) and `docs/
GD-010-audit-dag-verifier-implementation-authorization.md` (Accepted, 2026-09-14; implementation
merged and post-merge verified, 2026-09-15) as jointly satisfying the specific prerequisite GD-009
§11 itself named as its own stop-and-return condition. It does not amend `ADR-029`, `ADR-030`, or
`GD-010`. It is not proposed under Article XIV and does not amend this Constitution.

## Ratification Record

Ratified by Governance Authority for AquaSavannah LandVault, **2026-09-15**, following an independent
final ratification review (`GD-011 FINAL RATIFICATION REVIEW PASS — READY FOR SEPARATE RATIFICATION
ACTION`) that re-derived every material claim below directly from repository state. This record does
not alter the draft; it identifies what ratification covers:

- **Authority chain satisfied**: `ADR-029` → `GD-009` (Batch 1 authorization + §11 concurrency hard
  stop) → `ADR-030` (DAG topology, resolves the hard stop's architecture question) → `GD-010`
  (verifier implementation authorization, merged via PR #33 and post-merge verified) → this Decision
  (lifts the specific suspension only).
- **The underlying concurrency race is not eliminated** — restated from §3: the read-before-append
  `prev_hash` race remains an expected property of concurrent audit writes; what changed is that
  `ADR-030`/`GD-010` now correctly classify and verify a resulting legitimate shared-predecessor fork,
  rather than misreport it as corruption.
- **GD-011 modifies GD-009 §11's execution state only** — restated from §5: solely lifting the Batch 1
  suspension; all other `GD-009` provisions remain in force, unaffected and unamended.
- **Resumed scope is exactly `GD-009` §5** (§6): the transaction-coupled capability, migrating exactly
  `evidence.actor_attribution.recorded` and `evidence.actor_attribution.corrected`; no third event, no
  broader authority.
- **DAG compatibility, no linearisation** (§9): a shared predecessor is expected, not a defect; no
  lock, `SERIALIZABLE`, chain-head table, sequence, `UNIQUE(prev_hash)`, retry, or outbox is
  authorized.
- **Verifier and hash semantics remain frozen** (§10–§11): `verify_chain()`, its six invariants,
  `_compute_hash`, and `GENESIS_HASH` are unaffected; a stop-and-return applies if implementation
  reality is found to require otherwise.
- **No migration and no new dependency are authorized** (§12–§13); the exact `GD-009` stop phrases are
  preserved.
- **`ADR-028` HTTP/API authority remains ungranted** (§19); its full original sequencing gate is
  unshortened.
- **The preserved branch** `feat/gd009-batch1-transactional-audit` (§17–§18) remains reference/evidence
  only; the resumed implementation must be reconstructed in a fresh worktree off current `main`, never
  incorporating that branch's files wholesale.
- **The `GD-010` 8-vs-9 file-count discrepancy** (§22) is recorded as non-substantive and is not
  corrected by this Decision.

## 1. Governance baseline verified for this drafting

Read directly against the current repository, not assumed or carried over from any prior document:

- `origin/main` SHA: **`54af267bda08e5dc88d052a3cac126567cea3b03`** — the GD-010 DAG-aware audit
  verifier's squash-merge commit (PR #33), confirmed a single-parent commit (parent
  `a093c497dd2b2dc2dbc02291254f4994fe6ebbd7`, the GD-010 ratification squash, PR #32), confirmed the
  current tip of `main`, confirmed tree-identical to the formally human-approved PR #33 head
  (`73ea2aed7f10344f5513a09fd53ebb1f5da67331`), confirmed via all required CI checks green on the
  squash commit itself.
- `docs/adr/ADR-030-...md`: **ACCEPTED — 2026-09-13, on explicit Governance Authority ratification.
  IN FORCE.**
- `docs/GD-010-...md`: **ACCEPTED — 2026-09-14, on explicit Governance Authority ratification. IN
  FORCE.** Its implementation (the DAG-aware `verify_chain()` rewrite, PR #33) is merged and has been
  independently post-merge verified this session: exact landed files
  `backend/app/kernel/audit.py`, `backend/tests/test_audit_dag_verifier.py`; all required CI green on
  the squash commit; no secret/credential material in the landed diff.
- `docs/GD-009-...md`: **ACCEPTED — 2026-09-11, on explicit Governance Authority ratification. IN
  FORCE** — Batch 1 implementation remains suspended per its own §11 stop-and-return condition, which
  this Decision addresses.
- `docs/adr/ADR-029-...md`, `docs/adr/ADR-007-...md`: unaffected, unmodified by anything in this
  drafting.
- `docs/adr/ADR-028-...md`: HTTP exposure gate unaffected and unchanged.
- Article XVI Governance Decision Log (`docs/LV-000-constitution.md`): entries **GD-001 through
  GD-010** exist. No `GD-011` or higher entry exists anywhere in the repository (checked by direct
  search of every `docs/GD-0*.md` file and of the Log itself, not assumed).
- **Next available Governance Decision number, confirmed by repository reality: GD-011.**
- **Preserved branch** `feat/gd009-batch1-transactional-audit`: read-only inspected for this drafting,
  not modified. Its uncommitted working-tree state (5 modified files —
  `backend/app/contexts/evidence/application/attribution_service.py`,
  `backend/app/contexts/evidence/dependencies.py`, `backend/app/kernel/audit.py`,
  `backend/app/kernel/audit_postgres.py`, `backend/tests/test_evidence_actor_attribution_service.py`
  — plus one untracked live-concurrency test and several untracked ADR-030/GD-010 drafting
  documents already since superseded by their ratified, merged versions) is unchanged from every
  prior inspection this session. This diff was authored against a pre-`ADR-030`/`GD-010` baseline and
  predates the DAG-aware verifier entirely.

## 2. Purpose

This Decision does exactly one thing: **lifts `GD-009` §11's concurrency-related execution
suspension on Batch 1**, because the specific prerequisite that suspension named — a DAG-aware
verifier, conforming to an accepted chain-topology architecture, implemented, formally reviewed,
squash merged, and post-merge verified — now exists. It does **not** re-authorize, expand, narrow, or
otherwise alter Batch 1's scope beyond what `GD-009` §5 already authorized; it does not amend
`ADR-029`, `ADR-030`, or `GD-010`; and it does not itself authorize `ADR-028` HTTP exposure or any
other programme.

## 3. What was suspended, and why (restated, not re-litigated)

`GD-009` §11 found that the audit kernel's read-before-append `prev_hash` pattern
(`audit()`'s `prev_hash = await store.last_hash()` followed by a later, unlocked `store.append(entry)`)
exposes a genuine concurrency race — proven live against real PostgreSQL, both on the (then-)blocked
Batch 1 branch and, independently, on unmodified `origin/main`'s existing eager-independent path
(`docs/AUDIT_CHAIN_CONCURRENCY_REALITY_AUDIT.md` §3). `GD-009` §11 required that any such positive
finding halt implementation and return to Governance, naming the exact stop phrase
`GD-009 BATCH 1 BLOCKED — AUDIT CHAIN CONCURRENCY ARCHITECTURE REQUIRED` rather than permit an
implementing engineer to improvise a fix (a lock, `SERIALIZABLE` isolation, a sequence allocator, a
`UNIQUE(prev_hash)` constraint, or an outbox) inside Batch 1's own authority. `ADR-030` resolved the
architecture question this stop condition required — adopting a global hash-linked DAG topology and
a redefined, six-invariant verification semantics under which a shared-predecessor fork is a
legitimate, expected shape of concurrent writers, not corruption. `GD-010` authorized, and PR #33
implemented, formally reviewed, squash merged, and post-merge verified, the corresponding DAG-aware
`verify_chain()`.

The underlying read-before-append concurrency race has not been eliminated by `ADR-030` or `GD-010`
and remains an expected property of concurrent audit writes. Such concurrency may continue to produce
legitimate shared-predecessor forks; the architectural change is that those valid DAG structures are
now correctly recognised and verified rather than being misclassified as chain corruption.

## 4. Prerequisite satisfaction — verified directly, not assumed

- `ADR-030` Accepted 2026-09-13. ✓
- `GD-010` Accepted 2026-09-14. ✓
- PR #33 (verifier implementation) **MERGED** via squash commit `54af267...`, single parent
  `a093c497...` (the GD-010 ratification squash), current tip of `main`, tree-identical to the
  formally human-approved head `73ea2ae...`, all required CI (`pytest / ruff / mypy`,
  `typecheck / lint / test / build`) green on the squash commit itself, no secret/credential material
  in the landed diff. ✓
- Post-merge classification independently reached this session: **`POST-MERGE VERIFIED — GD-010 DAG
  VERIFIER ACTIVE ON MAIN`**. ✓

Therefore `GD-009` §11's stop condition's underlying concern is now architecturally resolved (by
`ADR-030`) and operationally resolved (by `GD-010`'s merged, verified implementation) — not merely
asserted to be.

## 5. Decision

**`GD-009` Batch 1's concurrency-related execution suspension is LIFTED.** `GD-009`'s original Batch 1
implementation authority (its own §5) may now be resumed, **exactly as originally scoped — no
broader authority is created by this Decision.**

`GD-011` modifies the execution state established by `GD-009` §11 solely by lifting the Batch 1
suspension; all other `GD-009` provisions remain in force, unaffected and unamended by this Decision.

## 6. Resumed scope — exactly GD-009 §5, restated, not widened

1. A transaction-coupled successful-mutation audit capability using the caller's existing
   Unit-of-Work session — capability, semantics, and boundary authorized; no specific method name or
   signature prescribed (per `GD-009` §5.1/§7).
2. Preservation, unmodified, of the existing independent path for every denial/failure audit call
   site.
3. Migration of **exactly two call sites**:
   `evidence.actor_attribution.recorded` and `evidence.actor_attribution.corrected`
   (`app/contexts/evidence/application/attribution_service.py`,
   `EvidenceActorAttributionService.record_attribution`/`correct_attribution`).

**No additional call site among the remaining 52 (29 unauthorized successful-mutation, 20 denial, 1
failure, 2 ambiguous — per `GD-009` §6/§18's own verified inventory) may be migrated under this
Decision.**

## 7. Explicit opt-in remains mandatory (restated from GD-009 §5)

The transaction-coupled path must be selected explicitly, in code, at each of the two authorized call
sites only. This Decision does not authorize, and Batch 1 must not implement the capability through,
any of: default replacement of the existing `audit()` path; global audit-store replacement;
request-scoped or session-scoped rebinding; ambient `ContextVar` repurposing of
`configure_audit_store`'s test-fixture pattern for production use; dependency-container rebinding; or
any other mechanism by which an unedited `audit()` call site could begin exhibiting transaction-coupled
behavior without its own source being touched.

## 8. Denial/failure path remains unchanged (restated from GD-009 §9)

Batch 1 must not touch the independent path's behavior. Representative denied/failed actions (at
minimum a `pep.py` role-gate denial and an `identity.refresh.replay_detected`-shaped case) must remain
provably, independently durable even when the surrounding business operation does not commit — the
exact regression `EagerPostgresAuditStore` was originally built to fix must not recur.

## 9. DAG compatibility — ADR-030 is now the governing topology

Batch 1 must treat the accepted global hash-linked DAG (`ADR-030` §1) as authoritative. Multiple
legitimate entries — including two concurrent transaction-coupled writes, or a transaction-coupled
write racing an eager-independent one — may share a predecessor; this is expected, not a defect. Batch
1 must **not** reintroduce mechanisms `ADR-030` considered and rejected as unnecessary: advisory locks,
`SERIALIZABLE` isolation, a chain-head table, a sequence allocator, a `UNIQUE(prev_hash)` constraint,
retry-on-conflict logic, or a transactional outbox. None of these is authorized by this Decision, and
none is required under the accepted architecture.

## 10. Verifier remains untouched

`app.kernel.audit.verify_chain()`, its six ADR-030 invariants, genesis semantics, branch legitimacy,
the completeness limitation, and ordering semantics are `GD-010`'s settled, merged, post-merge-verified
implementation. This Decision does not reopen, and Batch 1 must not modify, any of them. **If Batch 1
implementation reality is found to require a verifier change, the implementing engineer must stop and
return to Governance** rather than modify the verifier under this Decision's authority.

## 11. Audit hash semantics remain unchanged

`_compute_hash`'s inputs, `GENESIS_HASH`, and audit-entry identity semantics are unaffected. Batch 1
concerns transaction semantics only, not a redesign of audit cryptography.

## 12. No schema migration by default

`GD-009` found no schema migration necessary for Batch 1's architecture; nothing in `ADR-030`/`GD-010`
changes that finding. No migration is authorized by this Decision. If implementation reality proves
one unavoidable, the implementing engineer must stop and return exactly:

**`GD-009 BATCH 1 BLOCKED — MIGRATION AUTHORITY REQUIRED`**

## 13. No new runtime dependency

No new runtime dependency is authorized. If implementation reality indicates one is required,
Engineering Rule #5 applies, and the implementing engineer must stop and return exactly:

**`GD-009 BATCH 1 BLOCKED — NEW DEPENDENCY AUTHORITY REQUIRED`**

## 14. Atomicity tests remain mandatory (restated from GD-009 §8/§15 items 1–4)

The resumed implementation must include real transaction-level tests, against real PostgreSQL
(`docs/ENGINEERING_RULES.md` rule 7), proving:

1. Successful attribution record + audit commit together.
2. Successful attribution correction + audit commit together.
3. A forced rollback after audit staging leaves neither the attribution row nor the audit row durable.
4. A forced audit-stage failure prevents the business mutation from committing.
5. No intermediate commit clears request-scoped RLS/`is_local` context for the remainder of the
   request (`GD-009` §10, verified directly against `app/kernel/uow.py`).
6. Denial and failure audits remain independently durable when the surrounding business transaction
   does not commit (`GD-009` §9 regression guard).

## 15. Concurrency tests remain mandatory, re-evaluated under ADR-030/GD-010 semantics

`GD-009` §15 item 10's three cases (transactional-vs-transactional; transactional-vs-eager-independent;
repeated execution to expose timing-sensitive behavior) remain mandatory, against real PostgreSQL —
but the **evaluation criterion changes**, and the resumed implementation's own test report must apply
the correct one:

- A shared `prev_hash` between two legitimate, independently-hash-valid entries (the exact
  `A → {B, C}` shape `ADR-030`/`GD-010` establish as legitimate) is **not, by itself, a failure** —
  under `GD-009`'s original, strict-linear evaluation criterion it would have been; under the now-
  accepted DAG architecture it is an expected, valid outcome.
- The test must instead establish, for every entry produced by the concurrency scenario: per-entry
  hash validity; referential validity (every `prev_hash` resolves); reachability to genesis;
  acyclicity; and that `verify_chain()` (the now-merged, DAG-aware implementation) returns `True`
  against the resulting dataset.
- A genuine defect — an invalid hash, a dangling reference, an actual cycle, or a `verify_chain()`
  failure the DAG-aware invariants do not excuse — remains a stop-and-return condition, exactly as
  `GD-009` §11 originally required, though the specific architectural blocker §11 named
  (`GD-009 BATCH 1 BLOCKED — AUDIT CHAIN CONCURRENCY ARCHITECTURE REQUIRED`) is now resolved and would
  not itself recur from a legitimate fork alone.

## 16. Completeness/ordering limitations preserved

Nothing in this Decision alters `ADR-030` §6's completeness limitation (terminal-leaf, whole-branch,
or tail-truncation deletion may remain undetectable) or §7's ordering semantics (`prev_hash` is a
predecessor/reference relation only, never a chronological total order). No anchor, checkpoint, WORM
mechanism, or external commitment is authorized by this Decision.

## 17. Preserved branch reconciliation strategy

`feat/gd009-batch1-transactional-audit` remains reproduction/prototype evidence only, exactly as
`GD-010` §21 and `ADR-030`'s own text already established, and is **not** incorporated into this
Decision or automatically approved production code. Its current uncommitted diff — 5 modified files
(`attribution_service.py`, `dependencies.py`, `audit.py`, `audit_postgres.py`,
`test_evidence_actor_attribution_service.py`; ~225 insertions, 33 deletions) plus one untracked
live-concurrency test — was authored against a pre-`ADR-030`/`GD-010` baseline and predates the
DAG-aware verifier entirely; its own modifications to `audit.py`/`audit_postgres.py` in particular
cannot be assumed compatible with the now-merged `verify_chain()` without direct comparison.

**This Decision directs**: the actual resumed Batch 1 implementation must be reconstructed in a fresh,
clean worktree/branch off current `main` (at or after `54af267...`), using the preserved branch solely
as reference/evidence for what a working transaction-coupled design can look like — never merged,
rebased, cherry-picked, or copied wholesale into the new branch without each element being reviewed
against `ADR-029`, `GD-009`, `ADR-030`, `GD-010`, and this Decision. The original preserved branch and
its uncommitted evidence must not be deleted, rewritten, force-cleaned, or otherwise altered by this
reconstruction.

## 18. No automatic incorporation of prototype code

The six preserved Batch 1 files are evidence of prior investigative work, not pre-approved production
code. Each proposed change carried forward from them must be independently justified against this
Decision's own scope (§6) and the invariants above (§9–§11) before being written into the new
implementation branch.

## 19. ADR-028 remains blocked

This Decision grants no `ADR-028` HTTP/API authority: no router, DTO, OpenAPI change, generated
client, frontend, or Surveyor Dashboard work. The original `GD-009` requirement stands: the two
attribution success-audit events must first be correctly migrated, tested, formally reviewed, squash
merged, and post-merge verified, and `ADR-028` HTTP exposure requires its own, further, separate
Governance authorization after that.

## 20. Other GD-009 audit callers remain out of scope

The 29 unauthorized successful-mutation call sites, the 20 denial sites, the 1 failure site, and the 2
ambiguous sites (`GD-009` §6/§18) remain entirely unaffected and unclassified by this Decision. No
broader transaction-semantics migration is authorized here; any future batch requires its own,
separate Governance act naming `GD-009` and this Decision.

## 21. No unrelated programmes

This Decision does not touch, authorize, or bring closer to authorization: Marketplace; the Partner
programme; Job; Assignment; Customer; accreditation; payments; the Surveyor Dashboard; SECI; EQF; the
Professional Performance Index; Rights or licensing; Legacy Vault; `ADR-021` functionality; or general
Background Jobs infrastructure.

## 22. GD-010 8-vs-9 documentation discrepancy — recorded, not corrected here

`GD-010`'s own ratified text describes the pre-existing `verify_chain()` consumer inventory as "9
hermetic test files," while repository reality (confirmed independently, twice, by direct grep) shows
exactly **8** pre-existing files (a 9th, `test_audit_dag_verifier.py`, was added by `GD-010`'s own
implementation, PR #33). This is a non-substantive historical inventory discrepancy in the ratified
`GD-010` document, with no effect on `ADR-030`, `GD-010`'s verifier validity, or this Decision's own
resumption authority. **This Decision does not correct it** — a future, separate, documentation-only
Governance action may do so if desired.

## 23. Article XVI entry

The following text is inserted into `docs/LV-000-constitution.md`'s Article XVI Log by this
ratification (a separate edit to that file, not by this document itself):

> **GD-011 — GD-009 Batch 1 Resumption Authorization.** *(Ratified 15 September 2026.)* Operative
> authority: **Article XVI §2** — GD-011 is a later numbered decision that explicitly names `docs/
> GD-009-audit-transaction-semantics-implementation-authorization-and-adr-007-regularisation.md` (to
> lift its concurrency-related execution suspension only) and relies on `docs/adr/
> ADR-030-audit-chain-concurrency-ordering-and-linearization.md` (Accepted, 2026-09-13) and `docs/
> GD-010-audit-dag-verifier-implementation-authorization.md` (Accepted, 2026-09-14; implementation
> merged and post-merge verified) as satisfying `GD-009` §11's own stop-and-return condition; it is not
> proposed under Article XIV and does not amend this Constitution.
>
> **Decision.** `GD-009` Batch 1's concurrency-related execution suspension is lifted. `GD-009`'s
> original Batch 1 implementation authority (its own §5) may resume, exactly as originally scoped: a
> transaction-coupled successful-mutation audit capability, explicit per-call opt-in only, migrating
> exactly `evidence.actor_attribution.recorded` and `evidence.actor_attribution.corrected`. No schema
> migration, no new runtime dependency, and no change to `verify_chain()`, `_compute_hash`, or
> `GENESIS_HASH` is authorized or required. The resumed implementation must independently prove, under
> `ADR-030`/`GD-010`'s DAG-aware verification semantics, that legitimate concurrent forks verify valid
> and genuine defects (invalid hash, dangling reference, cycle) still verify invalid.
>
> **Scope excluded — no retroactive expansion.** This decision does not authorise migration of any
> call site beyond the two named above; any `ADR-028` HTTP/API exposure; any lock, serialization,
> retry, or sequence mechanism; any external completeness anchor or checkpoint; or any of the
> programmes `GD-009`/`GD-008`/`ADR-026`/`ADR-028` already exclude. `ADR-028`'s HTTP gate remains
> independently conditioned on this resumed Batch 1's full implementation, test, formal review, squash
> merge, and post-merge verification.

## Approval Gate

This Governance Decision is **ACCEPTED**, per the Ratification Record above. Acceptance authorizes
only lifting `GD-009` §11's Batch 1 concurrency-related execution suspension, and resumption of
Batch 1 exactly as `GD-009` §5 already scoped it — never anything broader.

**Explicit exclusions.** Ratification does not authorize: migration of any call site beyond the two
named in §6; any `ADR-028` HTTP/API exposure; any lock, serialization, retry, sequence, or
external-anchor mechanism; any change to `verify_chain()`, `_compute_hash`, or `GENESIS_HASH`; any
schema migration or new runtime dependency absent a further stop-and-return to Governance (§12, §13);
wholesale incorporation of the preserved `feat/gd009-batch1-transactional-audit` branch's prototype
code without independent review (§17, §18); or any of the programmes named in §21.

See the companion readiness report, `docs/GD-011_READINESS_REPORT.md`, for the independent challenge
of this draft that preceded ratification.
