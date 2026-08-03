# CLAUDE.md

## One constitution

As of 29 July 2026 there is exactly one governing constitution: **LV-000 Edition v1.8, Working
Edition, Revision H**, at `docs/LV-000-constitution.md`. The authored v1.7 no longer governs
anything. The adopted v1.0 continues *through* v1.8 by incorporation (v1.8 Article II §4) and its
principles remain in force verbatim; it is preserved unmodified at
`docs/LV-000-constitution-v1.0-adopted.md`.

Cite the Constitution **with its edition** — `LV-000 v1.8, Article X §3` — never by bare article
number. Bare article numbers are ambiguous across the historical lineages, and that ambiguity is
what reached shipped code in the first place. See `docs/GOVERNANCE_BASELINE.md` for the full
reconciliation record.

AquaSavannah LandVault — a Nigerian land-registry/verification platform, rebuilt from scratch on Claude Code after full security/architecture audits of two prior implementations (`docs/audits/`). **Current status: B1, B2, and B3 are complete, verified, and frozen (tagged `b2-freeze`, `b3-freeze`) — see `docs/adr/ADR-009-b1-platform-freeze.md`, `docs/adr/ADR-012-b2-platform-freeze.md`, `docs/adr/ADR-017-b3-platform-freeze.md`, `docs/audits/B2_RELEASE_NOTES.md`, `docs/audits/B3_RELEASE_NOTES.md`. B3 (Registry) is the current production architectural baseline: the Parcel aggregate, atomic parcel numbering, creator-aware mutation authorization (closing a confirmed ADR-005 defect), a geometry port boundary for future spatial capability, and — as of 2026-07-31 — append-only ownership and status assertion history (`docs/adr/ADR-023-registry-ownership-and-status-history.md`, Accepted — Implemented; migration `0011`) — see "B3 status" below. **`docs/ENGINEERING_RULES.md` #10 (the non-adjudication automated check, LV-000 v1.8 Article IV §4) is now implemented** (Phase 9, `docs/PHASE-9_IMPLEMENTATION_PLAN.md` / `docs/PHASE-9_ACCEPTANCE_PACKAGE.md`, PR #7, merged `88448e4`) — two independent scanning layers (static AST source scan, real API-response-content scan) running inside the existing required `pytest` CI job. **170/170 backend tests passing, 1 skipped** (the live-only Postgres rollback rehearsal, `backend/tests/live/`). B4 (Spatial Intelligence) has begun and progressed past discovery: Slices 1 and 2 are accepted and frozen under ADR-022, ADR-021 (Spatial Conflict Detection) is drafted and awaiting acceptance, and Slice 3 remains unauthorized — see "B4 status" below. B5 (Evidence) has begun: `docs/adr/ADR-026-evidence-domain-model.md` is **Accepted**, and Slice B5.1 (`StoragePort`) and Slice B5.2 (`EvidenceRecord` aggregate, migration `0012`) are implemented and live-verified — **on branch `feat/b5.2-evidence-domain-model`, not yet merged to `main`** — see "B5 status" below.**

Docker Compose (Postgres + Keycloak + backend + frontend) has been booted end-to-end and is the normal way this repo is verified locally now — see `docs/audits/B1_INFRASTRUCTURE_VERIFICATION.md` for the full live-infrastructure validation this passed (migrations, RLS, JWT, rate limiting, audit chain, adversarial security checks); Docker remains the local-development target regardless of the platform-baseline note below. Cloud (staging/production) environments do not exist yet. Delivery-platform infrastructure decisions (storage, identity, payments, compute at the time, secrets manager) are captured at `docs/adr/ADR-024-delivery-platform-and-infrastructure-decisions.md` (**Accepted**, 2026-07-30). **The identity provider and compute/cloud provider named there (Keycloak, AWS) were superseded the same day** by `docs/adr/ADR-025-supabase-platform-baseline.md` (**Accepted**, 2026-07-30): **Supabase Auth is the production identity provider — Keycloak is a retired evaluation**, with no future implementation owed against it (the previously-tracked `start-dev`-to-production hardening task is moot, not deferred). **Supabase-hosted PostgreSQL**, **Supabase Storage** (primary; Cloudflare R2 remains the WORM-grade escalation adapter), and **Supabase Edge Functions** (additive only — the existing FastAPI backend, ADR-002, is unchanged) are the production platform target, with **Vercel** as frontend hosting and **Docker retained for local development only** (Postgres, backend, frontend). Keycloak and the AWS Terraform provider block are preserved as historical artifacts, not deleted, pending a future archival decision.

