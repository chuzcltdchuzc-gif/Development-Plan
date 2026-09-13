# ADR-018 — Spatial Domain Model & Bounded Context Boundary

**Status:** **Accepted.** Reviewed and approved in full — the bounded-context boundary, the
`ParcelGeometry` aggregate, the append-only `ACTIVE`/`SUPERSEDED` lifecycle, validate-then-store
persistence, and the `geometry(Polygon, 4326)` storage/CRS decision are all adopted as B4's
governing domain model. **This acceptance does not by itself authorize implementation.** The one
`GeometryPort` interface change §5 identifies (extending `reference_is_valid`'s signature) is a
touch on frozen B3 code and, per explicit instruction, must be formally recorded and approved as
its own document — see `docs/adr/ADR-019-geometry-port-interface-amendment.md` — before B4 Slice
1 begins. Overlap detection, real geometry-validation rules, and any other GIS service remain
explicitly out of scope here — ADR-020 (real `GeometryPort` adapter & validation rules) and
ADR-021 (overlap & duplicate-geometry detection) own those, unwritten until ADR-019 is accepted.

**Date:** 2026-07-21

**Governed by:** `docs/B4_DISCOVERY_AND_PLANNING.md` (accepted planning baseline) and
`docs/B4_THREAT_MODEL.md` (accepted security baseline — its six trust boundaries, TB1–TB6, and
its STRIDE-derived requirements are mandatory constraints on everything decided below, not
optional input). Extends `docs/adr/ADR-009-b1-platform-freeze.md`,
`docs/adr/ADR-013-parcel-aggregate-registry-domain-model.md`,
`docs/adr/ADR-016-geometry-port-boundary-spatial-integration.md`, and
`docs/adr/ADR-017-b3-platform-freeze.md`. Does not modify any of them except for one explicitly
flagged, narrow extension to ADR-016's `GeometryPort` interface — see §5.

## Context

B3 (frozen, ADR-017) built the seam this ADR is the first real consumer of:
`GeometryPort.reference_is_valid(geometry_reference: str) -> bool` and
`Parcel.geometry_reference: str | None` (an opaque pointer, never geometry data — ADR-016).
ADR-016 deliberately left the actual domain model undecided: *"any real validation is B4's
responsibility... B4's own ADR will define what a real reference looks like."* This is that ADR.
`docs/B4_THREAT_MODEL.md` §6 additionally binds this ADR to one specific requirement: *"payload
validation must be structurally separated from storage — invalid geometry must never reach
persistence or query layers unvalidated."* Every decision below is designed to satisfy that
constraint directly, not as an afterthought.

## Decision

### The bounded context: `app.contexts.spatial`

A new bounded context, mirroring Registry's own internal shape exactly (`domain/`, `ports.py`,
`adapters/`, `application/`, `api/`, `dependencies.py`) — the same template ADR-013 established
and this codebase has now used twice. Spatial owns its own migrations (`0010`+), its own RLS
policies, and its own repository — it never writes to `parcels` or any other Registry table, and
Registry never writes to Spatial's tables (ADR-016's boundary, restated as a hard constraint on
this ADR's schema design, not merely a principle).

### The aggregate: `ParcelGeometry`

`ParcelGeometry` (`app.contexts.spatial.domain.parcel_geometry`) is the canonical representation
of one parcel's boundary submission. Fields: `geometry_id` (UUID, immutable identity — the exact
value Registry's `geometry_reference` stores, once accepted), `tenant_id` (real FK to
`tenants.id`, from its first migration — the corrected pattern ADR-013 already established,
never the string-then-retrofit detour B2 corrected), `parcel_id` (real FK to `parcels.id`,
required, not nullable — geometry submission always targets an already-existing parcel; there is
no workflow in this platform where geometry precedes parcel registration), `boundary` (the
PostGIS payload, §4), `status` (`ACTIVE` | `SUPERSEDED` — see §3), `created_by`, `created_at`,
`superseded_at`.

### Domain invariants

1. **`geometry_id` is immutable identity**, generated once at construction, never reassigned —
   identical convention to `parcel_id`/`user_id`/every other aggregate root in this codebase.
