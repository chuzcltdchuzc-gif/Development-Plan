# CLAUDE.md

AquaSavannah LandVault — a Nigerian land-registry/verification platform, rebuilt from scratch on Claude Code after full security/architecture audits of two prior implementations (`docs/audits/`). **Current status: B1 and B2 are complete, verified, and frozen (tagged `b2-freeze`) — see `docs/adr/ADR-009-b1-platform-freeze.md`, `docs/adr/ADR-012-b2-platform-freeze.md`, `docs/audits/B2_RELEASE_NOTES.md`. B3 (Registry) is in progress: Slice 1 (Parcel Aggregate) is done, verified against live infrastructure — see `docs/adr/ADR-013-parcel-aggregate-registry-domain-model.md` and "B3 status" below. Slices 2–4 (atomic numbering, mutation commands, geometry port) are not yet authorized.**

Docker Compose (Postgres + Keycloak + backend + frontend) has been booted end-to-end and is the normal way this repo is verified now — see `docs/audits/B1_INFRASTRUCTURE_VERIFICATION.md` for the full live-infrastructure validation this passed (migrations, RLS, JWT, rate limiting, audit chain, adversarial security checks). Cloud (staging/production) environments do not exist yet — Terraform has real version pins but no provider/resources (AWS vs. Azure is still open, see `docs/REBUILD_PLAN.md` §6).

## B1 status (Identity & Authorization) — frozen

Complete and verified against live infrastructure (real Docker/Postgres/Keycloak, not in-memory fakes) — see `docs/adr/ADR-009-b1-platform-freeze.md` for the full frozen architecture description (auth flow, JWT/refresh lifecycle, RLS model, audit-chain architecture, Unit-of-Work, rate limiting, etc.) and `docs/audits/B1_INFRASTRUCTURE_VERIFICATION.md` for the evidence. **Any change to what ADR-009 describes requires a new ADR referencing it — do not silently modify frozen B1 behavior while building B2+.**

## B2 status (tenant provisioning / role assignment / delegation) — frozen

Complete across four slices, each verified against live infrastructure — see
`docs/adr/ADR-012-b2-platform-freeze.md` for the freeze declaration and
`docs/audits/B2_RELEASE_NOTES.md` for the full evidence summary (migrations, 72/72 test
totals, per-slice live verification). **Any change to B2's invitation, tenant, or delegation
domains requires a new ADR referencing ADR-009/010/011/012 — do not silently modify frozen B2
behavior while building B3+.**

**Slices 1–2 — tenant membership invitations, full lifecycle (done, verified against live infrastructure):** a governance-role principal (`super_admin`/`surveyor_general`/`compliance_officer`) invites an email into their own tenant at a role no higher than their own rank (reuses `assign_role`'s hierarchy check exactly), via `POST /v1/admin/invitations`. The invitee redeems an opaque, hashed, expiring (7-day) token via `POST /v1/auth/invitations/accept` to complete registration directly into the inviter's tenant with the invited role. `GET /v1/admin/invitations` lists the caller's own tenant's invitations; `POST /v1/admin/invitations/{id}/revoke` cancels a pending one (any governance-role member of the tenant, not only the original inviter — revoking is strictly de-escalating, so no hierarchy check applies there). New table `identity_invitations` (migration `0004`), same RLS/grant shape as `identity_users`.

**Redemption-time authority re-validation:** creating an invitation only proves the inviter had authority *at that moment*. `AuthService.accept_invitation` re-fetches the inviter's *current* record at redemption time and re-runs the identical `highest_rank()` check against their present roles — if the inviter has since been deactivated or demoted below the invited role's rank, redemption is denied (`identity.invitation.redemption_denied`, generic 401) and the invitation is durably flipped to `REVOKED`, not left `PENDING` for a retry once/if authority is restored.

No email-delivery integration exists yet — the plaintext token is returned once to the inviter to relay out-of-band; this is a known, documented limitation, not a bug.

**Slice 3 — Tenant/Organization aggregate (done, verified against live infrastructure, `docs/adr/ADR-010-tenant-organization-aggregate.md`):** `tenant_id` is now backed by a real `Tenant` aggregate (`identity.domain.tenant`, migration `0005`) with lifecycle `ACTIVE <-> SUSPENDED -> ARCHIVED` (archive is terminal), FK'd from `identity_users.tenant_id` and `identity_invitations.tenant_id` — backward compatible by construction (same string ids, no remapping). `register_local` creates a real `Tenant` (status `ACTIVE`, `owner_user_id` = the new user) alongside the `User`. Suspending/reactivating/archiving a tenant is `super_admin`-only (`POST /v1/admin/tenants/{id}/suspend|reactivate|archive`) — narrower than the `GOVERNANCE_ROLES` used elsewhere, since it's a platform-operations action, not tenant-internal governance. `GET /v1/admin/tenants[/{id}]` (`super_admin`), `GET /v1/auth/me/tenant` (any authenticated user, own tenant only).

**Enforcement:** the context hydrator (`context_hydration.py`) fails closed on a suspended/archived tenant exactly like it already did for a suspended user — every authenticated request re-checks it, not just login, so a tenant suspended mid-session loses its members' effective authorization (any `require_role`-gated or PDP-checked route) on their very next request, without touching individual user records. `login_local` and `accept_invitation` also check tenant status directly, so a suspended tenant can't mint new tokens or accept new members either — this closes the exact gap slice 2 flagged as then-impossible-to-implement. **Precision worth remembering:** this does NOT make `require_auth`-only routes (e.g. `GET /v1/auth/me`) return 401 for that same token — `ExecutionContext.is_anonymous` only checks the literal `"anonymous"` sentinel, and that's existing, documented, frozen B1 behavior (ADR-009/`pep.py`), not something this slice changed. See ADR-010 for the full reasoning and for a real bug live verification caught and fixed (`PostgresTenantRepository.update()` initially dropped `owner_user_id` — the in-memory fake's full-object-replace masked it in unit tests).

