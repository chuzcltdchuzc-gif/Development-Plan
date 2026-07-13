# AquaSavannah LandVault — Rebuild Plan (Backend / Frontend / Feature tracks)

**v4** — migrated to disk from planning conversation; stack updated to Next.js (frontend), Keycloak/Auth0 (identity, PDP/PEP/PIP retained), Docker+Terraform+AWS/Azure (infrastructure), per Operator decision. Sprints are now formally one-per-bounded-context — see `docs/PHASE_GATES.md` for how the Phase 0–12 gate model governs progression between them.

Source material: full architecture/security audits of `landsecure-registry` (Base44 build) and `landverify-nigeria-101-NEW` (Emergent build) — see `docs/audits/`.

---

## 0. Target stack decision

| Layer | Decision | Why |
|---|---|---|
| Frontend | **Next.js + TypeScript** (App Router), Tailwind + shadcn/ui | Reuses the shadcn/ui component set both prior apps independently converged on; App Router gives file-based routing and room for SSR on public verification pages later |
| Backend | **Python / FastAPI**, DDD/hexagonal layering (domain → ports → adapters → application → api) | Emergent's bounded-context code is genuinely well-designed where it isn't undermined by its parallel legacy layer |
| Database | **PostgreSQL + PostGIS** (Identity role/tenant mapping, Registry, Spatial, Survey, Economic), self-managed (not Supabase-managed) | Nearly every critical bug in both audits traced back to not having real ACID transactions and native RLS — Postgres closes that bug class structurally |
| Object storage | S3-compatible, **Object Lock in Compliance mode**, for Evidence binaries | Both prior "WORM" implementations were fake at the storage layer (chmod meaningless under root; ephemeral `/tmp` by default) |
| Identity (authentication) | **Keycloak** (default) or **Auth0**, issuing OIDC/JWT identity tokens | Removes an entire class of custom-auth bugs found in both audits (password handling, MFA, OAuth flows, key rotation) by delegating to a proven IdP instead of reimplementing it |
| Authorization | **PDP/PEP/PIP engine retained**, ported from Emergent's design — verifies IdP-issued JWTs against the IdP's JWKS (not a self-issued KeyStore), applies fail-closed policy decisions to every route, no parallel/legacy auth path | This was the one subsystem the Emergent audit found structurally sound — the defect was letting a second, undocumented session-cookie auth system exist beside it. Removing the parallel system and keeping this one fixes the root cause |
| Graph store (Knowledge Graph) | Neo4j or Postgres + Apache AGE, fed by event projection | Real multi-hop relationship queries; never a source of truth, always rebuildable |
| Payments | Paystack (Nigeria) + Stripe (diaspora) | Matches audited-correct webhook signature verification code from Emergent, reused near-verbatim |
| Infrastructure | Docker (local + CI), Terraform (all cloud resources as code), AWS or Azure | Repeatable environments across dev/staging/production; closes the "works on my machine" and untracked-manual-config gaps found in both audits |
| Sessions | httpOnly, Secure, SameSite=Lax cookies only. Never a token in `localStorage` | Direct fix for the Emergent frontend's XSS-exfiltration finding |
| Audit | Event sourcing + transactional outbox + hash-chained immutable audit log, with a real `verify_chain()` integrity checker (missing in Emergent) | Reuses Emergent's outbox/audit design, closes its one gap |
| CI/tests | Real test suite + working CI from commit #1 | Base44's CI was broken from day one (no test script, doomed `npm publish` workflow) |

---

## 1. The 13 bounded contexts

