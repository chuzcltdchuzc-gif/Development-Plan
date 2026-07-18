# ADR-011 — Delegated Administration

**Status:** Accepted — extends ADR-009 (B1 Platform Freeze) and ADR-010 (Tenant/Organization
Aggregate). Does not supersede or modify any frozen decision; see §"Relationship to ADR-009
and ADR-010" for exactly which sections are extended vs. touched, and why none required
amendment.

**Date:** 2026-07-18

**Scope:** B2 slice 4, `backend/app/contexts/identity/domain/delegation.py`, migration
`0006_identity_delegations.py`, and the specific extensions to `context_hydration.py` and
`AdminService` described below. Introduces a new domain concept (a significant one, per the
same threshold that produced ADR-010), so it gets its own ADR rather than being folded into
ADR-010's text after the fact.

## Context

`docs/REBUILD_PLAN.md`'s B2 row calls for "delegation wired into the PDP." B2 slices 1–3
built tenant provisioning and a real Tenant aggregate but explicitly deferred delegation,
noting it "needs its own design pass since no prior spec exists for it." This ADR is that
design pass.

## Decision

**`Delegation`** (`app.contexts.identity.domain.delegation`) is a new aggregate: a governance-
role principal (the delegator) grants a subset of their own current authority — one or more
roles, never ranked higher than their own — to another user in the *same tenant* (the
delegate), for an optional bounded time. Delegation is **derived authority**: a delegate never
has more effective authority than their delegator currently holds, re-validated live on every
resolution, not just at grant time.

**No new authorization path.** The pipeline this ADR was asked to implement (Identity →
Context Hydration → Tenant Validation → Delegation Resolution → RBAC Evaluation → Decision)
maps onto the *existing single hydrator* extension point ADR-010 already established for
tenant validation — not a new pipeline stage, not a second decision engine. `context_hydration.
py`'s hydrator, on every authenticated request, resolves which of a principal's active
delegations are *currently* effective and unions their `delegated_roles` into
`ExecutionContext.roles` before `require_role`/the PDP ever run. The PDP and `require_role`
are unmodified — they simply receive a role set that may include delegated roles, exactly as
they already handle a principal's own direct roles.

**No caching, no grace period — by construction, not by extra effort.** No caching layer
exists anywhere in this request pipeline (confirmed already true for the user-active and
tenant-active checks ADR-010 added). Delegation resolution inherits that property for free:
revoking a delegation, demoting a delegator, or suspending a delegator's account or the tenant
itself takes effect on the delegate's very next request, using an access token that hasn't
changed at all.

**Authority ceiling reuses `highest_rank()` verbatim** — the identical function
`assign_role`/`create_invitation` already use, at three points: delegation creation, every
resolution (hydration), and `extend`. Never a second, divergent hierarchy check.

**Fields, and two deliberate omissions:**

- No `delegated_permissions` field. This platform's authorization model is role-based, not
  permission-based (ADR-004/ADR-009) — there is no PDP concept to bind a fine-grained
  permission to. Adding the field would be a decorative, unenforced placeholder; omitted
  rather than stubbed.
