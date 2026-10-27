# B4 Discovery & Planning — Spatial Intelligence

**Status:** Planning only. No B4 production code has been written. This document is the Phase 0
deliverable required before implementation begins — presented for review and explicit approval,
per the B4 program initiation instruction. B4 is treated as an entirely new programme, not a
continuation of B3 — the same discipline B3 itself was launched under.

**Date:** 2026-07-21

---

## 0. Framing

`docs/REBUILD_PLAN.md` §1 assigns B4 = **Spatial Intelligence** ("PostGIS-backed validation,
overlap + duplicate-geometry detection, spatial indexing/search, adjacency, distance, map
tiling"), sequenced immediately after Registry (B3, now frozen — `docs/adr/ADR-017-b3-platform-freeze.md`,
tag `b3-freeze`) and immediately before Evidence (B5) and Trust Engine (B7, which consumes B4's
duplicate-geometry detection as its first non-Evidence signal source). B3 already built the exact
seam B4 exists to fill: `docs/adr/ADR-016-geometry-port-boundary-spatial-integration.md` defines
`GeometryPort.reference_is_valid(geometry_reference: str) -> bool` and `Parcel.geometry_reference`
(an opaque pointer, never geometry data) specifically so that "B4 supplies the first real
implementation without any change to `ParcelService`, `Parcel`, or [the `GeometryPort`] protocol."
B4's job is to be that real implementation — not to redesign Registry, and not to guess at its own
scope, since ADR-016 deliberately left B4's actual domain model undecided ("any real validation is
B4's responsibility... B4's own ADR will define what a real reference looks like").

---

## 1. Discovery & Planning

### 1.1 Review of the frozen baseline (what B4 consumes, unmodified)

- **ADR-009 (B1 freeze):** PDP/PEP, `ExecutionContext`, Unit-of-Work, hash-chained audit,
  RLS session-variable mechanism. B4 reuses all of this exactly as B3 did — no second
  authorization path, no second audit mechanism (ADR-016 already commits future spatial work to
  this; this document does not reopen it).
- **ADR-010 (Tenant aggregate):** every B4 table must carry `tenant_id` (or a documented reason
  it doesn't — see §3, the cross-tenant overlap-detection question) and follow the RLS shape
  every tenant-scoped table has used since migration `0001`.
- **ADR-013 (Parcel Aggregate):** the aggregate B4 associates with via `parcel_id`. B4 must
  never gain write access to `parcels` beyond what `GeometryPort` already lets Registry ask of
  it — B4 answers a question Registry asks; it does not reach into Registry's tables.
- **ADR-014 (Atomic Parcel Number Allocation):** not consumed by B4 at all; noted only to confirm
  no interaction exists.
- **ADR-015 (Registry Mutation Authorization Model):** if B4 ever needs its own mutation
  commands (e.g., "submit geometry for a parcel"), they must follow the *identical*
  creator-or-governance model, reusing Registry's helpers or an equivalent pattern — not a
  spatial-specific authorization rule invented fresh. This is a planning constraint, not yet a
  decision about whether B4 needs mutation commands of its own at all (see §3).
- **ADR-016 (Geometry Port Boundary):** the contract B4 must satisfy
  (`GeometryPort.reference_is_valid`) and the column it must treat as an opaque foreign key from
  its own side (`parcels.geometry_reference`), never as something B4 writes to directly.
- **Current repository state** (verified by reading, not assumed): only
  `backend/app/contexts/{identity,registry}/` exist as bounded contexts. PostGIS `3.4.3` is
  already running and already has `CREATE EXTENSION IF NOT EXISTS postgis` confirmed live
  (migration `0007`) — zero infrastructure lift needed to begin. `PlaceholderGeometryAdapter`
  (`app/contexts/registry/adapters/geometry.py`) is the only "spatial" code that exists anywhere
  in the codebase, and it is deliberately a no-op. Frontend is still pre-F1 (no Auth UI, no
  generated API client) — F2 (Registry + Spatial UI, map/polygon editor) is blocked on F1, not
  on B4's backend work.

### 1.2 User needs

- **Field agents/surveyors** need to submit a parcel's boundary (a polygon, typically from GPS
  capture or a survey plan) at registration or after a survey — the actual reason
  `geometry_reference` exists on `Parcel`.
- **Compliance/government/surveyor-general roles** need to *see* parcels on a map and need
  automated flags when a new registration's geometry substantially overlaps an existing one —
  the direct fraud/integrity concern this bounded context exists to address.
