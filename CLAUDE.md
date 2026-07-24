# CLAUDE.md

AquaSavannah LandVault — a Nigerian land-registry/verification platform, rebuilt from scratch on Claude Code after full security/architecture audits of two prior implementations (`docs/audits/`). **Current status: B1, B2, and B3 are complete, verified, and frozen (tagged `b2-freeze`, `b3-freeze`) — see `docs/adr/ADR-009-b1-platform-freeze.md`, `docs/adr/ADR-012-b2-platform-freeze.md`, `docs/adr/ADR-017-b3-platform-freeze.md`, `docs/audits/B2_RELEASE_NOTES.md`, `docs/audits/B3_RELEASE_NOTES.md`. B3 (Registry) is the current production architectural baseline: the Parcel aggregate, atomic parcel numbering, creator-aware mutation authorization (closing a confirmed ADR-005 defect), and a geometry port boundary for future spatial capability — see "B3 status" below. B4 (Spatial Intelligence) is an entirely new programme, currently in Phase 0 discovery only (`docs/B4_DISCOVERY_AND_PLANNING.md`) — no B4 code exists; implementation awaits explicit approval of that plan.**

Docker Compose (Postgres + Keycloak + backend + frontend) has been booted end-to-end and is the normal way this repo is verified now — see `docs/audits/B1_INFRASTRUCTURE_VERIFICATION.md` for the full live-infrastructure validation this passed (migrations, RLS, JWT, rate limiting, audit chain, adversarial security checks). Cloud (staging/production) environments do not exist yet — Terraform has real version pins but no provider/resources (AWS vs. Azure is still open, see `docs/REBUILD_PLAN.md` §6).

**`docs/ARCHITECTURE_HANDBOOK.md` (v1.0)** is the consolidated engineering reference — platform philosophy, full architecture diagram, DDD vocabulary, engineering rules index, security model, programme governance lifecycle, documentation hierarchy, future-programme surveys, architectural evolution, and engineering culture, each pointing to its authoritative source document. It is not an ADR and decides nothing new; read it first to orient, then follow its links for the actual decision.

**`docs/LV-000-constitution.md`** (adopted 2026-07-26) is **the platform's supreme governing document** — above the Handbook in the precedence order its own Article II states (LV-000 → Handbook → Accepted ADRs → Programme Documents → Engineering Documentation). It establishes ten constitutional principles (Trust Platform before Software Platform; Platform-not-Aggregate; Bounded Context Sovereignty; Documentation Before Implementation; Architecture Before Code; Security by Design; Controlled Platform Authority; Government Readiness; Professional Partnership; Trust Network Doctrine) across 22 Articles, incorporates both entries previously logged in `docs/CONSTITUTIONAL_RECOMMENDATIONS.md`, and modifies no accepted ADR, creates no bounded context, and contains no implementation detail — it ratifies doctrine this platform's engineering already operates under, per its own Article VI/Article XX, Section 2.

**`docs/PLATFORM_STRATEGY.md`** (2026-07-25) sits one layer below the Handbook — vision, official positioning, the five-layer platform model (Identity/Land Intelligence/Marketplace/Enterprise/Government), the "Trust Platform before Software Platform" principle (now constitutional — LV-000 Article IX, Section 1), and network-effects/flywheel reasoning. Eight further planning-only documents sit beneath it, each ending in its own Approval Gate with no implementation authorized: `docs/PARTNER_PROGRAMME_STRATEGY.md`, `docs/ENTERPRISE_PROGRAMME_STRATEGY.md`, `docs/GOVERNMENT_PROGRAMME_STRATEGY.md`, `docs/DEVELOPER_PLATFORM_STRATEGY.md`, `docs/COMMERCIAL_ARCHITECTURE.md`, `docs/OPERATING_MODEL.md`, `docs/TRUST_FRAMEWORK.md`, `docs/NETWORK_GROWTH_STRATEGY.md` — plus an extension to the existing `docs/MARKETPLACE_DISCOVERY_AND_PLANNING.md` naming candidate domain concepts (Job, Assignment, Escrow, Wallet, Rating, Dispute, etc.). **None of this authorizes any new bounded context, ADR change, or code** — B1–B4 remain exactly as documented below, and B4 Slice 3 remains unauthorized.

