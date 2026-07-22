# CLAUDE.md

AquaSavannah LandVault — a Nigerian land-registry/verification platform, rebuilt from scratch on Claude Code after full security/architecture audits of two prior implementations (`docs/audits/`). **Current status: B1, B2, and B3 are complete, verified, and frozen (tagged `b2-freeze`, `b3-freeze`) — see `docs/adr/ADR-009-b1-platform-freeze.md`, `docs/adr/ADR-012-b2-platform-freeze.md`, `docs/adr/ADR-017-b3-platform-freeze.md`, `docs/audits/B2_RELEASE_NOTES.md`, `docs/audits/B3_RELEASE_NOTES.md`. B3 (Registry) is the current production architectural baseline: the Parcel aggregate, atomic parcel numbering, creator-aware mutation authorization (closing a confirmed ADR-005 defect), and a geometry port boundary for future spatial capability — see "B3 status" below. B4 (Spatial Intelligence) is an entirely new programme, currently in Phase 0 discovery only (`docs/B4_DISCOVERY_AND_PLANNING.md`) — no B4 code exists; implementation awaits explicit approval of that plan.**

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

## B3 status (Registry) — frozen

Complete across four slices, each verified against live infrastructure, culminating in a
dedicated End-of-B3 Quality Gate — see `docs/adr/ADR-017-b3-platform-freeze.md` for the freeze
declaration and `docs/audits/B3_RELEASE_NOTES.md` for the full evidence summary (migrations,
119/119 platform-wide test totals, live Postgres/Keycloak/RLS/delegation/audit-chain/cross-tenant/
ownership-attack/container verification). **Any change to B3's parcel, allocation, mutation-
authorization, or geometry-boundary domains requires a new ADR referencing
ADR-013/014/015/016/017 — do not silently modify frozen B3 behavior while building B4+.**

**Deferred-verification policy (effective mid-Slice-3, retired at freeze):** Slice 3 onward ran
comprehensive `ruff`/`mypy`/`pytest`/live verification once, at the End-of-B3 Quality Gate,
instead of per slice — a workflow change only, not a relaxation of engineering or governance
standards. The gate ran 2026-07-20 and **passed**: full `ruff`/`mypy` (one pre-existing,
unrelated type-annotation gap in `migrations/env.py` found and fixed), full `pytest` (119/119),
and live Postgres/Keycloak/RLS/delegation/audit-chain/cross-tenant/ownership-attack/container
verification — see `docs/B3_FINAL_VERIFICATION_CHECKLIST.md` for full evidence. Slices 1–2
already received full live verification before this policy existed and were unaffected by it.

`docs/B3_DISCOVERY_AND_PLANNING.md` is the accepted Phase 0 plan. **Slice 1 — Parcel
Aggregate (done, verified against live infrastructure, `docs/adr/ADR-013-parcel-aggregate-registry-domain-model.md`):**
a new bounded context, `app/contexts/registry/`, introduces `Parcel` — the single canonical
representation of a land parcel. `parcel_id` (UUID) is immutable identity; `tenant_id` is a
real FK to `tenants.id` *from its first migration* (`0007`), unlike Identity's own `tenant_id`,
which only got FK'd retroactively in B2 slice 3. `parcel_number` exists as a nullable column
with a database-level partial unique index (global, not tenant-scoped — a land registry number
identifies one parcel unambiguously across the whole jurisdiction) enforcing uniqueness.
Ownership is a *current reference* only (`current_owner_name`/`current_owner_contact`) — no
history table, no PII beyond free-text name/contact.

`POST /v1/parcels` is gated `require_role(*PARCEL_REGISTRANT_ROLES)`
(`field_agent`/`licensed_surveyor`/`surveyor_partner`/`surveyor_general`/
`compliance_officer`/`super_admin` — referencing Identity's existing `Role` enum, no new
role). `GET /v1/parcels[/{id}]` use bare `require_auth` — tenant isolation is RLS plus an
explicit repository-level filter, not a role gate. **No new authorization mechanism**: a
delegate holding a delegated registrant role (ADR-011) can register a parcel exactly as if
they held it directly — `require_role` doesn't distinguish a direct grant from a currently-
effective delegation, live-verified working with zero Registry-specific integration code.

