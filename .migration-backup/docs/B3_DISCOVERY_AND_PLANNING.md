# B3 Discovery & Planning — Registry (Property/Parcel Bounded Context)

**Status:** Planning only. No B3 production code has been written. This document is the
Phase 0 deliverable required before implementation begins — presented for review and
explicit approval, per the B3 program initiation instruction.

**Date:** 2026-07-18

---

## 0. Framing

`docs/REBUILD_PLAN.md` §1 already assigns B3 = **Registry** (canonical parcel aggregate,
ownership history, parcel numbering), and `docs/PHASE_GATES.md` already froze "one sprint per
bounded context, 13 total, dependency-ordered" as the sequencing model. Treating B3 as a new
governed program means fresh rigor and a fresh review of the frozen baseline before writing
code — it does not mean re-litigating which bounded context comes next; that was already
decided in Phase 0/1 planning. `docs/adr/ADR-005-property-registry-data-model.md` already
specifies the target data model in real detail (the `LandVault` aggregate, immutable-field
invariants, atomic allocator, ownership-transfer authorization) — this is authoritative prior
art to build from, not to redesign.

## 1. Review of the Frozen Baseline

- **ADR-009 (B1 freeze):** Identity/Auth primitives Registry will consume — PDP/PEP,
  `ExecutionContext`, Unit-of-Work, audit chain, RLS session-variable mechanism, RBAC role
  set. None of this is touched by B3.
- **ADR-010 (Tenant aggregate):** every Registry table must carry `tenant_id` and follow the
  same RLS shape (`tenant_id = current_setting('app.tenant_id') OR is_super_admin`).
- **ADR-011 (Delegated administration):** not immediately needed by Registry's own
  authorization (Registry uses resource-based checks, not role delegation), but the derived-
  authority principle is available later if Registry ever needs it (e.g., delegating survey
  assignment authority) — not assumed required now.
- **ADR-012 (B2 freeze):** confirms nothing further changes in Identity.
- **Current repository state** (verified by reading, not assumed): only
  `backend/app/contexts/identity/` exists as a bounded context. Frontend is still the F0
  scaffold (default Next.js page, one `Button` component, no auth integration). Terraform has
  only version pins, no provider/resources. **The running Postgres image is already
  `postgis/postgis:16-3.4`** (`infra/docker/docker-compose.yml`) — PostGIS is available with
  zero infrastructure lift, just needs `CREATE EXTENSION IF NOT EXISTS postgis` confirmed in
  a migration.

## 2. B3 Objectives (and why B3, not B2)

B2 extended *who can act* (tenant governance, delegation). B3 introduces *the first real
business-domain object* — a clean bounded-context boundary consistent with this codebase's
existing hexagonal/ports-and-adapters architecture (ADR-002), not a continuation of Identity.

- **Business:** enable actual parcel registration — without Registry, the platform has
  authentication but no product.
