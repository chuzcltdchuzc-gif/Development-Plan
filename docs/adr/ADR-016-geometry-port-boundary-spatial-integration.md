# ADR-016 — Geometry Port Boundary & Spatial Integration Architecture

**Status:** Accepted — extends ADR-009 (B1 Platform Freeze), ADR-013 (Parcel Aggregate &
Registry Domain Model), ADR-014 (Atomic Parcel Number Allocation), ADR-015 (Registry Mutation
Authorization Model). Does not modify any frozen decision; see §"Relationship to the frozen
baseline."

**Date:** 2026-07-20

**Scope:** B3 Slice 4 only — a nullable `parcels.geometry_reference` column (migration `0009`),
the `GeometryPort` protocol, one placeholder adapter with no business logic, DI wiring, and
`PUT /v1/parcels/{id}/geometry`. This slice is an **architectural boundary**, not a GIS feature:
no polygon drawing, coordinate systems, topology, spatial indexing, spatial search, adjacency/
overlap detection, survey workflows, boundary validation, AI-assisted mapping, or public map APIs
— all of that is B4 (Spatial Intelligence) and later.

## Context

The Registry bounded context (ADR-013/014/015) is now substantially complete: canonical Parcel
identity, atomic numbering, tenant isolation, creator-aware mutation authorization with
governance override, delegated administration integration, immutable archive behavior, audit
integration. `docs/REBUILD_PLAN.md` schedules B4 (Spatial Intelligence) as a *separate* bounded
context, not a Registry sub-feature — but nothing in the codebase yet defines *how* a future
Spatial context would relate to a `Parcel` without either (a) Registry growing a direct PostGIS
dependency (the coupling ADR-013 already avoided by keeping geometry off the aggregate entirely
in Slices 1–3), or (b) B4 needing to reach into Registry's internals to know which parcels exist.
This ADR is the seam that prevents both: Registry stays technology-agnostic about geometry, and a
future Spatial context integrates through one stable contract instead of a redesign.

## Decision

### Registry responsibility (unchanged, restated for this ADR's scope)

Registry owns: parcel identity (`parcel_id`), parcel number (ADR-014), registry metadata
(title/address/state/lga/ward/community/property_type/size_sqm/ownership_type), lifecycle
(`status`, ADR-013), mutation authorization (ADR-015), audit, and — future slices — ownership
history. Registry does **not** own spatial computation, and this slice does not change that: it
adds exactly one thing to Registry's surface — an *association point* (below), not a spatial
capability.

### Spatial responsibility (deferred to B4, named here only to draw the boundary)

Geometry, coordinate systems, topology, spatial indexing, polygon validation, spatial analysis,
adjacency, overlap detection, GIS processing, and mapping services all belong to a future Spatial
Intelligence bounded context. Nothing in this slice implements any of them — they are listed here
only so the boundary this ADR draws has two sides, not one.

### Aggregate boundary: `geometry_reference` is an association, not geometry

