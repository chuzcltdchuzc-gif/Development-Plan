# ADR-017 — B3 Platform Freeze

**Status:** Accepted — B3 is frozen as of this date, tagged `b3-freeze`. Amend via a new ADR
that references this one; do not edit this document's description of "what B3 is" retroactively
— a later ADR that changes B3 behavior supersedes the relevant section here and must say so
explicitly. Same amendment discipline ADR-009 and ADR-012 established for B1 and B2.

**Date:** 2026-07-20

**Verified against:** `docs/audits/B3_RELEASE_NOTES.md` (migrations `0007`–`0009`, 119/119 tests
platform-wide, 47/47 Registry-specific, full B3 Final Quality Gate — `docs/B3_FINAL_VERIFICATION_CHECKLIST.md`
— including live Postgres/Keycloak/RLS/delegation/audit-chain/cross-tenant/ownership-attack/
container verification) — this document is the architecture description; those are the evidence
it's accurate. Built on top of, and does not modify, `docs/adr/ADR-009-b1-platform-freeze.md` or
`docs/adr/ADR-012-b2-platform-freeze.md`.

## Context

B3 (the Registry bounded context) is complete across four slices, each individually reviewed and
accepted, each with its own ADR, each verified against real infrastructure — culminating in a
dedicated End-of-B3 Quality Gate that re-ran full static analysis, the complete test suite, and
live verification one final time across all four slices together. This document is the formal
close-out that declares B3 done, gathers all four slices' frozen shape in one place, and — per
the same governance model ADR-009 and ADR-012 established — puts B4+ on notice that B3 is now a
stable platform to build on, not a moving target to reach into.

**Amendment procedure:** identical to ADR-009/ADR-012 — a bounded context that needs B3 to behave
differently opens a new ADR referencing this one (and ADR-013/014/015/016 where relevant) and
states precisely what changes and why. It does not edit B3's source directly as a side effect of
B4+ work without that ADR existing first.

## Scope — what is frozen

Everything under `backend/app/contexts/registry/` (the entire bounded context, created in this
program), migrations `0007`–`0009`, the two small, deliberate, general-purpose extensions to
shared Identity/kernel code (`app/contexts/identity/context_hydration.py` and
`app/kernel/authorization/pep.py`, both extended to thread delegation-status visibility through
the already-existing `ExecutionContext.attributes` field — see ADR-015), and the API surface
listed below. B1's frozen scope (ADR-009) and B2's frozen scope (ADR-012) are unchanged and
unaffected.

---

## 1. Parcel Aggregate (slice 1 — full detail: ADR-013)

`Parcel` is the single, canonical representation of a land parcel: immutable identity
(`parcel_id`), tenant isolation (`tenant_id` FK'd to `tenants.id` from its first migration,
unlike Identity's own `tenant_id`, which was only FK'd retroactively in B2), registry metadata
(title/address/state/lga/ward/community/property_type/size_sqm/ownership_type), lifecycle
(`status`: `ACTIVE`/`ARCHIVED`, terminal), and a **current ownership reference**
(`current_owner_name`/`current_owner_contact` — deliberately distinct from a history). Twelve
domain invariants are enforced on the aggregate itself, not merely at the endpoint —
`_ensure_mutable()` (archived parcels cannot be modified) is the guard every later mutation
method inherited without re-implementing it.

`POST /v1/parcels` is gated `require_role(*PARCEL_REGISTRANT_ROLES)`; `GET` endpoints use bare
`require_auth` with RLS plus an explicit repository-level tenant filter. No new authorization
mechanism: a delegate holding a delegated registrant role registers a parcel exactly as if they
held it directly (ADR-011, zero Registry-specific integration code).

Table: `parcels` (migration `0007`), `FORCE`d RLS (same policy shape as every tenant-scoped
table since migration `0001`), least-privilege grants (`SELECT/INSERT/UPDATE`, no `DELETE`), a
database-wide partial unique index on `parcel_number` (global, not tenant-scoped — a land
registry number identifies one parcel unambiguously across the whole jurisdiction).