| # | Context | Responsibilities | Source of truth for design |
|---|---|---|---|
| 1 | **Identity** | User↔IdP mapping, hierarchy-checked role assignment, tenant scoping, delegation, service accounts | New build; Keycloak/Auth0 for authentication, custom for authorization data |
| 2 | **Registry** | Canonical parcel aggregate, ownership history, parcel numbering | Emergent invariants + Base44 field model |
| 3 | **Spatial Intelligence** | Coordinate/polygon validation, overlap + duplicate-geometry detection, GIS indexing, spatial search, adjacency, distance, map tiling, satellite overlays, spatial analytics | New build (server-side, PostGIS), Base44's `spatialValidation.js` as a starting reference |
| 4 | **Evidence** | Upload, server-side hashing, WORM sealing, Merkle anchoring, chain of custody, enforced legal hold | Emergent's pipeline (audited sound) |
| 5 | **Survey** | Surveyor licensing/credentials, assignment, survey plan upload (through the Evidence pipeline), archive import, revenue-share events | Base44's Surveyor Network / SurveyorDashboard / ArchiveRecord module, kept as-is (schema + UX), logic rebuilt |
| 6 | **Trust Engine** | Continuously recalculated, explainable per-parcel trust score, aggregating signals from every context below as they land | New build; `subscores` breakdown shape borrowed from Base44's `lvTrustValidationEngine` (structure only, not the math) |
| 7 | **Workflow** | Generic state-machine engine, sagas, timers, SLA/escalation, compensation, with real command handlers | Emergent's engine wholesale |
| 8 | **Community Trust** | Attestation, honest consensus scoring, conflict detection, traditional-authority endorsement | Base44's domain/field model as spec |
| 9 | **Inheritance & Customary Law** | Death verification, beneficiary/family ownership, regime selection, share calculation, disputes | Base44 + Emergent domain models as spec (neither implemented securely) |
| 10 | **Economic / Billing** | Credit wallet (atomic), service catalog, invoicing, payments, surveyor revenue-share consumption | Base44 field model + Emergent's audited-correct webhook code |
| 11 | **Knowledge Graph** | Surveyor↔Parcel↔Community↔Family↔Inheritance↔Verification↔Evidence↔Economic↔Certificates↔Disputes↔Banks↔Lawyers↔Government | New build |
| 12 | **Security** | Fraud detection, security incidents, real permission auditing, pen-test harness | Both apps' module lists as spec |
| 13 | **Operations** | Background job queue, backup/recovery testing, deployment observability | Both apps' job-type catalogs as spec |

---

## 2. BACKEND build plan

| Stage | Scope | Reuse from prior builds | Discard | Security fix baked in | Effort |
|---|---|---|---|---|---|
| **B0 — Kernel foundation** | Postgres schema/migrations (Alembic), fail-closed config, structured logging, RFC-7807 errors, health checks, Docker/Terraform scaffold | Emergent's `kernel/errors/problem.py` | — | No permissive env-var defaults anywhere; CI fails the build if found | 1–2 wk |
| **B1 — AuthN/AuthZ engine** | JWT verification against Keycloak/Auth0's JWKS (not self-issued keys), single PDP/PEP/PIP, audit hash-chain **+ `verify_chain()` checker**, tenant/country scoping via Postgres RLS | Emergent's fail-closed PDP/PEP pattern **in full** | Emergent's self-issued JWT/KeyStore/rotation code (Keycloak/Auth0 now owns this); Emergent's legacy session-cookie `core/security.py` RBAC entirely | Rate limiting on by default; CORS origin list required; `X-Forwarded-For` only trusted behind a configured proxy allowlist | 1–2 wk *(reduced — issuance delegated to IdP)* |
| **B2 — Identity** | User↔IdP-subject mapping, role assignment **with hierarchy check**, delegation wired into the PDP, tenant provisioning | Emergent's role/delegation aggregate logic | Broken `assign_role` as-is; Emergent's password/MFA/OAuth-provider code (not needed — IdP owns this) | Self-registration can never set role; every role change audited | 1–2 wk *(reduced)* |
| **B3 — Registry** | Parcel aggregate, immutable-field invariants, atomic allocator, append-only ownership history | Emergent's `_apply_patch` guard, atomic allocator; Base44's entity field list as spec | Base44 entity code as-is; Emergent's dual-write legacy adapter | Ownership-transfer authorization checks real actor identity against the resource | 3–4 wk |
| **B4 — Spatial Intelligence** | PostGIS-backed validation, overlap + duplicate-geometry detection, spatial indexing/search, adjacency, distance, map tiling | Base44's `spatialValidation.js` logic as reference (move server-side, make authoritative) | Base44's hardcoded LGA bounding-box check — replace with real polygon containment | Duplicate-geometry becomes a real signal (not GPS-proximity-only); first Trust Engine signal source | 3–4 wk |
| **B5 — Evidence** | Upload → server-side hash (stream, independent read-back) → real S3 Object Lock seal → Merkle anchoring → chain of custody → **enforced** legal hold | Emergent's hash/verify pipeline, Merkle/CT-log/OTS saga pattern | Chmod-based fake WORM; never-finished R2 stub | Legal hold as a guard at every delete/archive/seal-release path; break-glass dual-auth mechanically enforced | 4–6 wk |
| **B6 — Survey** | Surveyor onboarding/licensing, assignment-to-parcel workflow, survey plan upload through the Evidence pipeline, archive import, revenue-share event emission | `SurveyorPartner`, `SurveyAssignment`, `ArchiveRecord`, `RevenueTransaction`, `SurveyDocument` schemas kept verbatim; consolidates Base44's split legacy/LandVault survey tracks into one module | Base44's dual legacy-vs-LandVault duplication | Assignment/completion actions require real role + licence-status checks server-side | 2–3 wk |
| **B7 — Trust Engine** | Event-subscribing scoring engine; scaffolds with 3 signals (Evidence integrity + Spatial duplicate-geometry + Survey completion/licence-confidence), explainable score breakdown API | Base44's `subscores` object shape (structure only) | All of Base44's actual scoring functions (the "always passes" defect) | CI rule: every signal contributor must have a test asserting zero-data input yields `INSUFFICIENT_DATA`, never a high score | 2–3 wk + incremental |
| **B8 — Workflow engine** | Real command handlers wired to Registry/Evidence/Identity/Survey | Emergent's engine wholesale (audited as the most rigorously built part of that codebase) | `NullCommandHandler` | Compensation failures alert, don't silently log-and-continue | 2–3 wk |
| **B9 — Community Trust** | Attestation, honest consensus scoring, conflict detection, traditional-authority endorsement — 4th Trust Engine signal | Base44's domain/field model as spec | Base44's scoring code outright | Real authenticated actor on every review | 2–3 wk |
| **B10 — Inheritance & Customary Law** | Death verification → beneficiary validation → share calculation → certificate | Base44's + Emergent's domain models as spec | Both apps' actual implementations | PII routes through B5's encryption from day one | 4–5 wk |
| **B11 — Economic / Billing** | Atomic ledger, real invoicing, payment webhooks, consumes Survey's revenue-share events | Emergent's webhook signature code (audited correct); Base44's `RevenueTransaction` field model | Mock payment endpoint entirely; Base44's billing crash/race bugs | Balance mutation only via one atomic ledger function, DB-constrained non-negative | 3 wk |
| **B12 — Knowledge Graph** | Graph projection off the event outbox across all contexts | New build | — | Read-only, rebuildable from the outbox at any time | 3–4 wk |
| **B13 — Security** | Real fraud detection, security incidents, permission auditor **reading actual RLS policy config**, pen-test harness | Both apps' module lists as spec | Base44's fictional shadow-table permission auditor; Emergent's "R-2 CLOSED" self-cert pattern | Permission auditor fails loudly on any table with missing/permissive policy | 2–3 wk |
| **B14 — Operations** | Job queue, backup/recovery testing, deployment observability | Both apps' job-type catalogs as spec | Base44's disabled-by-default automations; unconditional `seed_demo_data()`-style startup seeding | All seeding environment-gated, never runs against a populated/production DB automatically | 2 wk |

