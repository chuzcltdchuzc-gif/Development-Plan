# ADR-022 — Spatial Authorization Model

**Status:** Proposed — drafted under explicit authorization to formally record Spatial's
authorization model before B4 Slice 2 begins. Not yet reviewed or accepted. **No code is
written or modified under this document.** Per the governing instruction, B4 Slice 2 does not
begin — and no Spatial service is touched — until this ADR is itself reviewed and explicitly
accepted, separate from B4 Slice 1's own acceptance.

**Date:** 2026-07-23

**Governed by:** `docs/adr/ADR-015-registry-mutation-authorization-model.md` (the model this ADR
is required to be consistent with, not reinvent), `docs/B4_THREAT_MODEL.md` (TB4/TB5, and the
Controlled Platform Authority doctrine it produced), `docs/ENGINEERING_RULES.md` rule 9
(Controlled Platform Authority), `docs/adr/ADR-018-spatial-domain-model.md` (the `ParcelGeometry`
domain model this ADR governs access to, not redefines), `docs/adr/ADR-019-geometry-port-interface-amendment.md`
(unaffected by this ADR — see §"Relationship to ADR-019"). Extends
`docs/adr/ADR-011-delegated-administration.md` (delegation, reused unchanged) and
`docs/adr/ADR-013-parcel-aggregate-registry-domain-model.md` (`Parcel.created_by`/`status`, read
but never modified). Does not modify any of them.

## Architectural Context — why this ADR is required now

B4 Slice 1 (`app/contexts/spatial/`) shipped with a deliberately coarse authorization boundary,
documented honestly in its own completion report and in `docs/B4_VERIFICATION_CHECKLIST.md`: the
same `PARCEL_REGISTRANT_ROLES` role gate Registry's endpoints use, plus a tenant-scope
`_in_scope` check — but no check on whether the caller is specifically authorized for the
*particular* parcel they are submitting geometry against. That was an acceptable, explicitly
flagged scope boundary for a slice whose entire purpose was establishing the domain model and
bounded-context shape (ADR-018), not shipping a production-ready mutation surface. It is not
acceptable to carry into Slice 2, which introduces real geometry validation and — per
`docs/B4_DISCOVERY_AND_PLANNING.md`'s own roadmap — precedes correction/supersession becoming a
routine, frequently-exercised operation rather than a foundation-proving one.

The shape of the gap is structurally identical to the historical defect ADR-005 documented and
ADR-015 closed for Registry: *any* principal holding a coarse, role-based grant could mutate a
specific resource regardless of whether they had any actual relationship to it. This platform has
already established, twice (ADR-013→ADR-015 for Registry, and now here), that authorization
models for a domain's mutation surface are architectural decisions requiring their own ADR — not
an implementation detail folded into a feature slice. This document is that decision for Spatial,
produced *before* Slice 2 rather than discovered as a defect after.

## Decision

### 1. Spatial authority model — one operation, uniformly authorized

Slice 1's `submit_geometry` already handles both "no `ACTIVE` geometry exists yet" (creation) and
"an `ACTIVE` geometry exists and is being replaced" (correction/supersession) as the *same code
path* — there is no separate "create" vs. "replace" command, and this ADR does not introduce one.
**Creation and replacement/supersession therefore receive identical authorization treatment by
construction, not two independently-designed rules that happen to agree.** "Validation,"
"approval," and "rejection" are not separately-authorized operations either:

- **Validation** is a mechanical consequence of an authorized submission attempt (structural
  validation today, per ADR-018; real geometric validation from ADR-020 onward) — it has no
  authority model of its own because it is never invoked except as part of an already-authorized
  `submit_geometry` call.