- **Technical:** one canonical parcel aggregate (per ADR-005, not two competing ones like
  Base44's audited defect), atomic parcel-number allocation, immutable-field invariants,
  append-only ownership history.
- **Government-readiness:** tenant/country-scoped parcel numbering, an audit trail for every
  parcel mutation (reusing the existing hash-chained kernel audit log, not a new one).
- **Security:** real actor-identity checks on every mutating command — this is a *named,
  confirmed historical defect* (ADR-005: "the PDP resource descriptor never carried
  `created_by`... any principal holding a create-tier role could update... any parcel in their
  tenant"), not a hypothetical hardening exercise.
- **Scalability:** the atomic allocator must hold under real concurrent registration load —
  a fraud/integrity vector, not a performance nicety.
- **Operational:** none required for B3 itself; legacy-data import tooling is explicitly a
  later concern per REBUILD_PLAN.

## 3. B3 Scope

### In scope (this is B3)

- `LandVault` parcel aggregate: immutable core fields (`registry_id`, `parcel_number`,
  `tenant_id`, `country_code`, `created_at`, `origin`).
- Atomic parcel-number allocator (Postgres-native — see Architectural Risks, §4).
- Mutable commands: `UpdateLocation`, `UpdateOwnershipContact`, `RecordOwnershipTransfer`
  (append-only `ownership_history`), `UpdateSurvey`, `UpdateCommunityData`, `Archive`
  (one-way).
- `UpdateGeometry` as a **port only** — a clean interface B4 (Spatial Intelligence) will
  later implement; B3 does not build real spatial validation.
- Real actor-identity authorization (`created_by` / assigned surveyor / field agent) as
  defense-in-depth alongside the existing role-based PDP checks — fixing the ADR-005 defect.
- RLS + kernel audit-chain integration, reusing the exact patterns from migrations `0001`–`0006`.
- Basic CRUD/query API (create, get, list/search within tenant, mutation commands, archive).
- Test suite at the same rigor as B1/B2: in-memory fakes + live-Postgres verification for
  every slice.

### Out of scope for B3 (explicit, to prevent creep)

| Category | Status | Why |
|---|---|---|
| Identity | Frozen (ADR-009/010/011/012) | Registry consumes it, never modifies it |
| GIS / Spatial Intelligence | Deferred to B4 | Registry defines the port; B4 implements real validation |
| Evidence | Deferred to B5 | Registry leaves extension points, doesn't build upload/WORM |
| Survey | Deferred to B6 | Licensing/assignment is its own context |
| Payments | Deferred to B11 | No transactions exist yet to bill for |
| Notifications | Not started, no owner yet | Known gap since B2; needs its own scoping pass, not folded into B3 |
| AI | Deferred (ADR-008) | Advisory-only, depends on Trust Engine (B7), which depends on B3/B4/B6 |
| Public Portal | Deferred (F9, later frontend milestone) | Needs F1 (Auth UI, not started) first |
| Government Operations (dashboards/approvals) | Deferred to B8/B13/B14 | Workflow + Security/Ops concern |
| Administration | Frozen | Identity's admin surface already covers governance; no new admin capability needed |
| Developer Experience | Not a dedicated initiative | Maintain existing tooling standards, no new program |
| Infrastructure | Mostly out of scope | Terraform/cloud provisioning remains unstarted; B3 only needs the PostGIS extension confirmed |

## 4. Architectural Boundaries

**Frozen, never touched by B3:** ADR-009/010/011/012 in full, `backend/app/kernel/`,
`backend/app/contexts/identity/`, migrations `0001`–`0006`, Keycloak config, the RBAC role set
(`value_objects.py` — "a new role is an ADR amendment, not a string literal," and that rule
applies to Registry too).

**May be extended:** the kernel may gain new *shared* utilities Registry genuinely needs (e.g.
a generic atomic-sequence helper, if truly cross-cutting) — additive only, never a change to
`audit.py`/`uow.py`/`context.py`/`authorization/`'s existing public contracts.

**Must be reused, not reinvented:** PDP/PEP (`require_auth`/`require_role`/`enforce`),
Unit-of-Work (`get_db_session`), the kernel `audit()` function, the declarative ORM `Base` +
`migrations/env.py` pattern, ports & adapters layering (ADR-002), and the
RLS-in-the-same-migration + least-privilege-grant pattern used in every migration since `0001`.

**New bounded context introduced:** Registry (B3) only. Spatial Intelligence's *real* logic is
explicitly not built here — only the port it will later implement.

### Architectural risks identified before implementation

1. **The atomic allocator cannot be a literal port of Emergent's mechanism.** ADR-005 says
   Emergent's Mongo-native `find_one_and_update` with `$inc`/upsert is reused "near-verbatim"
   — but this platform is Postgres (ADR-003), not Mongo. A `SEQUENCE` object or a
   `SELECT ... FOR UPDATE` row-locking pattern is the real Postgres-native equivalent; which
   one, and its exact concurrency guarantees, is a genuine design decision requiring its own
   ADR, not an assumption.
2. **Ownership-history representation is undecided.** ADR-005 describes an append-only
   `ownership_history[]` (array notation) — a JSONB array column (matching the `roles` column
   pattern already used on `identity_users`) is the simplest option; a separate relational
   table is more queryable and more consistent with "new tenant-scoped data needs its own RLS
   policy." Needs an explicit decision, not a default.
3. **Actor-identity authorization is the highest-security-risk piece of B3.** This is a
   *confirmed historical vulnerability* (ADR-005), not speculative hardening — it needs
   adversarial live testing (a non-owner attempting to mutate a parcel they don't own must be
   denied), at the same rigor as B1 Phase 9's adversarial security validation.
4. **No premature multi-country abstraction.** `country_code` is already an immutable field
   per ADR-005; government-specific numbering schemes likely vary by country, but building
   that abstraction now (Nigeria-first, per every other doc in this repo) would be speculative.

## 5. Proposed ADR Roadmap (not created — proposed for review)

| ADR | Purpose | Depends on | Why required |
|---|---|---|---|
| **ADR-013** — Registry Aggregate & Schema | `LandVault` table shape, ownership-history representation decision, geometry-column decision, migration numbering (`0007`+) | ADR-005 (spec), ADR-009/010 (RLS/tenant shape) | New schema + a real, undecided design choice (§4.2) |
| **ADR-014** — Atomic Parcel-Number Allocation Strategy | Postgres-native concurrency-safe allocator, with the Mongo→Postgres translation reasoning made explicit | ADR-013 | Genuine architectural translation, not a port; must document the concurrency guarantee |
| **ADR-015** — Registry Authorization Model | How actor-identity checks combine with PDP/PEP role checks as defense-in-depth | ADR-013, ADR-009 | Fixes a confirmed historical defect (ADR-005); needs its own decision record given the security stakes |
| **ADR-016** (open question) — Spatial Intelligence Port Boundary | Formalizes the Registry↔Spatial seam | ADR-013 | Could be written now (B3.4) or deferred to B4's own kickoff — flagged as a decision for the approval discussion, not presupposed |

None of these change ADR-009/010/011/012 — they extend the platform the same way ADR-010/011
extended B1's baseline.

## 6. Repository Assessment

**Strengths:** the Identity context is a genuinely clean reference implementation now (ports &
adapters, RLS-in-same-migration, audit-chain, Unit-of-Work) — B3 has a proven template to
replicate, not invent fresh. PostGIS is already the running database image. Test discipline
(fakes + live-Postgres verification, never marking something done without an observed pass)
is mature and directly reusable.

**Weaknesses / technical debt:**
- Frontend is still the F0 scaffold only — no auth integration, no generated API client. Not
  blocking for B3's backend work, but F2 (Registry+Spatial UI) needs F1 (Auth UI, not started)
  first.
- No committed Keycloak realm export (inherited limitation, ADR-009, still open).
- No dedicated secret-in-logs audit (inherited, still open).
- Terraform is effectively empty — every verification so far has been against local Docker
  Compose only. Fine for continued backend work, a growing gap before any real pilot.
- **No CI/CD verification has been observed or confirmed this session.** `docs/DOD.md` Tier 1
  requires "CI/CD pipeline passes" — whether GitHub Actions actually runs this test suite on
  push is unconfirmed. Worth checking before B3 code accumulates further.

**Refactoring opportunities (noted, not acted on):** `AdminService` now covers invitations,
tenants, and delegations in one class — still cohesive (all "Identity admin" concerns), but
worth watching if Registry grows a comparably-sized admin surface later.

## 7. Gap Analysis (current platform vs. long-term vision)

**Critical:** no Registry capability (this is what B3 addresses); no Spatial Intelligence
(B4); no Evidence pipeline (B5).

**High:** no Survey context (B6); no Workflow engine (B8); no Notifications capability at all
(invitations/tenant/delegation events are currently silent beyond API/audit log); CI/CD status
unconfirmed; no cloud infrastructure provisioned.

**Medium:** no Trust Engine (B7, correctly sequenced after Registry/Spatial/Survey); no
Economic/Billing (B11, no transactions exist yet); no Community Trust (B9) or Inheritance &
Customary Law (B10); frontend beyond the F0 scaffold.

**Low:** Knowledge Graph (B12, late-stage read-projection); AI integration (advisory-only,
depends on Trust Engine); multi-cloud/multi-region infrastructure.

**Government-readiness gaps specifically:** no parcel-numbering scheme validated against real
Nigerian land-registry conventions (needs domain/stakeholder input, not just engineering); no
compliance/legal review of PII handling for Inheritance's future scope; no accessibility audit
of the frontend (none exists yet to audit).

## 8. B3 Phase Breakdown

Proposed as four slices, mirroring B2's own 4-slice pattern (each individually reviewed and
accepted before the next begins):

### Slice B3.1 — Core Parcel Aggregate & Schema
- **Objective:** `LandVault` aggregate with immutable core fields, basic CRUD, RLS, audit
  integration.
- **Business value:** the platform can register a parcel and prove who created it and when.
- **Architecture impact:** first new bounded-context folder, first migration past `0006`,
  first real test of whether the kernel generalizes beyond Identity.
- **Security impact:** RLS ships in the same migration; reuses PDP/PEP, no bespoke auth.
- **Dependencies:** none beyond the frozen baseline.
- **Complexity:** Medium.
- **Deliverables:** domain aggregate, migration, repository port+adapter+fake, application
  service, API routes, tests.
- **Success/exit criteria:** live-Postgres RLS proven fail-closed and cross-tenant-invisible,
  same rigor as every B1/B2 slice.
- **ADR requirement:** ADR-013.

### Slice B3.2 — Atomic Parcel Numbering
- **Objective:** collision-free parcel-number allocation under real concurrent load.
- **Business value:** prevents duplicate parcel numbers — a direct fraud/integrity vector.
- **Architecture impact:** the Postgres-native replacement for Emergent's Mongo pattern.
- **Dependencies:** B3.1.
- **Complexity:** Medium-High (concurrency correctness is harder to verify than CRUD).
- **Deliverables:** allocator, concurrency test (parallel attempts, assert zero duplicates),
  live verification under real concurrent load — not simulated.
- **Success/exit criteria:** N concurrent live registration attempts produce N unique
  sequential numbers, zero duplicates.
- **ADR requirement:** ADR-014.

### Slice B3.3 — Ownership Transfer & Mutation Commands
- **Objective:** the remaining commands, with real actor-identity authorization — fixing the
  confirmed ADR-005 defect.
- **Business value:** the actual lifecycle operations a registry needs; closes a named
  historical vulnerability.
- **Security impact:** high — must be adversarially tested live (non-owner mutation attempt
  denied), same rigor as B1 Phase 9.
- **Dependencies:** B3.1, B3.2.
- **Complexity:** Medium-High.
- **ADR requirement:** ADR-015.

### Slice B3.4 — Geometry Port & Spatial Seam
- **Objective:** geometry column + an explicitly-a-stub validation port for B4 to implement.
- **Business value:** unblocks B4 without requiring Registry rework later.
- **Complexity:** Low — deliberately minimal, the point is not building real spatial logic.
- **Dependencies:** B3.1.
- **ADR requirement:** ADR-016, or deferred to B4 (open question, §5).

**Recommended execution order:** B3.1 → B3.2 → B3.3 → B3.4, each paused for review before the
next begins. B3.4 could instead run right after B3.1 (low complexity, unblocks B4 planning
sooner) — flagged as a decision for the approval discussion, not presupposed here.

## 9. Architectural Risks Summary

- Atomic allocator needs genuine Postgres-native design work, not a port of the Mongo pattern.
- Ownership-history storage shape needs an explicit decision (§4.2).
- Actor-identity authorization must be adversarially tested — a confirmed historical
  vulnerability, not a hypothetical.
- CI/CD verification status is unconfirmed and should be checked before B3 accumulates more
  code that may not actually be running in CI.
- No cloud infrastructure exists — B3 proceeds against local Docker Compose (consistent with
  B1/B2), but this gap needs addressing before any real pilot.

## 10. Recommended Overall Execution Order

1. Confirm/establish CI verification status (small, high-leverage, currently unknown) —
   recommend resolving this before or alongside B3.1, not deferred further.
2. B3.1 → B3.2 → B3.3 → B3.4 as above.
3. No reordering proposed for B4 onward — REBUILD_PLAN's existing sequencing (Spatial →
   Evidence → Survey → Trust Engine → Workflow → ...) stands.

---

## Approval Checkpoint

No B3 production code has been written. This document is presented for review of: the
objectives (§2), the in/out scope (§3), the architectural boundaries and risks (§4, §9), the
proposed ADR roadmap (§5), the phase breakdown (§8), and the recommended execution order
(§10). Waiting for explicit approval before beginning any B3 implementation.