**`docs/LV-000-constitution.md`** — **The LandVault Constitution, Edition v1.8, Working Edition, Revision H. RATIFIED and in force. Supreme.** Every other document in this index is subordinate to it. Read it before proposing any change to governed behaviour. The Prime Directive is Article I §3: *LandVault preserves and verifies land evidence. It does not decide who owns land.* This Edition consolidates the previously-adopted v1.0 (architecture lineage — Controlled Platform Authority at Article IX §3, Bounded Context Sovereignty at Article V, Trust Network Doctrine at Article VI; preserved unmodified at `docs/LV-000-constitution-v1.0-adopted.md`) and the authored v1.7 (values lineage; retired, historical only) into one instrument. See `docs/GOVERNANCE_BASELINE.md` for how the two were reconciled, and the Constitution's own Schedule 1 for which adopted principles are restated versus incorporated by reference only.

**`docs/ARCHITECTURE_HANDBOOK.md` (v1.0)** is the consolidated engineering reference — platform philosophy, full architecture diagram, DDD vocabulary, engineering rules index, security model, programme governance lifecycle, documentation hierarchy, future-programme surveys, architectural evolution, and engineering culture, each pointing to its authoritative source document. It is not an ADR and decides nothing new, and it is subordinate to LV-000 (LV-000 v1.8, Article XIII §1); read it after the Constitution to orient, then follow its links for the actual decision.

**`docs/PLATFORM_STRATEGY.md`** (2026-07-25) sits one layer below the Handbook — vision, official positioning, the five-layer platform model (Identity/Land Intelligence/Marketplace/Enterprise/Government), the "Trust Platform before Software Platform" principle (now constitutional — LV-000 Article IX, Section 1), and network-effects/flywheel reasoning. Eight further planning-only documents sit beneath it, each ending in its own Approval Gate with no implementation authorized: `docs/PARTNER_PROGRAMME_STRATEGY.md`, `docs/ENTERPRISE_PROGRAMME_STRATEGY.md`, `docs/GOVERNMENT_PROGRAMME_STRATEGY.md`, `docs/DEVELOPER_PLATFORM_STRATEGY.md`, `docs/COMMERCIAL_ARCHITECTURE.md`, `docs/OPERATING_MODEL.md`, `docs/TRUST_FRAMEWORK.md`, `docs/NETWORK_GROWTH_STRATEGY.md` — plus an extension to the existing `docs/MARKETPLACE_DISCOVERY_AND_PLANNING.md` naming candidate domain concepts (Job, Assignment, Escrow, Wallet, Rating, Dispute, etc.). **None of this authorizes any new bounded context, ADR change, or code** — B1–B4 remain exactly as documented below, and B4 Slice 3 remains unauthorized.

**`docs/LANDVAULT_BIBLE_VOLUME_I_EXECUTIVE_OVERVIEW.md`** (2026-07-27) is the LandVault Bible™ Volume I — a 15–25 page executive narrative (Problem/Vision/Mission/Philosophy/Architecture/Five-Layer Model/Trust Ecosystem/Commercial Vision/Governance/Roadmap/Strategic Position) written for governments, investors, executives, enterprise clients, and procurement teams. **Explanatory and non-normative only** — it synthesizes LV-000, the Handbook, and Platform Strategy in plain executive prose, decides nothing, and is corrected in favor of any document it summarizes if the two ever differ. Deliberately avoids the "Uber for Land Verification" marketplace framing in its external positioning language, per explicit instruction, in favor of the trust/governance/infrastructure framing throughout this file.