- **Rejection**, in this model, means *"the submission failed validation"* (a `400`, exactly
  Registry's own `_bad_request` pattern) — **not** *"a governance role reviewed and declined a
  pending submission."* **No approval workflow exists.** ADR-018 already decided
  validate-then-store with no `PENDING` status (§"Validation gates persistence"), a frozen,
  accepted decision this ADR does not reopen. If a genuine governance-review-gate workflow is
  ever needed, that is a change to `ParcelGeometry`'s persistence lifecycle — its own ADR
  amending ADR-018, not something an authorization-only ADR introduces by implication.
- **Archival**, as a status distinct from `SUPERSEDED`, does not exist on `ParcelGeometry`
  (ADR-018 defines only `ACTIVE`/`SUPERSEDED`). "Archived parcel behaviour" in this document
  (§8) refers to the effect of the *Parcel's* `ARCHIVED` status (ADR-013) on Spatial's
  authorization decision — not a new Spatial-specific archival concept.

**Every mutating operation Spatial exposes today (`submit_geometry`, covering both creation and
replacement) requires: tenant scope (§5) evaluated first, then creator-or-governance authority
(§§2–3) — see §6 for the complete matrix.**

### 2. Creator authority

**Creator authority is the *parcel's* creator, reusing `Parcel.created_by` — not a second,
Spatial-local notion of "who submitted the last geometry."** A parcel's registrant retains
authority over the geometry associated with their own parcel for the same reason ADR-015 grants
them mutation authority over the parcel's other fields: `created_by` is the single, already-
established fact of resource ownership in this platform, and Spatial does not need — and must
not invent — a second, competing definition of "owner" for the same underlying resource.

- **When creator authority exists:** whenever `parcel.created_by == ctx.principal_id`, for the
  parcel the geometry submission targets. Evaluated fresh on every request (no caching, matching
  every other authorization check in this codebase).
- **Permanence:** creator authority is permanent and non-revocable by any action short of the
  parcel itself ceasing to exist (which this platform never does — parcels are archived, not
  deleted) — identical to ADR-015's treatment of `Parcel.created_by`.
- **Revocability:** not revocable. `created_by` is not a role or a grant; it is a historical fact
  about who registered the resource. There is no "transfer creator authority" command in this or
  any prior ADR.
- **Survives delegation changes:** yes, trivially — creator authority does not depend on
  delegation state at all. A delegate never inherits another principal's creator status on a
  resource they did not create (ADR-015's identical rule, restated: "ownership is a fact about who
  registered THIS resource, never delegable as a role is").
- **Survives tenant lifecycle changes:** the question is moot in the failure case — if the
  creator's tenant is suspended, `context_hydration`'s existing fail-closed behavior (ADR-010)
  denies *all* authenticated access for every member of that tenant, creator included; this is
  not a Spatial-specific rule, it is the platform's existing tenant-suspension mechanism applying
  uniformly, unchanged by this ADR.

### 3. Governance authority

**Reuses `GOVERNANCE_ROLES` (`super_admin`, `surveyor_general`, `compliance_officer`) exactly as
ADR-015 defines it — no new governance role, no Spatial-specific governance tier.** A governance-
role holder (direct or delegated, per §4) may submit or replace geometry for *any* parcel within
their tenant scope, regardless of who created it — the identical override shape ADR-015 grants
for Registry mutations.

- **Tenant-wide authority:** yes, for all three roles, matching their existing reach elsewhere in
  this codebase.
- **Cross-tenant authority:** `super_admin` only, via the same `_in_scope` bypass every other
  cross-tenant check in this platform uses (§5) — `surveyor_general`/`compliance_officer` remain
  tenant-scoped, unchanged from their existing reach.
- **Override capability:** covered above — governance override is the *entire* content of
  "governance authority" here; there is no additional, separate override mechanism.
- **Emergency authority:** **no separate concept is introduced.** `super_admin`'s existing
  cross-tenant reach already covers operator-level intervention; inventing a distinct "emergency
  authority" tier would be exactly the kind of parallel model this ADR is instructed not to build.

### 4. Delegated authority

**Reuses ADR-011 verbatim — no new delegation mechanism, no Spatial-specific delegation rule.**
`ExecutionContext.roles` is already the union of direct and currently-effective delegated roles
(ADR-011); the creator-or-governance check (§§2–3) reads that union exactly as
`ParcelService._can_mutate` already does for Registry, so a delegate holding a delegated
governance role gets exactly that role's reach, capped by `highest_rank()` at delegation-creation
time, with no Spatial-specific code needed to enforce the cap.

- **Delegation eligibility / scope / limits / hierarchy ceiling:** unchanged, ADR-011.
- **Expiry / revocation / suspension (delegate or delegator) / tenant suspension:** unchanged,
  ADR-011's fail-closed re-resolution on every request — a delegation that stops being effective
  simply stops appearing in `ctx.roles`, with the identical immediate effect (no caching, no
  grace period) ADR-011 already guarantees and B3 already live-verified for Registry mutations.
  This ADR asserts, and Slice 2's tests must confirm, that the identical guarantee holds for
  Spatial mutations — not a new guarantee, a re-verification of an existing one in a new context.

### 5. Tenant authority

**Tenant scope is evaluated before creator or governance authority, using the identical
`_in_scope(ctx, resource_tenant_id)` pattern already implemented in Slice 1's `SpatialService`.**
A cross-tenant caller (not `super_admin`) receives `404` and never learns whether they would have
passed the creator-or-governance check — the same information-hiding property ADR-015 established
for Registry ("a cross-tenant caller never learns whether they would have passed it").

- **RLS interaction:** `parcel_geometries`' own `FORCE`d RLS (migration `0010`) is the first,
  database-level layer; `_in_scope` is the second, application-level layer exercised by this
  slice's own test suite (RLS itself cannot be exercised against an in-memory fake, per B4 Slice
  1's completion report) — the identical two-independent-layers pattern every tenant-scoped table
  in this codebase has used since migration `0001`.
- **Authorization ordering (binding):** tenant scope → creator-or-governance → (implicitly)
  archived-parcel check (§8, itself evaluated as part of loading the parcel's current state).
  Never the reverse — a caller must first be proven in-scope before any resource-specific
  authority question is even asked.

### 6. Spatial mutation matrix

| Operation | Creator (of the parcel) | Governance (direct or delegated) | Ordinary registrant, not creator | Cross-tenant (non-`super_admin`) |
|---|---|---|---|---|
| Submit geometry — creation (no `ACTIVE` geometry exists) | permit | permit | **deny (403)** | 404 |
| Submit geometry — replacement/supersession (an `ACTIVE` geometry exists) | permit | permit | **deny (403)** | 404 |
| Read active geometry (`GET`) | permit | permit | permit (tenant-wide read, unchanged from Slice 1 — reading is not a mutation) | 404 |
| Validation (structural today, real from ADR-020) | n/a — a consequence of an authorized submission, not a separately-invoked operation | | | |
| Approval / rejection as a distinct workflow | **not implemented; no such operation exists** (§1) | | | |
| Archival as a distinct Spatial status | **not implemented; no such status exists** (§1; see §8 for the Parcel-archival interaction) | | | |

Delegation behaviour for every row above: identical to the governance column, since a delegate
exercising a currently-effective governance role is indistinguishable, at the authorization-check
level, from a direct holder of that role (§4). Audit requirements for every row: §9. Failure
behaviour: `403` for an in-scope, non-creator/non-governance caller; `404` for out-of-scope or
non-existent; `409` for an archived parcel (§8); `400` for a submission that fails validation.

### 7. Geometry lifecycle

```
ACTIVE  --(a new authorized submission for the same parcel)-->  SUPERSEDED (immutable, terminal)
  |
  +--(the parcel this geometry belongs to becomes ARCHIVED)--> no further transition possible (§8)
```

There is no standalone "supersede" or "archive" command exposed to any caller. A transition from
`ACTIVE` to `SUPERSEDED` happens *only* as an automatic side effect of a new, independently-
authorized `submit_geometry` call succeeding (exactly as Slice 1 already implements it) — never
as its own directly-invokable operation, and never reversible (ADR-018's "only `ACTIVE`
geometries are valid... `SUPERSEDED` rows are retained... not eligible input to any future
overlap query," unchanged).

### 8. Archived parcel behaviour

**Once the underlying `Parcel`'s `status` is `ARCHIVED` (ADR-013), no further geometry mutation
is permitted for that parcel — creator, governance, and `super_admin` alike, no exception, no
override path.** This is a deliberate mirror of ADR-015's identical rule for Registry's own
mutation commands ("archival is meant to be a genuine terminal state... no override path...
creator, governance role, and `super_admin` alike, no exception"), extended here for consistency
rather than left as an unaddressed gap. `GET` (reading the active geometry) remains permitted on
an archived parcel — reading is not a mutation, matching Registry's identical carve-out.

**Consequence for Slice 2's implementation (decided here, not built here):** `ParcelExistencePort`
(currently `get_tenant_id(parcel_id) -> str | None`) must be extended to also return the parcel's
`created_by` and `status` — e.g., a richer `get_parcel_authority(parcel_id) ->
ParcelAuthorityInfo | None` returning `(tenant_id, created_by, status)` — so `SpatialService` can
evaluate §§2, 3, 5, and 8 without a second round-trip or a second port. This is a design
consequence this ADR requires Slice 2 to implement; per the stop condition governing this
document, no such change is made now.

### 9. Audit requirements

**No second audit mechanism — the existing kernel `audit()` function (ADR-007), unchanged.**
Every mutation attempt, permitted or denied, is audited:

- `spatial.parcel_geometry.created` — already implemented (Slice 1); payload gains
  `effective_authority` (`"creator"` or `"governance:<role[,role...]>"`, identical shape to
  Registry's ADR-015 payload) and `delegated_roles` (from `ctx.attributes["delegated_roles"]`,
  the same ADR-015/hydration mechanism, unchanged) once Slice 2 implements the creator-or-
  governance check this ADR specifies.
- `spatial.parcel_geometry.mutation_denied` — new action name (mirroring
  `registry.parcel.mutation_denied` exactly), fired when an in-scope caller fails the creator-or-
  governance check, with a `reason` field (`"not_creator_and_not_governance"`, matching Registry's
  literal reason string for consistency) and the same `tenant_id`/`delegated_roles` fields.
- Validation failures (`400`) and archived-parcel denials (`409`) are **not** separately audited
  as distinct events beyond whatever the existing request/response cycle already logs — matching
  Registry's own precedent (`_bad_request`/`_conflict` responses are not independently audited
  events; only permit/deny *authorization* decisions are).
- Cross-tenant `404`s are **not** separately audited — matching Registry's identical precedent
  (existence itself is not revealed cross-tenant, and auditing a 404 would itself leak that a
  request was made against a specific `parcel_id`, without adding investigative value beyond what
  the existing per-request audit context already would, if any existed at that layer).

### 10. Authorization invariants (constitutional, binding on every future Spatial mutation)

1. Authorization always precedes mutation — never after, never optimistically.
2. Every mutation is attributable to a specific `ExecutionContext.principal_id`.
3. Every mutation decision (permit or deny) produces an immutable, hash-chained audit record,
   except where §9 explicitly carves out a non-authorization failure mode (validation, archived-
   parcel conflict, cross-tenant 404) as not independently audited, matching Registry's identical
   precedent.
4. No mutation bypasses the PDP/PEP pipeline — there is exactly one authorization path.
5. No mutation bypasses RLS — the least-privilege `landvault_app` role has no path around it.
6. **RLS is never bypassed except through Controlled Platform Authority**
   (`docs/ENGINEERING_RULES.md` rule 9) — and this ADR's own mutation model requires no such
   bypass at all; every operation here is same-tenant creator-or-governance. Controlled Platform
   Authority becomes relevant only when ADR-021 designs the cross-tenant overlap-detection read
   (§11) — never as a shortcut for an ordinary Spatial mutation.
7. Delegated authority never exceeds the delegator's own current authority (`highest_rank()`,
   re-validated fresh on every request).
8. Tenant boundaries are absolute, evaluated before creator or governance authority, at two
   independent layers (RLS + application `_in_scope`).
9. Archived-parcel geometry mutation is permanently and unconditionally blocked — no privileged
   bypass for any role, mirroring ADR-015 exactly.
10. Creator authority is a fact about the *parcel's* creator (`Parcel.created_by`), never a
    second, Spatial-local "geometry ownership" concept competing with it.
11. Authorization decisions are deterministic — the same `(ctx, parcel)` pair always yields the
    same permit/deny outcome within one request's transaction.
12. Fail closed on any uncertainty — a parcel that cannot be found, is out of tenant scope, is
    archived, or fails the creator/governance check all deny (404/404/409/403 respectively),
    never silently permit.

### 11. Relationship to Controlled Platform Authority

**This ADR's own mutation model requires no cross-tenant read or write at all** — every operation
it governs is same-tenant (creator or governance, `_in_scope`-checked), with `super_admin`'s
existing, already-established cross-tenant reach as the only exception, unchanged from every
other context in this codebase. Controlled Platform Authority (`docs/ENGINEERING_RULES.md` rule
9) is therefore **not invoked by this ADR** — it remains the doctrine ADR-021 must satisfy when it
designs the genuinely new cross-tenant read overlap detection requires (`docs/B4_THREAT_MODEL.md`
TB5). This ADR does not pre-empt, weaken, or substitute for that future design; it simply has no
occasion to use the doctrine itself.

### 12. Relationship to ADR-021

**Explicitly out of scope for this ADR, reserved for ADR-021:** overlap detection, duplicate-
geometry detection, fraud/conflict investigation, the actual Controlled-Platform-Authority-
compliant cross-tenant comparison mechanism, and cross-tenant geometry comparison of any kind.
This ADR governs only same-tenant authorization for the mutation surface Slice 1 already
implemented (`submit_geometry`, `get_active_geometry`). When ADR-021 introduces genuinely new
operations (e.g., a cross-tenant overlap check triggered by submission), those operations need
their own authority-model entries, extending this document's matrix (§6) rather than this
document attempting to anticipate them now.

## Alternatives considered and rejected

1. **A Spatial-specific "geometry ownership" concept, independent of `Parcel.created_by`** —
   rejected (§2): would fragment authority over one logical resource (a parcel and its
   geometry) across two competing "creator" facts, with no evidence this platform needs that
   distinction, and directly against the instruction to reuse existing governance doctrine rather
   than inventing a parallel one.
2. **A governance-approval-gated submission workflow** (submissions enter a `PENDING` state until
   a governance role approves them) — rejected: this is a persistence-lifecycle change belonging
   to ADR-018 (frozen, "validate-then-store... no `PENDING`/`REJECTED` status"), not an
   authorization-model decision; introducing it here would silently redefine an accepted ADR's
   domain model under the cover of an authorization ADR, exactly what §12's discipline (and this
   ADR's own scope) forbids.
3. **A distinct "emergency authority" tier** — rejected (§3): `super_admin`'s existing cross-
   tenant reach already serves this purpose; a second tier would be an undocumented parallel
   escalation path, not a named, narrow, justified exception.
4. **Allowing governance override of archived-parcel geometry** (on the theory that governance
   roles need "escape hatches") — rejected (§8): directly contradicts ADR-015's own precedent that
   archival is a genuine terminal state with no privileged bypass; carving an exception here for
   Spatial specifically, while Registry has none, would be an inconsistency with no stated
   justification strong enough to survive this platform's "no undocumented behavior" standard.

## Relationship to ADR-015 (Registry authorization)

Every substantive rule in this ADR is a direct, deliberate mirror of ADR-015's: creator-or-
governance as the two independent grants, tenant scope evaluated first, archived-resource
mutation unconditionally blocked, delegation reusing ADR-011 unchanged, audit payload shape
(`effective_authority`, `delegated_roles`), and the identical invariant list adapted only in
wording, not in substance. Where this ADR differs from ADR-015 at all, it is because Spatial's
resource (`ParcelGeometry`, referencing a `Parcel` it does not own) is genuinely different from
Registry's own resource (`Parcel` itself) — never because a weaker or differently-reasoned model
was judged acceptable for Spatial.

## Relationship to ADR-018 (Spatial domain model)

This ADR governs *access to* `ParcelGeometry`; it does not add, remove, or reinterpret any field
or invariant ADR-018 established. §1 explicitly declines to introduce an approval workflow or an
archival status because doing so would modify ADR-018's persistence lifecycle, which is outside
this ADR's mandate. §8's "consequence for Slice 2" (extending `ParcelExistencePort`) is an
implementation detail this ADR requires but does not itself specify beyond the shape of the
information needed (`tenant_id`, `created_by`, `status`).

## Relationship to ADR-019 (GeometryPort interface amendment)

**Unaffected.** `GeometryPort.reference_is_valid(geometry_reference, tenant_id, parcel_id)`
governs the seam between Registry and a future real Spatial adapter (ADR-020's job to implement);
this ADR governs Spatial's own mutation endpoints (`submit_geometry`/`get_active_geometry`),
which are a separate authorization surface entirely. No assumption ADR-019 made about
`GeometryPort`'s signature, behavior, or scope is touched, extended, or relied upon differently
by this document.

## Risks (identified, not hidden)

- **Slice 1's currently-shipped code does not yet implement the creator-or-governance check this
  ADR specifies** — until Slice 2 implements it, any `PARCEL_REGISTRANT_ROLES` holder in the
  correct tenant can still submit geometry for any parcel in that tenant, the exact gap this ADR
  exists to close. This ADR is the design; it is not, by itself, a fix. Documented as an active,
  known gap in `docs/B4_VERIFICATION_CHECKLIST.md` until Slice 2 lands and is verified.
- **`ParcelExistencePort`'s required extension (§8) is not yet designed in full** — this ADR
  specifies what information it must return, not its exact method signature or return type;
  Slice 2 must finalize that design, ideally without a second round-trip to the database per
  request.
- **No stakeholder input has been sought on whether creator-only (vs. tenant-wide registrant)
  authority is the commercially correct model for geometry specifically** — this ADR reasons from
  architectural consistency with ADR-015, not from a fresh product/domain requirements pass;
  flagged as inherited reasoning, not independently re-validated for Spatial's specific use case.

## Deferred responsibilities

- **ADR-020** — the real `GeometryPort` adapter and real geometric validation rules (self-
  intersection, coordinate bounds, administrative-boundary containment). Not authorization; this
  ADR does not constrain ADR-020's validation-algorithm choices beyond what ADR-018 already did.
- **ADR-021** — overlap/duplicate-geometry detection, and the actual Controlled-Platform-
  Authority-compliant cross-tenant read mechanism (§11/§12). This ADR explicitly does not
  design that mechanism.
- **ADR-023** — map tiling / spatial search API, likely deferred pending frontend scheduling
  (unchanged assessment from `docs/B4_DISCOVERY_AND_PLANNING.md`).

## Recommendation

**If this ADR is accepted, B4 Slice 2 — Geometry Validation & Real Geometry Adapter is
recommended for authorization next**, with the explicit expectation that Slice 2's implementation
includes: (a) extending `ParcelExistencePort` per §8's consequence, (b) implementing the creator-
or-governance check in `SpatialService` per §§2–3/§6, (c) the archived-parcel block per §8, (d)
the `spatial.parcel_geometry.mutation_denied` audit event per §9, and (e) live-verified tests
reproducing the ADR-005-shaped attack this ADR exists to prevent — a non-creator, non-governance
registrant denied geometry mutation on a colleague's parcel — the same regression-test discipline
`test_non_creator_registrant_denied_update_adr005_regression` already established for Registry.

## Approval Gate

This ADR is **proposed**, not accepted. Per the governing instruction, no B4 Slice 2
implementation — including any change to `SpatialService`, `ParcelExistencePort`, or any other
Spatial code — begins until this document is reviewed and explicitly accepted.
