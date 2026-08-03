# B5 — Evidence Context: Repository Assessment, ADR Determination & Implementation Plan

**Status:** Planning package, **superseded in part by implementation progress** (this note is an
implementation-progress record only — no architectural decision in this document has changed).
`docs/adr/ADR-026-evidence-domain-model.md` (Slice B5.0's own deliverable, below) is now
**Accepted**. **Slice B5.1 (`StoragePort`) and Slice B5.2 (`EvidenceRecord` domain model, migration
`0012`) are implemented and live-verified**, on branch `feat/b5.2-evidence-domain-model` (commit
`50b970d`), **not yet merged to `main`** — see `docs/PHASE-B5-SLICE1_ACCEPTANCE_PACKAGE.md` and
`docs/PHASE-B5-SLICE2_ACCEPTANCE_PACKAGE.md` for full evidence. Slices B5.3 onward remain exactly as
planned below — not authorized, not begun.

**Date:** 2026-08-01 (planning); implementation progress recorded 2026-08-02.

**Author's note on scope discipline:** this document follows the same evidentiary standard as
ADR-023 and `docs/ENGINEERING_RULES.md` §10 — every claim below is either a direct citation of a file
in this repository or is explicitly marked as a proposal awaiting decision. Nothing is assumed
complete that was not observed complete.

---

## Executive Summary — two findings that must be resolved before implementation

Before the repository assessment, two findings surfaced during Phase 1 investigation that bear
directly on whether B5 can lawfully begin next, under this platform's own governance instruments.
Per `docs/ENGINEERING_RULES.md` rule 4 ("Claude must stop and ask a human when... Requirements are
ambiguous or conflict with an existing ADR") and LV-000 v1.8 Article III §3 ("Transparency over
convenience"), both are stated here plainly rather than smoothed over. Neither blocks *this planning
package* — the authorizing instruction already withholds implementation pending Governance Authority
approval — but both should be resolved as part of that approval, not discovered later.

### Finding 1 — B5 is not next in the platform's own binding phase order

`docs/EXECUTION_PLAN.md` §5 (Phase plan) and §12 ("Start here") sequence work as: **Phase 0
(stabilise delivery) → Phase 1 (Registry ownership/status history) → Phase 2 (B4 Spatial, Slices
1–3) → Phase 3 (B5 Evidence)**. §12 states explicitly: *"Phase 1 does not begin until Phase 0's gate
is met. B4 Spatial does not begin until Phase 1's gate is met. That sequence is Article X §4, and it
is not negotiable against a delivery date."* By the same clause, Phase 3 (B5) does not begin until
Phase 2's gate is met.

Phase 2's own gate (`EXECUTION_PLAN.md` §5, Phase 2 row) requires, among other things, "**overlaps
surfaced**" — i.e., B4 Slice 3 (Spatial Conflict Detection). Slice 3 is explicitly not authorized to
begin: `docs/adr/ADR-021-spatial-conflict-detection-and-controlled-cross-tenant-intelligence.md` is
**Proposed, not Accepted** ("No B4 Slice 3 implementation... begins until this document is reviewed
and explicitly accepted" — ADR-021, Approval Gate). LV-000 v1.8 Article VIII §2 confirms this at the
constitutional level: *"B4 — Spatial Foundation, through its currently-accepted slices (Slices 1–2,
frozen... B4 as a whole programme remains open pending Slice 3/ADR-021)."*

**Conclusion:** per the platform's own EXECUTION_PLAN.md and Constitution, B4's programme gate is not
met, and B5 (Phase 3) is therefore not yet authorized to begin under the existing phase order. The
authorizing instruction's framing of B5 as "the next governed implementation slice following B1–B3"
is accurate for the *bounded-context freeze record* (B1/B2/B3 are indeed frozen) but does not account
for the *phase-gate* ordering, which is a separate, also-binding instrument. This is not a reason to
refuse the planning work requested (Phases 1–5 below proceed on that basis), but it is a conflict a
human Governance Authority should resolve explicitly — either by closing Phase 2's gate first, or by
recording a deliberate, reasoned exception to the phase order (itself a governance act under Article
VI §2, not a default any single session may assume).

### Finding 2 — Engineering Rule §10 (non-adjudication check) is not implemented

The authorizing instruction states Rule §10 is "Implemented." A repository-wide search (`grep -ri
"non.adjudication\|adjudicat"` across `backend/`, plus the CI workflows) found no automated check
anywhere. `docs/ENGINEERING_RULES.md` rule 10 says so directly: *"This is not yet implemented as an
automated check anywhere in this codebase; it is recorded here as a required rule, not yet as a
satisfied one."* ADR-023 itself confirms the same: *"The non-adjudication automated check... remains
outstanding after this ADR's implementation lands... it should not be marked done until that check
actually exists and runs."* `docs/EXECUTION_PLAN.md` §7.6 lists this check as item 9 of Phase 1's own
test matrix, required for Phase 1's gate — meaning **Phase 1's gate, too, is not fully closed**, a
second instance of the same pattern as Finding 1.

**Conclusion:** B5 — which introduces the platform's first document/evidence-facing API surface and
is, if anything, at *higher* risk of ownership-adjudication wording than Registry's history endpoints
— should not ship without this check existing and covering it. This plan treats building the Rule
§10 CI check as an explicit prerequisite (Slice B5.0b, below), not an assumption.

---

## Phase 1 — Repository Assessment

*(Grounded in a full read-only pass over `backend/app`, `backend/migrations`, and the governance
corpus in `docs/`. File:line citations below are as observed on 2026-08-01.)*

### 1.1 Current registry model & Parcel aggregate

`backend/app/contexts/registry/domain/parcel.py` — `Parcel` is a plain `@dataclass`, no ORM/framework
coupling. Immutable identity (`parcel_id`, `tenant_id`, `country_code`, `origin`, `created_by`),
one-way terminal `status` lifecycle (`ACTIVE`→`ARCHIVED`, no restore), a guarded, once-only
`parcel_number`, registry metadata fields, and a **current-ownership reference only**
(`current_owner_name`/`current_owner_contact` — never a history, per ADR-013 invariant #12). An
`_ensure_mutable()` guard blocks every mutator once archived. `UPDATABLE_FIELDS` is an explicit
allow-list on the aggregate itself. `geometry_reference` is an opaque pointer into Spatial, never
interpreted by Registry.

### 1.2 Ownership/status history (ADR-023, migration `0011`)

`backend/app/contexts/registry/domain/history.py` defines `OwnershipAssertion`/`StatusAssertion` —
frozen value objects recording "who asserted what, on what basis, when," explicitly never a
determination of ownership. Persisted via `ParcelHistoryRepository` (Protocol, `ports.py:21-35`;
Postgres adapter `postgres_repositories.py:160-220`), populated as a side effect of the existing
`create_parcel`/`update_parcel`/`archive_parcel` commands — no new endpoint. Migration `0011` creates
two append-only tables (`parcel_ownership_history`, `parcel_status_history`) with: RLS `ENABLE` +
`FORCE`, the identical tenant-isolation predicate every tenant-scoped table has used since migration
`0001`; append-only enforced at **two independent layers** — `GRANT SELECT, INSERT` only (no
UPDATE/DELETE), plus a `BEFORE UPDATE OR DELETE` trigger that unconditionally raises, binding even
the schema-owning migration role; `supersedes_id` self-FK for corrections; `audit_ref` linking to a
real `AuditEntry`; no backfill (history begins at the migration epoch, by explicit, reasoned design).

**This is the closest and most directly reusable precedent in the codebase for B5's own chain-of-
custody and append-only-history needs**, and the model this plan's migration/repository design
follows (§4, below).

### 1.3 Existing storage abstraction

**None exists.** A repository-wide search for `Storage|Blob|S3|Supabase|multipart|UploadFile` across
`backend/app` returns only incidental word matches (a comment in `kernel/audit.py`, unrelated hits in
`spatial/domain/geometry_validation.py` and `kernel/security/http_hardening.py`). No `StoragePort`,
no adapter, no SDK call. This matches ADR-024 D1's own "Current implementation status, verified, not
assumed" note ("no `StoragePort` code... exists anywhere in `backend/` as of this ADR; checked by
search; zero matches") — and confirms that note is **still true today**, despite
`docs/EXECUTION_PLAN.md` §6 step 7 and §7.2 having scoped a `StoragePort` skeleton + R2 adapter as
Phase-0/Phase-1-concurrent work ("introduced now, used by Evidence in Phase 3... so Evidence has a
seam from the first day rather than a retrofit on the last"). **This did not happen.** It is a
concrete schedule gap this plan must absorb (§7, Risk R1).

### 1.4 Audit model

Lives in the shared kernel (`backend/app/kernel/audit.py`, `audit_orm.py`, `audit_postgres.py`) —
explicitly cross-cutting, not per-context. Append-only, **hash-chained** (`AuditEntry.hash` over a
canonical encoding of every prior field plus `prev_hash`); `verify_chain()` actually **recomputes**
every hash rather than checking a status flag — the direct fix for the "security theater" pattern
`docs/adr/ADR-007-audit-trail-evidence-model.md` names as a confirmed defect in both audited prior
codebases. `PostgresAuditStore.append()` commits **independently and immediately**, not just flushes
— so a deny/failure audit entry survives even if the surrounding request's transaction rolls back.
`audit()` accepts a pre-generated `entry_id`, which is exactly the mechanism ADR-023's `audit_ref`
column relies on, and which B5's evidence-action audit trail should reuse unchanged.

**ADR-007 status, precisely:** ADR-007 names five decisions. (1) event sourcing + outbox +
`verify_chain()` — **implemented**, this is `app/kernel/audit.py`. (2) real S3-compatible object
storage with Object Lock — **not implemented** (§1.3). (3) legal hold enforced as a guard at every
delete/archive/seal-release path — **not implemented** (no `legal_hold`/`ObjectLock`/`WORM` match
anywhere in `backend`). (4) hash/integrity verification that actually recomputes — **implemented** in
the audit chain's own `verify_chain()`, but not yet applied to any document/evidence binary, because
none exists yet. (5) dual-authorization break-glass — **not implemented**. ADR-007 is therefore a
**decided architecture with an unbuilt implementation** — exactly the situation `docs/REBUILD_PLAN.md`
scopes as B5 (4–6 weeks, sequenced after B4).

### 1.5 Upload capabilities & document metadata

**Neither exists.** No file-upload endpoint, no `multipart/form-data` handling, no FastAPI
`UploadFile` usage, no `Document`/evidence entity, no mime-type/filename/size/checksum field on any
existing entity — confirmed by search. All 21 current `@router.*` routes (§1.6) are JSON-body only. A
future Evidence Context introducing a `Document`/`EvidenceRecord` entity is genuinely new ground, not
an extension of a partial existing model.

### 1.6 Existing APIs

| Context | Prefix | Routes |
|---|---|---|
| Identity | `/v1/auth` | register, login, invitation-accept, refresh, logout, `GET /me`, `GET /me/tenant` |
| Identity (admin) | `/v1/admin` | role assignment, invitations (CRUD + revoke), tenant lifecycle, delegations (CRUD + revoke/extend) |
| Registry | `/v1/parcels` | `POST`, `PATCH /{id}`, `POST /{id}/archive`, `PUT /{id}/geometry`, `GET`, `GET /{id}` |
| Spatial | `/v1/spatial` | `PUT /parcels/{id}/geometry`, `GET /parcels/{id}/geometry` |
| Kernel | — | `GET /health/live`, `GET /health/ready` |

Wired centrally at `backend/app/main.py:76-79` (the composition root — the one place permitted to
know about more than one bounded context, per LV-000 v1.8 Article V §2). No `/v1/evidence` route
exists.

### 1.7 Cross-context dependency graph

- **Registry → Identity** (domain-layer): reuses `Role`, `GOVERNANCE_ROLES`, `CountryCode` directly
  — no duplicated literals.
- **Spatial → Identity**: same pattern, for authorization.
- **Spatial → Registry**: imports `PARCEL_REGISTRANT_ROLES` for its own route gating.
- **Registry does not import Spatial.** Registry defines its own `GeometryPort` Protocol
  (`registry/ports.py:51-72`); Spatial *implements* it (`spatial/adapters/geometry_port_adapter.py`),
  wired at the composition root (`main.py:20-24`). This is the live, working precedent for how a
  bounded context exposes a capability to another **without** either importing the other's
  adapters/ORM — the exact discipline LV-000 v1.8 Article V §2 requires ("a named,
  `Protocol`-typed contract the consuming context defines and the supplying context implements").
- **Identity depends on nothing else.** **Kernel** depends on nothing (contexts depend on it, never
  the reverse).
- Every router depends on the kernel's PDP/PEP (`kernel/authorization/{pdp,pep,pip}.py`) — no context
  reimplements its own authorization check.

**Direct implication for B5:** Evidence should (a) reuse Identity's role/value-object pattern exactly
as Registry/Spatial do; (b) depend on Registry through **a port Evidence itself defines** (e.g. a
`ParcelExistencePort`-shaped contract, mirroring the one Spatial's own Slice 2 already established for
validating a `parcel_id` exists/is in-tenant without a cross-context join) rather than importing
Registry's ORM directly; (c) never be imported *by* Registry, which should at most hold an opaque
reference to Evidence records, exactly as it holds `geometry_reference` today.

### 1.8 Application/adapter layering & migration conventions

Established, reusable pattern (Registry as the model): `application/<x>_service.py` — a single
service class, constructor-injected with Protocol ports only, no adapter imports;
`adapters/orm.py` — SQLAlchemy models, all `TIMESTAMPTZ`; `adapters/postgres_<x>_repositories.py` —
one adapter class per port, each constructed from the **same per-request `AsyncSession`**
(`kernel/uow.get_db_session`, FastAPI-cached) so writes in one request share one transaction;
`dependencies.py` — the context-local `Depends()` wiring. Migrations: sequential 4-digit
zero-padded prefix + `snake_case` description (`0001`…`0011` today), each shipping its RLS policy in
the same migration (Engineering Rule 1), with a tested `downgrade()`. **B5's first migration would be
`0012_<description>.py`**, following this convention exactly.

---

## Phase 2 — Does B5 require a new ADR? (Determination)

Per the authorizing instruction: reviewed against every Accepted ADR, ADR-021, ADR-024, ADR-025,
`docs/ENGINEERING_RULES.md`, and LV-000 v1.8. The test is whether B5 introduces a new architectural
boundary, bounded context, trust model, persistence model, external dependency, or security model.

**Determination: partially yes — narrowly, and for exactly two things. Not a blanket "new ADR
required," and not "no ADR required" either.**

| Dimension | New? | Reasoning |
|---|---|---|
| New architectural boundary | **No** | The port/adapter, composition-root, and RLS-tenant-isolation disciplines Evidence must follow are already established (`GeometryPort`/`ParcelHistoryRepository` precedent, §1.7–1.8). No new boundary shape is needed. |
| New bounded context | **No, in the sense of new doctrine** — but see below | Evidence is already named as context #4 of 13 in `docs/REBUILD_PLAN.md` §1, not a context this ADR determination invents. However, LV-000 v1.8 Article VI §1 ("Architecture Before Code") requires a domain-model ADR precede any new aggregate of consequence — the exact step ADR-013 took for `Parcel` and ADR-018 took for `ParcelGeometry`. **Evidence needs the equivalent domain-model ADR before Slice B5.2's migration is written** — not because Evidence is architecturally novel, but because this platform's own constitutional discipline requires the step for every new aggregate, without exception. |
| New trust model | **No** | LV-000 v1.8 Article XII already sets the standard ("structurally produced and independently verifiable... not because it was submitted and stored"), and ADR-007 already made the core evidence-trust decisions (hashing, verification, legal hold, break-glass) at the architecture level. B5 implements a already-decided trust model; it does not invent one. |
| New persistence model | **No** | Same Postgres + RLS + append-only-where-warranted pattern as every prior context (ADR-023 precedent, §1.2). `StoragePort` is already decided in shape (ADR-024 D1, refined by ADR-025 E3) — Supabase Storage primary, Cloudflare R2 for `governance`-grade WORM escalation. B5 implements this port; it does not redesign it. |
| New external dependency | **Conditionally** | Supabase Storage / Cloudflare R2 are already governed dependencies (ADR-024/025). **If** Merkle-tree anchoring / OpenTimestamps (named in ADR-007 decision 1 and `docs/REBUILD_PLAN.md`'s B5 description) is implemented in this programme, that introduces a genuinely new external dependency requiring `docs/ENGINEERING_RULES.md` rule 5's governed-dependency approval (human sign-off, justification, pinned version) — not necessarily its own ADR, but it should be recorded in whichever document decides the Evidence domain model, for the same "one citable place" discipline ADR-024 itself modeled. |
| New security model | **Yes — narrowly, for one capability only** | ADR-007 decision 5 (break-glass cross-tenant/cross-country evidence access, dual-authorization) is a **new instance of Controlled Platform Authority** (LV-000 v1.8 Article IX §3, `docs/ENGINEERING_RULES.md` rule 9). Rule 9 and Article IX §3 are explicit and absolute: *"No exception to tenant isolation inherits another exception's justification. Each new instance of Controlled Platform Authority requires its own named exception and, where it introduces genuinely new reach, its own ADR."* This is the identical situation ADR-021 was written to resolve for Spatial's cross-tenant conflict detection — and it sets the direct, citable precedent for how B5's break-glass mechanism must be governed: **its own Proposed ADR, reviewed and accepted, before that specific capability is implemented.** The core Evidence context (upload, hashing, WORM sealing within one tenant, chain of custody, legal hold) requires no such ADR — it never reads or writes across a tenant boundary. |

### Conclusion, stated plainly

**No additional ADR is required for the core, single-tenant Evidence context** (upload, hashing,
WORM sealing, chain of custody, legal hold) beyond the standard, already-required domain-model ADR
every new aggregate in this codebase has needed before its first migration (ADR-013, ADR-018
precedent) — this is not new doctrine, it is the platform's existing discipline applied to a new
aggregate, exactly as required.

**One additional ADR is required, and must be Proposed-then-Accepted before implementation, for the
break-glass cross-tenant/cross-country evidence-access mechanism** (ADR-007 decision 5) specifically
— a new, narrow, explicitly justified Controlled Platform Authority instance. That ADR's own text
must state explicitly, per LV-000 v1.8 Article VII §1, whether a dedicated threat-model document is
required — this plan's own judgment (not binding on that ADR) is that it plausibly is, given the
cross-tenant/cross-country reach, mirroring `docs/B4_THREAT_MODEL.md`'s TB5 precedent for the
structurally identical Spatial case.

**Recommended sequencing (this plan's Phase 5, below, reflects this):** the Evidence domain-model ADR
is Slice B5.0 and gates everything after it, exactly as ADR-013 gated B3 Slice 1. The break-glass CPA
ADR is a separate, later, independently-gated slice (B5.7) that does not block the rest of the
programme — mirroring exactly how B4 Slices 1–2 shipped and froze while Slice 3 remained gated on
ADR-021's acceptance.

This determination does not resolve Finding 1 (§ Executive Summary) — whether B5 may begin *at all*
ahead of B4 Slice 3/Phase 2's gate. That is a phase-sequencing question, not an ADR-content question,
and is left explicitly for Governance Authority decision.

---

## Phase 4 — B5 Architecture Design

### 4.1 Evidence Aggregate

`EvidenceRecord` (`app.contexts.evidence.domain.evidence_record`), the aggregate root, mirroring
`Parcel`'s shape (plain dataclass, no ORM coupling, guarded mutators):

- **Immutable identity:** `evidence_id` (UUID), `tenant_id`, `parcel_id` (a reference, resolved
  through a Registry-facing port — see §4.6 — never a direct FK crossing the context boundary at the
  domain layer, matching how `geometry_reference` is an opaque pointer on `Parcel`), `uploaded_by`,
  `created_at`.
- **Document metadata** (immutable once hashed): `filename`, `mime_type`, `size_bytes`, `sha256`
  (server-computed, independent read-back re-hash — never a client-supplied hash trusted, per ADR-007
  decision 4).
- **Lifecycle status:** `RECEIVED → HASHED → SEALED`, one-way, mirroring `Parcel.status`'s
  `ACTIVE → ARCHIVED` terminal-transition discipline. A `LEGAL_HOLD` flag is a separate, orthogonal
  boolean (not a status value) so hold/release does not collide with the seal lifecycle.
- **Storage reference:** `storage_key` (opaque, provider-agnostic, resolved through `StoragePort` —
  never a raw S3/R2 URL persisted as if it were portable), `worm_grade` (`"governance"` |
  `"compliance"`, recorded at seal time from `StoragePort.wormGrade()`, per ADR-024 D1/ADR-025 E3).
- **Provenance:** `basis` (free-text, mirroring ADR-023's own honest-narrow-basis discipline — what
  the upload asserts to be, not what it is proven to be), `audit_ref`.

### 4.2 Evidence Repository

`EvidenceRepository` Protocol (`evidence/ports.py`) — `add`, `get`, `list_for_parcel`,
`update_hash`, `seal`. No update/delete beyond the guarded lifecycle transitions — mirroring
`ParcelHistoryRepository`'s deliberately narrow shape (§1.2). A Postgres adapter constructed from the
same per-request `AsyncSession` as every other repository in this codebase.

### 4.3 Evidence Metadata

Covered by §4.1's document-metadata fields. No PII-specific encryption strategy is decided by this
plan — mirroring ADR-013's own explicit deferral of `owner_nin`-style sensitive-field handling to a
dedicated future decision. Where an uploaded document plausibly contains PII (a national ID scan, a
survey report with a beneficiary's name), that is a retention/access question for counsel (§7, R6),
not a schema question this plan resolves.

### 4.4 Evidence Timeline (chain of custody)

**No new event-bus or ledger mechanism.** Reuses the kernel `audit()` function exactly as ADR-023
did (§1.2/§1.4) — new action names (`evidence.uploaded`, `evidence.hashed`, `evidence.sealed`,
`evidence.viewed`, `evidence.legal_hold.applied`, `evidence.legal_hold.released`), each carrying
`audit_ref` back onto the `EvidenceRecord`/a dedicated append-only `evidence_custody_event` table
**only if** a query pattern needs "full custody history for one document" more efficiently than
scanning the audit log by `resource_id` — this is an implementation-time decision for Slice B5.5,
not decided here, consistent with "no speculative abstraction" (LV-000 v1.8 Article XVII §1).

### 4.5 Evidence Types, Verification Status, Provenance, Hashing

- **Evidence Types:** a bounded enum (e.g. `SURVEY_PLAN`, `TITLE_DOCUMENT`, `IDENTITY_DOCUMENT`,
  `OTHER`) — exact taxonomy is a Slice B5.0 domain-model-ADR decision, not invented here.
- **Verification status:** explicitly **not** an adjudication field. `EvidenceRecord` never carries
  a `verified`/`authentic` boolean implying the platform has determined the document is genuine —
  only `status` (upload lifecycle) and `worm_grade` (storage integrity guarantee). This is the direct
  application of the non-adjudication doctrine (Finding 2) to the domain model itself, not only to
  API wording.
- **Provenance:** `basis` + `uploaded_by` + `audit_ref` (§4.1).
- **Hashing:** streamed server-side SHA-256 at upload time, with an **independent read-back re-hash**
  after the write completes — the exact ADR-007 decision 4 requirement, and the fix for the
  "security theater" pattern (a status flag standing in for a real check) both prior audits found
  three times.

### 4.6 Evidence Relationships — Parcel & Ownership linkage

Evidence attaches to a `Parcel` via `parcel_id`, validated through a **port Evidence defines itself**
(e.g. `ParcelExistencePort` — tenant/existence check only, mirroring the shape Spatial's own Slice 2
already uses against Registry, per §1.7). Evidence never joins against `parcels` directly. Where
evidence is cited as the `basis` for a future `OwnershipAssertion`/`StatusAssertion` (ADR-023's own
stated forward-compatibility: *"When B5 (Evidence) ships, `basis` gains real evidence references as a
follow-up, additive change"*), that link is an `evidence_id` reference recorded in Registry's own
`basis` column — Registry references Evidence's identifier, Evidence never reaches into Registry's
tables. This is additive to ADR-023's schema, requires no migration to `parcel_ownership_history`
itself (the column is already a free-text `basis` string; a future, separate decision could formalize
it as a structured reference, but that is out of this plan's scope).

### 4.7 Storage abstraction (`StoragePort`)

Already decided in shape by ADR-024 D1/ADR-025 E3 (`put`/`get`/`list`, `putImmutable(retention)`,
`wormGrade()`), **not yet implemented anywhere** (§1.3). B5 Slice B5.1 builds it: Supabase Storage as
the primary adapter for ordinary evidence storage, Cloudflare R2 (Bucket Locks, `governance` grade)
as the WORM-escalation adapter for sealed evidence — exactly ADR-025 E3's text. No bounded context,
including Evidence itself, calls a storage SDK directly (Article X §5).

### 4.8 Audit integration

Fully covered by §4.4/§1.4 — no new mechanism.

---

## Phase 2 (continued) — `PHASE-B5_IMPLEMENTATION_PLAN` body

### Scope

B5 — Evidence: the Registry-adjacent bounded context that lets a registrant upload a document,
receive a server-computed, independently-verified integrity hash, have it sealed under WORM
retention, and have every subsequent access to it recorded in an immutable chain of custody, with
legal hold enforceable at every deletion-adjacent path. Registry's own contract (`Parcel`,
`OwnershipAssertion`/`StatusAssertion`) is unchanged.

### Objectives

1. A real, provider-backed `StoragePort` — no chmod-based or filesystem-default "WORM" of the kind
   both prior audits found fake (ADR-007's founding motivation).
2. Server-side hashing with independent read-back verification — no client-supplied hash trusted.
3. Legal hold enforced as a guard at every delete/archive/seal-release path, not a database flag
   nobody checks.
4. Chain of custody as real, queryable, audit-chain-backed history.
5. Every evidence-facing surface (API, response, export) observes the non-adjudication doctrine from
   day one — not retrofitted, per Finding 2 above.

### Non-goals

- Ownership *transfer* as a distinct command (ADR-015 already left this open; unaffected by B5).
- Survey-document-specific workflow (B6 — Survey, a later context, reuses Evidence's upload pipeline
  but is not built here).
- AI/OCR document classification (Phase 6 — AI Layer, per `docs/PHASE_GATES.md`; explicitly deferred).
- Any public verification portal (Government programme, LV-000 v1.8 Article XV; not authorized).
- Any UI (`F3 Evidence UI` is a separate frontend track, `docs/REBUILD_PLAN.md` §3).
- Any automated fraud/authenticity determination — an evidence record is never adjudicated by this
  context, only preserved, hashed, and made available to a human governance process (LV-000 v1.8
  Article XVII §3, mirroring ADR-021 §2/§6's identical restraint for Spatial).
- Break-glass cross-tenant/cross-country access (Slice B5.7 — separately gated on its own ADR, §Phase
  2 determination above; not built in the slices this plan authorizes for immediate work).
- Merkle-tree/OpenTimestamps anchoring beyond what's needed to satisfy `docs/EXECUTION_PLAN.md`
  Phase-3 gate text ("integrity check demonstrated") — treated as a stretch item requiring its own
  governed-dependency approval (§Phase 2 determination), sequenced last, subject to Governance
  Authority sign-off if timeline pressure requires deferring it past pilot MVP (mirrors `docs/DOD.md`
  §3's explicit sign-off requirement for any MVP scope change).

### Dependencies

- **Phase-gate resolution (Finding 1)** — Governance Authority decision required before Slice B5.1
  begins: close Phase 2's gate first, or record an explicit, reasoned exception to the phase order.
- **Rule §10 CI check (Finding 2)** — should exist and cover Evidence responses before or alongside
  Slice B5.3 (upload endpoint), not after.
- **`StoragePort` does not exist** (§1.3) — becomes B5's own Slice B5.1, not inherited work.
- **Data residency / required WORM grade** — `docs/EXECUTION_PLAN.md` §10 lists this as a decision
  "needed by Phase 3" (i.e., needed by B5) and explicitly **still undecided** — confirmed by
  Cloudflare R2 vs. S3 Object Lock/Azure/GCS/MinIO not yet chosen as the compliance-grade default.
  Blocks finalizing which adapter is *default*, not the `StoragePort` abstraction's own
  implementation (ADR-024 D1's replacement criteria: escalation is an adapter swap, no code change).
- **Legal/retention/erasure posture** — undecided, per counsel (mirrors ADR-023's own outstanding
  item; more acute here since B5 stores actual document bytes, not free-text fields).

### Architecture

See Phase 4 above (§4.1–4.8) in full. Summary: one new bounded context, `app.contexts.evidence`,
following the domain → ports → adapters → application → api layering every existing context uses;
depends on Identity's value objects directly and on Registry through a self-defined port; is never
imported by Registry; wired at the composition root (`main.py`) exactly as Spatial's `GeometryPort`
adapter is today.

### Migrations

One new migration, `0012_evidence_records.py` (naming convention, §1.8), Evidence-owned, additive
only:

- `CREATE TABLE evidence_records` — the `EvidenceRecord` aggregate's persisted shape (§4.1).
- `CREATE TABLE evidence_custody_events` (if Slice B5.5 determines a dedicated table is warranted
  over scanning the shared `audit_log` — see §4.4) — append-only, same dual-layer (grant + trigger)
  enforcement as migration `0011`'s history tables, if built.
- RLS `ENABLE` + `FORCE`, identical tenant-isolation predicate, **in the same migration** (Engineering
  Rule 1, ADR-023 precedent) — no exception for Evidence.
- Indexes: `(tenant_id)`, `(parcel_id)`, and any index the eventual query pattern for "evidence for
  this parcel" / "evidence pending legal hold review" requires — exact set decided at
  implementation time against real query plans (`docs/DOD.md` Tier 1 "Performance" criterion).
- Tested `downgrade()` — drops everything this migration created, no data migration needed downward
  (nothing pre-existed).
- **No backfill** — mirrors ADR-023's own reasoning verbatim: there is no reliable record of what a
  pre-migration document's hash, uploader, or basis actually was; fabricating one would manufacture
  provenance, which Article IV exists to prevent.

### Repository changes

New: `backend/app/contexts/evidence/{domain,ports.py,adapters,application,api,dependencies.py}` —
following the exact directory shape of `backend/app/contexts/registry/` (§1.8). No existing Registry
or Spatial file is modified, other than `main.py`'s router/adapter wiring (composition root only) and,
optionally, a later, separately-decided change to how `basis` values reference `evidence_id` (§4.6,
out of this plan's scope).

### API changes

New router, `backend/app/contexts/evidence/api/evidence_router.py`, prefix `/v1/evidence` (or
`/v1/parcels/{parcel_id}/evidence`, exact shape a Slice B5.0 domain-model-ADR decision — this plan
does not prescribe the URL shape, only that it is new, since no prior context needed one):

- `POST` — upload (multipart), gated `require_role(*EVIDENCE_UPLOAD_ROLES)` (a role set the domain-
  model ADR defines, plausibly mirroring `PARCEL_REGISTRANT_ROLES` — not invented here).
- `GET /{evidence_id}` — metadata + custody summary, tenant-scoped, `require_auth`.
- `GET` (list for parcel) — tenant-scoped.
- `POST /{evidence_id}/legal-hold` / `DELETE /{evidence_id}/legal-hold` — governance-role-gated.
- No `PATCH`/`DELETE` on a sealed record — mirrors the append-only-after-seal discipline (§4.1).

This is the platform's **first multipart/file-upload endpoint** — a genuinely new request-handling
surface (streaming body, size limits, content-type allowlisting) that needs its own OWASP-checklist
pass (unrestricted-file-upload, path traversal via filename, zip-bomb/decompression, content-type
spoofing) beyond what any existing JSON-body route has needed. This belongs in the Security Model
below, not assumed away.

### Storage changes

`StoragePort` (Slice B5.1), Supabase Storage primary adapter, Cloudflare R2 `governance`-grade
adapter — per §4.7. No context other than Evidence calls either adapter directly in this plan's
scope (a future Survey context, per `docs/REBUILD_PLAN.md` B6, is expected to reuse Evidence's upload
pipeline rather than call `StoragePort` itself — consistent with "route through this same pipeline
rather than each building its own weaker version," ADR-007's own stated consequence).

### Security model

- **Upload surface hardening** (new, since this is the first file-upload endpoint in this codebase):
  content-type allowlist, size ceiling, filename sanitization (no path-traversal via a crafted
  filename persisted anywhere), streamed hashing (no full-file buffering in memory), and a
  content-type check that does not trust the client-declared MIME type alone.
- **No new authorization path** — reuses `require_role`/`require_auth` (PDP/PEP), exactly as every
  other context does (Engineering Rule 9/LV-000 v1.8 Article X §3). The exact role set and
  creator-or-governance shape (mirroring ADR-015) is a Slice B5.0 decision.
- **RLS** — identical predicate/strength to every tenant-scoped table since migration `0001`
  (§ Migrations above).
- **Legal hold** — a single, shared guard function, called by every delete/archive/seal-release code
  path (ADR-007 decision 3) — never a per-caller opt-in check.
- **Break-glass cross-tenant access** — explicitly **out of this plan's immediate scope** (§ Non-goals,
  Slice B5.7) pending its own ADR.
- **Non-adjudication** — every response field, label, and export uses "submitted"/"recorded"/
  "asserted" language, never "verified"/"authentic"/"proven" — covered by the Rule §10 CI check once
  built (Finding 2), and reviewed manually until it exists.

### Authorization model

No new model. Reuses the PDP/PEP pipeline and `ExecutionContext` propagation exactly as Registry does
(§1.6/§1.7). Exact role gating is a Slice B5.0 decision, expected to follow the creator-or-governance
shape ADR-015 established, absent a stated reason to diverge.

### Rollback strategy

- **Migration** — standard Alembic `downgrade()`, tested up/down/up on a staging-like database before
  merge (Engineering Rule 6, ADR-023 precedent — including ADR-023's own caught defect: build fresh
  `Column`/`ForeignKey` objects per table, never share a tuple across `create_table()` calls).
- **Storage adapter** — escalating or rolling back the *default* adapter behind `StoragePort` is a
  configuration/adapter swap, no code change and no migration (ADR-024 D1's replacement criteria).
- **Sealed evidence is never deleted by a rollback.** A schema-level rollback (dropping
  `evidence_records`) must not attempt to delete provider-side sealed objects under active WORM
  retention — that would defeat the retention guarantee the whole context exists to provide. Any
  rollback runbook for this context must say so explicitly, not merely inherit the generic
  "reversible migration" rule uncritically.

### Definition of Done

Full `docs/DOD.md` Tier 1 (Feature) and Tier 2 (Sprint/bounded-context) criteria apply unchanged,
plus `docs/EXECUTION_PLAN.md` Phase-3 gate text verbatim: *"Sealed evidence demonstrably cannot be
altered · integrity check demonstrated · storage, retention and break-glass pass security review."*
Note the gate's own wording includes "break-glass" — meaning **Phase 3's gate, as written, does not
close until Slice B5.7 (or an explicit, recorded descoping of break-glass from this pilot) is also
resolved.** This plan flags that rather than silently narrowing the gate's own text.

### Acceptance Criteria

1. `StoragePort` implemented, Supabase Storage + Cloudflare R2 adapters both pass a live upload/seal/
   read-back rehearsal against real infrastructure (not mocked) — Engineering Rule 7 ("never mark
   something complete without observing it pass").
2. A registrant can upload a document to a parcel they created; the resulting `EvidenceRecord`'s
   `sha256` matches an independent, out-of-band re-hash of the stored object.
3. Sealing a record and then attempting any mutation of its metadata or its stored bytes is rejected,
   observed both at the application layer and the storage-provider layer.
4. Legal hold, once applied, is observed to block deletion/archival/seal-release attempts; release
   permits it again.
5. Every evidence action produces a resolvable `audit_ref`.
6. Cross-tenant isolation, positive and negative, on every new table.
7. Non-adjudication check (once built, Finding 2) passes against every new response shape.
8. Migration `0012` up/down/up rehearsed live.
9. `Parcel`/Registry regression: zero change to any existing Registry endpoint's request/response
   shape or domain contract.

### Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | `StoragePort` does not exist despite being scoped as Phase-0/1-concurrent work | Confirmed | Schedule | Built as explicit Slice B5.1, not assumed inherited |
| R2 | Rule §10 CI check does not exist; Phase 1's own gate is not fully closed | Confirmed | Governance/compliance | Build the check before/alongside Slice B5.3, covering both Registry and Evidence surfaces at once |
| R3 | WORM grade / data-residency decision still undecided (`EXECUTION_PLAN.md` §10) | Confirmed open | Blocks confident default-adapter choice | Escalate to Governance Authority/pilot partner/counsel before Slice B5.1's default-adapter selection is finalized; `StoragePort`'s own swap-without-code-change guarantee limits the blast radius |
| R4 | Break-glass CPA mechanism has no governing ADR | Confirmed | Would violate Article IX §3/Rule 9 if built without one | Gate Slice B5.7 behind its own Proposed→Accepted ADR, mirroring ADR-021/B4 Slice 3 |
| R5 | Phase-gate sequencing conflict (Finding 1) — B4 Phase 2 gate not met | Confirmed | Governance | Explicit Governance Authority resolution required before Slice B5.1 begins |
| R6 | Legal/retention/erasure posture for evidence PII undecided | Confirmed open | Legal/compliance | No auto-delete/erasure automation until counsel sign-off; log the gap, mirroring ADR-023's own treatment |
| R7 | First multipart/file-upload endpoint in this codebase — new attack surface (unrestricted upload, path traversal, zip bombs, content-type spoofing) | New capability, not yet reviewed | Security | Dedicated OWASP pass on the upload path specifically, not inherited from JSON-route review history |
| R8 | Merkle/OpenTimestamps anchoring, if built, is a new external dependency | Depends on scope decision | Governed-dependency review | Route through Engineering Rule 5's approval process explicitly if/when this is scoped in |

### Test Matrix

*(All items to be observed passing, per Engineering Rule 7 — not assumed from code inspection.)*

1. Upload → server-computed hash → independent read-back re-hash matches; a tampered/corrupted
   stored object is detected by re-verification, not silently trusted.
2. Seal transition: `putImmutable`/`wormGrade()` called and recorded; post-seal metadata mutation
   rejected, both at the application layer and by the storage provider itself.
3. Cross-tenant isolation, positive and negative, RLS.
4. Every evidence action writes an `audit_ref`-resolvable, payload-consistent `AuditEntry`.
5. Legal hold blocks delete/archive/seal-release at every relevant code path — observed denied while
   active, permitted once released.
6. Integrity verification recomputes and compares — never a status-flag check (direct application of
   ADR-007 decision 4 / Engineering Rule 3).
7. Non-adjudication wording check passes against every Evidence response/export.
8. Migration `0012` up/down/up, rehearsed live against real Postgres.
9. Break-glass dual-authorization (once its own ADR is accepted and Slice B5.7 built): mechanically
   rejected if the second approver is absent; the security-incident record is written durably
   *before* the unwrap operation returns (ADR-007 decision 5, verbatim requirement).
10. Parcel/Registry regression — zero behavioral change to any existing Registry contract.
11. Upload-surface security: oversized file rejected, disallowed content-type rejected, a filename
     containing path-traversal sequences does not affect the stored object's key.

---

## Phase 5 — Implementation Roadmap

Each slice below states purpose, files affected, migrations, tests, risks, acceptance criteria, and
rollback, per the authorizing instruction. **No slice below is authorized to begin implementation by
this document** — this is the roadmap Governance Authority approval would activate, starting from
Slice B5.0.

### Slice B5.0 — Evidence domain-model ADR (governance only, no code)

**Status (2026-08-02): Complete.** `docs/adr/ADR-026-evidence-domain-model.md` drafted and
**Accepted** by Governance Authority.

- **Purpose:** satisfy LV-000 v1.8 Article VI §1 ("Architecture Before Code") for the new
  `EvidenceRecord` aggregate, before any migration exists — the same step ADR-013 took for `Parcel`
  and ADR-018 took for `ParcelGeometry`.
- **Files affected:** new `docs/adr/ADR-0XX-evidence-domain-model.md` (number confirmed by reading
  `docs/adr/` at the time, per `docs/EXECUTION_PLAN.md` §11.2's own numbering-floor discipline — not
  assumed here).
- **Migrations:** none.
- **Tests:** none (architecture document).
- **Risks:** none beyond normal ADR-review risk.
- **Acceptance criteria:** ADR reviewed and Accepted before Slice B5.1 begins.
- **Rollback:** N/A (documentation).
- **Phase gate:** blocks every subsequent slice, exactly as ADR-013 blocked B3 Slice 1's code.

### Slice B5.0b — Rule §10 non-adjudication CI check (Finding 2 closure)

**Status (2026-08-02): Moot — already resolved independently.** Engineering Rules §10 was
implemented as its own governed slice ("Phase 9", PR #7, commit `88448e4`) before this B5 slice
began, covering the Registry surface — see `docs/PHASE-9_ACCEPTANCE_PACKAGE.md`. Extending its
blocklist/scan surface to a future Evidence API response is noted as follow-up work for whichever
slice adds that surface (B5.3), not a prerequisite slice of its own.

- **Purpose:** close the still-outstanding Phase 1 gate item (`EXECUTION_PLAN.md` §7.6 item 9) before
  Evidence — a second, higher-risk adjudication-adjacent surface — ships without it.
- **Files affected:** a new CI step/script (exact location decided at implementation time — likely
  `backend-ci.yml` plus a lint-style checker over API response schemas/strings).
- **Migrations:** none.
- **Tests:** the check's own test suite (fails on known-bad wording fixtures, passes on the current
  Registry history responses).
- **Risks:** false positives on legitimate legal/administrative language; mitigate with a reviewed
  allowlist, not a blanket suppression.
- **Acceptance criteria:** CI fails a deliberately-introduced adjudication-wording violation; passes
  current Registry responses unmodified.
- **Rollback:** revert the CI step; no data/schema impact.

### Slice B5.1 — `StoragePort` + Supabase Storage + Cloudflare R2 adapters

**Status (2026-08-02): Partially complete — Protocol implemented and live-verified against a
hermetic fake; real adapters deliberately not built.** `app/contexts/evidence/ports.py`
(`StoragePort`) and `backend/tests/fakes/storage.py` (`InMemoryStoragePort`) exist, with 11 passing
tests (`backend/tests/test_storage_port.py`). Real `supabase_storage.py`/`r2_storage.py` adapters
were **not** built, and this is a deliberate scope decision, not an oversight: both require a new
external dependency (`docs/ENGINEERING_RULES.md` rule 5 — needs explicit human approval) and real
credentials for a live rehearsal (rule 7), neither available to this implementation session. See
`docs/PHASE-B5-SLICE1_ACCEPTANCE_PACKAGE.md` for full evidence.

- **Purpose:** close the R1 gap (§7) — the storage seam `docs/EXECUTION_PLAN.md` §7.2 expected to
  already exist.
- **Files affected:** new kernel-level or Evidence-owned `ports.py` (`StoragePort` Protocol,
  exact ownership location decided against whether any other future context needs it before Evidence
  does — likely kernel, since ADR-024 frames it as platform-wide, not Registry/Evidence-specific);
  `adapters/supabase_storage.py`, `adapters/r2_storage.py`.
- **Migrations:** none (code-only; no DB schema for the port itself).
- **Tests:** live rehearsal against real Supabase Storage and R2 — put/get/list/putImmutable/
  wormGrade, per Engineering Rule 7.
- **Risks:** R3 (WORM grade/data-residency undecided) — affects which adapter is *default*, not
  whether the abstraction can be built.
- **Acceptance criteria:** both adapters pass live put/get/putImmutable/wormGrade rehearsal.
- **Rollback:** adapter swap, no code change to callers (none exist yet at this slice).

### Slice B5.2 — Evidence aggregate, repository, migration `0012`

**Status (2026-08-02): Complete, live-verified, not yet merged.** `EvidenceRecord`,
`EvidenceRepository` (Postgres + in-memory adapters), `EvidenceService`, DI wiring, and migration
`0012` are all implemented on branch `feat/b5.2-evidence-domain-model` (commit `50b970d`). Migration
`0012` was rehearsed live against Docker Postgres: up/down/up repeatability, RLS positive/negative
isolation, `super_admin` bypass, mutable `UPDATE`, `DELETE` denied at the grant level. 34 new tests,
`ruff`/`mypy` clean, 215/215 passing. See `docs/PHASE-B5-SLICE2_ACCEPTANCE_PACKAGE.md` for full
evidence. **Not merged to `main`** — awaiting Governance Authority merge authorization.

- **Purpose:** the `EvidenceRecord` domain object and its persistence, no upload endpoint yet.
- **Files affected:** `backend/app/contexts/evidence/{domain,ports.py,adapters/orm.py,
  adapters/postgres_evidence_repository.py,dependencies.py}`.
- **Migrations:** `0012_evidence_records.py` (§ Migrations above).
- **Tests:** repository unit tests (in-memory fake + Postgres adapter), migration up/down/up.
- **Risks:** none beyond standard new-table risk; RLS parity with `parcels` must be confirmed
  identical, per the ADR-023 discipline.
- **Acceptance criteria:** Test Matrix items 3, 8.
- **Rollback:** standard `downgrade()`.

### Slice B5.3 — Upload endpoint, server-side hashing

- **Purpose:** the platform's first file-upload API surface.
- **Files affected:** `backend/app/contexts/evidence/{application/evidence_service.py,
  api/evidence_router.py}`; `main.py` router wiring.
- **Migrations:** none (uses B5.2's schema).
- **Tests:** Test Matrix items 1, 11.
- **Risks:** R7 (new upload attack surface) — dedicated OWASP pass required.
- **Acceptance criteria:** Test Matrix items 1, 11; Rule §10 check (B5.0b) passes against new
  responses.
- **Rollback:** router removal; no data impact (uploaded-but-unsealed records may be purged per a
  retention policy decided at implementation time — not sealed, so no WORM conflict).

### Slice B5.4 — WORM sealing, integrity verification

- **Purpose:** `putImmutable`/`wormGrade()` wiring, seal transition, on-demand/scheduled
  re-verification.
- **Files affected:** `evidence_service.py` (seal + verify methods), possibly a scheduled job
  (mirroring `verify_chain()`'s own "run on a schedule" precedent, ADR-007 decision 1).
- **Migrations:** none, or an additive column if a "last verified at" timestamp is added.
- **Tests:** Test Matrix items 2, 6.
- **Risks:** R3 (default grade choice).
- **Acceptance criteria:** Test Matrix items 2, 6; Acceptance Criterion 3.
- **Rollback:** standard.

### Slice B5.5 — Chain of custody

- **Purpose:** queryable custody history per evidence record.
- **Files affected:** `evidence_service.py` (audit-action wiring); optional new migration for a
  dedicated `evidence_custody_events` table if the audit-log-scan approach proves insufficient (§4.4).
- **Migrations:** optional, additive, same append-only dual-layer pattern as `0011` if built.
- **Tests:** Test Matrix item 4.
- **Risks:** none beyond standard.
- **Acceptance criteria:** Test Matrix item 4.
- **Rollback:** standard.

### Slice B5.6 — Legal hold

- **Purpose:** the shared guard ADR-007 decision 3 requires, checked at every delete/archive/
  seal-release path.
- **Files affected:** `evidence_service.py` (guard function), `evidence_router.py` (hold/release
  endpoints).
- **Migrations:** additive `legal_hold` boolean + `legal_hold_reason`/`legal_hold_by` columns on
  `evidence_records`, or a small dedicated table if a hold needs its own audit trail independent of
  the record — decided at implementation time.
- **Tests:** Test Matrix item 5.
- **Risks:** R6 (retention/erasure posture undecided) — legal hold is the *enforcement* mechanism;
  the *policy* of when to apply/release it is a separate, counsel-dependent decision this slice does
  not make.
- **Acceptance criteria:** Test Matrix item 5; Acceptance Criterion 4.
- **Rollback:** standard.

### Slice B5.7 — Break-glass cross-tenant/cross-country access (separately gated)

- **Purpose:** ADR-007 decision 5, implemented only after its own governing ADR is Accepted.
- **Files affected:** TBD by that ADR.
- **Migrations:** TBD by that ADR.
- **Tests:** Test Matrix item 9.
- **Risks:** R4 — building this without its own ADR would be a direct Article IX §3/Rule 9 violation.
- **Acceptance criteria:** Test Matrix item 9; the governing ADR's own acceptance criteria.
- **Rollback:** TBD by that ADR.
- **Phase gate:** does not block Slices B5.1–B5.6, mirroring how ADR-021/B4 Slice 3 did not block B4
  Slices 1–2's freeze.

### Slice B5.8 — Merkle/OpenTimestamps anchoring (stretch, conditionally scoped)

- **Purpose:** the remaining ADR-007 decision 1 scope (Merkle-tree batch anchoring,
  OpenTimestamps secondary anchor), if retained for pilot MVP.
- **Files affected:** TBD.
- **Migrations:** TBD.
- **Tests:** an anchoring-integrity test, structurally analogous to `verify_chain()`.
- **Risks:** R8 — new external dependency, requires Engineering Rule 5 approval before adoption.
- **Acceptance criteria:** TBD; explicit Governance Authority sign-off required if this is descoped
  from pilot MVP (per `docs/DOD.md` §3's sign-off requirement for any MVP scope change).
- **Rollback:** TBD.
- **Phase gate:** last in sequence; does not block Test Matrix items 1–8 or the Phase-3 "integrity
  check demonstrated" gate text, which `verify_chain()`-style hash re-verification (Slice B5.4)
  already satisfies independent of anchoring.

---

## Success Criteria for This Planning Package (restated)

- Repository assessment grounded in the current codebase — Phase 1, above, cites file:line evidence
  throughout, not assumption.
- Dependency analysis — Phase 1 §1.7, Phase 4 §4.6.
- A definitive ADR determination — Phase 2 above: narrow yes, for the domain-model ADR and the
  separately-gated break-glass ADR; no for everything else.
- A governance-compliant implementation plan — Phase 2 (continued) body, above.
- A phased roadmap with acceptance criteria and rollback — Phase 5, above.
- **No application code, migrations, or pull requests accompany this document.**

**Outstanding for Governance Authority, before implementation begins:**
1. Resolve Finding 1 (phase-gate sequencing) — explicitly.
2. Confirm Slice B5.0b (Rule §10 CI check) is built before or alongside upload-endpoint work.
3. Confirm the ADR-numbering floor by reading `docs/adr/` at the time Slice B5.0's ADR is drafted
   (per `docs/EXECUTION_PLAN.md` §11.2's own discipline — not assumed here).