**`docs/LANDVAULT_BIBLE_VOLUME_II_PRODUCT_STRATEGY_AND_ENTERPRISE_DEFINITION.md`** (2026-07-28) expands Volume I into full market analysis (Nigeria/Africa/global, deliberately hedged — no fabricated market-size figures, per LV-000's "truth over assertion" value), Product Philosophy, a fully expanded Five-Layer Model (Purpose/Capabilities/Stakeholders/Revenue/Dependencies/Evolution per layer), a complete Trust Network framework (11 participant categories), Marketplace as enterprise strategy, every commercial revenue stream, competitive positioning against 7 categories of alternative, a long-term roadmap through continental expansion (explicitly not authorized), and strategic conclusions. **Explanatory and non-normative**, same standing as Volume I.

**`docs/LV-013-market-intelligence-report.md`** (2026-07-29) is a genuine quantitative research report, not synthesized narrative — every figure was checked via live web search/fetch on 2026-07-29 and tagged VERIFIED (with source)/ESTIMATE/NOT VERIFIED. Real, sourced findings include: Nigeria's National Land Digital System (signed with the World Bank 11 Sept 2024, 90%+ of land reported unregistered, ~$300B potential capital locked); ~65% of Nigerian civil court cases are land-related (NIALS 2023, via secondary citation); population/urbanization/GDP/remittance figures; SURCON's structure (59 Council members — but its total registered-surveyor count could **not** be found and is flagged as a research gap, not guessed at); and 7 international benchmarks (Rwanda, Estonia, UK, Singapore, India, Kenya, Brazil) with specific verified statistics each. Part IX (TAM/SAM/SOM) explicitly declines to invent a market-size figure where no defensible input exists, recommending commissioned primary research instead. **Supplements, does not replace, LV-000/Handbook/Platform Strategy/Bible I–II — introduces no architecture, ADR, or governance.**

## Precedence

1. `docs/LV-000-constitution.md` — the Constitution, Edition v1.8 Revision H. Supreme.
2. The Bible volumes, LV-001 – LV-017 (see the Constitution's Schedule 3 for the full register — only the LV-013 slot, the protected Market Intelligence Report, exists as a file in this repository today).
3. Ratified ADRs in `docs/adr/`.
4. `ENGINEERING_RULES.md`.
5. `PLATFORM_INTELLIGENCE_ARCHITECTURE.md` and the architecture documents.
6. `REBUILD_PLAN.md`, `EXECUTION_PLAN.md`, `PHASE_GATES.md`, `DOD.md`.
7. Implementation and code.

This file is a **pointer, not the source of truth**. Where it conflicts with a document it points to, that document wins and this file is corrected.

On *current state* — what is frozen, what tests pass, what has shipped — the repository and an observed test run govern. On *what to build and how*, the hierarchy above governs. Do not confuse the two.

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

## B5 status (Evidence) — ADR-026 Accepted; Slices B5.1–B5.2 implemented, live-verified, not yet merged

`docs/adr/ADR-026-evidence-domain-model.md` is **Accepted**. `docs/PHASE-B5_IMPLEMENTATION_PLAN.md`
is the accepted Phase 1–5 planning package; `docs/PHASE-B5-SLICE1_ACCEPTANCE_PACKAGE.md` and
`docs/PHASE-B5-SLICE2_ACCEPTANCE_PACKAGE.md` are the per-slice evidence records.

**Slice B5.1 — `StoragePort`** (`app/contexts/evidence/ports.py`): the provider-agnostic
object-storage Protocol (`put`/`get`/`list_keys`/`put_immutable`/`worm_grade`), governed by
`docs/adr/ADR-024-delivery-platform-and-infrastructure-decisions.md` D1 and `docs/adr/
ADR-025-supabase-platform-baseline.md` E3 (both already Accepted — this slice implements, not
redecides). Only an in-memory fake (`backend/tests/fakes/storage.py`) exists — no real Supabase
Storage or Cloudflare R2 adapter, since both require a new external dependency
(`docs/ENGINEERING_RULES.md` rule 5, needs explicit approval) and live credentials this programme
does not yet have (rule 7).

**Slice B5.2 — `EvidenceRecord` domain model** (`app/contexts/evidence/{domain,adapters,
application,dependencies.py}`, migration `0012`): the aggregate (`RECEIVED → HASHED → SEALED`
lifecycle, legal hold, storage/provenance fields), `EvidenceRepository` port + Postgres/in-memory
adapters, `EvidenceService`, and DI wiring — no upload endpoint, no hash computation, no physical
WORM sealing, no chain-of-custody or legal-hold *workflow*, all explicitly deferred to later
slices per ADR-026's own scope. 34 new tests, `ruff`/`mypy` clean, 215/215 passing (1 pre-existing
skip). Migration `0012` live-rehearsed against Docker Postgres: up/down/up repeatability, RLS
positive/negative isolation, `super_admin` bypass, mutable `UPDATE` (this table is a guarded
mutable aggregate root, matching `parcels`' own shape — not append-only like migration `0011`'s
history tables), `DELETE` denied at the grant level.

**Not yet merged.** Implemented on branch `feat/b5.2-evidence-domain-model` (commit `50b970d`),
pushed to `origin`. No pull request exists yet as of this note — opening one requires GitHub
authentication (`gh` CLI or a token) not available in this environment; the branch is ready for a
PR to be opened manually. **B5.3 (upload endpoint) is not authorized and has not begun.**

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
| The execution instrument — ordering and content of delivery work beneath REBUILD_PLAN's gates (Revision H, GD-004) | `docs/EXECUTION_PLAN.md` |
| Process/quality gates per phase, the Claude Code Loop, standing review questions | `docs/PHASE_GATES.md` |
| Definition of Done (Feature / Sprint / Product tiers) | `docs/DOD.md` |
| Full engineering rules, incl. when to stop and ask a human | `docs/ENGINEERING_RULES.md` |
| Why a specific architectural decision was made | `docs/adr/` |
| The audit findings everything above is derived from | `docs/audits/` |
| ADR-023 live-rollback acceptance evidence; Engineering Rules #10 implementation plan and acceptance evidence | `docs/PHASE-8_ACCEPTANCE_PACKAGE.md`, `docs/PHASE-9_IMPLEMENTATION_PLAN.md`, `docs/PHASE-9_ACCEPTANCE_PACKAGE.md` |
| Consolidated governance/implementation-maturity snapshot | `docs/REPOSITORY_STATUS_REPORT.md` |

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
