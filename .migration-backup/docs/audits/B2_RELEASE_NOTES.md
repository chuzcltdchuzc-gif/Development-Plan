# B2 Release Notes

**Release tag:** `b2-freeze`
**Date:** 2026-07-18
**Governing ADRs:** `docs/adr/ADR-009-b1-platform-freeze.md` (baseline, unmodified),
`docs/adr/ADR-010-tenant-organization-aggregate.md`,
`docs/adr/ADR-011-delegated-administration.md`,
`docs/adr/ADR-012-b2-platform-freeze.md` (this release's freeze declaration)

B2 extends B1's Identity context with tenant provisioning, tenant lifecycle management, and
delegated administration — closing every item in `docs/REBUILD_PLAN.md`'s B2 row ("User↔IdP
mapping, hierarchy-checked role assignment, delegation wired into the PDP, tenant
provisioning"). No frozen B1 decision (ADR-009) was modified; every extension point used
already existed in B1's design.

---

## Completed slices

| Slice | Delivered | ADR |
|---|---|---|
| 1 | Tenant membership invitations — governance-gated creation, hierarchy-checked (`POST /v1/admin/invitations`), anonymous redemption (`POST /v1/auth/invitations/accept`) | — (frozen in ADR-012) |
| 2 | Invitation lifecycle — listing, revocation, and redemption-time authority re-validation (closes the "inviter loses authority after issuing, before redemption" gap) | — (frozen in ADR-012) |
| 3 | Tenant/Organization aggregate — real lifecycle (`ACTIVE ↔ SUSPENDED → ARCHIVED`), FK-backed, backward compatible, fail-closed enforcement via context hydration | ADR-010 |
| 4 | Delegated administration — derived, re-validated-live authority delegation within a tenant, folded into the existing hydration/PDP pipeline | ADR-011 |

## Migrations (0004–0006)

| # | File | Adds |
|---|---|---|
| 0004 | `0004_identity_invitations.py` | `identity_invitations` table, RLS, least-privilege grants (`SELECT/INSERT/UPDATE`, no `DELETE`), partial unique index (one pending invite per tenant+email) |
| 0005 | `0005_tenants.py` | `tenants` table; backfills one row per pre-existing `tenant_id` string (owner = earliest-created user in that tenant); adds FK constraints on `identity_users.tenant_id` and `identity_invitations.tenant_id`; RLS; grants |
| 0006 | `0006_identity_delegations.py` | `identity_delegations` table; FK constraints to `tenants`/`identity_users`; indexes including the composite `(tenant_id, delegate_user_id)` the hot per-request hydration lookup depends on; RLS; grants |

No destructive migration in the set. Every migration was applied to the live Postgres instance
and independently inspected via `psql` (schema, indexes, FK constraints, RLS policy text,
grants) before being marked done — not assumed correct from reading the migration source.

## API surface added

```
POST   /v1/admin/invitations
GET    /v1/admin/invitations
POST   /v1/admin/invitations/{id}/revoke
POST   /v1/auth/invitations/accept

GET    /v1/admin/tenants
GET    /v1/admin/tenants/{id}
POST   /v1/admin/tenants/{id}/suspend
POST   /v1/admin/tenants/{id}/reactivate
POST   /v1/admin/tenants/{id}/archive
GET    /v1/auth/me/tenant

POST   /v1/admin/delegations
GET    /v1/admin/delegations
GET    /v1/admin/delegations/{id}
POST   /v1/admin/delegations/{id}/revoke
POST   /v1/admin/delegations/{id}/extend
```

Every route existing before B2 (`/v1/auth/register|login|refresh|logout|me`,
`/v1/admin/users/{id}/roles`) is unchanged in request/response shape — B2 is additive at the
API surface, confirmed by the full pre-B2 test suite (B1's 27 acceptance/unit tests) still
passing unmodified throughout.

## Test totals

**72/72 tests passing** at freeze (0 failures, 0 skips), `ruff` clean, `mypy` clean (strict,
zero `# type: ignore` added in B2 beyond one pre-existing, documented FastAPI stub limitation
from B1).

| Suite | Count | Covers |
|---|---|---|
| B1 acceptance + unit (`test_b1_acceptance.py`, `test_authorization.py`, `test_config.py`, `test_health.py`, `test_jwt_verifier.py`) | 27 | Unmodified from B1 — regression-checked after every B2 slice |
| Invitations (`test_b2_invitations.py`) | 16 | Creation, hierarchy ceiling, accept, replay, duplicate-pending, listing, revoke, expiry, authority-loss (demoted/suspended inviter), audit integrity |
| Tenants (`test_b2_tenants.py`) | 11 | Register-creates-tenant, response-shape backward compatibility, super_admin-only lifecycle, suspend/reactivate/archive, login/invitation denial for suspended tenant, listing/get scoping, audit integrity |
| Delegations (`test_b2_delegations.py`) | 18 | Same-tenant grant + real PDP-gated access, cross-tenant denial, hierarchy ceiling, self-delegation rejected, non-governance denial, expiry, revoke-immediate-no-replay, delegator suspended/demoted, delegate suspended, tenant suspension/archival, computed effective status, revoke/extend edge cases, audit integrity |

Every new test file exercises real business logic against in-memory fakes at the port
boundary (`tests/fakes/`, `tests/app_factory.py`) — never mocked-out application logic. Every
slice was additionally verified against real Postgres and real Keycloak (below) before being
marked complete, per the standing "never mark something complete without having actually
observed it pass" rule.

## Accepted ADRs

- **ADR-010** — Tenant/Organization Aggregate. Accepted; documents the backward-compatible FK
  migration strategy, the mutual-FK insert ordering (tenant → user → tenant-with-owner), and
  the fail-closed hydration extension.
- **ADR-011** — Delegated Administration. Accepted; documents the no-new-authorization-path
  design, the two deliberate non-features (`delegated_permissions`, unenforced `scope`), and
  the `_in_scope()` correctness fix.
- **ADR-012** — B2 Platform Freeze (this release). Accepted; formally closes B2, gathers
  slices 1–2's frozen shape (no dedicated ADR existed for them), and puts B3+ on notice.

## Known limitations (tracked, not hidden)

- **No email-delivery integration.** Invitation tokens are returned once in the API response;
  the inviter relays them out-of-band. No Notifications bounded context exists yet.
- **No Keycloak realm export committed.** Inherited from ADR-009 — the service account used
  for admin operations correctly lacks permission to enumerate/export realm config
  (least-privilege, confirmed live), so there is no automated way to produce one yet.
- **`Delegation.scope` is descriptive only**, not independently enforced beyond the
  `delegated_roles` hierarchy ceiling — see ADR-011 for why building real per-scope
  enforcement now would mean a second authorization dimension parallel to roles.
- **No dedicated secret-leakage-in-logs audit.** Inherited from ADR-009, still open.
- **No push notifications** for tenant suspension, invitation, or delegation lifecycle
  events — all visible only via API polling or the audit log.

## Production verification summary

Every slice's live-infrastructure verification was performed against the actual running stack
(Docker Compose: Postgres, Keycloak, backend), not simulated:

- **Migrations**: all three (`0004`–`0006`) applied cleanly to the live Postgres instance;
  schema, FKs, indexes, and RLS policy text independently inspected via `psql` after each.
- **RLS**: for every new table, confirmed live via `psql` as the least-privilege `landvault_app`
  role — a bogus/unset tenant session variable returns zero visible rows (fail-closed, never
  an implicit full-table leak), and a direct `DELETE` attempt is denied at the database grant
  level (`permission denied for table ...`), independent of any application-level check.
- **End-to-end flows**: for each slice, the complete real-world flow was run through the
  actual HTTP API against real Keycloak-issued, RS256-signed tokens and real Postgres data —
  not `TestClient` against fakes. This included: invitation creation → hierarchy denial →
  acceptance → replay rejection; tenant registration → suspension → login denial →
  reactivation → archival → reactivate-after-archive conflict; delegation creation → real
  PDP-gated access before/after → cross-tenant denial → delegator demotion and restoration
  (both directions) → delegator suspension → tenant suspension and reactivation → revoke →
  replay denied twice with the same unchanged access token.
- **Audit chain**: `verify_chain()` confirmed `True` after every slice's live testing, with
  every expected action name present in the real, Postgres-persisted audit log (not the
  in-memory fake).
- **Containerized backend**: rebuilt and health-checked after every slice, not only the local
  dev server — the shipped Docker image was independently confirmed to run the same code
  verified above.

## Freeze declaration

Per ADR-012, B2 is frozen as of this release. No further changes to the Identity context's B2
scope (invitation, tenant, or delegation domains) land without a new ADR referencing ADR-009,
ADR-010, ADR-011, and/or ADR-012 as appropriate. B3 planning may begin from this baseline.
