# ADR-010 — Tenant/Organization Aggregate

**Status:** Accepted — extends ADR-009 (B1 Platform Freeze). Does not supersede or modify any
frozen B1 decision; see §"Relationship to ADR-009" below for why each touched area is an
extension, not a change, and exactly which lines of ADR-009 this builds on top of.

**Date:** 2026-07-17

**Scope:** B2 slice 3, `backend/app/contexts/identity/domain/tenant.py`, migration
`0005_tenants.py`, and the specific extensions to `context_hydration.py`, `AuthService`, and
`AdminService` described below.

## Context

ADR-009 froze B1 with `tenant_id` as an unstructured string field on `User` — every
self-registered user got their own, isolated, randomly-generated tenant, with no way for a
second person to join an existing one, no lifecycle, and no ownership/governance metadata.
`docs/REBUILD_PLAN.md`'s B2 row calls for "tenant provisioning" explicitly, and B2 slice 2's
own documentation (`CLAUDE.md`) flagged this precisely: "there is no `Tenant`/`Organization`
aggregate anywhere in this codebase... so a genuine 'is the tenant itself active/suspended'
check has no concept to verify against yet." This ADR closes that gap.

## Decision

**`Tenant`** (`app.contexts.identity.domain.tenant`) is a new aggregate with lifecycle
`ACTIVE <-> SUSPENDED -> ARCHIVED` (archive is terminal, matching the Registry aggregate's
"Archive: one-way" convention, ADR-005). Fields: `tenant_id`, `name`, `owner_user_id`,
`status`, `suspension_reason`/`suspended_at`/`archived_at`, `created_at`/`updated_at`.

**Backward-compatible by construction, not by migration risk-taking:** `tenants.id` is a
`String`, not a UUID, and uses the *exact same values* `identity_users.tenant_id` already
held before this table existed. No existing tenant id is remapped. Migration `0005`:
creates the table, backfills one row per distinct pre-existing `tenant_id` (owner =
earliest-created user in that tenant), then adds real FK constraints
(`identity_users.tenant_id -> tenants.id`, `identity_invitations.tenant_id -> tenants.id`).
Same RLS-tenant-isolation shape and least-privilege grant (`SELECT/INSERT/UPDATE`, no
`DELETE`) as every other tenant-scoped table.

**Enforcement is fail-closed at the one place authorization attributes are already resolved**
(`context_hydration.py`): the existing hydrator already returned `None` — "no authorization
attributes" — for a suspended *user* (`user.can_authenticate()`). This ADR adds the identical
check for a suspended/archived *tenant*. Since the hydrator runs on every authenticated
request (not just at login), a tenant suspended after its members already hold valid access
tokens loses effective authorization on their very next `require_role`-gated or PDP-checked
request — not only at their next login. `AuthService.login_local` gets the same check
directly, so a suspended tenant can't even mint a new token in the first place.
`AuthService.accept_invitation`'s redemption-time re-validation (B2 slice 2) is extended with
a real tenant-active check, replacing what was previously documented as an impossible-to-
implement gap.

**Tenant creation is now explicit, not implicit-via-string-generation:**
`AuthService.register_local` creates a real `Tenant` row (status `ACTIVE`) alongside the
`User`, with the new user as `owner_user_id`. Because `tenants.owner_user_id ->
identity_users.id` and `identity_users.tenant_id -> tenants.id` are a genuine mutual FK pair,
neither row can carry a valid forward reference to the other at insert time — the tenant is
inserted first with no owner (nullable), then the user (referencing the now-real tenant),
then the tenant is updated with its owner. Three round-trips, deliberately not a deferred-
constraint trick, so the ordering stays legible from reading the code.

**Lifecycle authority is `super_admin`-only**, narrower than the `GOVERNANCE_ROLES` set used
elsewhere in Identity: suspending or archiving an entire organization is a platform-operations
action, not tenant-internal governance a `compliance_officer`/`surveyor_general` should be
able to exercise over their own tenant.

New endpoints: `GET /v1/admin/tenants` (list, `super_admin`), `GET /v1/admin/tenants/{id}`
(`super_admin`), `POST /v1/admin/tenants/{id}/suspend|reactivate|archive` (`super_admin`),
`GET /v1/auth/me/tenant` (any authenticated user, their own tenant only). All additive — no
existing endpoint's request/response shape changes.

## Relationship to ADR-009 (why this extends, not changes, the frozen baseline)

- **§2 Authorization Flow / §11 Dependency Injection** — ADR-009 documents the
  `ContextHydrator` as a `Callable[[str], Awaitable[dict | None]]` contract where `None`
  means "no valid authorization attributes, PDP default-denies." That contract is unchanged;
  this ADR adds a second *cause* of returning `None` (tenant not active) alongside the
  existing one (user not active), using the identical mechanism the frozen design already
  established for exactly this purpose.
- **§1 Authentication Flow** — `login_local`'s existing `user.can_authenticate()` gate is
  extended with one more condition (`tenant.is_active()`), using the same generic-rejection
  message pattern ADR-009 already documents. The credential-verification flow itself
  (Keycloak Direct Access Grant) is untouched.
- **§6 Database Schema / §7 RLS Policy Model** — a new table, not a change to any frozen
  table's columns or existing RLS policies. The new table's RLS policy is the *same shape*
  ADR-009 documents for `identity_users`, applied to a new resource, not a divergent pattern.
- **§10 Unit-of-Work** — completely untouched. `get_db_session` still sets exactly the same
  two session variables, from the same `ExecutionContext` fields, the same way.
- **No frozen decision required amendment.** Nothing above required changing tenant
  isolation *semantics*, identity boundaries, or the authentication flow's actual credential
  path — only extending an already-established "fail-closed on ineligibility" pattern to a
  new eligibility condition.

## A caveat found during implementation, corrected before merge

Live verification (this project's standing rule: nothing is marked done without an observed
pass against real infrastructure) caught a real defect the in-memory-fake unit tests could
not: `PostgresTenantRepository.update()` initially never wrote `owner_user_id` to the row,
because the in-memory fake's `update()` replaces the whole cached object (masking the
omission) while the real adapter updates fields selectively. `owner_user_id` came back `null`
after registration against the live database despite the unit test asserting it correctly.
Fixed and re-verified live. Documented here rather than quietly folded in, per this project's
"evidence before assertions" rule (`CLAUDE.md`).

## Consequences

- B2 slice 4 (delegated administration) can now delegate *within* a real organizational
  boundary instead of a one-person, string-only tenant.
- A tenant's suspension is a single, auditable action that locks out every member's effective
  authorization immediately, without iterating or mutating individual user records.
- `require_auth`-only routes (e.g. `GET /v1/auth/me`) do **not** start returning `401` for a
  suspended tenant's already-issued token — `ExecutionContext.is_anonymous` only checks the
  literal `"anonymous"` sentinel, and a hydration-empty token still carries the raw IdP
  subject as `principal_id` (existing, documented ADR-009/`pep.py` behavior). The real
  security boundary such a token loses is every `require_role`-gated and PDP-checked action —
  confirmed by test and by live verification. This is not a gap introduced here; it is
  inherited, unchanged, frozen B1 behavior this ADR does not touch.
- Every self-registered tenant now has real ownership metadata (`owner_user_id`), which B2
  slice 4's delegated-administration work can use as the natural "who may delegate within
  this org" starting point.
