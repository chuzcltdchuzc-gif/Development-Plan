# ADR-005 — Property Registry Data Model

**Status:** Accepted
**Date:** 2026-07-13

## Context

Both prior builds modeled the land parcel differently, and neither got it fully right. Base44 ran **two parallel parcel entities** (`LandParcel`, a legacy model with 500+ historical records, and `LandVaultParcel`, a newer model with essentially no live data) with a confusing, never-completed migration between them, and no single authoritative record. Emergent's Registry bounded context had a single, well-designed `LandVault` aggregate — the audit confirmed its immutable-field invariants (`registry_id`, `parcel_number`, `tenant_id`, `country_code`, `created_at`, `origin`) and atomic parcel-number allocator (a genuine single `find_one_and_update` with `$inc`/upsert, zero duplicates under concurrent load) were sound — but its "owner-only" update authorization was dead code in practice: the PDP resource descriptor never carried `created_by`, so any principal holding a create-tier role could update location/geometry/ownership on *any* parcel in their tenant, not just ones they created or were assigned to. Its migration tool's idempotency guarantee also didn't hold under concurrent runs (the provenance index used to detect already-imported records wasn't unique), and unmappable geometry was silently dropped rather than quarantined as its own documentation claimed.

## Decision

One canonical parcel aggregate — `LandVault` — per the Emergent design, carried into this rebuild's Registry bounded context (`docs/REBUILD_PLAN.md` B3):

- Immutable at creation: `registry_id`, `parcel_number` (from the atomic allocator, reused pattern), `tenant_id`, `country_code`, `created_at`, `origin`.
- Mutable via explicit, invariant-guarded commands only: `UpdateLocation`, `UpdateGeometry` (delegates to Spatial Intelligence, ADR per `docs/REBUILD_PLAN.md` B4), `UpdateOwnershipContact`, `RecordOwnershipTransfer` (append-only `ownership_history[]`), `UpdateSurvey`, `UpdateCommunityData`, `Archive` (one-way).
- **Fixed:** ownership-transfer and update authorization checks the real actor identity against the resource (`created_by` / assigned surveyor / field agent), not just role membership — the PDP resource descriptor is populated correctly this time, and the aggregate itself independently re-checks actor identity as true defense-in-depth (not the documented-but-absent version from the audit).
- **Fixed:** the legacy-import migration tool's provenance-uniqueness constraint is enforced at the database level (a real unique index, not just an application-level pre-check), and unmappable geometry is quarantined, never silently dropped.
- Base44's field-level richness (the union of fields across `LandParcel` and `LandVaultParcel`) is used as the requirements checklist for what this one aggregate needs to capture — not its code, which is discarded.

There is **one** parcel entity in this rebuild. No legacy/new dual-track pattern.

## Consequences

- Eliminates the "which parcel record is authoritative" confusion that existed in Base44 and the dual-write drift risk that existed in Emergent's legacy-compatibility adapter (a non-transactional mirror write with no reconciliation path, confirmed in the audit to be able to leave a parcel durably registered but invisible to legacy readers).
- Ownership-transfer and update operations are meaningfully restricted per actor, not just per role — closing a confirmed authorization gap.
- The atomic allocator and immutable-field invariant logic are reused near-verbatim from Emergent, since the audit found no defect in that specific logic.
