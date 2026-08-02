# ADR-026 — Evidence Domain Model

**Status:** Accepted — Governance Authority authorization, "B5.2 — Evidence Domain Model
Implementation." Slice B5.2 (the `EvidenceRecord` aggregate, its migration, its repository, and its
application-service/DI wiring — explicitly *not* its API; upload endpoints remain out of scope for
B5.2) is authorized to proceed on this basis. `StoragePort` (Slice B5.1) was never gated by this ADR
— see "Relationship to Slice B5.1" below.

**Date:** 2026-08-01

**Revision note:** revised against a narrower Governance Authority charter for this ADR specifically
(EvidenceRecord aggregate, EvidenceRepository port, invariants, lifecycle, relationship to Parcel,
custody model, hash model, legal hold model, identifiers, repository responsibilities, transaction
boundaries, domain events — nothing else). Adds explicit "Transaction boundaries" and "Domain events"
subsections that the first draft left implicit; makes no other substantive change. Confirmed, on
re-review against that charter: this document does not redesign `StoragePort`, Supabase Storage,
Cloudflare R2, hashing algorithms, authentication, authorization, audit, or parcel ownership — each
is referenced to its own governing ADR (ADR-024/ADR-025 for storage; ADR-007 for the audit mechanism
and the SHA-256 convention it already established; ADR-013/ADR-015/ADR-023 for Parcel/ownership),
never redecided here.

**Scope:** Defines the `EvidenceRecord` aggregate — its identity, lifecycle, fields, and invariants
— and the `EvidenceRepository` port shape it is persisted through. This is the same category of
decision ADR-013 made for `Parcel` and ADR-018 made for `ParcelGeometry`: a new aggregate's domain
model, decided before its first migration, per LV-000 v1.8 Article VI §1 ("Architecture Before
Code"). Out of scope, decided elsewhere or deliberately deferred:

- **`StoragePort`'s own shape** — already decided (`docs/adr/ADR-024-delivery-platform-and-infrastructure-decisions.md`
  D1, refined by `docs/adr/ADR-025-supabase-platform-baseline.md` E3). This ADR does not redecide it.
- **Break-glass cross-tenant/cross-country evidence access** (ADR-007 decision 5) — a new
  Controlled Platform Authority instance requiring its own ADR before implementation, mirroring
  ADR-021's relationship to B4 Slice 3. Not decided here; explicitly deferred to a later, separately
  gated slice.
- **Merkle-tree/OpenTimestamps anchoring specifics** — architecture already named in ADR-007
  decision 1; exact implementation is a later slice's concern, not decided here.
- **Exact API URL shape and role-gating** — mirrors how ADR-013 decided `Parcel`'s domain model
  without deciding mutation authorization (that came later, as ADR-015); this ADR decides the
  aggregate, not its endpoint surface or authorization matrix.
- **Evidence type taxonomy's exact enum values** — a bounded set exists (§"Decision" below), but its
  precise membership is an implementation-time decision against real requirements, not fixed here
  as an irreversible schema commitment beyond what's needed to prove the pattern.

**Constitutional anchors:** LV-000 v1.8 Article IV (evidence over assertion, non-adjudication);
Article V §2 (bounded context sovereignty — Evidence is context #4 of 13, already named in
`docs/REBUILD_PLAN.md` §1, not invented here); Article VI §1 (Architecture Before Code); Article
VIII §2 (RLS ships with the migration); Article XII (evidence is structural, not asserted).

## Context

`docs/adr/ADR-007-audit-trail-evidence-model.md` already decided Evidence's architecture at a level
above any specific aggregate: real S3-compatible object storage with Object Lock, server-side
hashing with independent read-back verification, legal hold enforced as a guard at every
delete/archive/seal-release path, hash/integrity verification that actually recomputes, and a
break-glass dual-authorization mechanism for cross-tenant/cross-country access. None of that
architecture has been reduced to a persisted aggregate yet — no `EvidenceRecord`, no migration, no
`Document` entity of any kind exists anywhere in this codebase (confirmed by repository-wide search,
`docs/PHASE-B5_IMPLEMENTATION_PLAN.md` §1.5/§1.6).

`docs/PHASE-B5_IMPLEMENTATION_PLAN.md` (Phase 1–5 planning package, this same programme) and its
follow-up Phase Sequence Reconciliation Report already established, from repository evidence: (a) no
existing ADR blocks B5 beyond what this ADR itself must supply (ADR-021 blocks only B4 Slice 3); (b)
`docs/ENGINEERING_RULES.md` §10 (non-adjudication check) is implemented and already covers Registry;
(c) B5's core features (upload, hashing, WORM sealing, chain of custody, legal hold) have no
technical dependency on Spatial Conflict Detection, geometry, or survey validation. This ADR is the
next step that planning package's own Phase 2 (ADR determination) concluded was required: a
domain-model ADR for the `EvidenceRecord` aggregate specifically, following exactly the precedent
`docs/adr/ADR-013-parcel-aggregate-registry-domain-model.md` set for `Parcel` and
`docs/adr/ADR-018-spatial-domain-model.md` set for `ParcelGeometry` — architecture decided, and
reviewed, before the first migration exists.