Domain invariants are enforced on the aggregate itself, not just at the endpoint:
`allocate_parcel_number()` raises if called twice or against an archived parcel — "reserve the
field" means a guarded mutation point, not a bare mutable column. No mutation commands,
ownership transfer, geometry, evidence, or survey upload are implemented — explicitly out of
scope per the Slice 1 authorization.

**Slice 2 — Atomic Parcel Number Allocation (done, verified against live infrastructure,
`docs/adr/ADR-014-postgresql-atomic-parcel-number-allocation.md`):** every parcel now receives
a real, unique `parcel_number` at creation time via one atomic
`INSERT ... ON CONFLICT DO UPDATE ... RETURNING` against a `registry_parcel_counters` table
(migration `0008`), in the same request transaction as the parcel insert — a rollback undoes
the counter increment along with everything else, so no gaps are ever created by a failed
request. The counter is scoped by **`country_code`, not `tenant_id`**: the first draft of
ADR-014 chose per-tenant, and live concurrency testing across two tenants sharing a country
caught that it collides with `parcel_number`'s existing database-wide unique constraint the
moment more than one tenant operates in the same country — fixed before this slice's review,
see ADR-014's revision note for the full account. `registry_parcel_counters` holds no
tenant-owned data, so its RLS policy (still `FORCE`d, still no `DELETE` grant) admits any
authenticated request rather than matching a `tenant_id`.

90/90 tests pass. Live-verified: 12 real concurrent HTTP requests split across two different
tenants sharing `NG` land in one contiguous, duplicate-free, gap-free sequence (proving the
fix); a different `country_code` drawing its own independent sequence; rollback-gaplessness
(allocate → roll back → allocate again yields the identical number) proven directly against
`PostgresParcelNumberAllocator`; the live audit log carrying `parcel_number` in every
`registry.parcel.created` entry with `verify_chain()` returning `True`; RLS fail-closed via
`psql` (no session context → 0 rows, `DELETE` denied at the grant level); containerized backend
rebuilt and confirmed healthy (boots clean, correct routes) — full authenticated flow
verification goes through the host dev server, same as every other slice, since the
containerized backend's `KEYCLOAK_REALM_URL` is host-relative (`localhost:8080`), a pre-existing,
out-of-scope infra gap unrelated to this slice. A same-tenant `N=20` run separately surfaced
SQLAlchemy's default connection-pool ceiling (`pool_size=5` + `max_overflow=10` = 15) under
heavy concurrent load — a genuine, documented operational limit, not a correctness defect.

**Slice 3 — Mutation Commands & Authorization Hardening (implemented, verification deferred per
the policy above, `docs/adr/ADR-015-registry-mutation-authorization-model.md`):** the Registry's
first mutation commands, `PATCH /v1/parcels/{id}` (edit registry metadata / current-ownership
reference) and `POST /v1/parcels/{id}/archive` (one-way `ACTIVE → ARCHIVED`, no restore — ADR-013
already called `ARCHIVED` terminal). Authorization is a genuine domain-aware check, not just the
existing coarse role gate: `parcel.created_by == ctx.principal_id` (creator authority) **or**
`ctx.has_any_role(*GOVERNANCE_ROLES)` (`super_admin`/`surveyor_general`/`compliance_officer`,
direct or delegated) is required to mutate a specific parcel — closing the confirmed ADR-005
defect where any create-tier role could mutate any parcel in their tenant. A delegated governance
role inherits exactly the delegator's own reach (ADR-011's `highest_rank()` ceiling, unchanged);
a delegated non-governance role does not inherit override on a colleague's parcel. Cross-tenant
attempts 404 (existence not revealed, evaluated before ownership); an archived parcel rejects
every further mutation unconditionally, creator/governance/`super_admin` alike (409).
`ExecutionContext.attributes` — a field that has existed since B1, never populated until now —
carries `delegated_roles` from context hydration through to Registry's audit payloads, so every
mutation's audit entry (`registry.parcel.updated`/`.archived`/`.mutation_denied`) records
`effective_authority` (`creator` vs. `governance:<role>`) and delegation status. No new
migration — `parcels.updated_by`/`archived_at` were reserved, unused, since `0007`.

37/37 registry tests pass (19 new); `ruff`/`mypy` clean on every changed file. Full-suite and
live verification are the largest deferred items — see
`docs/B3_FINAL_VERIFICATION_CHECKLIST.md`'s Slice 3 section for the complete list (real
Postgres/RLS/Keycloak/delegation/audit-chain/container checks, plus a full B1+B2+B3 regression
run, since this slice also touched the shared `context_hydration.py`/`pep.py` hydration path).