- **The Trust Engine (B7, not yet built)** needs a duplicate-geometry signal as one of its first
  three scoring inputs (`docs/REBUILD_PLAN.md` §1's B7 row) — B4 is this signal's sole source.
- **Base44's own attempted version of this feature is documented, and its specific defects are
  the concrete negative example B4 must not repeat:** `asyncGISValidation`
  (`docs/audits/AQUASAVANNAH_LANDVAULT_FORENSIC_AUDIT.md` §53) existed and ran on every parcel
  create/update, but `docs/REBUILD_PLAN.md`'s B4 row names its specific failure mode explicitly —
  *"Base44's hardcoded LGA bounding-box check — replace with real polygon containment"* — and
  separately notes duplicate-geometry detection must become *"a real signal (not GPS-proximity-
  only)."* Base44's `FraudAlert` entity even carried the right-shaped fields
  (`gps_distance_m`, `overlap_percentage`, `duplicate_field`) without the underlying computation
  being real geometry-based — the exact "field exists, computation doesn't" pattern this
  engagement has already found and fixed twice in other contexts (Base44's trust-score
  `subscores`, Emergent's PDP resource descriptor). B4 must not reproduce that pattern under a
  new name.

### 1.3 Technical constraints and open questions

- **Coordinate reference system.** GPS capture is natively WGS84 (`EPSG:4326`, lat/lng,
  geographic, not projected) — the obvious default for storage — but area/distance calculations
  are more numerically correct in a projected CRS. Whether to store one geometry column in
  `4326` and reproject on demand for area/distance, or maintain both, is a real decision, not an
  assumed default (§2's ADR roadmap).
- **Spatial indexing.** PostGIS `GiST` indexing is the standard mechanism for the overlap/
  duplicate queries B4 exists to run — needs to be sized and designed against real query
  patterns (per-tenant scan? national scan? both?), not assumed to "just work" at scale.
- **The cross-tenant overlap-detection tension (the single highest-stakes open question in this
  document).** Registry's RLS makes tenant isolation absolute — a tenant cannot see another
  tenant's rows at all. But overlap/duplicate-geometry detection is only useful as a fraud
  signal if it can compare a new parcel's geometry against *every* existing parcel's geometry in
  the same country, including ones registered by other tenants (two different survey firms
  registering the same physical land is exactly the fraud pattern this feature exists to catch).
  This is structurally different from every RLS decision B1–B3 made, all of which assumed
  strict per-tenant isolation was the correct default with a narrow, named `super_admin`
  exception. B4 needs its own explicit ADR decision here — not a default, and not resolved by
  this planning document — covering: what a `field_agent` actually sees when an overlap is
  detected (presumably not full details of the other tenant's parcel, likely only "a conflict
  exists, escalate to governance/compliance"), what a compliance/governance role sees, and
  whether the detection *computation* running with elevated/cross-tenant read access is itself
  narrowly scoped and audited (matching the `super_admin`/hydration-service-account pattern
  already established, not a new bypass).
- **Dependencies.** Depends entirely on B3 (frozen, provides the seam). Precedes B7 (Trust
  Engine, consumes B4's signal) and likely informs B6 (Survey — a survey plan upload is a
  plausible source of the geometry payload B4 validates, though B6 itself remains unscoped).
  F2 (Registry + Spatial UI) needs F1 (Auth UI) first, independent of B4's backend readiness.

### 1.4 Repository assessment

**Strengths:** Registry (B3) is now a proven, twice-repeated template (ports & adapters,
RLS-in-same-migration, audit-chain, Unit-of-Work, a genuine authorization model closing a named
historical defect) — B4 has two clean precedents to replicate, not one. PostGIS is already the
running database image with the extension already confirmed live. `GeometryPort` already exists
as a stable, minimal, unimplemented contract — B4 does not need to negotiate that interface with
Registry; it only needs to implement it correctly.

**Weaknesses / technical debt (inherited, not introduced by B4 planning):**
- Frontend remains pre-F1 — no map UI, no polygon editor exists to even receive a payload B4
  would validate. Not blocking for B4's backend-only slices, but real end-to-end use of B4
  cannot be demonstrated until F1/F2 land.
- The containerized backend's `KEYCLOAK_REALM_URL` host-relative networking gap (documented
  since B3 Slice 2) remains open — B4's own live verification will hit the same limitation and
  should plan around it (host dev server for authenticated flows) rather than attempt to fix it
  as part of B4.
- SQLAlchemy's default connection-pool ceiling (documented since B3 Slice 2) is a platform-wide
  constraint B4's own live-concurrency testing (if any) should be aware of.
- No CI/CD verification has been reconfirmed since B3's own discovery document flagged this as
  unconfirmed — still worth resolving independent of B4.

### 1.5 Gap analysis (current platform vs. long-term vision, B4-relevant slice only)

**Critical:** no Spatial Intelligence capability at all (this is what B4 addresses); no Evidence
pipeline (B5) — relevant because a survey-plan upload feeding B4's geometry validation may
eventually route through B5's integrity pipeline, an open question, not a B4 decision.

**High:** no Trust Engine (B7) to consume B4's signal yet — correctly sequenced after, not a B4
blocker, but worth naming so B4's output contract (what exactly is "the duplicate-geometry
signal," in what shape) is designed with B7's eventual consumption in mind, not redesigned later.

**Medium/Low:** unchanged from B3's own gap analysis for everything not spatial-adjacent (Survey,
Workflow, Community Trust, Economic/Billing, Knowledge Graph, AI, frontend beyond F0/F1) — not
re-litigated here.

---

## 2. Architectural Scope

### 2.1 What Registry (B3, frozen) owns — unchanged, not reopened

Parcel identity (`parcel_id`), parcel number (ADR-014), registry metadata, lifecycle (`status`),
mutation authorization (ADR-015), audit, and the *association point* `geometry_reference` — an
opaque string, never geometry data, never validated for spatial correctness by Registry itself.
B4 does not add fields to `parcels`, does not gain a migration that touches Registry's tables,
and does not introduce a second way to mutate a `Parcel`.

### 2.2 What Spatial Intelligence (B4, new) owns

- The actual geometry payload — coordinates, polygon rings, coordinate reference system — in
  **its own table(s), its own migration series (`0010`+), its own bounded-context folder**
  (`app/contexts/spatial/`, mirroring Registry's internal shape: `domain/`, `ports.py`,
  `adapters/`, `application/`, `api/`, `dependencies.py`).
- Validation of that payload: well-formed (no self-intersection), within plausible coordinate
  bounds, real polygon containment against administrative boundaries (replacing Base44's
  hardcoded LGA bounding-box check, per `docs/REBUILD_PLAN.md`'s explicit instruction).
- Overlap and duplicate-geometry detection — the actual fraud-signal feature, and the first B7
  signal source.
- Spatial indexing, adjacency, and distance queries.
- Map tiling / spatial search — the serving layer a future F2 frontend consumes (API design
  only in B4's backend scope; the frontend itself is F2's concern).

### 2.3 The interaction contract (the boundary itself)

Registry calls `GeometryPort.reference_is_valid(geometry_reference)` before storing or clearing
a reference (already built, ADR-016) — B4 supplies the real adapter, replacing
`PlaceholderGeometryAdapter`, with zero change to `ParcelService`, `Parcel`, or any Registry test
(the concrete proof ADR-016's design was correct, not merely asserted). B4's own API (a new route
prefix, e.g. `/v1/spatial/...`) is where an actual geometry payload gets submitted or queried —
`PUT /v1/parcels/{id}/geometry` on the Registry side continues to store only a reference *string*
(plausibly, by convention TBD in ADR-018, an id B4 itself issues once it accepts a payload).
**No direct cross-context database access in either direction:** B4 never writes to `parcels`;
Registry never writes to B4's tables. Where B4 needs to know a `parcel_id`/`tenant_id` exists at
all, it does so through its own repository against its own foreign-keyed reference to
`parcels.id`/`tenants.id` (read-only relationship, exactly how `parcels.tenant_id` already
FK's to `tenants.id` without Registry writing into Identity's tables) — never a live call back
into Registry's application services.

### 2.4 What must not happen

B4 must not modify `parcels`, must not weaken or bypass Registry's RLS, must not introduce a
second authorization mechanism, must not introduce a second audit mechanism, and must not resolve
the cross-tenant overlap-detection question (§1.3) via an ad hoc bypass — that question gets its
own ADR decision (§3) before any code implementing it is written.

---

## 3. ADR Roadmap

**Status: ADR-018 accepted; ADR-019 accepted; ADR-022 accepted, fully implemented, and frozen (B4
Slice 2 — see `docs/B4_VERIFICATION_CHECKLIST.md`'s Slice 2 section for live-verified evidence);
ADR-021 proposed (drafted, architecture only, pending review — B4 Slice 3 not authorized until
accepted); ADR-020, ADR-023 not yet created.** (Renumbered from the original discovery draft: the
`GeometryPort` interface amendment ADR-018 §5 flagged got its own dedicated slot, ADR-019, per
explicit instruction that it be formally recorded and reviewed separately before B4 Slice 1
began — every ADR after it shifted by one accordingly.)

| ADR | Purpose | Depends on | Why required |
|---|---|---|---|
| **ADR-018** — Spatial Domain Model & Schema *(Accepted)* | Geometry storage type (PostGIS `geometry` vs `geography`), SRID/CRS decision, the aggregate B4 introduces (name, invariants), migration numbering (`0010`+), exact relationship to `parcels.geometry_reference` | ADR-016 (the seam), ADR-009/010 (RLS/tenant shape) | New bounded context, new schema, a real undecided design choice (§1.3's CRS question) |
| **ADR-019** — GeometryPort Interface Amendment *(Accepted, implemented)* | Formally records the tenant/parcel-scoped extension to `GeometryPort.reference_is_valid` that ADR-018 §5 identified as necessary — closes a cross-tenant-reference leak the placeholder adapter couldn't have caught | ADR-016 (extends), ADR-018 (identifies the need) | Touches frozen B3 code (`ParcelService`'s call site); this codebase's amendment discipline requires that be its own explicit, reviewable record, not folded silently into a larger ADR |
| **ADR-020** — GeometryPort Real Adapter & Validation Rules *(superseded in practice — see note below the table)* | What "valid" means in `reference_is_valid`'s real implementation: well-formed polygon, no self-intersection, real administrative-boundary containment (replacing Base44's hardcoded bounding-box check) | ADR-018, ADR-019, ADR-022 (the authorization model any real submission path must respect) | Directly closes a named audit defect (`docs/REBUILD_PLAN.md`'s B4 row); must document the validation algorithm, not assume it |
| **ADR-021** — Spatial Conflict Detection & Controlled Cross-Tenant Intelligence *(Proposed — `docs/adr/ADR-021-spatial-conflict-detection-and-controlled-cross-tenant-intelligence.md`)* | Controlled Platform Authority scope for the one component permitted a cross-tenant geometry read; the six-category conflict classification model (no conflict/overlap/duplicate/near-duplicate/suspicious pattern/confirmed conflict — model only, no algorithm); minimal-disclosure default to ordinary registrants vs. governance's narrowly-extended reach; Registry/Spatial ownership split; audit requirements. Explicitly does not define spatial query design, indexing strategy, or thresholds — that remains Slice 3's implementation job against this model | ADR-018, ADR-010 (tenant isolation), ADR-022 (same-tenant model this must not weaken), `docs/ENGINEERING_RULES.md` rule 9 | The highest-stakes architectural decision in B4 — a genuine tension with the platform's absolute-tenant-isolation default, not a routine query-design choice |
| **ADR-022** — Spatial Authorization Model *(Accepted, implemented — `docs/adr/ADR-022-spatial-authorization-model.md`)* | The complete creator-or-governance mutation authorization model for `ParcelGeometry`, mirroring ADR-015's model for Registry — closes the coarse-role-gate gap B4 Slice 1 shipped with and explicitly flagged; the full mutation matrix, archived-parcel behavior, and audit requirements for every Spatial mutation | ADR-015 (the model mirrored), ADR-011 (delegation, reused unchanged), ADR-018 (the domain model governed, not redefined) | Elevated from an implementation observation to a governance requirement after Slice 1's review — the identical ADR-005-shaped gap Registry once had, caught by design review this time rather than by a later audit |

**Note on ADR-020:** B4 Slice 2 (authorized directly against ADR-022's acceptance, without a
separate ADR-020) implemented both the real `GeometryPort` adapter (`RealGeometryAdapter`) and
real structural geometry validation under ADR-018/ADR-022's existing authority, rather than
waiting for a dedicated ADR-020. Self-intersection and administrative-boundary containment —
ADR-020's originally-envisioned harder content — remain undesigned and undecided; if that real
geometric validation is ever built, it still needs its own ADR (whether numbered ADR-020 or
later), extending ADR-018 rather than silently expanding Slice 2's already-implemented structural
validator.
| **ADR-023** (open question, likely deferred) — Map Tiling / Spatial Search API & Public Exposure | Serving mechanism for map tiles/spatial search, whether any of it is ever public-facing | ADR-018 | Backend-only design has no frontend to validate against yet (F2 blocked on F1) — flagged as a candidate for deferral to whenever F2 actually begins, not decided here |

None of these change ADR-009 through ADR-017 — they extend the platform the same way ADR-013–016
extended B1/B2's frozen baseline into Registry.

---

## 4. Implementation Plan

Proposed as slices, mirroring B2's and B3's own pattern (each individually reviewed and accepted
before the next begins). Slice count and order are a recommendation, not a commitment — subject
to the approval discussion, same as B3.4 was flagged as reorderable in B3's own planning doc.

**Actual execution has diverged from this section's original plan, in ways worth recording
rather than leaving as stale numbering:** what shipped as "B4 Slice 1 — Spatial Domain
Foundation" implemented only the domain-model half of Slice B4.1 below (the aggregate, schema,
bounded-context shape) — the real `GeometryPort` adapter half was deferred once Slice 1's own
review surfaced the authorization gap ADR-022 now governs. "B4 Slice 2 — Geometry Validation &
Real Geometry Adapter" (implemented and live-verified — see
`docs/B4_VERIFICATION_CHECKLIST.md`'s Slice 2 section) is Slice B4.1's *remaining* half below,
now complete, not Slice B4.2 (Overlap & Duplicate-Geometry Detection) — that slice, if the
numbering below is kept literally, is an effective "Slice 3" in execution order, **not
authorized**, per Slice 2's own explicit stop condition. Not renumbered here to avoid churn;
whichever numbering is used going forward, ADR-021 must be accepted before Slice 3 begins.

### Slice B4.1 — Spatial Domain Model & Real GeometryPort Adapter
- **Objective:** the actual geometry aggregate, its own table/migration, and a real
  `reference_is_valid` implementation replacing `PlaceholderGeometryAdapter` — with zero change
  to Registry code, proving ADR-016's boundary claim for real.
- **Business value:** the platform can store and validate real parcel geometry for the first
  time; unblocks every later B4 slice.
- **Architecture impact:** first new bounded-context folder since Registry; first migration past
  `0009`.
- **Dependencies:** none beyond the frozen B3 baseline.
- **Complexity:** Medium.
- **ADR requirement:** ADR-018, ADR-019, ADR-020.

### Slice B4.2 — Overlap & Duplicate-Geometry Detection
- **Objective:** the actual fraud-signal feature — real polygon overlap/duplicate detection,
  GiST-indexed, live-tested under real concurrent registration load (mirroring B3 Slice 2's
  concurrency-verification rigor).
- **Business value:** the first genuine anti-fraud spatial signal this platform has ever had
  correctly implemented (Base44's version is the confirmed negative example, §1.2).
  Directly feeds B7's future scoring.
- **Dependencies:** B4.1; resolves the cross-tenant question ADR-021 must decide before this
  slice's authorization model can be finalized.
- **Complexity:** High — the cross-tenant visibility decision (§1.3/§3) is a genuine open
  architectural question, not routine implementation.
- **ADR requirement:** ADR-021, ADR-022.

### Slice B4.3 — Spatial Search / Adjacency / Distance
- **Objective:** the remaining query capabilities named in `docs/REBUILD_PLAN.md`'s B4 row
  (adjacency, distance) beyond overlap/duplicate detection specifically.
- **Dependencies:** B4.1, B4.2.
- **Complexity:** Medium.
- **ADR requirement:** likely none beyond ADR-018/021 if the query model is already settled;
  reassessed at B4.2's completion, not presupposed here.

### Slice B4.4 — Map Tiling Foundation (candidate for deferral)
- **Objective:** the serving-layer groundwork for a future map UI.
- **Recommendation:** likely defer until F1/F2 frontend work is scheduled, since there is no
  consumer to validate against yet — flagged as a decision for the approval discussion, not
  presupposed.
- **ADR requirement:** ADR-023, if and when pursued.

**Recommended execution order:** B4.1 → B4.2 → B4.3, each paused for review before the next
begins, matching B3's own slice-by-slice governance. B4.4 recommended deferred pending frontend
scheduling — an explicit recommendation, not a default assumption.

---

## 5. Approval Gate

No B4 production code has been written. This document is presented for review of: the user
needs and technical constraints (§1), the Registry/Spatial architectural boundary (§2),
the proposed ADR roadmap (§3), the phased implementation plan (§4), and the recommended
execution order (§4's closing paragraph) — most importantly, **the cross-tenant overlap-
detection question (§1.3/§3/ADR-021)**, which is a genuine architectural tension with this
platform's absolute-tenant-isolation default and should be explicitly discussed before any ADR
resolves it, not resolved by default inside an ADR draft.

**Waiting for explicit approval before beginning any B4 implementation** — coding does not
commence until this discovery phase, the architectural scope, and the ADR roadmap are reviewed
and approved, per the B4 program initiation instruction.