**Slice 4 — Delegated administration (done, verified against live infrastructure, `docs/adr/ADR-011-delegated-administration.md`):** a governance-role principal delegates a subset of their own current authority (one or more roles, never ranked higher than their own — reuses `highest_rank()` verbatim) to another user in the *same tenant*, optionally time-bounded, via `POST /v1/admin/delegations`. No new authorization path: the pipeline (Identity → Context Hydration → Tenant Validation → Delegation Resolution → RBAC Evaluation → Decision) maps onto the *same single hydrator* ADR-010 already extended for tenant validation — `context_hydration.py` resolves currently-effective delegated roles fresh on every request and unions them into `ExecutionContext.roles` before `require_role`/the PDP ever run, so no caching layer means revocation is immediate by construction, not extra effort (live-verified: revoke → the delegate's unchanged access token is denied on its very next request, and a replay of the same request stays denied). Authority is re-validated against the delegator's *current* state on every resolution — delegator demoted/suspended, or the whole tenant suspended/archived, all immediately invalidate every delegation depending on them (also live-verified, including that restoring the delegator's role or the tenant's ACTIVE status correctly re-enables the delegation with no manual re-grant). `GET/POST /v1/admin/delegations[/{id}[/revoke|/extend]]`, `GOVERNANCE_ROLES`-gated (tenant-internal governance, unlike the `super_admin`-only tenant lifecycle actions).

**Two deliberate, documented non-features (see ADR-011):** no `delegated_permissions` field (this platform's RBAC is role-based, not permission-based — a permissions field with nothing to bind it to would be a decorative placeholder); `scope` is retained as a required descriptive label but is *not* independently enforced beyond the `delegated_roles` hierarchy ceiling in this slice (enforcing it would mean a second authorization dimension parallel to roles, explicitly out of scope).

**A correctness bug found via this slice's test coverage, affecting existing code too:** the explicit `resource.tenant_id != ctx.tenant_id` checks added in B2 slices 2–3 didn't account for `super_admin`'s legitimate cross-tenant reach (the same bypass RLS itself grants that role) — a `super_admin` acting cross-tenant was incorrectly 404'd. Fixed with a shared `_in_scope()` helper mirroring the RLS policy shape, applied retroactively to `revoke_invitation` too, not just the new delegation code.

**Not yet built:** nothing further planned for B2 — B2 is frozen (ADR-012, tag `b2-freeze`).

## B3 status (Registry) — Slice 1 done, Slices 2–4 not authorized

`docs/B3_DISCOVERY_AND_PLANNING.md` is the accepted Phase 0 plan. **Slice 1 — Parcel
Aggregate (done, verified against live infrastructure, `docs/adr/ADR-013-parcel-aggregate-registry-domain-model.md`):**
a new bounded context, `app/contexts/registry/`, introduces `Parcel` — the single canonical
representation of a land parcel. `parcel_id` (UUID) is immutable identity; `tenant_id` is a
real FK to `tenants.id` *from its first migration* (`0007`), unlike Identity's own `tenant_id`,
which only got FK'd retroactively in B2 slice 3. `parcel_number` exists as a nullable column
with a database-level partial unique index already enforcing uniqueness, reserved for Slice
2's atomic allocator — no allocation logic exists yet, deliberately. Ownership is a *current
reference* only (`current_owner_name`/`current_owner_contact`) — no history table, no PII
beyond free-text name/contact.

`POST /v1/parcels` is gated `require_role(*PARCEL_REGISTRANT_ROLES)`
(`field_agent`/`licensed_surveyor`/`surveyor_partner`/`surveyor_general`/
`compliance_officer`/`super_admin` — referencing Identity's existing `Role` enum, no new
role). `GET /v1/parcels[/{id}]` use bare `require_auth` — tenant isolation is RLS plus an
explicit repository-level filter, not a role gate. **No new authorization mechanism**: a
delegate holding a delegated registrant role (ADR-011) can register a parcel exactly as if
they held it directly — `require_role` doesn't distinguish a direct grant from a currently-
effective delegation, live-verified working with zero Registry-specific integration code.

Domain invariants are enforced on the aggregate itself, not just at the endpoint:
`allocate_parcel_number()` exists now (unused by any Slice 1 API path) and raises if called
twice or against an archived parcel — "reserve the field" means a guarded mutation point, not
a bare mutable column. No mutation commands, ownership transfer, geometry, evidence, or survey
upload are implemented — explicitly out of scope per the Slice 1 authorization.

86/86 tests pass (72 existing + 14 new). Live-verified: real parcel creation via Keycloak-
authenticated `field_agent`, cross-tenant `GET` denied (404), tenant-scoped listing, `general_user`
denied creation (403), the database-level `parcel_number` uniqueness constraint rejecting a
duplicate insert directly, RLS fail-closed via `psql` (bogus tenant → 0 rows, `DELETE` denied
at the grant level), audit chain intact, containerized backend rebuilt and confirmed healthy.
PostGIS confirmed active (`3.4.3`) — zero infrastructure lift needed for B3 Slice 4's future
geometry column.

**Not yet built (explicitly deferred, per the Slice 1 authorization):** atomic parcel
numbering (Slice 2, needs its own ADR — the Postgres-native mechanism cannot be a literal port
of Emergent's MongoDB-native `$inc`/upsert allocator), mutation commands and real actor-
identity authorization (Slice 3, fixes a confirmed ADR-005 defect), the geometry port (Slice
4). **Slices 2–4 are not authorized** — this execution authorized Slice 1 only.

This file is the always-loaded operational summary. It is a pointer, not the source of truth — if anything here ever conflicts with the documents it points to, **those documents win.**

## The 5 non-negotiable rules (full detail: `docs/ENGINEERING_RULES.md`)

1. **No new entity/table without an RLS/authorization policy in the same commit.** (Base44 shipped wallet/invoice entities with unconditional public update access — this is the exact bug class that rule prevents.)
2. **No permissive fallback default on any security-relevant env var.** Missing config must fail startup, never silently degrade to an insecure default. (Emergent's CORS wildcard-with-credentials and hardcoded signing-secret fallback.)
3. **Exactly one authorization path: the PDP/PEP/PIP engine.** No parallel/legacy auth system, no unguarded dev-login, ever — not even temporarily. (Emergent's dual auth system + unauthenticated admin bypass.)
4. **Every scoring/validation function fails safe:** zero/missing data → low or neutral result, never a passing score. (Base44's trust engine reported 100/A+ with zero real evidence.)
5. **Never mark something complete without having actually observed it pass.** Static code inspection is not evidence — run the test, see it pass.

## Where to look for more

| Need | Go to |
|---|---|
| The technical build plan (stack, 13 bounded contexts, stages, milestones) | `docs/REBUILD_PLAN.md` |
| Process/quality gates per phase, the Claude Code Loop, standing review questions | `docs/PHASE_GATES.md` |
| Definition of Done (Feature / Sprint / Product tiers) | `docs/DOD.md` |
| Full engineering rules, incl. when to stop and ask a human | `docs/ENGINEERING_RULES.md` |
| Why a specific architectural decision was made | `docs/adr/` |
| The audit findings everything above is derived from | `docs/audits/` |

## Repo layout

```
/frontend   — Next.js + TypeScript (F0 shell landed; bounded-context UI stages land per docs/REBUILD_PLAN.md §3)
/backend    — Python + FastAPI (B0 kernel in app/kernel/; app/contexts/identity/ has B1+B2; app/contexts/registry/ has B3 slice 1)
/infra      — Terraform (version-pinned baseline, no provider yet), Docker (infra/docker/docker-compose.yml)
/docs       — this planning package
```

## Working model

Sprints are one per bounded context (13 total, dependency-ordered per `docs/REBUILD_PLAN.md` §1), each gated through the Claude Code Loop in `docs/PHASE_GATES.md` and signed off against `docs/DOD.md` before merge. Do not start a sprint whose dependencies (per the bounded-context ordering) aren't yet Sprint Done.

## Build/test/run commands

**Backend** (from `/backend`):
```
python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"
.venv/Scripts/pytest                 # unit tests
.venv/Scripts/ruff check .           # lint
.venv/Scripts/mypy app tests         # type check
.venv/Scripts/uvicorn app.main:app --reload --no-proxy-headers   # run locally; needs env vars, see .env.example
# --no-proxy-headers: no trusted reverse proxy is configured (ADR-004) — without
# this flag uvicorn trusts X-Forwarded-For from 127.0.0.1 by default and rewrites
# request.client, defeating the app's own anti-spoofing rate-limiter logic.
```

**Frontend** (from `/frontend`):
```
npm install
npm run typecheck
npm run lint
npm run build && npm run start       # or `npm run dev` for local development
```

**Full stack** (from repo root, requires Docker):
```
cp .env.example .env   # then fill in real values
docker compose --env-file .env -f infra/docker/docker-compose.yml up --build
# --env-file is required: plain env_file: in the compose YAML only injects
# vars into containers, it does not feed ${VAR} substitution in the YAML itself.
```
Migrations against the live database (owning role, not the app's least-privilege role):
```
docker compose --env-file .env -f infra/docker/docker-compose.yml exec backend alembic upgrade head
```