**Backend total: ~31–37 weeks sequential** (reduced from v3's ~33–40 by delegating auth issuance to Keycloak/Auth0).

---

## 3. FRONTEND build plan

| Stage | Scope | Reuse | Discard | Security fix | Effort |
|---|---|---|---|---|---|
| F0 Shell | Next.js App Router scaffold, Tailwind+shadcn/ui theme, layout, generated API client, `ProtectedRoute`/middleware on every route | Base44's shadcn/ui set + layout pattern; Emergent's SDK discipline | Both apps' auth-context implementations; Base44's Vite config | Route-audit lint rule; auth via Keycloak/Auth0 SDK, no token in localStorage | 1–2 wk |
| F1 Auth | Login/register via Keycloak/Auth0 hosted flow, real CSRF/state handling | Base44's role-selection UX | Emergent's stateless OAuth callback | CSRF-protected callback (handled by IdP SDK) | 1 wk |
| F2 Registry + Spatial UI | Parcel CRUD, GIS map, polygon editor, overlap/duplicate warnings live during registration, bulk import | Base44's map/form components as reference | Naive CSV parser; client-side-only LGA bounds check | Spatial validation calls B4 server-side, never trusts client geometry | 3–4 wk |
| F3 Evidence UI | Upload/list/detail/tabs | Emergent's evidence pages wholesale | — | Missing `ProtectedRoute` added; SDK path-param encoding fixed | 2 wk |
| F3.5 Survey / Surveyor Network UI | Surveyor dashboard, network directory, public profile, archive import wizard | `SurveyorDashboard.jsx`, `SurveyorNetwork.jsx`, `SurveyorPublicProfile.jsx`, `ArchiveImportWizard.jsx` ported closely | Base44's separate legacy-tier survey pages, consolidated | Assignment actions require server-verified role/licence status | 2–3 wk |
| F3.6 Trust & Transparency UI | Trust dashboard with explainable score breakdown, duplicate-alert dashboard, evidence timeline, public transparency portal | Base44's `TrustArchitecture.jsx` and `CommunityTransparency.jsx` layout | Base44's single-number trust score display with no factor breakdown | Every displayed score paired with its signal list | 2–3 wk |
| F4 Community Trust UI | Attestation/review/consensus | Base44 UX as reference | Hardcoded-`"admin"`-actor components | Real authenticated actor on every review | 2–3 wk |
| F5 Inheritance UI | Case/beneficiary/certificate mgmt | Base44 UX as reference | `document.write()` cert generator (confirmed XSS) | No client-built HTML strings anywhere | 3–4 wk |
| F6 Economic UI | Wallet/billing/revenue, surveyor revenue-share view | Base44 pages as reference | Direct wallet/invoice writes | UI confirms only after atomic server write | 2–3 wk |
| F7 Knowledge Graph explorer | Relationship visualization for fraud/due-diligence users | New build | — | Read-only viewer; no mutation surface via the graph | 2–3 wk |
| F8 Security/Ops/Gov dashboards | Admin consoles | Both apps' layouts as reference | Score-without-evidence display pattern | Server-verified role, not sidebar-hiding | 2–3 wk |
| F9 Public pages | Landing, verify, transparency | Both apps' content | — | CI route-audit confirms nothing else is public | 1 wk |

**Frontend total: ~23–29 weeks.**

---

## 4. FEATURE rollout timeline

| Milestone | Unlocks | Needs | Cumulative (parallelized) |
|---|---|---|---|
| M0 Platform online | Auth works (via Keycloak/Auth0), CI green | B0-B2, F0-F1 | Weeks 1–4 |
| M1 Core registry MVP | Register/search/verify a parcel, real spatial validation at registration | B3-B4, F2, F9 | Weeks 4–12 |
| M2 Evidence-backed registry | Real evidence, integrity, enforced legal hold | B5, F3 | Weeks 10–18 |
| M2.4 Surveyor Network live | Surveyor onboarding, assignment, archive import, survey plans through the Evidence pipeline | B6, F3.5 | Weeks 16–20 |
| M2.5 Trust Intelligence | Confidence engine, duplicate detection, chain of custody, trust dashboard with explainable breakdown, 3 real signals | B7, F3.6 | Weeks 18–24 |
| M3 Community trust | Attestations feed Trust Engine as a 4th signal; consensus, traditional authority | B8-B9, F4 | Weeks 22–28 |
| M4 Inheritance & customary law | Death→beneficiary→share→certificate, PII-protected | B10, F5 | Weeks 26–34 |
| M5 Economic operations | Real billing, atomic wallets, surveyor revenue-share paid out | B11, F6 | Weeks 30–36 |
| M6 Knowledge Graph & fraud intelligence | Relationship graph live, fraud detection consumes it | B12-B13, F7-F8 | Weeks 34–40 |
| M7 Operations hardening & pilot launch | Real job queue, backup/recovery tested, environment-gated seeding, runbook | B14, F9 polish | Weeks 38–42 |

**Total to pilot-ready: ~38–40 weeks.**

---

## 5. Maturity read: Base44 vs. M2.4/M2.5 deliverables

| Deliverable | Base44 state | Read |
|---|---|---|
| Surveyor Network / Dashboard / Archive Import (M2.4) | Fully scaffolded, routed, but **0 live records** — never exercised | ~70% reusable as UX/schema, ~0% backend logic to inherit |
| Confidence Engine | `lvEvidenceConfidence`/`lvAttestationConfidence` exist, inverted `risk_score`, unauthenticated write | ~50% spec, 0% code |
| Duplicate Detection | GPS-proximity only, 7 redundant automations, 0 alerts ever generated | ~40% spec |
| Chain of Custody | Functionally real (10 records confirmed working), `EvidenceChain` entity has no RLS at all | ~55% UX, needs full security rebuild |
| Trust Dashboard | Real, well-built UI; underlying number is the confirmed "100/A_PLUS/GO despite 0 evidence" defect | ~60% UI, ~10% trustworthy data |
| Transparency Dashboard | Confirmed working with real data (8 attestations) | ~65% directly reusable |
| Explainable Trust Score | `subscores` breakdown shape exists structurally; every value fabricated by no-op branches | ~15% |

---

## 6. Open sub-decisions

1. **Keycloak vs. Auth0** — Keycloak recommended default (self-hosted, avoids per-MAU cost, better data-residency story for a land-registry pilot); Auth0 as a faster-to-bootstrap fallback. See `docs/adr/ADR-004-authentication-authorisation-model.md`.
2. **Knowledge Graph engine** — Neo4j (separate service, more capable) vs. Postgres + Apache AGE (one database, less mature tooling). Leaning AGE for a lean team.
3. **Monorepo vs. multi-repo** — monorepo recommended (`/frontend`, `/backend`, `/infra`). See `docs/adr/ADR-001-repository-strategy.md`.
4. Team size — assumed 1–3 engineers + Claude Code; effort estimates rescale roughly linearly if that's wrong.