## 2. PostgreSQL-Native Atomic Parcel Number Allocation (slice 2 — full detail: ADR-014)

Every parcel receives a real, unique `parcel_number` at creation time via one atomic
`INSERT ... ON CONFLICT DO UPDATE ... RETURNING` against `registry_parcel_counters`, in the same
request transaction as the parcel insert — a rollback undoes the counter increment along with
everything else, so a failed request never burns or duplicates a number.

**A genuine mid-slice correction, recorded here permanently, not smoothed over:** the counter
was initially scoped per-tenant. Live concurrency testing (two tenants concurrently registering
parcels in the same country) exposed that this collides with `parcel_number`'s own database-wide
unique constraint the instant more than one tenant operates in the same country — the normal
case for a multi-tenant registry, not an edge case. Fixed before review by re-scoping the counter
to `country_code`: every tenant registering parcels in the same country now correctly shares one
gapless sequence, live-verified across two different tenants interleaved into one contiguous run.

Table: `registry_parcel_counters` (migration `0008`), keyed by `country_code`. Since this table
holds no tenant-owned data, its RLS policy admits any authenticated session rather than matching
a specific `tenant_id` — still `FORCE`d, still fail-closed against anonymous access, still no
`DELETE` grant.

**Known limitation, carried forward:** a same-tenant `N=20` concurrent-load test separately
surfaced SQLAlchemy's default connection-pool ceiling (`pool_size=5` + `max_overflow=10` = 15) —
a genuine, documented operational constraint for future capacity planning, not a Registry defect.

## 3. Mutation Commands & Authorization Hardening (slice 3 — full detail: ADR-015)

`PATCH /v1/parcels/{id}` (registry metadata / current-ownership-reference fields) and
`POST /v1/parcels/{id}/archive` (one-way `ACTIVE → ARCHIVED`, no restore — `status` remains the
terminal state ADR-013 established). Authorization is a genuine, resource-aware domain check, not
merely the pre-existing coarse role gate: `parcel.created_by == ctx.principal_id` (creator
authority) **or** any currently-effective `GOVERNANCE_ROLES` member, direct or delegated
(governance authority, tenant-wide, capped at the delegator's own rank by the unchanged
`highest_rank()` ceiling) — closing the confirmed ADR-005 historical defect where any
create-tier role could mutate any parcel in its tenant, not only the ones it registered.

Cross-tenant mutation attempts 404 (existence not revealed, evaluated before the ownership
check); an archived parcel rejects every further mutation unconditionally, creator/governance/
`super_admin` alike (409, no privileged bypass). `ExecutionContext.attributes` — a field that
existed, unused, since B1 — now carries `delegated_roles` from context hydration through to
Registry's audit payloads, so every mutation records `effective_authority`
(`creator`/`governance:<role>`) and delegation status. No new migration — `parcels.updated_by`/
`archived_at` were reserved, unused, since migration `0007`.

**Live-reproduced and confirmed closed:** the exact ADR-005 attack shape — a same-tenant,
non-creator, non-governance registrant attempting to mutate a colleague's real, Keycloak-
authenticated, Postgres-persisted parcel — denied with 403 at both the B3 Final Quality Gate and
at Slice 3's own implementation-time testing.

## 4. Geometry Port Boundary & Spatial Integration Foundation (slice 4 — full detail: ADR-016)

An architectural boundary, not a GIS feature. `Parcel.geometry_reference: str | None` is an
opaque pointer to a future Spatial Intelligence context's own geometry data — never a polygon or
PostGIS type, never interpreted by Registry. `GeometryPort.reference_is_valid(geometry_reference)
-> bool` is the entire contract Registry depends on; `PlaceholderGeometryAdapter` satisfies it
with zero business logic (always `True`), proving the dependency-injection seam works today with
no GIS infrastructure. `PUT /v1/parcels/{id}/geometry` reuses ADR-015's authorization helpers
verbatim — no geometry-specific rule, no new role, no parallel pipeline.

