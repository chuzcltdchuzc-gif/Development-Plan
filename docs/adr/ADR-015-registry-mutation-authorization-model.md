# ADR-015 — Registry Mutation Authorization Model

**Status:** Accepted — extends ADR-009 (B1 Platform Freeze), ADR-010 (Tenant/Organization
Aggregate), ADR-011 (Delegated Administration), ADR-013 (Parcel Aggregate & Registry Domain
Model), ADR-014 (Atomic Parcel Number Allocation). Does not modify any frozen decision; see
§"Relationship to the frozen baseline."

**Date:** 2026-07-20

**Scope:** B3 Slice 3 only — `Parcel.update_details()`, `Parcel.archive()`, the ownership/
governance authorization check in `ParcelService`, `PATCH /v1/parcels/{id}`,
`POST /v1/parcels/{id}/archive`, and the small, general-purpose extension to context hydration
that makes delegation status visible for authorization/audit use (§"Actor Ownership" below). No
ownership *transfer*, survey workflow, evidence, geometry, public portal, spatial intelligence,
payments, notifications, or AI — those remain out of scope per this slice's authorization.

## Context

`docs/adr/ADR-005-property-registry-data-model.md` documented a confirmed historical defect in
the Emergent architecture: its PDP resource descriptor never carried `created_by`, so any
create-tier role could mutate *any* parcel in their tenant, not only the ones they registered.
ADR-013 (B3 Slice 1) closed half of this gap — `created_by` exists on every `Parcel` from the
first one ever created — but deliberately implemented no mutation commands at all, so the other
half (an authorization rule that actually *uses* `created_by` to gate a mutation) had nothing to
attach to yet. This ADR is that authorization rule, attached to the first real mutation commands
the Registry ships.

## Decision

### Actor ownership

The acting principal is `ExecutionContext.principal_id` — the same value every other mutation in
this codebase (Identity, Tenant, Delegation) already uses, established once at
`app.kernel.authorization.pep._build_context_from_token` from a verified JWT's `sub` claim,
resolved through Identity's hydrator, and never re-derived by Registry. Registry introduces no
second notion of "who is acting." Actor identity propagates automatically through the request
lifecycle via the existing `ExecutionContext` dependency chain (`current_context_dep` →
`require_role`/`require_auth` → `ParcelService` method) — the same path every prior slice used,
not a new one.

**Making delegation status visible to authorization and audit (the one general-purpose
extension this slice makes to shared code):** `ExecutionContext` has carried an `attributes: dict`
field since B1, unused by every context until now — nothing populates it. Registry's audit
requirement ("every mutation records whether the actor was exercising a delegated role") needs
that answer, and the only place it can be answered correctly is context hydration, since that is
the sole place delegated roles are resolved (ADR-011) — recomputing delegation status inside
Registry would be exactly the "second, divergent check" ADR-011 was written to prevent.
`app.contexts.identity.context_hydration._hydrate` (both the test and production variants) now
sets `attrs["attributes"] = {"delegated_roles": sorted(delegated)}` whenever any currently-
effective delegation contributed roles to this request, and
`app.kernel.authorization.pep._build_context_from_token` threads it into the
already-existing `ExecutionContext.attributes` field. This is not a new pipeline stage and not a
new mechanism — it is the existing hydration choke point populating a field that was always part
of the contract but never used, exactly the same shape ADR-010 and ADR-011 each used to extend
the hydrator (tenant-active check, then delegation resolution, now delegation *visibility*). No
context but Registry reads `attributes["delegated_roles"]` today; nothing prevents another
context from doing the same later without further kernel changes.

### Creator authority

**Creator status alone grants full mutation authority over the parcels that principal created.**
`parcel.created_by == ctx.principal_id` is sufficient, on its own, to permit `update` or
`archive` on that parcel (subject to the tenant-scope and archived-immutability guards below).
This is the direct fix for the ADR-005 defect: a `field_agent` who registered a parcel may
correct or archive it; a *different* `field_agent` in the same tenant, holding the identical
role, may not touch it merely by virtue of holding a registrant role — mutation authority is
tied to the specific parcel's `created_by`, not to possessing a registrant role in the abstract.

Creator authority is **not delegable as ownership**. A delegate exercising a delegated role does
not inherit the delegator's `created_by` standing on the delegator's past parcels — ownership is
a fact about who physically registered a specific resource, not a role, and ADR-011 delegates
*roles*, not resource-level facts. (A delegate who *creates* a new parcel while a delegated role
is effective becomes that parcel's `created_by` in their own right, exactly as `create_parcel`
already works unchanged since Slice 1 — they are the creator of that parcel, full stop.) What a
delegate *does* inherit is described next.