**Slice 4 — Geometry Port Boundary & Spatial Integration Foundation (implemented, verification
deferred per the policy above, `docs/adr/ADR-016-geometry-port-boundary-spatial-integration.md`):**
an architectural boundary, not a GIS feature — no polygon drawing, coordinate systems, topology,
spatial search, or survey workflows (all B4). `Parcel` gains one nullable field,
`geometry_reference: str | None` — an opaque pointer to a future Spatial Intelligence context's
own geometry data, never a polygon or PostGIS type, never interpreted by Registry (migration
`0009`, purely additive). Registry depends on exactly one new contract,
`GeometryPort.reference_is_valid(geometry_reference: str) -> bool`
(`app/contexts/registry/ports.py`) — never PostGIS or any concrete GIS technology directly. This
slice's `PlaceholderGeometryAdapter` (`app/contexts/registry/adapters/geometry.py`) satisfies it
with zero business logic (always returns `True`); a future B4 adapter swaps in without changing
`ParcelService`, `Parcel`, or any Registry test. `PUT /v1/parcels/{id}/geometry` reuses ADR-015's
`_load_in_scope`/`_authorize_mutation` verbatim — no geometry-specific authorization rule, no new
role, no parallel pipeline. Two new audit actions,
`registry.parcel.geometry_attached`/`.geometry_detached`, through the existing `audit()` function.

47/47 registry tests pass (10 new) at implementation time; 119/119 across the whole suite after
the Quality Gate. **B3 is frozen** (`docs/adr/ADR-017-b3-platform-freeze.md`, tag `b3-freeze`) —
full `ruff`/`mypy`/`pytest`, live Postgres/Keycloak/RLS/delegation/audit-chain/cross-tenant/
ownership-attack/container verification all passed (`docs/B3_FINAL_VERIFICATION_CHECKLIST.md`,
one pre-existing type-annotation gap found and fixed). **B3 is the current production
architectural baseline** — every later programme builds on it, and no B3-scope change lands
without a new ADR referencing ADR-013/014/015/016/017.

## B4 status (Spatial Intelligence) — Slice 1 implemented, verification deferred, Slice 2 not authorized