**`docs/LANDVAULT_BIBLE_VOLUME_I_EXECUTIVE_OVERVIEW.md`** (2026-07-27) is the LandVault Bible™ Volume I — a 15–25 page executive narrative (Problem/Vision/Mission/Philosophy/Architecture/Five-Layer Model/Trust Ecosystem/Commercial Vision/Governance/Roadmap/Strategic Position) written for governments, investors, executives, enterprise clients, and procurement teams. **Explanatory and non-normative only** — it synthesizes LV-000, the Handbook, and Platform Strategy in plain executive prose, decides nothing, and is corrected in favor of any document it summarizes if the two ever differ. Deliberately avoids the "Uber for Land Verification" marketplace framing in its external positioning language, per explicit instruction, in favor of the trust/governance/infrastructure framing throughout this file.

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

## B4 status (Spatial Intelligence) — Slices 1 & 2 accepted and frozen under ADR-022; ADR-021 proposed; Slice 3 not authorized

`docs/B4_DISCOVERY_AND_PLANNING.md` and `docs/B4_THREAT_MODEL.md` are **accepted baselines** —
the threat model's six trust boundaries (TB1–TB6) are mandatory constraints on all B4 work, and
its central finding (overlap detection needs a cross-tenant read, unlike every prior RLS boundary
in this codebase) produced **Controlled Platform Authority** as platform-wide rule 6, above.

