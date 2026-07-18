# ADR-012 — B2 Platform Freeze

**Status:** Accepted — B2 is frozen as of this date, tagged `b2-freeze`. Amend via a new ADR
that references this one; do not edit this document's description of "what B2 is"
retroactively — a later ADR that changes B2 behavior supersedes the relevant section here and
must say so explicitly. Same amendment discipline ADR-009 established for B1.

**Date:** 2026-07-18

**Verified against:** `docs/audits/B2_RELEASE_NOTES.md` (migrations `0004`–`0006`, 72/72 tests,
live Postgres/Keycloak verification per slice) — this document is the architecture
description; that one is the evidence it's accurate. Built on top of, and does not modify,
`docs/adr/ADR-009-b1-platform-freeze.md`.

## Context

B2 (Identity context extensions: tenant provisioning, invitation lifecycle, tenant lifecycle,
delegated administration) is complete across four slices, each individually reviewed and
accepted, each verified against real infrastructure, not simulated. Two of the four slices
introduced significant new domain concepts and already have their own ADRs
(`docs/adr/ADR-010-tenant-organization-aggregate.md`,
`docs/adr/ADR-011-delegated-administration.md`); this document is the formal close-out that
declares B2 done, gathers all four slices' frozen shape in one place, and — per the same
governance model ADR-009 established — puts B3+ on notice that B2 is now a stable platform to
build on, not a moving target to reach into.

**Amendment procedure:** identical to ADR-009 — a bounded context that needs B2 to behave
differently opens a new ADR referencing this one (and ADR-010/011 where relevant) and states
precisely what changes and why. It does not edit B2's source directly as a side effect of B3+
work without that ADR existing first.

## Scope — what is frozen

Everything under `backend/app/contexts/identity/` added or modified since ADR-009 (invitation,
tenant, and delegation domain modules, their repositories/adapters, the extended
`AuthService`/`AdminService`, the extended `context_hydration.py`), migrations `0004`–`0006`,
and the API surface listed below. B1's frozen scope (ADR-009) is unchanged and unaffected.

---

## 1. Tenant Membership Invitations (slices 1–2 — no dedicated ADR; frozen here for the first time)

