# ADR-021 — Spatial Conflict Detection & Controlled Cross-Tenant Intelligence

**Status:** Proposed — architecture only. **No code is written or modified under this document.**
Per the governing instruction, B4 Slice 3 (overlap detection, duplicate detection, fraud
detection, conflict scoring, AI analysis, spatial search, risk engines) does not begin — no
implementation, no algorithm, no query design — until this ADR is itself reviewed and explicitly
accepted.

**Date:** 2026-07-23

**Governed by:** `docs/B4_THREAT_MODEL.md` §5 TB5 (the cross-tenant overlap-detection read
boundary — this document's single most binding source; TB5's five requirements are restated and
resolved, not reopened, below), `docs/ENGINEERING_RULES.md` rule 9 (Controlled Platform
Authority — the doctrine this ADR's entire cross-tenant mechanism must satisfy), `docs/adr/
ADR-018-spatial-domain-model.md` (the `ParcelGeometry` aggregate this ADR reads, never redefines),
`docs/adr/ADR-022-spatial-authorization-model.md` (the same-tenant mutation model this ADR must
not weaken — §11 there already anticipated this document by name), `docs/REBUILD_PLAN.md` §1
(B4's own scope explicitly lists "overlap + duplicate-geometry detection" as B4's, not a separate
programme's, responsibility). Extends `docs/adr/ADR-013-parcel-aggregate-registry-domain-model.md`
(`Parcel.tenant_id`/`created_by`, read but never modified) and reuses `docs/adr/
ADR-007-audit-trail-evidence-model.md` (the one audit mechanism, unchanged). Does not modify any
of them.

## Architectural context — why this ADR is required now

B4 Slice 1 (the `ParcelGeometry` aggregate and its own bounded context) and B4 Slice 2 (real
structural validation, ADR-022's creator-or-governance authorization, the real `GeometryPort`
adapter) have both operated entirely **within the boundary of a single parcel and a single
tenant.** Every check either slice performs — structural validity, creator-or-governance
authority, tenant scope — answers a question about one `ParcelGeometry` row in isolation. Nothing
built so far reads, compares, or reasons about more than one geometry at a time, and nothing built
so far crosses a tenant boundary except through the one existing, already-audited `super_admin`
exception.

Overlap/duplicate-geometry detection is a different architectural category, not a larger version
of the same one: it requires comparing a submitted geometry against *other* geometries — plural,
potentially belonging to *other* tenants — before any conflict determination can be made at all.
This is precisely the scenario `docs/B4_THREAT_MODEL.md` §5 (TB5) identified, before any of Slice
1 or Slice 2 was built, as B4's single highest-severity finding: a same-country registrant has a
direct commercial incentive to use an overlap-check response as a reconnaissance tool against a
competing tenant's land holdings, unless the response is deliberately, architecturally minimal.
This ADR is the constitutional resolution TB5 required before that capability could be designed,
consistent with this platform's established discipline that a genuinely new authority shape gets
its own ADR before implementation (ADR-005→ADR-015 for Registry; the coarse-gate→ADR-022
escalation for Spatial itself, one slice ago).

## Decision

### 1. Controlled Platform Authority — which components may perform cross-tenant comparison

**Exactly one component may read geometry belonging to more than one tenant in a single
operation: a conflict-detection service, internal to the Spatial bounded context, invoked only as
a side effect of an already-authorized `submit_geometry` call.** No other code path — no Registry
code, no other Spatial method, no ad hoc query, no future context — may perform a cross-tenant
geometry read. This satisfies `docs/ENGINEERING_RULES.md` rule 9's four conditions by
construction, not by convention:

- **Fixed at the call site:** the conflict-detection service's cross-tenant read is invoked from
  exactly one place (the geometry-submission path), with a fixed shape — "geometries within a
  bounded spatial neighbourhood of the geometry just submitted" — never a general-purpose query
  parameterized by arbitrary caller input. A caller cannot ask the service to search anywhere
  other than around their own just-submitted geometry.
- **Read-only:** the cross-tenant portion of this operation never writes to another tenant's
  data. Any write this capability produces (a conflict record, a flag) is scoped to the
  submitting tenant's own geometry and/or a platform-level conflict record (§4) — never a mutation
  of the other tenant's `ParcelGeometry` row.
- **As narrow as the task allows:** the read returns only what §3 (Cross-Tenant Visibility)
  permits at each caller's privilege tier — never a raw, unfiltered cross-tenant result set.
- **Audited:** every invocation of the cross-tenant read is audited (§7) — no exception, unlike
  the one existing precedent (`context_hydration`'s per-request lookup, deliberately unaudited
  because of its request-volume), because this operation runs only on geometry submission, not on
  every request, so the performance rationale that justified skipping audit there does not apply
  here (`docs/B4_THREAT_MODEL.md` §5's explicit distinction).

This is a structural elevation-of-privilege boundary in the same sense the `super_admin` RLS
bypass and the hydration service-account lookup already are — a named, narrow, explicitly
justified exception, never an implicit one. No second Controlled Platform Authority exception may
be introduced for this capability; if a future need requires a differently-shaped cross-tenant
read, that need gets its own ADR extending this one, not a quiet broadening of this exception's
scope.

### 2. Fraud detection boundary — six distinct concepts, never conflated

This ADR names six distinct situations a submitted geometry's relationship to existing geometries
can represent. **These are architecturally distinct outcomes with different disclosure, audit,
and downstream-consumption implications — a system that conflates any two of them produces a
wrong or misleading answer, not merely an imprecise one:**

1. **Duplicate submission** — the same registrant (or the same tenant) submitting materially the
   same geometry more than once, e.g. a retried request or a genuine correction. Not inherently
   suspicious; ADR-018's own append-only supersede lifecycle already handles the same-tenant,
   same-parcel case structurally (a correction supersedes, it does not duplicate).
2. **Overlapping boundaries** — two geometries (any tenant) whose areas genuinely intersect. A
   geometric fact, not by itself an accusation of anything.
3. **Conflicting ownership claims** — two *different* parcels, in the *Registry* sense
   (potentially different tenants), whose submitted boundaries overlap in a way that implies both
   cannot be correct simultaneously. This is the situation this ADR's conflict-detection service
   exists to surface — a geometric finding, with Registry-level consequences this ADR does not
   itself adjudicate (§5).
4. **Neighbouring parcels** — geometries that are adjacent or nearby but do not overlap. Not a
   conflict of any kind; this ADR's classification model (§4) must be able to say "no conflict"
   for this case as confidently as it says "confirmed conflict" for another, per this platform's
   fail-safe-scoring doctrine (`docs/ENGINEERING_RULES.md` rule 4) applied to conflict detection
   specifically: absence of genuine conflict must report as "no conflict," never omitted or left
   ambiguous.
5. **Intentional fraud** — a deliberate attempt to register land already claimed by another party,
   or to fabricate a boundary the registrant knows conflicts with reality. This is an *inference*
   about intent that this ADR's classification model (§4) does not itself make — geometric
   overlap is evidence a governance investigation may consider, never an automated fraud
   determination. Automated fraud adjudication is explicitly out of scope for this ADR and for B4
   generally (§6).
6. **Legitimate corrections** — a registrant fixing a genuine surveying error, which may
   transiently overlap a since-superseded prior submission of their own. ADR-018's append-only
   `SUPERSEDED` lifecycle already distinguishes "the parcel's own prior geometry" from "another
   party's geometry" structurally; this ADR's conflict detection must exclude a geometry's own
   `SUPERSEDED` history from cross-tenant comparison, not flag a registrant's own correction as a
   conflict against themselves.

### 3. Cross-tenant visibility — what each tier may see

**The response to an ordinary registrant on conflict is minimal, by design, per TB5's own explicit
requirement:** a boolean/flag-shaped signal — "a conflict was detected; escalate to governance" —
and nothing more. Specifically, an ordinary registrant (any role that is not a governance role,
per ADR-022's `GOVERNANCE_ROLES`) submitting a geometry that triggers §4's classifier **never**
receives, in any API response:

- the other tenant's geometry (boundary, coordinates, or any derived shape),
- the other tenant's `tenant_id` or any tenant-identifying metadata,
- the other parcel's `parcel_id`, title, address, or any other Registry-owned field,
- the identity (`created_by`, name, contact) of the other geometry's submitter.

**A governance role (`GOVERNANCE_ROLES`, direct or delegated per ADR-011/ADR-022) may see more —
but this is itself a new decision this ADR makes explicitly, not an assumed consequence of
existing governance reach.** `GOVERNANCE_ROLES`' reach today (ADR-015/ADR-022) is tenant-wide, not
cross-tenant, except for `super_admin`. This ADR extends that reach, narrowly and only for this
purpose: a governance-role member of *either* tenant involved in a confirmed conflict (§4) may
view enough detail to resolve it — the specific extent (full boundary vs. bounding summary,
whether the other tenant's identity is disclosed) is deferred to Slice 3's own design, but is
bounded by this ADR's own doctrine: **never more than a named governance investigator legitimately
needs, never as a blanket "governance sees everything cross-tenant" grant.** This exception is
itself subject to Controlled Platform Authority (§1) — fixed at the call site (only reachable
through the conflict-resolution path for a conflict that actually names that governance member's
tenant), read-only, and audited.

**Every disclosure decision above produces an audit record (§7)** — visibility is not a silent
property of a response shape, it is itself an auditable event.

### 4. Conflict classification — the model, not the algorithm

This ADR defines the categories a conflict-detection result may take. **It does not define, or
constrain the future design of, the geometric algorithm, spatial index, or threshold that decides
which category applies** — that is Slice 3's implementation job, against this model:

| Category | Meaning | Disclosure default (ordinary registrant) |
|---|---|---|
| **No conflict** | No other geometry's boundary bears a relationship to the submitted one that any later category names. | Full detail of their own submission, as today. |
| **Boundary overlap** | Two geometries' areas genuinely intersect — a geometric fact only, §2 item 2. | Minimal signal only (§3) if the other geometry belongs to a different tenant; full detail if same-tenant (already visible under existing tenant-scoped reads). |
| **Duplicate geometry** | A submitted geometry is materially identical (or near-identical, within a to-be-defined tolerance) to another tenant's existing geometry — §2 item 1/2 in combination. | Minimal signal only, cross-tenant. |
| **Near duplicate** | Materially similar but not identical — closer than "merely neighbouring" (§2 item 4) but not clearly the same claim. | Minimal signal only, cross-tenant; governance escalation is the only path to more detail. |
| **Suspicious pattern** | A classification reserved for signals this ADR does not itself define (e.g., a submission pattern a future analytics capability flags) — explicitly a placeholder category, not a defined rule, so that Slice 3 is not forced to invent a rule to fill it prematurely. | Governance-only visibility; never surfaced to an ordinary registrant as "suspicious," which would itself be an accusation this ADR does not authorize any automated system to make (§2 item 5, §6). |
| **Confirmed conflict** | A governance role has reviewed a **Boundary overlap**/**Duplicate geometry**/**Near duplicate** finding and determined it represents a genuine, unresolved competing claim. | This is a human governance determination, not an automated one — the classifier itself never assigns this category; it is the output of the governance investigation §3 grants access for. |

**This table is the complete model.** Thresholds, tolerances, spatial-index choice, and query
design are explicitly Slice 3's job, constrained by this ADR but not specified by it.

### 5. Registry interaction — neither context absorbs the other

**Registry remains authoritative for parcel identity** (`parcel_id`, `tenant_id`, `created_by`,
`status` — unchanged, ADR-013). **Spatial remains authoritative for geometry** (`ParcelGeometry`,
its validation, its lifecycle — unchanged, ADR-018). **Conflict detection is a capability of the
Spatial bounded context** (per `docs/REBUILD_PLAN.md`'s own B4 scope, which already lists
"overlap + duplicate-geometry detection" as B4's responsibility, not a separate programme's) —
but implemented as its own internal application service, architecturally distinguished from
`SpatialService`'s existing per-parcel-geometry operations, since it is the first Spatial
capability that reads across aggregate instances (multiple `ParcelGeometry` rows) and potentially
across tenants, which no existing `SpatialService` method does. **This is not a new bounded
context** — it does not introduce a fourteenth entry to `docs/REBUILD_PLAN.md`'s context list —
it is a service-level distinction inside Spatial's own existing boundary, the same way
`ParcelExistencePort` is a distinct concern from `ParcelGeometryRepository` inside that same
context today.

Registry is never queried, joined against, or modified by the conflict-detection service beyond
the read-only `ParcelExistencePort` access Slice 2 already established (tenant/creator/status,
per ADR-022 §8) — a conflict determination never requires Registry to expose any new information,
and Registry's own endpoints remain completely unaware that conflict detection exists, the
identical isolation Registry already maintains toward Spatial's validation and authorization
logic (ADR-018/ADR-022, unchanged).

### 6. Intelligence boundary — a platform capability, not a domain entity

**Conflict detection, fraud detection, risk scoring, machine learning, and analytics are platform
intelligence *services* — not Registry services, and not Spatial *domain* entities.** Concretely:
none of these capabilities is modeled as a field, status, or invariant on `ParcelGeometry` or
`Parcel`. `ParcelGeometry` (ADR-018) remains exactly what it has always been — a validated
boundary with an append-only lifecycle — with no "conflict status," "fraud score," or "risk
level" field ever added to it under this ADR or by implication. A conflict finding (§4) is its own
data, produced and owned by the conflict-detection service, referencing a `ParcelGeometry` (and,
where cross-tenant, another tenant's) by identifier — never a mutation of the geometry aggregate
itself. This mirrors this platform's existing separation between `Parcel`/`ParcelGeometry`
(the things being described) and the Trust Engine (`docs/REBUILD_PLAN.md` B7 — a future
consumer of signals *about* those things, never a field grafted onto them). Any future risk-
scoring or ML capability that consumes a conflict finding does so through whatever narrow,
pre-scoped signal interface Slice 3 (or a later ADR) defines — never by querying
`parcel_geometries` cross-tenant directly, which would silently bypass this entire ADR's
containment (`docs/B4_THREAT_MODEL.md` TB6's own stated requirement).

### 7. Audit requirements

**Every comparison is auditable. Every privileged (cross-tenant) comparison is attributable to
the request that triggered it. Every cross-tenant comparison is justified by the fact that it ran
only as a side effect of an already-authorized geometry submission — no comparison runs
speculatively, on a schedule, or outside a submission's own request. No silent comparison may
exist:** any code path that performs the cross-tenant read described in §1 without producing a
corresponding audit entry is a defect against this ADR, not an acceptable optimization. Reusing
the existing kernel `audit()` mechanism (ADR-007) unchanged — no second audit mechanism, matching
every prior ADR's precedent in this codebase:

- A conflict-detection invocation that finds **No conflict** is audited as a permit-shaped event
  (the comparison ran, found nothing) — this is itself a meaningful record (proof the check was
  performed at all), not a no-op unworthy of a record.
- A finding of **Boundary overlap**/**Duplicate geometry**/**Near duplicate** is audited with
  enough detail to support a later governance investigation, without itself leaking the §3
  disclosure boundary into the audit log's own payload (`docs/B4_THREAT_MODEL.md` §5's explicit
  repudiation requirement) — i.e., the audit record may reference the other tenant's identifiers
  for investigative purposes even where the *API response* to the ordinary registrant does not
  disclose them, since an audit record is not returned to the requesting caller.
- A governance-role investigation accessing expanded detail under §3 is itself audited as a
  distinct, attributable event — the platform must be able to answer "who looked at this
  cross-tenant conflict, and when," not only "was a conflict found."
- A **Confirmed conflict** determination (a governance decision, §4) is audited as the governance
  action it is, distinct from the automated classifier's own finding.

### 8. Security requirements (restating, not weakening, existing doctrine)

This ADR introduces no new security principle — it applies four already-adopted ones to a
capability that, for the first time in this codebase, requires them simultaneously:

- **Controlled Platform Authority** (`docs/ENGINEERING_RULES.md` rule 9) — §1, above.
- **Least privilege** — the conflict-detection service's cross-tenant read has exactly the access
  described in §1/§3, nothing broader; it is not granted general cross-tenant `SELECT` on
  `parcel_geometries`, only the fixed, bounded-neighbourhood query §1 describes.
- **Read-only comparison** — restated from §1: the cross-tenant portion of this capability never
  writes to another tenant's `ParcelGeometry` or `Parcel` rows.
- **No geometry disclosure, no identity disclosure, no data leakage** (to an ordinary registrant,
  cross-tenant) — restated from §3, the binding default this entire ADR exists to guarantee.
- **No bypass of any constitutional security principle already established** — RLS is not
  relaxed, disabled, or given a second bypass condition beyond the existing, named
  `super_admin`/service-account exceptions (`docs/ENGINEERING_RULES.md` rule 9's own "why," B3/B4
  precedent); the ADR-022 same-tenant mutation authorization model is not weakened, altered, or
  given a new bypass path by anything in this document (ADR-022 §11 already anticipated and
  reserved this exact relationship).

## Alternatives considered and rejected

1. **Folding conflict detection into `SpatialService` as another method alongside
   `submit_geometry`/`get_active_geometry`** — rejected (§5): those two methods only ever read/
   write a single `ParcelGeometry` in a single tenant's scope; conflict detection's cross-tenant,
   multi-geometry read is a categorically different operation that deserves its own explicit
   architectural treatment, not a quiet addition to an existing service's responsibilities.
2. **A new, fourteenth bounded context ("Platform Intelligence") separate from Spatial** —
   rejected (§5): `docs/REBUILD_PLAN.md` already scopes overlap/duplicate detection as part of B4
   itself; inventing a new context boundary purely to host this capability would fragment Spatial
   geometry ownership across two contexts for no architectural benefit this document can identify,
   and was not requested by the governing review.
3. **Governance roles see full cross-tenant detail on any conflict, by default** — rejected (§3):
   this would silently and substantially expand `GOVERNANCE_ROLES`' existing tenant-scoped reach
   without ever having been decided as its own question; TB5 requires this be an explicit,
   narrow, justified decision, not an assumed consequence of an existing role name.
4. **Treating "suspicious pattern" and "confirmed conflict" as automated classifier outputs** —
   rejected (§4/§6): would make this ADR implicitly authorize automated fraud/suspicion
   determinations, which §2/§6 explicitly reserve as a human governance judgment, never a
   classifier's own output.
5. **Deferring the visibility question (§3) entirely to Slice 3's implementation** — rejected:
   TB5 identified this as B4's single highest-severity finding specifically because it is easy to
   get wrong by default (the natural implementation is "just return what the query found"); this
   ADR resolves the *default* and the *boundary* now, leaving only the narrow question of exact
   governance-tier disclosure shape to Slice 3.

## Relationship to ADR-018 (Spatial domain model)

Unaffected. `ParcelGeometry`'s fields, invariants, and append-only lifecycle are not extended,
modified, or reinterpreted by this ADR (§6). Conflict findings are new, separate data that
*reference* a `ParcelGeometry`, never a change to it.

## Relationship to ADR-019 (GeometryPort interface amendment)

Unaffected. `GeometryPort` governs the Registry↔Spatial reference-validation seam; this ADR
governs a Spatial-internal, cross-geometry comparison capability with no Registry-facing
interface at all (§5). No assumption ADR-019 made is touched.

## Relationship to ADR-022 (Spatial authorization model)

**This ADR does not weaken or reopen ADR-022.** ADR-022 §11 explicitly reserved this exact
relationship: "Controlled Platform Authority... remains the doctrine ADR-021 must satisfy when it
designs the genuinely new cross-tenant read." The same-tenant creator-or-governance mutation model
ADR-022 defines for `submit_geometry`/`get_active_geometry` is unchanged; this ADR's cross-tenant
read is a distinct, additional, narrowly-scoped mechanism that runs *alongside* an already-
authorized submission, never a replacement for or relaxation of ADR-022's own tenant-scope-first
ordering.

## Risks (identified, not hidden)

- **The exact tolerance for "near duplicate" vs. "duplicate" vs. "merely overlapping" is a
  geometric/product judgment this ADR does not make** — Slice 3 must propose it, and given TB5's
  severity, that proposal likely warrants its own review before implementation, not merely
  inclusion in a completion report.
- **The exact shape of governance-tier disclosure (§3) is deferred**, per TB5's own residual-risk
  note (`docs/B4_THREAT_MODEL.md` §7) — described as a product/legal question, not purely
  architectural, and may need input beyond this ADR's own reasoning.
- **Performance at realistic volume is unproven** — this ADR defines no index or query design
  (§4), so nothing here has been evaluated against `docs/B4_THREAT_MODEL.md` §5's denial-of-
  service finding; that evaluation is explicitly Slice 3's job, using this ADR's model as its
  constraint.
- **No stakeholder/legal input has been sought on the minimal-disclosure default (§3)** — this ADR
  reasons from the threat model's own architectural requirement, not from an independently
  validated product or legal decision about what a Nigerian land registry may disclose about a
  competing claim.

## Deferred responsibilities

- **B4 Slice 3** — the actual conflict-detection service implementation: the spatial query/index
  design, the tolerance thresholds for §4's categories, the governance-tier disclosure UI/API
  shape within §3's bounds, and live verification of all of the above. Not authorized to begin
  until this ADR is accepted.
- **Real geometric validation** (self-intersection, administrative-boundary containment) —
  remains undesigned and unauthorized, as noted in `docs/B4_DISCOVERY_AND_PLANNING.md`'s ADR-020
  note; orthogonal to this ADR, not required by it.
- **ADR-023** — map tiling / spatial search API, unaffected by and unrelated to this ADR.

## Recommendation

**If this ADR is accepted, B4 Slice 3 — Spatial Conflict Detection is recommended for
authorization next**, with the explicit expectation that Slice 3's implementation: (a) treats
this document's six-category classification (§4) and cross-tenant visibility defaults (§3) as
binding, not advisory; (b) proposes concrete tolerance thresholds and query/index design for
review, given TB5's severity, rather than shipping them silently inside a larger completion
report; (c) implements the audit requirements of §7 in full before any cross-tenant read path is
enabled; and (d) live-verifies the minimal-disclosure default (§3) with an actual cross-tenant
attack simulation — a same-country, non-governance registrant attempting to extract another
tenant's geometry/identity through the conflict-detection response — mirroring the ADR-005/
ADR-022 regression-test discipline already established for every prior authorization ADR in this
codebase.

## Approval Gate

This ADR is **proposed**, not accepted. Per the governing instruction, no B4 Slice 3
implementation — including any overlap detection, duplicate detection, fraud detection, conflict
scoring, AI analysis, spatial search, or risk engine — begins until this document is reviewed and
explicitly accepted.