## Decision

### The `EvidenceRecord` aggregate

`EvidenceRecord` (`app.contexts.evidence.domain.evidence_record`) is the single, canonical
representation of one uploaded piece of evidence. `evidence_id` (a UUID, matching every other
aggregate's `<name>_id` convention in this codebase) is its immutable identity, generated at
construction and never reassigned — mirroring `Parcel.parcel_id`/`ParcelGeometry`'s own identity
discipline exactly.

**Owned by the aggregate:**

- **Immutable identity:** `evidence_id`, `tenant_id`, `parcel_id` (a reference, resolved through a
  Registry-facing port `EvidenceRecord` itself never joins against directly — see "Relationship to
  Registry" below), `uploaded_by`, `created_at`.
- **Document metadata, immutable once hashed:** `filename`, `mime_type`, `size_bytes`, `sha256`
  (server-computed only; a client-supplied hash is never trusted or persisted as authoritative — the
  direct application of ADR-007 decision 4). SHA-256 is not a new algorithm choice this ADR is
  making: it is the algorithm `app.kernel.audit`'s hash chain already uses platform-wide (docs/
  PHASE-B5_IMPLEMENTATION_PLAN.md §1.4); this ADR reuses that existing convention rather than
  independently selecting one.
- **Lifecycle status, one-way and terminal like `Parcel.status`/`ParcelGeometry`'s own append-only
  discipline:** `RECEIVED` → `HASHED` → `SEALED`. No restore path, no reopening a sealed record —
  mirroring ADR-013 invariant #6 (`_ensure_mutable`) and ADR-015's identical archived-parcel
  discipline ("no override path... creator, governance role, and `super_admin` alike, no
  exception").
- **Legal hold — a separate, orthogonal boolean, not a status value:** `legal_hold: bool`,
  `legal_hold_reason: str | None`, `legal_hold_by: str | None`. Kept independent of `status` so a
  hold/release action never collides with, or is confused for, the upload lifecycle — a `SEALED`
  record can be under legal hold or not; the two dimensions vary independently.
- **Storage reference:** `storage_key` (an opaque, provider-agnostic string returned by
  `StoragePort.put`/`put_immutable` — never a raw S3/R2 URL persisted as though it were portable
  across adapters), `worm_grade` (`"governance"` | `"compliance"`, recorded at seal time from
  `StoragePort.worm_grade()`, per ADR-024 D1/ADR-025 E3 — not decided by this ADR, only consumed).
- **Provenance:** `basis` (free-text — what the upload asserts itself to be, e.g. "submitted by
  registrant as supporting survey documentation" — never what it is proven to be; mirrors ADR-023's
  own honest-narrow-`basis`-string discipline exactly, for the identical reason: no automated
  authenticity determination exists to back a stronger claim), `audit_ref` (the `AuditEntry.entry_id`
  for the upload action, same mechanism ADR-023 already established).
- **Evidence type:** a bounded enum (`SURVEY_PLAN`, `TITLE_DOCUMENT`, `IDENTITY_DOCUMENT`, `OTHER`)
  — a starting, deliberately small set; extending it is an additive, non-breaking change (a new enum
  member), not a reason to revisit this ADR.

**Explicitly not owned by the aggregate, deliberately, per this ADR's own scope:**

- **A `verified`/`authentic` boolean, or any field implying the platform has determined the
  document is genuine.** `EvidenceRecord` carries `status` (upload lifecycle) and `worm_grade`
  (storage integrity guarantee) — never an adjudication field. This is the direct, structural
  application of the non-adjudication doctrine (Article IV, `docs/ENGINEERING_RULES.md` §10) to the
  domain model itself, not only to API response wording.
- **Ownership determination of any kind.** `EvidenceRecord` never asserts who owns the parcel it
  evidences — that remains entirely Registry's concern (`current_owner_name`/`current_owner_contact`
  on `Parcel`, and `OwnershipAssertion` per ADR-023), unmodified by this ADR.
- **Merkle-anchoring/OpenTimestamps state** — reserved for whichever later slice implements that
  piece of ADR-007 decision 1; not a field on this aggregate today, added additively later if and
  when built, exactly as ADR-023 itself notes for its own `basis` column's forward compatibility
  with evidence references.
- **Cross-tenant/cross-country access records** — reserved for the future break-glass ADR (§"Out of
  scope" above); this aggregate carries no field anticipating that mechanism.

### Domain invariants (enforced as domain rules, not endpoint validation)

1. **`evidence_id` is immutable** — set once, at construction, never reassigned; no setter exists.
2. **`sha256`/`size_bytes`/`mime_type`/`filename` become immutable once `status` reaches `HASHED`**
   — a guarded mutation point, mirroring `Parcel.allocate_parcel_number()`'s "reserve the field"
   discipline: the fields exist from `RECEIVED`, but a mutator raises once they are set.
3. **`status` only ever moves forward** (`RECEIVED → HASHED → SEALED`), never backward, never
   skipped in a way that reaches `SEALED` without having passed through `HASHED` — a sealed record
   without a verified hash would defeat the entire integrity guarantee this context exists to
   provide.
4. **Once `SEALED`, no field on the aggregate may change except `legal_hold`/`legal_hold_reason`/
   `legal_hold_by`.** This mirrors `Parcel._ensure_mutable()`/`ParcelArchivedError`'s discipline
   exactly: a guard every mutator calls first, raising `EvidenceSealedError` for anything outside
   the legal-hold fields.
5. **Legal hold blocks deletion-adjacent operations unconditionally** — no privileged bypass for any
   role, mirroring ADR-015's identical archived-parcel discipline ("creator, governance role, and
   `super_admin` alike, no exception, no override path"). This ADR states the invariant; the guard's
   exact call sites (delete/archive/seal-release) are Slice B5.6's implementation, per
   `docs/PHASE-B5_IMPLEMENTATION_PLAN.md`'s roadmap.
6. **Every mutation creates an immutable audit event** — reuses the kernel `audit()` function
   (ADR-007) unchanged; no second audit mechanism, matching every prior ADR's precedent in this
   codebase without exception.
7. **Tenant isolation is absolute** — RLS (same policy shape as every tenant-scoped table since
   migration `0001`) plus an explicit application-layer tenant filter, the same two-independent-
   layers pattern every prior context has used.
8. **No `EvidenceRecord` command bypasses the existing PDP** — no new authorization mechanism is
   introduced by this ADR (exact role-gating is left to the implementing slice, per "Out of scope"
   above, but it will compose from the existing PDP/PEP, never a second path).

### `EvidenceRepository` port

Mirrors `ParcelHistoryRepository`'s deliberately narrow shape (`docs/adr/
ADR-023-registry-ownership-and-status-history.md`) — no generic update/delete method exists on the
Protocol at all; only the specific, guarded lifecycle transitions do:

```python
class EvidenceRepository(Protocol):
    async def add(self, record: EvidenceRecord) -> EvidenceRecord: ...
    async def get(self, evidence_id: str) -> EvidenceRecord | None: ...
    async def list_for_parcel(self, parcel_id: str) -> list[EvidenceRecord]: ...
    async def mark_hashed(self, record: EvidenceRecord) -> EvidenceRecord: ...
    async def seal(self, record: EvidenceRecord) -> EvidenceRecord: ...
    async def set_legal_hold(self, record: EvidenceRecord) -> EvidenceRecord: ...
```

A Postgres adapter (`app.contexts.evidence.adapters.postgres_repositories.PostgresEvidenceRepository`)
and an in-memory fake (`backend/tests/fakes/evidence.py`) implement this Protocol once this ADR is
accepted — neither exists yet; both are Slice B5.2 work, not part of this ADR.

### Transaction boundaries

`EvidenceRepository`'s Postgres adapter, once built, must be constructed from the same per-request
`AsyncSession` (`app.kernel.uow.get_db_session`) as every other repository in this codebase — the
identical Unit-of-Work discipline ADR-023 established for `ParcelHistoryRepository`. An
`EvidenceRecord` row's `INSERT`/`UPDATE` and its corresponding audit entry commit or roll back
together, within one request's transaction, exactly as ADR-023's history rows do.

**One boundary is genuinely new here and did not exist in ADR-023's shape: `StoragePort` writes to
a system outside Postgres entirely, so they cannot share that transaction.** This ADR fixes the
required ordering, since getting it wrong has a real integrity consequence: **the `StoragePort`
write (`put`, at `RECEIVED`; `put_immutable`, at `SEALED`) must complete and return a `storage_key`
*before* the corresponding `EvidenceRecord` row referencing that key is persisted.** The reverse
order — a database row created first, referencing a `storage_key` a subsequent storage write might
still fail to produce — would let a caller observe an `EvidenceRecord` that claims to hold data no
object actually backs, which this context's entire integrity purpose exists to prevent. The
accepted, named residual risk of the required ordering is the opposite failure: a storage write
that succeeds, followed by a database write that then fails or rolls back, can leave an orphaned
object in storage with no `EvidenceRecord` referencing it — unreferenced storage is a housekeeping/
garbage-collection concern, not an integrity or security defect, and its cleanup mechanism is
implementation-time work for whichever slice needs it, not decided by this ADR (mirroring how
ADR-023 named its own "no orphan history row" gap honestly rather than silently assuming it away).

### Domain events (audit)

No new event-bus or audit mechanism — reuses the existing kernel `audit()` function (ADR-007)
unchanged, exactly as every prior ADR in this codebase has, without exception. New action names:
`evidence.uploaded` (at `RECEIVED`), `evidence.hashed` (at `HASHED`), `evidence.sealed` (at
`SEALED`), `evidence.legal_hold.applied`, `evidence.legal_hold.released`. Each `EvidenceRecord`'s
`audit_ref` is set to the corresponding `AuditEntry.entry_id`, the same "resolvable reference" shape
ADR-023 already established for its own history rows — not a new pattern.

### Relationship to Slice B5.1 (`StoragePort`) — not gated by this ADR

`StoragePort`'s method signatures (`put`/`get`/`list_keys`/`put_immutable`/`worm_grade`) were
already decided by ADR-024 D1, refined by ADR-025 E3 — nothing about defining that Protocol, or an
in-memory fake proving its semantics, requires a new architectural decision. This mirrors exactly
how `docs/adr/ADR-016-geometry-port-boundary-spatial-integration.md` shipped `GeometryPort` and its
`PlaceholderGeometryAdapter` a full programme (B3 Slice 4) before `docs/adr/
ADR-018-spatial-domain-model.md` decided the aggregate (`ParcelGeometry`) that would eventually
supply a real implementation — the port-before-aggregate sequencing is established precedent, not a
novelty introduced by this ADR. `StoragePort` therefore proceeds under its own already-accepted
governance (ADR-024/025) and is not blocked on this ADR's acceptance; `EvidenceRecord`'s migration,
repository, service, and API are.

### Relationship to Registry

Mirrors the Registry↔Spatial boundary exactly (`GeometryPort`, `docs/PHASE-B5_IMPLEMENTATION_PLAN.md`
§4.6/§1.7): Evidence depends on Registry through a port **Evidence itself defines**
(`ParcelExistencePort`-shaped — tenant/existence check only), never a direct join against
`parcels`. Registry is never imported by Evidence's adapters; Registry never imports Evidence at
all, and holds at most an opaque `evidence_id` reference where a future, additive change to
`parcel_ownership_history.basis` cites one (ADR-023's own stated forward-compatibility, unchanged by
this ADR).

## Relationship to the frozen baseline

- **ADR-007** — this ADR is the first aggregate-level realization of ADR-007's already-decided
  architecture; it does not revisit hashing, WORM, legal hold, or break-glass as concepts, only
  gives `EvidenceRecord` the shape needed to carry them.
- **ADR-013** — `Parcel`'s domain contract is untouched; `EvidenceRecord.parcel_id` is a reference
  Evidence resolves through a port, never a modification to `Parcel` itself.
- **ADR-015** — no new authorization model; exact role-gating is an implementing-slice decision that
  will compose from the existing PDP/PEP, per "Out of scope" above.
- **ADR-023** — `basis` on `parcel_ownership_history` remains a free-text string today; a future,
  separate, additive decision may let it reference `evidence_id` structurally. Not decided or
  required by this ADR.
- **ADR-024/ADR-025** — `StoragePort`'s shape is consumed, not redecided (see "Relationship to Slice
  B5.1" above).
- **No frozen decision requires amendment.**

## Consequences

- Slice B5.2 (migration `0012`, `EvidenceRecord` domain, `EvidenceRepository` adapters) has a
  reviewed, accepted domain model to build against, exactly as ADR-013 gave B3 Slice 1 and ADR-018
  gave B4 Slice 1.
- Slice B5.1 (`StoragePort`) is confirmed independent and may proceed under this same programme
  without waiting on this ADR's acceptance.
- The break-glass cross-tenant mechanism (ADR-007 decision 5) remains explicitly ungoverned by any
  accepted ADR and may not be implemented until its own, separately gated ADR is accepted — this ADR
  does not authorize it, by omission or implication.
- The non-adjudication check (`docs/ENGINEERING_RULES.md` §10, already implemented and covering
  Registry) will need its blocklist/scan surface extended to cover Evidence's future API responses
  once Slice B5.3 (upload endpoint) exists — noted here as a known follow-up, not performed by this
  ADR.

## Approval Gate

This ADR is **Accepted**. Slice B5.2 (the `EvidenceRecord` aggregate, its migration, its repository,
and its application-service/DI wiring) is authorized. The upload endpoint / API surface remains a
separately scoped, later slice (B5.3), per the Governance Authority's B5.2 implementation
authorization — this ADR's own "Out of scope" section already declined to decide the API shape, and
that remains true after acceptance. Slice B5.1 (`StoragePort`) was never gated by this ADR and
proceeded under ADR-024/025's existing acceptance.