### Delegated authority

A delegate's mutation authority on a parcel they did not create comes entirely from whichever
**governance** role (see below) they currently, effectively hold — including a role held only
because it is currently delegated to them. `ExecutionContext.roles` is already the union of a
principal's direct roles and every currently-effective delegated role (ADR-011); Registry's
authorization check reads that union exactly as `require_role` already does, adding no
delegation-specific branch of its own. This means:

- A delegate holding a delegated `compliance_officer` (or `surveyor_general`, or — vanishingly
  rare in practice, but structurally identical — `super_admin`) role gets exactly that role's
  tenant-wide mutation reach over Registry, no more and no less than a direct holder of the same
  role, because `highest_rank()` already capped the delegation at creation time (ADR-011) to
  never exceed the delegator's own rank — "no mutation exceeds delegator authority" is therefore
  satisfied structurally, not by a Registry-specific check.
- A delegate holding only a delegated `field_agent`/`licensed_surveyor`/`surveyor_partner` role
  can create new parcels (as they always could) but cannot mutate a colleague's existing parcel
  they didn't create — the same rule that applies to any direct holder of those roles.
- **Expiry, revocation, delegator demotion, delegator suspension, and tenant suspension all take
  effect on the delegate's very next request**, with no code added by this slice: hydration
  re-resolves `delegation_is_effective()` fresh on every call (ADR-011), so a role that stops
  being effective simply stops appearing in `ctx.roles`, and Registry's mutation check sees
  exactly the same "not authorized" outcome it would for a principal who never held the role.
  This slice's live verification proves this holds for Registry specifically; it does not add a
  new enforcement mechanism, because none is needed.

### Tenant authority

Unchanged from ADR-013: RLS (`FORCE`d, the same `tenant_id = current_setting('app.tenant_id',
true) OR is_super_admin` policy every tenant-scoped table has used since migration `0001`) plus
the application-layer `_in_scope(ctx, parcel.tenant_id)` check, applied identically to mutation
paths as it already is to `get_parcel`. Cross-tenant mutation is impossible at two independent
layers; a cross-tenant caller who is not `super_admin` receives 404 (existence itself is not
revealed across tenants — the same choice ADR-013 already made for `GET`), not 403. Tenant
authority is evaluated **before** ownership/governance authority — a cross-tenant caller never
learns whether they would have passed the ownership check, since they never reach it.

### Super administrator authority

`super_admin` is a `GOVERNANCE_ROLES` member (`app.contexts.identity.domain.value_objects`,
unchanged), so it satisfies the governance branch of the mutation check like any other governance
role, and it is also the one role `_in_scope` grants a cross-tenant bypass to (unchanged from
ADR-013/RLS). The combination gives `super_admin` cross-tenant override on any parcel, in any
tenant, subject to the same immutable-once-archived guard as everyone else — no separate
override code path, no special case in `ParcelService`, the two existing checks simply both
evaluate to "permit" for this role. Every `super_admin` mutation is audited exactly like every
other mutation (§"Audit" below); this slice adds no operational restriction beyond what auditing
already provides, since the brief's "least-privilege expectations" for this role were already
addressed at the RLS/RBAC design stage (ADR-009) — `super_admin` is a role a principal is
explicitly granted, never a default, and every grant of it is itself an audited action
(`identity.role.assign`).

### Immutable Registry rules

Unchanged and reused, not redefined:

- `parcel_id`, `tenant_id`, `country_code`, `origin`, `created_by`, `created_at` — never
  mutable, by any actor, at any time (no setter exists; `update_details` only ever touches its
  explicit allow-list, below).