2. **`boundary` is immutable once the row exists.** A `ParcelGeometry` row is never edited in
   place. A correction is a *new* row with a new `geometry_id`; the row it corrects transitions
   `ACTIVE → SUPERSEDED` (append-only, mirroring ADR-013's own "ownership history is append-only"
   principle, generalized here to geometry history). This is not merely a style preference: an
   in-place edit would silently invalidate any overlap-detection result already computed against
   the old boundary (ADR-021's future concern) without leaving a trace of what changed or when —
   an audit and correctness gap this ADR closes structurally, before ADR-021 ever needs to worry
   about it.
3. **Only `ACTIVE` geometries are valid.** `SUPERSEDED` rows are retained (never deleted — no
   `DELETE` grant, matching the platform's universal convention) but are not eligible answers to
   `GeometryPort.reference_is_valid` and are not eligible input to any future overlap query
   (ADR-021). There is no `PENDING`/`REJECTED` status — see §3 for why.
4. **A `ParcelGeometry` row is created only from an already-validated payload** — see §3.
5. **Tenant isolation is absolute**, the same default every table in this codebase has used since
   migration `0001` — `FORCE`d RLS, `tenant_id = current_setting('app.tenant_id', true) OR
   is_super_admin`. **This ADR does not define any cross-tenant read mechanism.** The threat
   model (TB5) established that overlap detection will need one — that mechanism is ADR-021's
   decision, bound by `docs/ENGINEERING_RULES.md` rule 9 (Controlled Platform Authority: fixed at
   the call site, read-only, as narrow as the task allows, audited). ADR-018 explicitly refuses
   to weaken this table's default policy to make ADR-021 easier — the narrow exception belongs
   in ADR-021, applied on top of, not instead of, this default.
6. **No second authorization mechanism.** Whatever endpoint eventually submits a `ParcelGeometry`
   (ADR-022's job to design in full) reuses the identical Identity → Tenant → Delegation → RBAC →
   PDP pipeline every other mutation in this codebase uses — this ADR introduces no new role and
   assumes none is needed (submitting geometry for a parcel one is authorized to mutate is a
   natural extension of ADR-015's creator-or-governance model, reusable rather than reinvented).

### Validation gates persistence — not stored-then-flagged (satisfies the threat model's binding requirement directly)

Two designs were considered for how validation interacts with storage:

- **(Rejected) Store-then-flag:** persist every submission, valid or not, with a
  `PENDING`/`VALID`/`REJECTED` status column; exclude non-`VALID` rows from query eligibility.
  Rejected: this creates a grey area the threat model specifically warned against — a
  `REJECTED` (or worse, still-`PENDING`) row is "invalid geometry that reached persistence,"
  which is the literal condition `docs/B4_THREAT_MODEL.md` §6 says must never happen. It also
  means every query touching this table must remember to filter by status correctly, forever —
  a structural foot-gun, not a one-time correctness question.
- **(Chosen) Validate-then-store:** a `ParcelGeometry` row is only ever created *after* the
  submitted payload has already passed validation (ADR-020's real rules — well-formedness, no
  self-intersection, coordinate-bounds sanity, administrative-boundary containment). A failed
  submission produces no row at all — the equivalent of a `400`-class rejection, exactly like
  Registry's own `_bad_request` pattern for `size_sqm <= 0` (ADR-013/015) — not a stored, marked-
  invalid artifact. This makes "every row in `parcel_geometries` is valid" a structural
  invariant of the table itself, not a runtime filter every consumer must remember to apply —
  directly satisfying the threat model's requirement that invalid geometry never reach the
  persistence or query layers.

The actual validation *algorithm* is explicitly ADR-020's job, not this ADR's — ADR-018 decides
only that validation happens before the `INSERT`, never after.

### Geometry storage type and coordinate reference system

- **PostGIS `geometry(Polygon, 4326)`**, not `geography`. `4326` (WGS84) matches GPS capture
  natively — storing in the CRS the data actually arrives in avoids a lossy reprojection at
  ingestion time, the exact "closer to the source of truth" reasoning ADR-013 already applied to
  keeping `size_sqm` a self-declared figure rather than a derived one at this stage. `geometry`
  (planar), not `geography` (geodesic), because ADR-021's overlap/duplicate-detection queries
  will need PostGIS's full `ST_Overlaps`/`ST_Intersects`/GiST-indexing function surface, which is
  more complete and better-optimized against `geometry` than `geography` for this exact use case
  (polygon-to-polygon comparison at parcel scale, not global-scale geodesic distance).
- **SRID is enforced at the column level** (`geometry(Polygon, 4326)` rejects any other SRID or
  geometry subtype at `INSERT` time — a real database-level guarantee, the same "constraints
  belong in the database, not just application code" discipline `ix_parcels_number_unique`
  already demonstrated for parcel numbering).
- **Area/distance calculations reproject on demand, never store a second, redundant geometry.**
  Nigeria spans UTM zones 31N–33N (`EPSG:326xx` family, meters-based, appropriate for accurate
  area/distance); the specific zone/projection choice and the reprojection call sites are
  ADR-020/021's implementation concern — this ADR fixes only that the *authoritative* stored
  value stays `4326`, never a projected CRS, so there is exactly one source of truth per
  geometry, not two that could drift.
- **`Polygon` only, not `MultiPolygon` or generic `Geometry`, for this first ADR.** Real
  discontiguous parcels exist but are not evidenced as a near-term requirement — deliberately
  deferred rather than solved speculatively (rule of three), the same discipline ADR-016 applied
  to leaving B4's whole domain model undecided until this ADR. Widening to `MultiPolygon` later
  is additive (a column-type migration, not a redesign) if real registration data demands it.
- **Administrative reference boundaries (LGA/state polygons, needed for ADR-020's real
  containment check) are explicitly a separate, not-yet-designed concept** — reference data,
  not tenant data, likely seeded once and read-mostly (closer to `registry_parcel_counters`'
  RLS shape than to a tenant-scoped table's). Not designed here; named so ADR-020 does not have
  to rediscover that this data has different ownership/RLS characteristics than `ParcelGeometry`
  itself.

## 5. A flagged, narrow, necessary extension to ADR-016's `GeometryPort` (the one place this ADR touches frozen B3 code)

**This section's proposal is formally recorded, reviewed, and accepted as its own document,
`docs/adr/ADR-019-geometry-port-interface-amendment.md`** — per explicit instruction that a
change touching frozen B3 code receive its own dedicated governance record rather than ride along
inside this ADR's broader acceptance. The analysis below is preserved as the original reasoning
that produced ADR-019; ADR-019 itself is the authoritative record for whether and how the
`GeometryPort` signature actually changes, and implementation waits for *that* document's
acceptance, not this section's.

`GeometryPort.reference_is_valid` currently takes only `geometry_reference: str`. Under
`PlaceholderGeometryAdapter` this was fine — the adapter validated nothing. A **real** adapter
backed by `ParcelGeometry` cannot correctly answer "is this reference valid *for this parcel and
tenant*" without knowing which parcel and tenant are asking — without that, a real adapter could
only check "does a `geometry_id` matching this string exist *anywhere*, for any tenant," which
would let one tenant attach another tenant's `geometry_reference` to their own parcel merely by
guessing or observing a valid-looking UUID — a real, avoidable information/integrity leak this
ADR is obligated to close rather than carry forward.

**Proposed extension:** `GeometryPort.reference_is_valid(self, *, geometry_reference: str,
tenant_id: str, parcel_id: str) -> bool`. This requires one small, explicitly-justified change to
`ParcelService.set_geometry_reference` (frozen B3 code, ADR-015/016) — passing `ctx.tenant_id`
and `parcel_id` through to the existing call site, nothing else. This is the *only* frozen-B3
code this ADR proposes touching, and it is additive (a new required keyword argument on a
protocol only Registry and Spatial implement/consume — no third caller exists to break) rather
than a behavior change for `PlaceholderGeometryAdapter`, whose trivial always-`True` semantics is
unaffected either way. Per this codebase's amendment discipline (ADR-011/012/017: "a bounded
context that needs [a frozen decision] to behave differently opens a new ADR referencing it and
states precisely what changes and why — it does not edit the source directly as a side effect"),
this section is that statement. The actual code change happens only once this ADR is accepted and
B4 Slice 1 begins — not now.

## Alternatives considered and rejected

1. **A single `Geometry` table shared across future bounded contexts** (e.g., also used for
   evidence-photo GPS tags, survey waypoints) — rejected: speculative, no second consumer is
   evidenced yet, and conflating concerns before a second real need exists is the exact
   premature-abstraction pattern this engagement avoids everywhere else.
2. **Storing geometry directly on `parcels` via a PostGIS column** — rejected already by ADR-016
   itself (technology leakage into Registry's schema); restated here because ADR-018 is the ADR
   that could have reopened it and deliberately does not.
3. **`geography` type instead of `geometry`** — rejected, §4.
4. **Store-then-flag validation** — rejected, §3.
5. **Leaving `GeometryPort`'s signature unchanged and enforcing tenant/parcel matching only in
   `ParcelService`** — rejected: `ParcelService` cannot verify a fact only Spatial's own data
   knows (whether a given `geometry_id` truly belongs to this tenant/parcel) without asking
   Spatial the right question; leaving the port under-specified would either silently permit the
   cross-tenant-reference leak described in §5, or force a second, informal channel between the
   two contexts — exactly the kind of undocumented coupling ADR-002 (ports & adapters) exists to
   prevent.

## Relationship to the frozen baseline

- **ADR-009** — PDP/PEP, Unit-of-Work, RLS session-variable mechanism, audit chain: consumed
  unchanged, exactly as every prior context has.
- **ADR-010** — `ParcelGeometry.tenant_id` is a real FK to `tenants.id` from its first migration,
  the corrected pattern, never the string-then-retrofit detour.
- **ADR-013** — `Parcel` is untouched; this ADR does not add, remove, or reinterpret any Parcel
  field or invariant.
- **ADR-015** — no new authorization rule; ADR-022 will reuse the creator-or-governance model,
  not reinvent one, when it designs Spatial's own endpoints.
- **ADR-016** — one explicit, narrow, flagged extension (§5) to `GeometryPort`'s signature,
  additive only, with the actual code change deferred to implementation once this ADR is
  accepted. No other part of ADR-016 is touched.
- **ADR-017 (B3 freeze)** — the §5 extension is the only B3-scope code this ADR proposes
  changing, and it is disclosed here precisely because B3 is frozen and such a change requires
  exactly this kind of explicit justification, not a silent edit.
- **`docs/B4_THREAT_MODEL.md`** — §3 (validate-then-store) directly satisfies the binding
  requirement stated in the threat model's §6 item 1. §2 invariant 5 explicitly declines to
  define any cross-tenant mechanism, deferring it to ADR-021 under Controlled Platform Authority
  (`docs/ENGINEERING_RULES.md` rule 9) rather than solving it here under different framing.
- **No frozen decision is modified** — ADR-016 is extended, not changed in what it already
  decided; every other frozen ADR is unaffected.

## Consequences

- ADR-020 (real `GeometryPort` adapter & validation rules) can now be written against a concrete
  schema and a concrete "validation happens before persistence" contract, rather than against an
  undecided domain model.
- ADR-021 (overlap & duplicate-geometry detection) inherits a table already correctly indexed for
  tenant isolation and already guaranteed to contain only `ACTIVE`, previously-validated
  geometry — it does not need to re-litigate what "valid" or "current" means before designing the
  actual spatial queries.
- The `GeometryPort` extension (§5) is a real, if narrow, precedent: the first time a B4+ ADR has
  needed to extend rather than merely consume a B3-frozen contract. Recorded explicitly so it is
  never mistaken for undisclosed drift by a future session reading git history without this ADR.
- `MultiPolygon` support and administrative-boundary reference data remain explicitly open,
  deferred questions (§4) — not decided by omission, decided to be decided later.

## Approval Gate

This ADR is **accepted**. Per the governing instruction, implementation of any kind — including
the §5 `GeometryPort` signature change — does not begin until `docs/adr/ADR-019-geometry-port-interface-amendment.md`
is itself reviewed and explicitly accepted. ADR-020, ADR-021, and ADR-022 remain unwritten
pending that review.