A governance-role principal (`super_admin`/`surveyor_general`/`compliance_officer`) invites an
email into their own tenant at a role no higher than their own rank (`highest_rank()`,
identical to `assign_role`'s check), via `POST /v1/admin/invitations`. The invitee redeems an
opaque, hashed, 7-day-expiring token via `POST /v1/auth/invitations/accept` to complete
registration directly into the inviter's tenant with the invited role. `GET
/v1/admin/invitations` lists the caller's own tenant's invitations; `POST
/v1/admin/invitations/{id}/revoke` cancels a pending one (any governance-role member of the
tenant, not only the original inviter — revoking only de-escalates, no hierarchy check).

**Redemption-time re-validation** (not just creation-time): `AuthService.accept_invitation`
re-fetches the inviter's *current* record and re-runs the hierarchy check against their
present roles, and (since slice 3) checks the target tenant is still active. Any failure
durably revokes the invitation (not left `PENDING` for a later retry) and audits
`identity.invitation.redemption_denied` with a specific reason before returning the same
generic 401 used for unknown/expired tokens.

Table: `identity_invitations` (migration `0004`), same RLS-tenant-isolation and
least-privilege-grant shape (`SELECT/INSERT/UPDATE`, no `DELETE`) as `identity_users`, plus a
partial unique index enforcing at most one pending invitation per `(tenant_id, email)` at the
database level.

**Known limitation, carried forward, not fixed in B2:** no email-delivery integration exists.
The plaintext invitation token is returned once, in the creation response, for the inviter to
relay out-of-band. This is a deliberate scope boundary (no Notifications bounded context
exists yet), not an oversight.

## 2. Tenant/Organization Aggregate (slice 3 — full detail: ADR-010)

`tenant_id` is a real `Tenant` aggregate (`identity.domain.tenant`, migration `0005`) with
lifecycle `ACTIVE <-> SUSPENDED -> ARCHIVED` (archive terminal), FK'd from
`identity_users.tenant_id` and `identity_invitations.tenant_id` — backward compatible by
construction (same string ids, no remapping; a `String` primary key, not a UUID). Suspending/
reactivating/archiving is `super_admin`-only, deliberately narrower than the `GOVERNANCE_ROLES`
used for invitations and delegations — a platform-operations action, not tenant-internal
governance.

Enforcement extends `context_hydration.py`'s existing fail-closed pattern (already used for a
suspended user): a suspended/archived tenant returns `None` from the hydrator on every
subsequent authenticated request, so it takes effect immediately for already-issued access
tokens on any `require_role`-gated or PDP-checked route — not only at next login.
`login_local` and `accept_invitation` check tenant status directly too, so a suspended tenant
can neither mint new tokens nor accept new members.

**Precision preserved from ADR-010, still true:** this does not make `require_auth`-only
routes (e.g. `GET /v1/auth/me`) return 401 for that same token — that is pre-existing, frozen
B1 behavior (`ExecutionContext.is_anonymous` only checks the literal sentinel), not something
B2 changed.

## 3. Delegated Administration (slice 4 — full detail: ADR-011)

A governance-role principal delegates a subset of their own current authority (roles, never
ranked higher than their own) to another user in the same tenant, optionally time-bounded, via
`POST /v1/admin/delegations`. Resolution folds into the same hydrator extension point slice 3
established — no new pipeline stage, no second authorization path. No caching layer exists
anywhere in this pipeline, so revocation, delegator demotion/suspension, and tenant suspension
all take effect on the delegate's very next request, live-verified against real infrastructure
in both directions (loss and restoration of authority).

Table: `identity_delegations` (migration `0006`), same RLS/grant shape as every other
tenant-scoped table, indexed on `(tenant_id, delegate_user_id)` for the hot hydration lookup.

**Known, documented non-features, not placeholders:** no `delegated_permissions` field (this
platform's RBAC is role-based, not permission-based — ADR-004/ADR-009 — there is no PDP
concept to bind a fine-grained permission to); `scope` is a required descriptive label,
retained per the requested minimum field set, but not independently enforced beyond the
`delegated_roles` hierarchy ceiling.

## 4. Cross-cutting fix discovered during B2 (affects B1-era code too)

`AdminService._in_scope()` — a `super_admin` acting on a resource outside their own
(largely irrelevant) tenant was, for a stretch of B2 slices 2–3, incorrectly `404`'d by an
application-level `resource.tenant_id != ctx.tenant_id` check that didn't account for the
same cross-tenant bypass Postgres RLS already grants that role. Fixed with a helper mirroring
the RLS policy shape exactly (`tenant_id = ctx.tenant_id OR is_super_admin`), applied to
`revoke_invitation` and every delegation read/mutate path. Confirmed via regression tests that
no other caller's behavior changed.

## 5. Migrations shipped in B2

| Migration | Adds |
|---|---|
| `0004_identity_invitations.py` | `identity_invitations` table, RLS, least-privilege grants, partial unique index |
| `0005_tenants.py` | `tenants` table, backfill from existing `tenant_id` strings, FK constraints on `identity_users`/`identity_invitations`, RLS, grants |
| `0006_identity_delegations.py` | `identity_delegations` table, FK constraints, indexes (incl. the hot-path composite index), RLS, grants |

All three follow the same pattern established in B1: RLS shipped in the same migration that
creates the table, least-privilege grants (`SELECT/INSERT/UPDATE`, never `DELETE`), no
destructive changes to any existing table's data.

## Known limitations carried into B3 (not fixed in B2, tracked, not hidden)

- No email-delivery integration (§1).
- No Keycloak realm export committed (inherited from ADR-009 — still true, still blocked by
  the service account's own least-privilege scope).
- `scope` field on `Delegation` is descriptive only, not enforced (§3 / ADR-011).
- No dedicated secret-leakage-in-logs audit (inherited from ADR-009 — still open).
- No email/notification mechanism for tenant suspension, invitation, or delegation events —
  all visible only via the API and audit log, not pushed to affected users.

## Consequences

- B3+ contexts build on a stable Identity platform with real tenant, invitation, and
  delegation primitives — not the single-string `tenant_id` ADR-009 froze B1 with.
- Any future context needing a genuine per-action permission system (beyond role-based RBAC)
  needs its own ADR and its own PDP-level design — B2 explicitly did not build one, twice
  (delegated_permissions, scope enforcement), on the same "do not redesign RBAC" principle.
- The `_in_scope()` fix is a behavior change for `super_admin` callers specifically (now
  correctly permitted where previously incorrectly denied) — documented here so it is never
  mistaken for a regression by a future session reading git history without this context.
- B2 is tagged `b2-freeze` at the commit this ADR is accepted in. No further B2-scope changes
  land without a new ADR referencing this one.