- `parcel_number` — immutable once allocated (ADR-013 invariant #2, ADR-014); no Slice 3
  command touches it.
- `status` — one-way `ACTIVE → ARCHIVED` only. **No restore command exists in this slice.**
  ADR-013 already called `ARCHIVED` "terminal"; introducing a restore path would be revisiting a
  frozen invariant, which requires its own ADR explicitly reopening that decision, not a default
  assumption inside a mutation-commands slice. If a real operational need for restore emerges,
  it is a Slice 4+ (or later) proposal, argued on its own merits against ADR-013's existing
  text — not decided here.
- Mutable, subject to authorization + the archived guard: `title`, `address`, `state`, `lga`,
  `ward`, `community`, `property_type`, `size_sqm`, `ownership_type`, `current_owner_name`,
  `current_owner_contact` — exactly the fields ADR-013 already classified as "registry metadata"
  and "current ownership reference," now finally reachable through a guarded mutation command
  instead of only at creation time. The allow-list lives on the aggregate itself
  (`Parcel.UPDATABLE_FIELDS`), not only in the API DTO — so "which fields can change" is a
  domain invariant even if a future second entry point into `update_details` is ever added.
- Every mutation requires authorization and produces an audit record — see below; not a new
  rule, restated here because ADR-013 stated it in the abstract (invariant #7/#8) before any
  mutation command existed to honor it concretely.

### Mutation permissions matrix

| Operation | Creator | Governance role (direct or delegated) | Ordinary registrant, not creator | Cross-tenant (non-`super_admin`) |
|---|---|---|---|---|
| Create | n/a (always self) | permit | permit (any `PARCEL_REGISTRANT_ROLES` holder) | n/a — create has no target resource |
| Read (`GET`) | permit | permit | permit (tenant-wide read, unchanged from Slice 1) | 404 |
| Update | permit | permit | **deny (403)** | 404 |
| Archive | permit | permit | **deny (403)** | 404 |
| Restore | not implemented — see §"Immutable Registry rules" | | | |
| Administrative override | n/a | *is* the override (Update/Archive rows above) | n/a | n/a |

"Ordinary registrant, not creator" is exactly the ADR-005 defect's shape, now closed: holding a
`PARCEL_REGISTRANT_ROLES` role is necessary to reach the mutation endpoints at all (the existing
coarse `require_role(*PARCEL_REGISTRANT_ROLES)` gate, unchanged from Slice 1's create-endpoint
gate, reused verbatim for the new endpoints) but is no longer *sufficient* — the fine-grained
ownership-or-governance check inside `ParcelService` is what actually decides permit/deny for a
specific resource, and it is this second, resource-aware layer that ADR-005's Emergent
implementation never had.

**Future ownership transfer compatibility:** `created_by` denotes *registrant/creator identity*
and must remain permanently distinct from *current legal ownership*
(`current_owner_name`/`current_owner_contact`, ADR-013 invariant #12) and from *actor identity*
(who is making a given request, which varies mutation to mutation). A future ownership-transfer
command changes only the current-ownership reference — it must never reassign `created_by`
(ADR-013 invariant #4: "ownership transfer never creates a new Parcel" already implies
`created_by` survives any such command unchanged, since it is not a new Parcel). This slice does
not decide who may *initiate* a future transfer — plausibly creator-or-governance like the
commands here, plausibly something narrower once a real ownership-history mechanism exists — that
is a decision for whichever slice builds it, made against the real requirements at that time, not
speculated here.

### Authorization invariants (constitutional, binding on every future Registry mutation)

1. Authorization is always evaluated before a mutation executes — never after, never optimistically.
2. Every mutation is attributable to a specific `ExecutionContext.principal_id`.
3. Every mutation produces an immutable, hash-chained audit record (`app.kernel.audit`) — no
   second audit mechanism, ever.
4. No mutation bypasses the PDP/PEP pipeline (`require_role`/`require_auth`) — there is exactly
   one authorization path, unchanged since ADR-009.
5. No mutation bypasses RLS — the least-privilege `landvault_app` role has no path around it;
   only the schema-owning migration role can.
6. Delegated authority never exceeds the delegator's own current authority (`highest_rank()`,
   re-validated fresh on every request — ADR-011, unchanged, reused).
7. Tenant boundaries are absolute — enforced at two independent layers (RLS + application scope
   check) for every mutation, not merely for reads.
8. Archived parcels remain permanently protected from further mutation — `_ensure_mutable()`,
   called first by every mutator without exception.
9. Authorization decisions are deterministic — the same `(ctx, parcel)` pair always yields the
   same permit/deny outcome; no time-of-check/time-of-use gap, since the check and the mutation
   happen inside the same request's Unit-of-Work transaction.
10. Fail closed on any uncertainty — a parcel that cannot be found, is out of tenant scope, or
    fails the ownership/governance check all deny (404/404/403 respectively), never silently
    permit.

### Audit

No second audit mechanism — the existing kernel `audit()` function (ADR-007), unchanged. Every
mutation call produces one of `registry.parcel.updated`, `registry.parcel.archived`, or, when the
ownership/governance check denies the attempt, `registry.parcel.mutation_denied` (the same
"audit the denial, with a reason" shape `identity.role.assign_denied` and
`identity.delegation.invalidated` already established — a 403 is exactly as auditable as a
permit, arguably more so, since it is the outcome that proves the ADR-005 fix is actually
enforced, not merely present in code). `principal_id` is captured automatically by `audit()`
from the ambient `ExecutionContext` (unchanged mechanism); each event's `payload` additionally
carries `tenant_id`, `effective_authority` (`"creator"`, or `"governance:<role[,role...]>"` for
whichever governance role(s) the check actually granted through), `delegated_roles` (from
`ctx.attributes["delegated_roles"]`, empty when the actor's authority was entirely direct), and,
for `updated`, which field names changed (values are not logged verbatim in the audit payload —
consistent with `current_owner_contact`/`current_owner_name` being free-text fields this
codebase has already decided not to encrypt-at-rest yet, ADR-013 — logging only field *names*
avoids duplicating potentially sensitive free-text into the audit store a second time).

### Archived parcel behaviour

Once `status == ARCHIVED`: `update_details` and `archive` both raise `ParcelArchivedError`
(mapped to `409 Conflict` at the service layer) unconditionally — creator, governance role, and
`super_admin` alike, no exception, no override path. This is deliberate: archival is meant to be
a genuine terminal state (ADR-013), and if an administrative correction is ever needed on
archived data, that is a "restore" capability question (explicitly not implemented, above), not
a reason to let mutation slip through the archived guard for privileged callers. `GET` remains
permitted on an archived parcel (reading is not a mutation); `list_parcels` continues to return
archived parcels alongside active ones, unchanged from Slice 1 (no filter was ever added, and
this slice adds none).

## Relationship to the frozen baseline

- **ADR-005** — the specific historical defect this slice was authorized to eliminate
  (create-tier mutation with no ownership context) is closed by the creator-or-governance check
  described above; §"Live verification" in the completion report reproduces the original attack
  shape against the new authorization model and confirms it is denied.
- **ADR-009** — PDP/PEP, Unit-of-Work, RLS session-variable mechanism, audit chain: all consumed
  unchanged. `ExecutionContext.attributes` is a field that already existed in ADR-009's original
  design; this slice is the first to populate it, not a change to the dataclass's shape.
- **ADR-010** — tenant-active hydration check: unchanged, still the first fail-closed gate a
  suspended tenant's members hit, before Registry mutation authorization is ever reached.
- **ADR-011** — delegation resolution, `highest_rank()` ceiling, and `delegation_is_effective()`:
  all reused verbatim. This slice's only extension to Identity code is making the *result* of
  that resolution (which roles are currently delegated) visible via the existing `attributes`
  field — the resolution logic itself is not touched.
- **ADR-013** — `Parcel.created_by`, `_ensure_mutable()`, `status`/`ARCHIVED`-as-terminal, and
  the `current_owner_name`/`current_owner_contact` "reference, not history" distinction: all
  reused exactly as designed; this slice is the first consumer of the guarded mutation point
  ADR-013 built and left deliberately unused.
- **ADR-014** — `parcel_number` remains untouched by every Slice 3 command; the atomic allocator
  is not a mutation path this slice interacts with at all.
- **No frozen decision required amendment.**

## Consequences

- The Registry's central historical vulnerability (ADR-005) has a concrete, tested, live-verified
  closure — not merely "the field exists now" (ADR-013's partial fix) but "the field is actually
  checked before every mutation" (this ADR's contribution).
- `ExecutionContext.attributes` is no longer dead weight in the dataclass — future contexts have
  a precedent for using it (a dict of context-specific, non-core authorization-relevant facts)
  rather than each inventing its own parallel side-channel.
- No new migration was required — `parcels.updated_by` and `parcels.archived_at` were reserved,
  unused, since migration `0007` (Slice 1); this slice is their first consumer. A deliberate
  consequence of Slice 1's forward-looking schema, not a coincidence.
- Slice 4 (geometry) inherits a Parcel aggregate whose mutation authorization is already correct
  and general — a future `update_geometry`-style command follows the identical
  creator-or-governance shape this ADR establishes, rather than needing its own authorization
  design from scratch.
- "Restore" and "ownership transfer" remain explicitly open questions for whichever future slice
  actually needs them — recorded here as compatible-with, not decided.
