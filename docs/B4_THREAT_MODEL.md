# B4 Threat Model & Trust Boundaries — Spatial Intelligence

**Status:** Analysis only. No B4 production code exists, no ADR has been written for B4 yet.
This document is the required gate between `docs/B4_DISCOVERY_AND_PLANNING.md` (accepted as the
official B4 planning baseline) and **ADR-018 — Spatial Domain Model**, per explicit instruction:
ADR-018 begins only after this threat model is reviewed and approved. `docs/PHASE_GATES.md`
Phase 1 already names "Threat Model" as a required System Architecture check — this is that
check, performed before Spatial Intelligence's architecture is decided, not after.

**Date:** 2026-07-21

**Governance note on this document's own scope:** this is a security *analysis*, not an
implementation. It identifies assets, trust boundaries, and threats, and derives **binding
architectural requirements** that ADR-018 through ADR-022 must satisfy — it does not itself
decide the schema, the query design, or the exact authorization mechanism (those remain ADR-018
through ADR-021's job). Where this document says "must," it is stating a constraint the
subsequent ADRs are required to meet, not pre-writing those ADRs.

---

## 1. Why this document exists now, specifically

`docs/B4_DISCOVERY_AND_PLANNING.md` §1.3 already flagged one specific tension as "the single
highest-stakes open question in this document": overlap/duplicate-geometry detection is only
useful as a fraud signal if it can compare a new parcel's geometry against geometry registered by
*other tenants*, which cuts directly against the absolute per-tenant RLS isolation every prior
programme (B1–B3) treated as a non-negotiable default. That is a genuine trust-boundary problem,
not a routine query-design question — exactly the category of issue this engagement's own
governing principle ("evidence over assumptions," `docs/ENGINEERING_RULES.md`) says must be
resolved by analysis before architecture, not discovered mid-implementation the way B3 Slice 2's
per-tenant-vs-per-country allocator scope was (a correctness bug caught by live testing; this
document exists so B4's analogous question is caught by *analysis*, before any code, since a
tenant-isolation defect is a security property, not a correctness one — a live-testing safety net
is the wrong tool for catching this class of problem before it ships).

## 2. Assets to protect

1. **Geometry payloads** — the actual coordinate/polygon data a parcel's boundary is made of.
   Sensitive because it reveals precise physical location and extent of land a specific tenant's
   principal has registered — information a competing tenant (a rival survey firm, in practice)
   has a real incentive to want and no legitimate need to see in full.
2. **The fact that an overlap exists** — distinct from the geometry itself. Even without seeing
   another tenant's exact polygon, learning "parcel X overlaps with *something* already
   registered" reveals that a specific area of land is contested — commercially and legally
   sensitive information in a land-dispute context, and itself a target for the same read
   boundary that must expose it *to the right principal* and no one else.
2. **Registry's frozen invariants** — `parcel_id`, `tenant_id`, `created_by`, RLS, the PDP/PEP
   pipeline, the audit chain (ADR-009/013/015, frozen). B4 must be analyzed for whether it could
   *weaken* any of these by consuming them incorrectly — it must never be able to modify them.
3. **The `GeometryPort` contract itself** — Registry's one dependency on B4 (ADR-016). If B4's
   real adapter is wrong, slow, or exploitable, that risk propagates directly into every Registry
   mutation that touches geometry, since `ParcelService.set_geometry_reference` calls it
   synchronously in the request path.
4. **Future consumers not yet built** — B7 (Trust Engine, reads B4's duplicate-geometry signal)
   and F2 (frontend map/tile consumer). Not yet real, but a trust boundary should be named for
   them now so ADR-018–021 don't have to be re-opened once those consumers exist (the same
   "design the seam before the consumer exists" discipline ADR-016 already applied to Registry
   itself).

## 3. Trust boundaries

Numbered so §5's threat analysis can reference each one directly.

- **TB1 — Anonymous → Authenticated.** Frozen, B1 (ADR-009). Unchanged by B4; named here only so
  every later boundary's starting assumption ("the caller has already crossed TB1") is explicit.
- **TB2 — Authenticated tenant-scoped principal → Registry.** Frozen, B1/B3 (ADR-009/013/015).
  RLS + PDP/PEP + creator-or-governance mutation authorization. B4 must not weaken this boundary
  by, e.g., giving `ParcelService` a reason to bypass `_authorize_mutation` "for spatial reasons."
- **TB3 — Registry → `GeometryPort`.** New, defined by ADR-016, not yet implemented for real.
  Registry trusts the adapter's answer to `reference_is_valid` and nothing else — B4's adapter
  must not be able to write to `parcels`, must not be able to raise an exception that leaks
  information about *other* tenants' data through Registry's error responses, and must return an
  answer B4 remains solely accountable for (Registry does no independent verification, by
  design — this is the one place B4's correctness is load-bearing for Registry's own behavior).
- **TB4 — Tenant-scoped principal → Spatial Intelligence's own API (not yet built).** The
  boundary a future `/v1/spatial/...` router introduces. Must reuse the identical
  Identity → Tenant → Delegation → RBAC → PDP pipeline (ADR-016's mandate, reaffirmed here) —
  no second authentication or authorization mechanism.
- **TB5 — The cross-tenant read boundary inside Spatial Intelligence itself (the crux of this
  document).** Whatever component computes overlap/duplicate-geometry detection necessarily
  reads geometry belonging to more than one tenant in a single operation — this is *structurally*
  different from every prior RLS boundary in this codebase, none of which ever needed to read
  across tenants except for the single, narrow, explicitly-audited `super_admin` exception. This
  boundary does not yet have a design (that is ADR-020's job) — this document's job is to state
  what any design crossing it must guarantee (§6).
- **TB6 — Spatial Intelligence → future consumers (B7, F2).** Not yet built. Named so its shape
  (what a "duplicate-geometry signal" actually contains, and whether map/tile data is ever public)
  is designed with these boundaries in mind from ADR-018 onward, not discovered later.

## 4. Actors and trust levels (extends, does not replace, the existing role model)

No new role is introduced by this document — `docs/adr/ADR-004`'s "a new role is an ADR
amendment, not a string literal" applies to B4 exactly as it did to B3. The existing
`PARCEL_REGISTRANT_ROLES`/`GOVERNANCE_ROLES` distinction (ADR-013/015) is the starting point:

| Actor | Trust level for B4 purposes |
|---|---|
| Anonymous | No access (TB1, unchanged) |
| Ordinary registrant (`field_agent`, etc.), own tenant, own parcel | May submit/view geometry for parcels they created (mirrors ADR-015's creator authority) |
| Ordinary registrant, own tenant, colleague's parcel | Denied, mirroring ADR-015's ADR-005 fix — geometry mutation must not reopen the defect Registry just closed |
| Governance role (`compliance_officer`/`surveyor_general`), own tenant | Tenant-wide reach for geometry, mirroring ADR-015 |
| `super_admin` | Cross-tenant reach, mirroring existing RLS/`_in_scope` bypass |
| **The overlap-detection computation itself** | **A new trust level this codebase has never needed before** — see §6. Not a role a human holds; a system-internal read scope that must be as narrowly defined and as thoroughly audited as the existing hydration service-account pattern (`build_production_context_hydrator`'s documented `app.is_super_admin` bypass for the one fixed, non-input-influenced query it runs) — not a blanket cross-tenant grant to any code path that finds it convenient. |

## 5. Threat analysis (STRIDE, by trust boundary)

### TB3 — Registry ↔ GeometryPort

- **Spoofing:** N/A — this is an in-process call, not a network boundary; no separate identity to
  spoof. (If a future adapter calls an *external* service — e.g., a national mapping API,
  named as a possibility in ADR-016 — that becomes a new boundary requiring its own analysis at
  that time, not assumed safe by extension of this one.)
- **Tampering:** the adapter must not be able to mutate `parcel.geometry_reference` or any other
  `Parcel` field itself — `ParcelService` already owns that write, calling the port only for a
  boolean answer (ADR-016's existing design). **Requirement for ADR-019:** the real adapter's
  interface must not grow beyond returning a boolean/simple result; any adapter design that
  wants to return a mutable object handed back into Registry's write path is out of bounds.
- **Repudiation:** covered by Registry's existing audit — `registry.parcel.geometry_attached`/
  `.geometry_detached` already record the outcome (ADR-015/016). No new audit gap identified.
- **Information disclosure:** an adapter that raises an exception with detail about *why* a
  reference failed validation (e.g., "reference belongs to tenant X's private geometry store")
  could leak cross-tenant information through Registry's own error response. **Requirement for
  ADR-019:** `reference_is_valid`'s failure mode must be a plain boolean; any richer diagnostic
  information must never propagate through Registry's HTTP error surface.
- **Denial of service:** a slow or unbounded adapter call blocks the request thread inside
  Registry's own mutation path (it's awaited synchronously in `set_geometry_reference`).
  **Requirement for ADR-019:** the real adapter's validation must be boundable in cost (e.g., no
  unbounded external network call with no timeout) — this is a concrete constraint on
  implementation, not merely a performance nicety, since Registry's own mutation endpoints
  inherit whatever latency/failure characteristics the adapter has.
- **Elevation of privilege:** N/A at this boundary specifically — the adapter has no authority to
  grant; it only answers a validity question. (The actual privilege question lives at TB5.)

### TB4 — Principal ↔ Spatial Intelligence's own API (not yet built)

- Standard PDP/PEP threats, structurally identical to every prior context's own TB2-equivalent —
  no novel threat identified here **provided** ADR-021 in fact reuses the existing pipeline
  verbatim, as ADR-016 already mandates. The only threat worth naming explicitly:
  **elevation of privilege via a "helpful" spatial-specific bypass** — e.g., a future engineer
  adding "surveyors can always view any geometry, since they need to for fieldwork" as an
  informal exception, without an ADR. **Requirement for ADR-021:** any such exception must be
  named, scoped, and justified in the ADR itself — never added as an undocumented convenience.

### TB5 — The cross-tenant overlap-detection read boundary (highest-severity findings)

- **Information disclosure (the primary threat):** the most direct way this feature could go
  wrong is a same-country registrant learning more than "a conflict exists" about a competing
  tenant's parcel — e.g., its exact boundary, its owner's name, or which specific tenant
  registered it. This is a genuine, non-hypothetical risk given the asset (§2) and the actor
  (any ordinary registrant, not merely governance): a rival survey firm has a direct commercial
  incentive to use an overlap-check response as a way to map competitors' registered land.
  **Requirement for ADR-020:** the response to an ordinary registrant must be minimal — a
  boolean/flag ("a conflict was detected, escalate to governance") at most, never the other
  tenant's geometry, `tenant_id`, or any identifying metadata. A governance/compliance role may
  legitimately need more detail to resolve the conflict — if so, that expanded detail is itself a
  decision ADR-020/021 must make explicitly, not an assumed consequence of "governance roles see
  everything" (they don't, today — `GOVERNANCE_ROLES`' current reach is tenant-wide, not
  cross-tenant, except for `super_admin`; extending it cross-tenant for this one purpose is a new
  decision, not a reuse of an existing one).
- **Elevation of privilege (the mechanism-level threat):** whatever code path performs the
  actual cross-tenant read necessarily runs with elevated scope (structurally similar to
  `app.is_super_admin` being set for the hydration service-account's one fixed lookup,
  `context_hydration.py`'s `build_production_context_hydrator`). That precedent is instructive
  precisely because of *why* it was judged safe: the query is fixed at the call site, not
  influenced by request input beyond an already-verified subject, read-only, and immediately
  rolled back. **Requirement for ADR-020:** any cross-tenant read the overlap computation
  performs must satisfy the same shape — a fixed, input-bounded query (e.g., "geometries within
  a bounding box/radius of the submitted geometry," never an open-ended cross-tenant scan
  parameterized by arbitrary caller input), read-only, and **must be audited** (unlike the
  hydration lookup, which is explicitly *not* audited because it runs on every single request —
  an overlap check runs only on geometry submission, infrequent enough that auditing it is not
  the performance concern that ruled out auditing hydration). **This is the single most
  important architectural constraint this document identifies.**
- **Tampering:** a malicious or malformed geometry payload (self-intersecting polygon, absurd
  coordinate values, deliberately degenerate shapes crafted to make a spatial index query
  expensive or return incorrect results) is a direct input-validation threat. **Requirement for
  ADR-019:** payload validation (well-formedness, coordinate bounds, no self-intersection) must
  happen *before* the payload is ever used in an overlap query, not merely at storage time.
- **Denial of service:** an unindexed or naively-designed overlap query is an O(n) or worse scan
  across every parcel's geometry in a country as registration volume grows — a genuine
  availability risk at scale, not merely a performance-tuning afterthought, given this is
  explicitly meant to run synchronously (or near-synchronously) on every registration/survey
  submission. **Requirement for ADR-020:** GiST indexing and query design must be evaluated
  against realistic volume, not assumed adequate by default — mirroring B3 Slice 2's own
  live-concurrency-testing discipline, applied here to spatial query performance instead of
  allocator contention.
- **Spoofing:** GPS data itself can be spoofed (`identity_users`-adjacent precedent: this
  codebase already tracks a `gps_spoofing_flag`-shaped concern in the audited legacy schema,
  `docs/audits/AQUASAVANNAH_LANDVAULT_FORENSIC_AUDIT.md`'s field inventory) — B4 does not need to
  *solve* GPS spoofing (that's a data-quality/Trust-Engine-scoring concern, arguably B9/B7's
  territory), but ADR-019's validation rules must not silently treat a spoofed or degenerate
  coordinate as valid input just because it is well-formed JSON/WKT.
- **Repudiation:** every geometry submission and every overlap determination must be audited
  through the existing kernel `audit()` mechanism (ADR-007/009, unchanged) — **requirement for
  ADR-018/020:** no second audit mechanism, and the overlap-check audit entry itself must not leak
  the §5/TB5 information-disclosure risk into the audit log's own payload (i.e., audit *that* a
  conflict was found and against whom access was granted to investigate it, not necessarily the
  full competing geometry, unless a governance-role actor legitimately needs that recorded).

### TB6 — Spatial Intelligence → future consumers (B7, F2)

- No implementation exists to analyze yet. The one requirement worth stating now, before either
  consumer is built: **the duplicate-geometry signal B7 eventually consumes must be shaped so
  that Trust Engine scoring never needs to reach across the TB5 boundary itself** — B7 should
  receive a pre-computed, already-scoped signal (e.g., "conflict severity: high/medium/none"),
  never raw cross-tenant geometry, so that TB5's containment is not silently bypassed by a later
  context that simply queries B4's tables directly instead of going through whatever narrow
  interface ADR-020 defines.

## 6. Summary of binding requirements carried forward into ADR-018 through ADR-021

1. **ADR-018 (Domain Model):** payload validation must be structurally separated from storage —
   invalid geometry must never reach persistence or query layers unvalidated (feeds TB5's
   tampering/DoS findings).
2. **ADR-019 (Real Adapter & Validation):** `reference_is_valid`'s failure mode is a plain
   boolean, cost-bounded, no rich diagnostic leakage through Registry's error surface; validation
   rules must reject degenerate/self-intersecting geometry before it is usable in any query.
3. **ADR-020 (Overlap Detection):** the single most consequential ADR from a security standpoint.
   Must define: (a) what an ordinary registrant sees on conflict (minimal, no cross-tenant
   geometry/identity disclosure), (b) what a governance role sees and why that's a deliberate,
   named exception rather than an assumed default, (c) the cross-tenant read mechanism's exact
   shape (fixed, input-bounded, read-only, audited — not an open scan), and (d) indexing/query
   performance evaluated against realistic volume.
4. **ADR-021 (Spatial Authorization):** reuses the existing pipeline verbatim (TB4); any
   cross-tenant exception is named and justified explicitly, never an informal convenience.
5. **Carried into ADR-018–021 collectively:** every new table gets RLS in the same migration
   that creates it (the platform's existing non-negotiable rule, `docs/ENGINEERING_RULES.md` #1)
   — TB5's cross-tenant read is an explicit, narrow, *additional* mechanism layered on top of
   default-isolated RLS, never a reason to relax the default itself.

## 7. Residual risks and explicitly open questions (not resolved by this document)

- The exact shape of "minimal disclosure on conflict" (§5/TB5) is a product/legal question as
  much as an engineering one — what a real land-registry dispute process actually needs a
  registrant to see is domain input this document cannot supply; ADR-020 must either resolve it
  or explicitly flag it as needing non-engineering stakeholder input before that ADR is accepted.
- Whether the overlap-detection computation should run synchronously (blocking the registration
  request) or asynchronously (a background job, closer to Base44's own `asyncGISValidation`
  naming, but — per `docs/REBUILD_PLAN.md`'s explicit instruction — "made authoritative" this
  time, meaning its result cannot be silently ignorable the way Base44's apparently was) is an
  ADR-020 decision, not decided here.
- GPS spoofing detection itself remains out of scope for B4 (§5/TB5, "Spoofing") — named as a
  boundary this document deliberately does not try to close, so it is not forgotten.

## 8. Approval Gate

This threat model does not authorize implementation. Per the governing instruction: **ADR-018 —
Spatial Domain Model begins only after this document is reviewed and approved.** ADR-019 through
ADR-021 must each satisfy the binding requirements in §6 to be accepted; ADR-020 in particular
should not be considered accepted on architectural merits alone if §7's product/legal question
remains unresolved. No B1–B3 frozen ADR is touched, modified, or reopened by this document. No
production code has been written.
