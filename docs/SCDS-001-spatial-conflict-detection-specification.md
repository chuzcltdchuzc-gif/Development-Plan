# SCDS-001 — Spatial Conflict Detection Specification

**Type:** Engineering specification, **not an ADR.** This document sits beneath
`docs/adr/ADR-021-spatial-conflict-detection-and-controlled-cross-tenant-intelligence.md` and
converts its architectural intent into implementation guidance — it does not itself decide
architecture, and it contains **no implementation code, no working query, no concrete index DDL**.
Where this document proposes a mechanism (e.g., a named session variable), it is a specification
of the *shape* that mechanism must take, for Slice 3's implementation and its own review to
target — not a claim that any of it has been built.

**Status:** Draft, pending review alongside ADR-021 (see
`docs/B4_SLICE3_PREIMPLEMENTATION_REVIEW.md`).

**Date:** 2026-07-24

**Governed by:** ADR-021 (this document specifies, never overrides, its eight decision sections),
`docs/B4_THREAT_MODEL.md` §5 (TB5), `docs/ENGINEERING_RULES.md` rule 9 (Controlled Platform
Authority), `docs/adr/ADR-022-spatial-authorization-model.md` (the same-tenant model this
specification's cross-tenant mechanism sits alongside, never replaces).

---

## 1. Conflict taxonomy

Ten named conflict-adjacent conditions. Each is a **detection trigger + business meaning**, never
an accusation of intent (ADR-021 §2/§6) — intent is a governance judgment, not a taxonomy label.

| # | Name | Definition | Detection trigger | Business meaning | Expected response |
|---|---|---|---|---|---|
| 1 | **Duplicate Geometry** | A submitted geometry is materially identical to another tenant's existing `ACTIVE` geometry. | Geometric equality within a to-be-defined tolerance (§3, not specified here). | Two tenants claim the identical boundary — the single most serious finding, since both cannot be a correct, independent registration of the same physical land. | `ADR-021 §4` "Duplicate geometry" classification; minimal cross-tenant signal to the submitter. |
| 2 | **Boundary Overlap** | Two geometries' areas genuinely intersect, without being identical. | Non-zero intersection area/ratio above a to-be-defined minimum (avoids flagging negligible edge-rounding noise as a conflict). | Two claims cover some of the same physical land — may be legitimate (adjoining surveys with minor edge error) or may indicate a real dispute. | `ADR-021 §4` "Boundary overlap" classification. |
| 3 | **Containment** | One geometry's area is wholly contained within another's. | Intersection area equals the smaller geometry's full area. | A named sub-case of Boundary Overlap worth distinguishing for governance investigation — e.g., a small parcel wholly inside a larger claimed estate is a qualitatively different situation from two similarly-sized parcels partially overlapping. | Reported as a **Boundary Overlap** (ADR-021 §4 does not define a separate top-level category for this), with `containment` recorded as a sub-type attribute on the finding record for governance investigation — not a new disclosure tier. |
| 4 | **Adjacent Boundaries** | Geometries share a border or are within a small buffer distance but do not overlap. | Zero intersection, distance below a to-be-defined proximity threshold. | Ordinary, expected outcome for correctly-surveyed neighbouring land. Not a conflict. | `ADR-021 §4` "No conflict" — must report as cleanly as a geometry with no nearby claims at all, per ADR-021 §2 item 4's fail-safe requirement. |
| 5 | **Near Duplicate** | Materially similar to another tenant's geometry but not identical — closer than Adjacent, not clearly the same claim as Duplicate. | High but non-total geometric similarity within a to-be-defined band between the Duplicate and Boundary-Overlap thresholds. | Ambiguous — could be a data-entry/survey-precision difference describing the *same* land, or two distinct, genuinely adjacent claims that happen to be similar in size/shape. Requires governance judgment, not an automated resolution. | `ADR-021 §4` "Near duplicate" classification. |
| 6 | **Topology Errors** | The submitted geometry, considered alone, is structurally self-inconsistent in a way ADR-018/Slice 2's structural validator does not check (self-intersection, non-simple polygon). | A future real geometric validator (ADR-018's deferred "self-intersection" item, orthogonal to ADR-021 — see `docs/B4_DISCOVERY_AND_PLANNING.md`'s ADR-020 note). | Not a cross-tenant conflict at all — a single-geometry structural defect. | Rejected at submission time (`400`), before conflict detection ever runs — conflict detection only ever compares *validated* geometries against each other. Named here only to state explicitly that Topology Errors are **not** part of this taxonomy's cross-tenant comparison surface. |
| 7 | **Invalid Geometry** | Fails ADR-018/Slice 2's existing structural validator (ring closure, point count, coordinate bounds, winding order, SRID). | Already implemented (`app/contexts/spatial/domain/geometry_validation.py`). | Not a conflict-detection concern at all. | Already rejected at submission time (`400`), unchanged by this specification. Named here only for completeness of the taxonomy, not as new scope. |
| 8 | **Survey Discrepancy** | A conflict finding where the two competing geometries' metadata (survey date, surveyor licence tier, evidence confidence — see §3 Risk Scoring) suggests one submission is materially less reliable than the other. | Not a geometric trigger — a metadata-comparison trigger, evaluated only once a geometric finding (Duplicate/Overlap/Near Duplicate) already exists. | Informs a governance investigator's resolution of a **Confirmed Conflict** (ADR-021 §4); never itself a top-level classification result surfaced automatically. | Recorded as an attribute on an existing finding for governance review — not a new classification category, not a new disclosure tier. |
| 9 | **Reference Reuse** | A `geometry_reference` (Registry's `parcels.geometry_reference`) is set to point at a `ParcelGeometry` that is `SUPERSEDED` rather than `ACTIVE`, or at a geometry that itself belongs to a different tenant than the parcel referencing it. | Already rejected today by `RealGeometryAdapter.reference_is_valid` (B4 Slice 2) — status and tenant/parcel identity are already checked. | Not a new conflict — named here to confirm this taxonomy does not need to invent a rule Slice 2 already enforces. | No new behavior. Existing `400` rejection, unchanged. |
| 10 | **Geometry Identity Collision** | Two distinct `ParcelGeometry` rows are ever assigned the same `geometry_id`. | Structurally impossible today — `geometry_id` is a server-generated UUID primary key (ADR-018), never caller-supplied. | Not a real risk under the current design. | Named here only to explicitly rule it out as a taxonomy member requiring detection logic — the primary key constraint is the entire mitigation, already in place since migration `0010`. |
| 11 | **Future AI Suspicion** | A classification a future analytics/ML capability (not built, not designed) might produce — a pattern across many submissions rather than a single geometric comparison. | Undefined — deliberately, per ADR-021 §4's "Suspicious pattern" placeholder category. | Explicitly out of scope for this specification and for B4 Slice 3. Any future capability that wants to populate this category does so through the same finding-record structure §4/§7 define, never a new data model. | Governance-only visibility (ADR-021 §3/§4) if and when such a capability exists; nothing to implement now. |

**Binding note:** items 6, 7, 9, and 10 are included for completeness of the taxonomy, not as new
Slice 3 scope — each already has an existing, adequate answer elsewhere in this codebase, and
this specification does not reopen or duplicate that handling.

---

## 2. Conflict severity

Four levels, applied only to conflict-adjacent taxonomy items (1, 2, 3, 5, 8, 11 above) — never to
items 4, 6, 7, 9, 10, which are not conflicts.

| Level | Name | Applies to | Escalation rule |
|---|---|---|---|
| **1** | Informational | Adjacent Boundaries reported for completeness in a governance-facing view (never surfaced as a "conflict" to an ordinary registrant — this is not a conflict per §1). | None — recorded, never escalated. |
| **2** | Warning | Near Duplicate; Boundary Overlap below a to-be-defined area-ratio threshold. | Visible to governance on request; does not itself notify governance proactively. |
| **3** | High Risk | Boundary Overlap above the Level-2 threshold; Containment. | Governance is notified (not merely queryable) — the specific notification mechanism is Slice 3's implementation job, not specified here. |
| **4** | Critical | Duplicate Geometry. | Governance is notified; per ADR-021 §3, the submitting registrant receives only the minimal signal regardless of severity level — severity affects *governance* urgency, never ordinary-registrant disclosure depth (disclosure depth is governed exclusively by ADR-021 §3/§4, not by this severity scale). |

**Escalation is one-directional and purely additive to visibility for governance** — no severity
level ever changes what an ordinary registrant may see (ADR-021 §3's minimal-disclosure default is
constant across all four levels). Severity is a triage aid for governance investigators, not a
second disclosure-control axis.

---

## 3. Risk scoring model

**Specification only — no formula, weighting, or implementation is decided here.** This section
names the inputs a future risk score may consider and the constraints any such score must satisfy;
it does not commit to a scoring algorithm, and Slice 3 does not need to implement scoring at all
to satisfy ADR-021 (scoring is explicitly listed among ADR-021 §6's "platform intelligence
services," most of which remain unbuilt).

**Candidate inputs** (named for future extensibility, not all required for Slice 3):

- Percentage overlap (geometric, computed by whatever spatial query Slice 3 designs).
- Survey age (how long ago the competing geometry was submitted/superseded).
- Geometry confidence (a future concept — not defined by ADR-018, which validates structure only,
  never a confidence score; if this ever becomes real, it requires its own ADR extending
  ADR-018, not an assumption smuggled in through this specification).
- Surveyor quality score (a future Trust Engine (B7) concept — this specification does not define
  it; if it exists, it is consumed as a pre-computed signal, per ADR-021 §6's intelligence-
  boundary doctrine, never computed by Spatial itself).
- Historical disputes (count/recency of prior **Confirmed Conflict** determinations involving
  either tenant — a future signal, not built).
- Evidence confidence (a future Evidence bounded-context concept, `docs/REBUILD_PLAN.md`'s B5 —
  out of this specification's scope entirely).
- Government data (a future external data-source integration — out of scope, named only for
  extensibility).
- AI confidence (a future ML capability's own output — consumed, never produced, by this
  specification's model).
- Registry history (`Parcel.created_at`, prior mutation count — already available via existing
  Registry reads, but not consumed by anything this specification defines).

**Binding constraints on any future risk-scoring implementation** (these ARE specified, even
though the algorithm is not):

1. A risk score, if it ever exists, is **additional metadata on a conflict finding** (§7), never a
   replacement for the four-level severity scale (§2) or the six-category classification
   (ADR-021 §4).
2. A risk score **never determines disclosure** to an ordinary registrant — ADR-021 §3's minimal-
   disclosure default is not parameterized by score, ever.
3. A risk score computation, if it ever needs cross-tenant data beyond what §1's fixed
   neighbourhood read already retrieves, requires its own Controlled Platform Authority exception
   and its own ADR — it does not inherit ADR-021's single exception (ADR-021 §1's "no second
   Controlled Platform Authority exception may be introduced for this capability" applies with
   equal force to a future scoring capability).
4. Fail-safe scoring (`docs/ENGINEERING_RULES.md` rule 4) applies without exception: missing or
   low-confidence input data must never produce a numerically "safe-looking" score — it must
   produce an explicit "insufficient data" result, matching the exact discipline the Trust Engine
   (B7) is already required to follow.

**This section is intentionally the least specified in this document** — it names the extension
points without committing this platform to build any of them as part of B4 Slice 3.

---

## 4. Disclosure matrix

Extends ADR-021 §3 (which already fixes the *ordinary-registrant* default) with the fuller set of
participant tiers the review directive named. **Minimum Necessary Disclosure is the default for
every tier below citizen and every non-governance registrant tier** — no tier not explicitly
listed as receiving more sees more.

| Participant | May see, on a conflict finding | Rationale |
|---|---|---|
| **Citizen** (a public/unauthenticated viewer, if any future public-facing view exists — none does today, `docs/REBUILD_PLAN.md` F2 not yet built) | Nothing. No conflict-related information is ever surfaced to an unauthenticated or public context. | No public API surface exists yet for parcel data at all; this specification does not create one. |
| **Surveyor** (`licensed_surveyor`/`surveyor_partner`, ADR-022's `PARCEL_REGISTRANT_ROLES` minus governance) | Exactly ADR-021 §3's ordinary-registrant default — a minimal boolean/flag signal, own-tenant only. | Not a governance role under `GOVERNANCE_ROLES` (ADR-015/ADR-022) — no expanded reach. |
| **Survey Firm** (a tenant, collectively — no distinct role beyond its members' individual roles today) | Whatever its individual members are entitled to see under their own role, above/below — a tenant has no reach beyond the union of its members' individual authorization, unchanged from every other authorization decision in this codebase. | This platform does not model tenant-level visibility separate from member-role visibility anywhere else (ADR-010/ADR-022); this specification does not introduce a first exception. |
| **Enterprise** (a distinguished tenant tier — no such tier exists in this platform today, `docs/REBUILD_PLAN.md` has no "Enterprise" bounded context or role) | Not applicable — named in the review directive as a forward-looking placeholder; this specification records that no such tier currently exists and defers its definition entirely to whatever future ADR introduces it. | Avoids inventing a role/tier this platform has no other use for. |
| **Government** (a future external-integration consumer, `docs/REBUILD_PLAN.md` B11/B12-adjacent — not built) | Not applicable today. If a future government-integration capability is built, its read access to conflict findings requires its own Controlled Platform Authority justification and its own ADR — it does not inherit any reach from this specification. | Consistent with ADR-021 §1's "no second exception inherits this one" doctrine. |
| **Platform Intelligence** (the internal conflict-detection service itself, and any future sibling service under the same layer — see `docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md`) | The full fixed-neighbourhood read described in ADR-021 §1 — this is the one component with cross-tenant read access at all. | This is the exception ADR-021 §1 names, not an additional one. |
| **Super Admin** | Full detail, cross-tenant, unchanged from every existing `super_admin` reach in this platform (RLS bypass, ADR-022 §3's cross-tenant governance override). | No new reach granted by this specification — `super_admin`'s existing, already-audited reach already covers this case. |
| **Controlled Platform Authority** (not a participant — the doctrine itself, listed here per the review directive's own table shape) | N/A — this row documents that the *doctrine*, not a person or role, is what authorizes the Platform Intelligence row above. Restated for completeness, not a new participant tier. | Avoids the reader mistaking "Controlled Platform Authority" for an omitted role. |

**Default principle, restated:** Minimum Necessary Disclosure. Never expose another tenant's
geometry, identity, or Registry-owned metadata to any tier above except **Platform Intelligence**
(internally) and **Super Admin** (already-existing reach) — **Governance**, per ADR-021 §3, is a
narrower, conflict-scoped exception, not a blanket cross-tenant grant, and is not listed as a
separate row here since ADR-021 §3 already fully specifies its exact, bounded reach.

---

## 5. Controlled Platform Authority — refinement

ADR-021 §1 establishes that exactly one component may perform the cross-tenant read, and that it
must be fixed at the call site, read-only, narrow, and audited. **This section specifies the
mechanism's required shape — still not its implementation:**

- **Who may invoke it:** the conflict-detection service, and only from the one call site ADR-021
  §1 names (as a side effect of an already-authorized `submit_geometry`). No API endpoint, admin
  action, or scheduled job may invoke it directly.
- **When:** synchronously, within the same request/transaction as the geometry submission that
  triggered it — never asynchronously, never batched, never on a schedule (a scheduled or batch
  cross-tenant scan would not be "fixed at the call site" in ADR-021 §1's sense, since its scope
  would no longer be tied to one specific, already-authorized submission).
- **Why:** to answer, for a just-submitted geometry, whether it conflicts with any other tenant's
  existing geometry within a bounded spatial neighbourhood — no other justification is
  authorized under this specification.
- **Mechanism (specified, not implemented):** the cross-tenant read must be achieved through a
  named, fixed, request-scoped elevated context — structurally analogous to the existing
  `app.is_super_admin` session-level RLS exception (migration `0001` onward) and the
  `context_hydration` service-account's own fixed lookup — **never** a blanket relaxation of
  `parcel_geometries`' existing RLS policy (migration `0010`), and never a second, independent
  bypass condition added to that policy for a different reason. Whether this is implemented as a
  distinct session variable (e.g., an `app.platform_intelligence`-shaped flag, set only for the
  single, fixed query the conflict-detection service issues) or some other RLS-compatible
  mechanism is Slice 3's implementation decision — but it **must** satisfy: scoped to exactly the
  one fixed query in ADR-021 §1, never settable by any caller-supplied input, and torn down
  before the surrounding request continues past that one query (no session-wide elevation that
  outlives the single lookup, mirroring `context_hydration`'s own precedent of an immediately-
  rolled-back elevation).
- **Approval requirements:** this mechanism's exact final shape (the specific session-variable
  name, or whichever RLS-compatible approach Slice 3 proposes) should be reviewed before
  implementation, given TB5's severity — the same discipline ADR-021's own Recommendation section
  already calls for regarding tolerance thresholds and query design.
- **Logging:** every invocation is audited per §7/ADR-021 §7 — this is not optional or
  batchable into a summary; each individual cross-tenant read produces its own audit entry.
- **Future AI usage / Future Fraud Engine / Future Compliance Engine / Future Government
  Analytics:** none of these may reuse this same Controlled Platform Authority exception. Each,
  if ever built, requires its own named exception and its own ADR, per ADR-021 §1's explicit
  "no second exception inherits this one" rule — restated here because it is the single most
  important constraint standing between "one narrow, audited exception" and "a general-purpose
  cross-tenant bypass with several unaudited callers," the exact failure mode Controlled Platform
  Authority (`docs/ENGINEERING_RULES.md` rule 9) exists to prevent.

**Cross-reference:** `docs/B4_THREAT_MODEL.md` §5 (TB5) is the binding source for every
requirement in this section; `docs/adr/ADR-021-...md` §1/§8 is the architectural decision this
section specifies against.

---

## 6. Performance specification

**Specification of expectations, not of implementation.** No index type, query plan, or caching
technology is decided here.

- **Expected throughput:** conflict detection runs once per geometry submission — its throughput
  requirement is therefore identical to the existing `submit_geometry` write path's own
  throughput requirement (unspecified elsewhere in this codebase beyond "acceptable for the
  registration workflow it serves"); this specification does not set a new, independent
  throughput target.
- **Expected latency:** the cross-tenant neighbourhood read (§5) must complete within the same
  request that already performs validation, authorization, and persistence (ADR-022's ordering) —
  it must not turn a synchronous registration-style operation into one with materially different
  latency characteristics than Registry's own mutation endpoints exhibit today. No numeric target
  is set here; Slice 3 must propose one, informed by realistic registration volume.
- **Spatial indexing assumptions:** a bounded-neighbourhood query (ADR-021 §1) is assumed to
  require a spatial index (e.g., GiST, unspecified further) rather than a full-table scan — this
  specification assumes such an index is necessary, not that any particular index type is
  correct; `docs/B4_THREAT_MODEL.md` §5's denial-of-service finding is the reason this assumption
  exists at all.
- **Future scaling assumptions:** this specification assumes single-database-instance operation,
  matching this platform's current architecture (`docs/adr/ADR-003-database-choice.md`) —
  distributed/sharded operation is explicitly out of scope and not assumed.
- **Caching assumptions:** none. This specification does not assume any conflict-detection result
  is cached, memoized, or reused across requests — every submission re-evaluates fresh, matching
  this platform's existing "no caching of authorization/validation decisions" discipline
  (ADR-011's "re-resolved fresh on every request, no caching" precedent, applied here by analogy).
- **Search radius assumptions:** "bounded spatial neighbourhood" (ADR-021 §1) implies some
  distance or bounding-box parameter exists — this specification does not set its value; Slice 3
  must propose one, informed by realistic parcel sizes (a purely local, small-area radius for an
  individual residential plot vs. a much larger one for an estate-scale parcel may need different
  handling, itself a question for Slice 3's own review, not resolved here).
- **Future distributed execution assumptions:** none — explicitly out of scope, consistent with
  the scaling assumption above.

---

## 7. Audit specification

Extends ADR-021 §7 with the concrete list of audit events Slice 3 must produce. **Event names
below are illustrative of the required shape (verb-noun, matching this codebase's existing
`spatial.parcel_geometry.*` convention) — Slice 3 finalizes exact naming at implementation time,
not this specification.**

| Event (illustrative name) | Fired when | Must include (never leaks §3/ADR-021 §3 boundary into the *response*, but the audit payload itself may hold more, per ADR-021 §7) |
|---|---|---|
| `spatial.conflict_check.performed` | Every conflict-detection invocation, regardless of outcome (including **No conflict**). | Submitting `tenant_id`, submitted `geometry_id`, classification result (ADR-021 §4), count of other-tenant geometries considered (not their identities, unless a conflict was found). |
| `spatial.conflict.detected` | A **Boundary Overlap**/**Duplicate Geometry**/**Near Duplicate** classification is produced. | As above, plus the *other* tenant's `tenant_id`/`geometry_id`/`parcel_id` (investigative detail, permitted in an audit payload per ADR-021 §7 even though the API response to the submitter does not disclose it), severity level (§2). |
| `spatial.conflict.governance_reviewed` | A governance-role principal accesses expanded detail on a conflict finding (ADR-021 §3's governance exception). | Reviewing principal's `principal_id`, the conflict finding's identifier, `delegated_roles` (mirroring every other governance-action audit payload in this codebase, e.g. `registry.parcel.updated`'s shape). |
| `spatial.conflict.confirmed` | A governance role formally determines a finding is a **Confirmed Conflict** (ADR-021 §4). | Reviewing principal's `principal_id`, the conflict finding's identifier, both tenants' identifiers. |
| `spatial.conflict.cross_tenant_read_denied` (defensive event — should never fire under correct implementation) | Any attempt to invoke the cross-tenant read mechanism (§5) from a call site other than the one ADR-021 §1 authorizes. | Whatever context is available at the point of denial — this event's existence is itself a verification aid Slice 3's live testing should exercise (attempt an unauthorized invocation, confirm it is both blocked and audited), not a normal-operation event. |

**Binding requirement, restated from ADR-021 §7:** no code path may perform the cross-tenant read
(§5) without producing at least `spatial.conflict_check.performed` (or its finalized-name
equivalent) — this is the audit-completeness bar Slice 3's own live verification must
specifically test for, the same way Slice 2's live verification specifically tested that every
mutation attempt (permit or deny) produced a corresponding audit entry.

---

## 8. Future AI extension

**Extension points only — no capability named here is designed, scheduled, or authorized by this
specification.** Each, if ever pursued, requires its own ADR extending ADR-021, per ADR-021 §6's
intelligence-boundary doctrine (these are platform intelligence services, never Registry or
Spatial domain entities) and per `docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md`'s layer diagram:

- **Fraud Detection** — consumes conflict findings (§7's audit records and/or a future dedicated
  finding-read interface) as input signal; never itself performs the cross-tenant geometry read
  (§5) — it reads *findings*, already-filtered by this specification's disclosure rules, never raw
  cross-tenant geometry.
- **Risk Engine** — consumes §3's candidate inputs (or a subset) to produce a score; per §3's
  binding constraints, never determines ordinary-registrant disclosure, never invents a second
  Controlled Platform Authority exception.
- **AI Analysis** — any future ML-based pattern detection populating the "Suspicious pattern"
  taxonomy slot (§1 item 11) — governance-only visibility, per ADR-021 §4, unconditionally.
- **Machine Learning** — as a technique, not a capability in itself; any ML model this platform
  ever trains on conflict-finding data consumes the same finding-record structure this
  specification defines, never raw `parcel_geometries` rows directly (ADR-021 §6/TB6).
- **Satellite Validation** — a future external-data-source input to Topology Errors/Invalid
  Geometry validation (§1 items 6/7) or to Risk Scoring (§3) — named as a placeholder extension
  point only; no integration is designed.
- **Government Intelligence** — as in §4's disclosure matrix, a future external consumer with no
  defined access today; any future integration requires its own ADR and its own Controlled
  Platform Authority justification, inheriting nothing from this specification.

**None of these extension points require any change to Registry or Spatial's existing domain
models** (ADR-021 §6) — each consumes the conflict-finding data structure this specification
establishes, through whatever narrow read interface a future ADR defines, never by reaching into
`parcel_geometries` or `parcels` directly.