**Accepted ADRs:** **ADR-018** (Spatial Domain Model — the `ParcelGeometry` aggregate,
`app/contexts/spatial/`'s shape, validate-then-store persistence, `geometry(Polygon, 4326)`).
**ADR-019** (GeometryPort Interface Amendment — `reference_is_valid` now takes
`tenant_id`/`parcel_id`; implemented and verified, 119/119 tests, zero test-file changes;
`docs/adr/ADR-016-...md` preserved unmodified as historical record). **ADR-022** (Spatial
Authorization Model — creator-or-governance mutation authority for `ParcelGeometry`, mirroring
ADR-015 exactly; accepted and now fully implemented, see below).

**B4 Slice 1 — Spatial Domain Foundation is implemented** (`app/contexts/spatial/`, mirroring
Registry's shape exactly): `ParcelGeometry`'s append-only `ACTIVE`/`SUPERSEDED` lifecycle,
validate-then-store persistence, `geometry(Polygon, 4326)` via a small dependency-free `Geometry`
`TypeEngine` (no `geoalchemy2` added). Migration `0010` applied and verified live via `psql`.

**B4 Slice 2 — Geometry Validation & Real Geometry Adapter is implemented and live-verified**
(`docs/adr/ADR-022`): real structural WKT `POLYGON` validation
(`app/contexts/spatial/domain/geometry_validation.py` — ring closure, minimum point count,
coordinate bounds, OGC winding order via the shoelace formula, EWKT SRID verification — all pure
Python, no GIS dependency added); ADR-022's creator-or-governance authorization is now enforced
in `SpatialService` (mirroring `ParcelService._can_mutate`/`_effective_authority` exactly),
including delegated governance (ADR-011, unchanged) and an unconditional archived-parcel block
(`409`, no override for any role, mirroring ADR-015); `ParcelExistencePort` extended to
`get_parcel_authority` returning `ParcelAuthorityInfo` (`tenant_id`/`created_by`/`status`) in one
round-trip; a real `GeometryPort` implementation (`RealGeometryAdapter`, in
`app.contexts.spatial.adapters`) is wired into Registry via `app/main.py`'s
`dependency_overrides` only — Registry's own code was not touched and still imports nothing from
Spatial. The persist-ordering bug Slice 1 shipped with (superseding the old geometry *before*
validating the new one, which could strand a parcel with no ACTIVE geometry on a validation
failure) was fixed: validation now happens before any persistence. 29/29 Spatial tests pass
(148/148 full suite); `ruff`/`mypy` clean. **Full live verification performed, not deferred**:
real Postgres/PostGIS/Keycloak/RLS (fail-closed under `landvault_app`, confirmed 0 rows
cross-tenant, DELETE denied), all four authorization tiers (creator/governance/delegated/
`super_admin` cross-tenant), archived-parcel `409` for every tier, cross-tenant `404`, malformed/
clockwise-wound geometry `400`, the real Registry↔Spatial `GeometryPort` seam (a genuine
`geometry_id` accepted, an unknown one and a foreign parcel's rejected), audit chain integrity
(`verify_chain()` → `True` over the platform's full history), and a full container rebuild +
health-check — see `docs/B4_VERIFICATION_CHECKLIST.md` for the complete evidence log. One
pre-existing infra gap, unrelated to Slice 2's own code, was found and fixed as a live-verification
blocker: `infra/docker/docker-compose.yml`'s `backend` service overrode `DATABASE_URL` for
container-to-container networking but not the three `KEYCLOAK_*` URLs, which leaked `.env`'s
host-oriented `localhost` values — real Keycloak was unreachable from inside the container. Fixed
by adding the same kind of override already used for `DATABASE_URL`.

**B4 Slice 2 has completed architectural review and is accepted; its architecture is frozen under
ADR-022** — no further change to Spatial's authorization model, geometry validation, or the
Registry↔Spatial `GeometryPort` seam lands without a new ADR referencing ADR-018/019/022. The
real `GeometryPort` production integration (`RealGeometryAdapter`, wired via `app/main.py`'s
`dependency_overrides`) is recorded as a permanent architectural milestone — the first time this
platform has connected two bounded contexts' real (non-placeholder) implementations across the
ports-and-adapters seam established in ADR-002/ADR-016. The Keycloak container-networking
correction (`infra/docker/docker-compose.yml`) is recorded in `docs/B4_VERIFICATION_CHECKLIST.md`'s
Slice 2 section as this release's operational fix.

**ADR-021 — Spatial Conflict Detection & Controlled Cross-Tenant Intelligence is now drafted**
(`docs/adr/ADR-021-spatial-conflict-detection-and-controlled-cross-tenant-intelligence.md`),
architecture only, no implementation — the constitutional doctrine `docs/B4_THREAT_MODEL.md` TB5
required before overlap/duplicate-geometry detection could be designed: which single component
may perform a cross-tenant geometry read (Controlled Platform Authority, `docs/
ENGINEERING_RULES.md` rule 9), the six-category conflict classification model (no conflict /
boundary overlap / duplicate / near duplicate / suspicious pattern / confirmed conflict — model
only, no algorithm), the minimal-disclosure default to an ordinary registrant vs. a governance
role's narrowly-extended reach, the Registry/Spatial ownership split (conflict detection is a
Spatial-internal service, not a new bounded context and not something Registry absorbs), and full
audit requirements. **Not yet accepted. B4 Slice 3 is not authorized** — no overlap detection,
duplicate detection, fraud detection, conflict scoring, AI analysis, spatial search, or risk
engine exists anywhere in this codebase yet, and none begins until ADR-021 is reviewed and
explicitly accepted, the same discipline every prior escalation in this codebase has followed.

**Pre-Slice-3 governance package complete** (2026-07-24, `docs/
B4_SLICE3_PREIMPLEMENTATION_REVIEW.md`): a full architectural review of ADR-021 found no
amendment required and no contradiction against ADR-017/018/019/022 or any frozen B1–B3 ADR.
**SCDS-001 — Spatial Conflict Detection Specification** (`docs/
SCDS-001-spatial-conflict-detection-specification.md`, an engineering specification beneath
ADR-021, not an ADR) converts ADR-021's architecture into implementation guidance — an 11-item
conflict taxonomy, 4-level severity scale, risk-scoring extension points (unimplemented), a full
disclosure matrix per participant tier, and a refined Controlled Platform Authority mechanism
shape — with no algorithm, index, or code. **Platform Intelligence** is now named as a standing
architectural layer, not a bounded context (`docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md`) — a
four-part test for "is this capability Platform Intelligence" (cross-context/cross-tenant read,
produces a finding never a domain mutation, one named Controlled Platform Authority exception,
narrow signal-only downstream consumption), with the Conflict Engine (ADR-021) as its first
proposed instance and the Trust Engine (B7, unbuilt) recognized retroactively as its shape's first
example. A Marketplace Programme Phase 0 recommendation is recorded (`docs/
MARKETPLACE_DISCOVERY_AND_PLANNING.md`, planning only — no code) — the scoping question of
whether "Marketplace" (Wallet/Payments/Escrow/Ratings/Enterprise Dispatch) is an expansion of
`docs/REBUILD_PLAN.md` context #10 or one or more new contexts is left open for that programme's
own discovery, not decided here. A constitutional recommendation for the eventual LV-000 is logged
(`docs/CONSTITUTIONAL_RECOMMENDATIONS.md`) — Platform Intelligence's cross-context observation
boundary, restating `docs/ENGINEERING_RULES.md` rule 9 at constitutional altitude — recorded, not
adopted; LV-000 does not exist yet. **None of this authorizes B4 Slice 3.** It remains gated on
ADR-021's explicit acceptance.

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