`Parcel` gains one new nullable field: `geometry_reference: str | None`. This is **not** a
polygon, not a coordinate pair, not a PostGIS type, and not validated for spatial correctness —
it is an opaque pointer (a foreign identifier, a URI, whatever a future geometry provider defines)
that Registry stores and returns but never interprets. This mirrors the exact pattern ADR-013
already established for `current_owner_name`/`current_owner_contact` ("a *reference*, not a
*history*") and for `parcel_number` before ADR-014 populated it ("reserve the field is a guarded
mutation point, not a bare mutable column"): the aggregate holds a pointer to a concept it does
not own, so a later slice can populate what the pointer means without touching Registry's own
invariants. `set_geometry_reference()` is guarded by the same `_ensure_mutable()` every other
mutator uses — an archived parcel cannot gain or lose a geometry association either.

### Port boundary: `GeometryPort`

```python
class GeometryPort(Protocol):
    async def reference_is_valid(self, *, geometry_reference: str) -> bool: ...
```

This is the **entire** contract Registry depends on. Deliberately minimal: Registry needs to know
only "does this reference make sense to attach" before storing it — it does not need, and must
never gain, a method that returns geometry content, computes anything spatial, or accepts a
polygon payload, because any of those would mean Registry code branching on spatial data, the
exact coupling this ADR exists to prevent. `ParcelService` is constructed with a `GeometryPort`
instance (`app.contexts.registry.dependencies.get_geometry_port`) the same way it already
receives a `ParcelRepository` and a `ParcelNumberAllocator` — one more port, wired through the
identical FastAPI dependency-injection seam, not a new wiring mechanism.

**This slice's implementation, `PlaceholderGeometryAdapter`
(`app.contexts.registry.adapters.geometry`), satisfies the contract with zero business logic —
`reference_is_valid` always returns `True`.** This is deliberately not a feature: it exists so
Registry can be wired, tested, and deployed today with a functioning DI seam, without depending on
any GIS infrastructure ("ports before adapters" — the port must exist and be consumable before
any real adapter does). B4 supplies the first adapter that actually means something (validating
against a real geometry store, an external mapping service, national spatial infrastructure) —
swapping `PlaceholderGeometryAdapter` for that implementation changes zero lines in
`ParcelService`, `Parcel`, or any Registry test, which is the concrete proof this boundary works,
not merely an assertion that it should.

**Why not richer, "obviously useful later" port methods (e.g. `get_geometry_summary`,
`compute_area`, `validate_polygon`):** rejected under "rule of three, avoid speculative
abstractions beyond the immediate architectural seam." Every one of those methods would require
guessing at B4's actual data model before B4's own discovery/planning exists — exactly the
mistake ADR-013 avoided by leaving `parcel_number` an unpopulated nullable column rather than
guessing at Slice 2's allocation mechanism ahead of time. `reference_is_valid` is the one
operation Registry's own mutation flow (below) genuinely needs today; anything else is B4's ADR
to write, against B4's real requirements.

### Why a plain string reference, not a PostGIS geometry column

`parcels` already has PostGIS available (`CREATE EXTENSION IF NOT EXISTS postgis`, migration
`0007`) — but adding a `geometry`-typed column to `parcels` itself would be exactly the technology
leakage this ADR exists to prevent: it would make Registry's own schema depend on PostGIS being
present and correct, rather than depending on a port whose backing implementation happens to use
PostGIS (or doesn't). A `VARCHAR` reference column has no spatial semantics at all — it is
inert to Registry, meaningful only to whatever B4 adapter is configured behind `GeometryPort`.

### Authorization boundary: no new mechanism

`PUT /v1/parcels/{id}/geometry` is gated by the identical coarse
`require_role(*PARCEL_REGISTRANT_ROLES)` every other mutation endpoint uses, and
`ParcelService.set_geometry_reference` reuses `_load_in_scope`/`_authorize_mutation` (ADR-015)
verbatim — creator-or-governance, tenant-scoped, archived-guarded. There is no
geometry-specific authorization rule, no second check, no new role. This is deliberate: the
brief's own instruction ("geometry operations must inherit the existing
Identity → Tenant → Delegation → RBAC → PDP pipeline; no separate authorization mechanism") is
satisfied by literally reusing ADR-015's helpers rather than writing parallel ones that happen to
compute the same answer.

### Audit: no new mechanism

`registry.parcel.geometry_attached` (a non-null reference was set) and
`registry.parcel.geometry_detached` (cleared to null) are two new *action names* through the
existing `audit()` function (ADR-007) — not a new audit mechanism. Payload shape matches every
other Slice 3 mutation event: `tenant_id`, `effective_authority`, `delegated_roles`.

### Future evolution — what this boundary is designed to support without amendment

- **B4 (Spatial Intelligence):** supplies a real `GeometryPort` adapter and its own bounded
  context owning actual geometry data, keyed off `geometry_reference`. Registry's schema,
  domain, and authorization code do not change.
- **Survey workflows:** a survey process can produce a geometry payload, persist it in B4's own
  store, and call `PUT /v1/parcels/{id}/geometry` with the resulting reference — Registry's role
  is unchanged (record the pointer, nothing more).
- **Evidence capture:** evidence attaches to a parcel by `parcel_id`, independent of whether a
  geometry reference exists yet — no ordering dependency this ADR needs to resolve.
- **Boundary disputes:** a dispute over what a `geometry_reference` actually describes is a B4
  (or later) concern entirely; Registry has no opinion on geometry content to be disputed.
- **AI analysis / public verification / government operations:** all consume Registry's parcel
  identity (`parcel_id`, `parcel_number`) and, where relevant, the geometry reference — never a
  reason to add spatial fields or logic to `Parcel` itself.
- None of the above requires modifying ADR-013, ADR-014, or ADR-015 — each already anticipated
  this (ADR-013's "clean seam... adds it without needing to touch or migrate around a placeholder
  column" for Slice 4, written before this slice existed).

### Alternatives considered and rejected

1. **Add a real PostGIS `geometry` column to `parcels` now, unused until B4** — rejected: this is
   exactly the "premature persistence structure" the brief warns against, and it commits Registry
   to a specific spatial technology before B4's own ADR ever argues for one. A plain reference
   column commits to nothing.
2. **No column at all this slice — pure interface definition, no persistence** — rejected: without
   *some* place to store a reference, the port has nothing to attach to a specific `Parcel`, and
   "Aggregate Boundary: geometry is associated with a Parcel" would be an unimplemented claim, not
   an architectural fact. The nullable column is the minimum persistence needed to make the
   association real and testable.
3. **A separate `parcel_geometry_associations` table (parcel_id → geometry_reference)** —
   rejected as unnecessary indirection for a 1:1, nullable, single-string association; a table
   makes sense once there is an actual multiplicity or lifecycle to the association beyond "set/
   clear," which B4 may introduce but this slice has no evidence for yet (rule of three).
4. **`GeometryPort` with a richer contract (validate polygon, compute area, etc.)** — rejected,
   see §"Port boundary" above.

## Relationship to the frozen baseline

- **ADR-013** — `Parcel`'s core invariants (identity, `parcel_number` uniqueness, archived
  immutability, ownership-reference-not-history) are unchanged; `geometry_reference` follows the
  same "reserved pointer, not yet meaningful" pattern ADR-013 itself set for `parcel_number`
  before ADR-014.
- **ADR-014** — untouched; the allocator and its counter table have no relationship to geometry.
- **ADR-015** — `set_geometry_reference` is authorized by literally reusing
  `_load_in_scope`/`_authorize_mutation`/`_effective_authority`/`_delegated_roles`, not a
  parallel implementation of the same rule.
- **ADR-009** — PDP/PEP, Unit-of-Work, RLS, audit chain: unchanged, consumed exactly as every
  prior Registry slice consumed them.
- **No frozen decision required amendment.**

## Consequences

- B4 (Spatial Intelligence) can begin its own Phase-0 discovery knowing exactly one integration
  contract to honor (`GeometryPort.reference_is_valid`) and exactly one column Registry already
  persists (`geometry_reference`) — it does not need to renegotiate Registry's schema or
  authorization model to begin.
- Registry remains fully testable with zero GIS infrastructure — `PlaceholderGeometryAdapter`
  (production) and an equivalent configurable fake (tests) are the only "geometry" code that
  exists anywhere in this bounded context.
- The Registry bounded context (B3) is now feature-complete per its original Phase-0 scope
  (`docs/B3_DISCOVERY_AND_PLANNING.md`): Parcel aggregate, atomic numbering, mutation
  authorization, and the spatial integration boundary. What remains before freeze is the deferred
  B3 Final Quality Gate (`docs/B3_FINAL_VERIFICATION_CHECKLIST.md`), not further Registry design.