- `scope` is retained (per the requested minimum fields) as a descriptive label validated
  against a small fixed set (`tenant_governance`, `role_assignment`, `invitation_management`),
  shown in listings and audit payloads, but **not independently enforced** in this slice
  beyond what `delegated_roles`' hierarchy ceiling already restricts. The only authorization
  primitive this platform's `require_role`/PDP mechanism understands is roles; enforcing
  per-scope restrictions on individual endpoints would mean either a second authorization
  dimension parallel to roles, or making every existing service method scope-aware — both
  explicitly ruled out ("do not redesign RBAC," "do not introduce a parallel authorization
  path"). Documented honestly rather than pretending scope gates something it doesn't yet.

**Audit events collapse onto this codebase's existing pattern**, not eight independent action
names with unclear per-request triggers: `identity.delegation.created`, `.denied` (creation-
time validation failures), `.revoked`, `.modified` (extend) are distinct actions;
`Expired`/`Authority Lost`/`Tenant Suspended` become `reason` values under one
`identity.delegation.invalidated` event — the same shape `identity.role.assign_denied` and
`identity.invitation.redemption_denied` already use for multi-cause denials. Fired at explicit
management touchpoints (`GET` single, `revoke`, `extend`), not from the hot hydration path —
consistent with the hydrator never auditing suspended-user/suspended-tenant lockouts from that
path either (ADR-010).

**Lifecycle authority for `revoke` is deliberately unrestricted by hierarchy**: any governance-
role member of the tenant may revoke any delegation in it, not only the original delegator —
revoking only de-escalates, the same reasoning `revoke_invitation` (B2 slice 2) already
established. `extend`, by contrast, re-validates the ceiling against the *original delegator's
current* rank (not the caller's), since extending prolongs derived authority and must satisfy
the same ceiling creation did.

New endpoints, all `GOVERNANCE_ROLES`-gated (tenant-internal governance, unlike the
`super_admin`-only tenant lifecycle actions in ADR-010): `POST/GET /v1/admin/delegations`,
`GET/POST /v1/admin/delegations/{id}[/revoke|/extend]`.

## A correctness bug found and fixed during this slice, affecting existing code too

Live-and-unit test coverage for `super_admin` cross-tenant access exposed that the explicit
`resource.tenant_id != ctx.tenant_id` checks added in B2 slices 2–3 (`revoke_invitation`, and
the new delegation methods) didn't account for `super_admin`'s legitimate cross-tenant reach —
the same bypass Postgres RLS already grants that role
(`tenant_id = current_setting('app.tenant_id') OR is_super_admin`). A `super_admin` acting on
a resource outside their own (largely irrelevant) tenant was incorrectly 404'd by the
application-layer check even though the database layer would have permitted it. Fixed with a
shared `_in_scope(ctx, resource_tenant_id)` helper mirroring the RLS policy shape exactly,
applied to `revoke_invitation` (retroactively) and all three delegation read/mutate paths.
Not applied to `create_delegation`'s delegate lookup — creating a delegation *into* a tenant
the caller doesn't belong to has no well-motivated use case and isn't what "same tenant only"
was asking for.

## Relationship to ADR-009 and ADR-010 (why this extends, not changes)

- **ADR-009 §2 Authorization Flow** — the `ContextHydrator` contract
  (`Callable[[str], Awaitable[dict | None]]`) is unchanged. Delegation resolution happens
  *inside* an existing, successful hydration (a `None` result already short-circuits before
  delegation is ever considered) — it only ever adds to an already-resolved role set, never
  replaces the hydrator's contract or the PDP's evaluation logic.
- **ADR-010's tenant-validation extension pattern** — this ADR reuses the identical mechanism
  (extend the hydrator's existing fail-closed checks) rather than inventing a new one,
  confirming that pattern generalizes rather than needing a redesign per new lifecycle concern.
- **ADR-009 §6/§7 Database Schema / RLS Policy Model** — one new table, the *same* RLS shape
  documented there, applied to a new resource.
- **ADR-009 §10 Unit-of-Work** — untouched. Still sets exactly the same two session variables
  from the same `ExecutionContext` fields.
- **RBAC / PDP architecture** — untouched. `require_role` and the PDP's policy evaluation
  logic are not modified; they consume an input (role set) that may now include delegated
  roles, resolved entirely upstream of them.
- **No frozen decision required amendment.** Nothing above changed identity boundaries,
  authentication flow, or tenant isolation semantics — only extended an already-established
  "resolve eligibility fresh, fail closed" pattern to a third condition (delegation) alongside
  the two ADR-010 already added (user active, tenant active).

## Consequences

- A tenant's governance can now distribute administrative work (role assignment, invitation
  management) without granting a permanent role change — reversible, time-boundable, and
  re-validated against the delegator's *current* standing on every use, not just at grant time.
- Delegation depends on a real `Tenant` aggregate existing (ADR-010) — this is a direct
  consumer of that work, not a coincidence of sequencing.
- The `scope` field's current non-enforcement is a real, documented limitation: if per-action
  fine-grained delegation is ever needed, it requires its own ADR and likely a genuine
  permission primitive this platform doesn't have yet — not an incremental extension of this
  one.
- The `_in_scope` fix changes behavior for `super_admin` callers of `revoke_invitation`
  specifically (previously incorrectly 404'd on cross-tenant targets, now correctly permitted,
  consistent with what RLS already allowed at the database layer) — a bug fix, not a new
  capability; regression tests confirm no other caller's behavior changed.