Table change: `parcels.geometry_reference` (migration `0009`), one nullable, purely additive
column. No RLS/grant change — row-level security already covers every column on the table.

## 5. Cross-cutting extension discovered/made during B3 (affects shared B1-era code, non-breaking)

`ExecutionContext.attributes` (declared since B1, never populated by any context until now) is
populated by `app.contexts.identity.context_hydration` with `{"delegated_roles": [...]}` whenever
a currently-effective delegation contributed roles, and threaded through by
`app.kernel.authorization.pep._build_context_from_token` into the field that already existed on
the dataclass. This is additive, not a behavior change to any existing consumer — no context
before Registry ever read `ctx.attributes`, so no prior behavior could have depended on it being
empty in a way this breaks.

## 6. Migrations shipped in B3

| Migration | Adds |
|---|---|
| `0007_parcels.py` | `parcels` table, `CREATE EXTENSION IF NOT EXISTS postgis`, database-wide partial unique index on `parcel_number`, RLS, least-privilege grants |
| `0008_registry_parcel_counters.py` | `registry_parcel_counters` table (keyed by `country_code`), RLS admitting any authenticated session, grants |
| `0009_parcels_geometry_reference.py` | `parcels.geometry_reference`, nullable `VARCHAR`, purely additive |

All three follow the same pattern established in B1/B2: RLS shipped in the same migration that
creates the table, least-privilege grants (`SELECT/INSERT/UPDATE`, never `DELETE`), no
destructive changes to any existing table's data.

## Known limitations carried into B4 (not fixed in B3, tracked, not hidden)

- No restore command — `ARCHIVED` remains a one-way terminal state (ADR-013, reaffirmed ADR-015).
  Revisiting this requires its own ADR explicitly reopening that decision.
- Ownership-transfer authorization is undecided — `created_by` must survive any future transfer
  command unchanged (ADR-015/ADR-016); who may initiate a transfer is left for whichever slice
  builds it.
- `GeometryPort` has exactly one production adapter, which validates nothing about a reference's
  content (`PlaceholderGeometryAdapter`, always permits) — deliberate, pending B4's own real
  implementation.
- The containerized backend's `KEYCLOAK_REALM_URL` is host-relative (`localhost:8080`), inherited
  from the platform's original Docker Compose configuration — full authenticated live
  verification goes through the host dev server, not the container directly. Out of Registry's
  scope; not introduced or worsened by B3.
- SQLAlchemy's default connection-pool ceiling (`pool_size=5` + `max_overflow=10` = 15), found
  under heavy same-tenant concurrent load in Slice 2 — a platform-wide operational constraint for
  future capacity planning.
- Carried unchanged from ADR-012: no email-delivery integration, no Keycloak realm export
  committed, `Delegation.scope` descriptive-only, no dedicated secret-leakage-in-logs audit, no
  push notifications for lifecycle events.

## Consequences

- B4+ contexts build on a stable Registry platform with real parcel identity, atomic numbering,
  resource-aware mutation authorization, and a spatial integration seam — not a placeholder or a
  moving target.
- The ADR-005 historical defect (Emergent's PDP resource descriptor never carrying `created_by`)
  is now demonstrably closed, live-reproduced and confirmed denied, not merely asserted fixed.
- Any future Spatial Intelligence work integrates through exactly one contract
  (`GeometryPort.reference_is_valid`) and exactly one association column
  (`parcels.geometry_reference`) — it does not renegotiate Registry's schema, domain model, or
  authorization design to begin.
- The B3 Final Quality Gate's one finding (a pre-existing, unrelated `mypy` type-annotation gap
  in `migrations/env.py`, outside B3's own changes) was fixed as part of this freeze — a
  whole-repo static-analysis pass catching something no context-scoped run had exercised before.
- B3 is tagged `b3-freeze` at the commit this ADR is accepted in. No further B3-scope changes
  land without a new ADR referencing this one.
- B4 (Spatial Intelligence) is treated as an entirely new programme: discovery, scope definition,
  and its own ADR planning come first, with explicit approval required before any implementation
  begins — the same discipline B3 itself was launched with.