`docs/B4_DISCOVERY_AND_PLANNING.md` is **accepted as the official B4 planning baseline**, and
`docs/B4_THREAT_MODEL.md` is **accepted as the official B4 security and trust-boundary
baseline** — its six trust boundaries (TB1–TB6) are mandatory architectural constraints on all B4
work, and its STRIDE analysis is Spatial Intelligence's initial security model. Its central
finding: overlap/duplicate-geometry detection needs a cross-tenant read to work as a fraud signal
at all — structurally unlike every prior RLS boundary in this codebase — so that read must be
fixed/input-bounded, read-only, and audited (ADR-021's job to design). **Controlled Platform
Authority** (rule 6, above) was formalized as a platform-wide doctrine from this finding.

**ADR-018 — Spatial Domain Model is accepted** (`docs/adr/ADR-018-spatial-domain-model.md`) —
the `ParcelGeometry` aggregate, `app/contexts/spatial/`'s bounded-context shape, validate-then-
store persistence (satisfying the threat model's binding requirement that invalid geometry never
reach storage), and the `geometry(Polygon, 4326)` storage/CRS decision. Domain model + bounded-
context boundary only — overlap detection, real validation rules, and GIS services remain later
ADRs' job.

**ADR-019 — GeometryPort Interface Amendment is accepted**
(`docs/adr/ADR-019-geometry-port-interface-amendment.md`) — the first formal amendment of the B4
programme, and the first time it reaches back into frozen B3 code: `GeometryPort.reference_is_valid`
now takes `tenant_id`/`parcel_id` so a real adapter can verify a reference actually belongs to the
parcel being mutated, closing a cross-tenant-reference leak the placeholder adapter couldn't have
caught. `docs/adr/ADR-016-geometry-port-boundary-spatial-integration.md` is preserved unmodified
as historical record of what B3 decided; ADR-019 is the current, authoritative contract.
**Implemented and verified:** `GeometryPort`, `PlaceholderGeometryAdapter`,
`ParcelService.set_geometry_reference` (using `parcel.tenant_id`, not `ctx.tenant_id` — a
mypy-caught refinement, since `ExecutionContext.tenant_id` is `str | None`), and `FakeGeometryPort`
all updated — strictly the signature change, no validation algorithm, no overlap detection, no
other GIS functionality. Full `ruff`/`mypy` clean; full `pytest` **119/119 passed with zero test
file changes**, confirming B3 regression is genuinely unaffected, not merely assumed to be.

**B4 Slice 1 — Spatial Domain Foundation is implemented** (`docs/B4_DISCOVERY_AND_PLANNING.md`
§4, Slice B4.1): a new bounded context, `app/contexts/spatial/`, mirroring Registry's exact
internal shape. `ParcelGeometry` — immutable identity, append-only `ACTIVE`/`SUPERSEDED`
lifecycle (a correction supersedes the prior `ACTIVE` row and adds a new one, never an in-place
edit), validate-then-store persistence (`ParcelGeometry.new()` is the only constructor and
rejects malformed WKT before an instance can exist). `boundary` is `geometry(Polygon, 4326)`
(migration `0010`) — SRID enforced at the column level; a small, local, dependency-free
`Geometry` `TypeEngine` handles `ST_GeomFromText`/`ST_AsText` wrapping, deliberately avoiding a
`geoalchemy2` dependency this slice doesn't need. `PUT`/`GET /v1/spatial/parcels/{id}/geometry`,
gated by the same coarse `PARCEL_REGISTRANT_ROLES` role check Registry uses, plus an explicit
`_in_scope` tenant check (the same two-independent-layers pattern every context in this codebase
uses) — **not yet a full creator-or-governance model**; that is explicitly ADR-022's job, and is
flagged in `docs/B4_VERIFICATION_CHECKLIST.md` as worth weighing carefully before this slice is
considered production-ready, since it is structurally similar in shape to the original ADR-005
defect. `PlaceholderGeometryAdapter` remains Registry's registered `GeometryPort` — this slice's
real data is not yet wired to it (ADR-020's job).

132/132 tests pass (13 new); `ruff`/`mypy` clean; migration `0010` applied and independently
verified live via `psql` (schema, FKs, RLS fail-closed, grants, the "one `ACTIVE` geometry per
parcel" partial unique index). One real design gap was found via a failing test (not assumed
correct) and fixed: the first draft relied solely on RLS for tenant scoping, which the in-memory
fake has no equivalent of — fixed by adding the explicit `_in_scope` check. Per the deferred-
verification policy, full live Postgres/Keycloak/RLS/concurrency/audit-chain/container
verification is deferred to the eventual B4 Quality Gate — every item tracked in
`docs/B4_VERIFICATION_CHECKLIST.md`, none skipped. **B4 Slice 2 is not authorized** — this
execution authorized Slice 1 only; B4 remains an entirely new programme with no further
implementation without its own explicit go-ahead, the same discipline B3 itself started under.

This file is the always-loaded operational summary. It is a pointer, not the source of truth — if anything here ever conflicts with the documents it points to, **those documents win.**

## The 6 non-negotiable rules (full detail: `docs/ENGINEERING_RULES.md`)

1. **No new entity/table without an RLS/authorization policy in the same commit.** (Base44 shipped wallet/invoice entities with unconditional public update access — this is the exact bug class that rule prevents.)
2. **No permissive fallback default on any security-relevant env var.** Missing config must fail startup, never silently degrade to an insecure default. (Emergent's CORS wildcard-with-credentials and hardcoded signing-secret fallback.)
3. **Exactly one authorization path: the PDP/PEP/PIP engine.** No parallel/legacy auth system, no unguarded dev-login, ever — not even temporarily. (Emergent's dual auth system + unauthenticated admin bypass.)
4. **Every scoring/validation function fails safe:** zero/missing data → low or neutral result, never a passing score. (Base44's trust engine reported 100/A+ with zero real evidence.)
5. **Never mark something complete without having actually observed it pass.** Static code inspection is not evidence — run the test, see it pass.
6. **Controlled Platform Authority: any cross-tenant/platform-wide read or write must be a named, narrow exception** — fixed at the call site (never parameterized by caller input), read-only wherever possible, as narrow as the task allows, and audited unless a specific, reviewed reason says otherwise. (Generalizes the existing `super_admin` RLS bypass and the hydration service-account's one fixed lookup into an explicit doctrine — formalized when `docs/B4_THREAT_MODEL.md` found Spatial Intelligence's overlap detection needs a third such exception.)

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
