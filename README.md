# AquaSavannah LandVault

A land-registry and verification platform for Nigeria — parcel registration, GIS-backed spatial validation, evidence chain-of-custody, community/traditional-authority attestation, survey network management, inheritance & customary-law resolution, and an economic/billing layer, built around an explainable, continuously-recalculated per-parcel trust score.

**Status:** B1, B2, and B3 are complete, verified against live infrastructure, and frozen (`docs/adr/ADR-009-b1-platform-freeze.md`, `docs/adr/ADR-012-b2-platform-freeze.md`, `docs/adr/ADR-017-b3-platform-freeze.md`), tagged `b2-freeze` and `b3-freeze`. B3 (Registry) delivered the Parcel aggregate (ADR-013), atomic parcel numbering (ADR-014), creator-aware mutation authorization closing a confirmed historical vulnerability (ADR-015), and a geometry port boundary for future spatial capability (ADR-016) — all verified via the B3 Final Quality Gate (full `ruff`/`mypy`/`pytest` plus live Postgres/Keycloak/RLS/delegation/audit-chain/cross-tenant/ownership-attack/container verification, see `docs/B3_FINAL_VERIFICATION_CHECKLIST.md`). B4 (Spatial Intelligence) is treated as an entirely new programme — its Phase 0 discovery, threat model, domain model (ADR-018), an accepted amendment to B3's `GeometryPort` contract (ADR-019), and the Spatial Authorization Model (ADR-022) are accepted; Slice 1 (Spatial Domain Foundation) and Slice 2 (Geometry Validation & Real Geometry Adapter — real structural WKT validation, ADR-022's creator-or-governance authorization, and the first real `GeometryPort` adapter wired into Registry via the composition root only) are both implemented, **fully live-verified** against real Postgres/PostGIS/Keycloak/RLS/audit-chain/container, and **accepted — Slice 2's architecture is frozen under ADR-022** (`docs/B4_VERIFICATION_CHECKLIST.md`). ADR-021 (Spatial Conflict Detection & Controlled Cross-Tenant Intelligence — the constitutional doctrine for overlap/duplicate-geometry detection) is drafted, not yet accepted, and has passed a full pre-Slice-3 architectural review with no amendment required (`docs/B4_SLICE3_PREIMPLEMENTATION_REVIEW.md`); its accompanying engineering specification (SCDS-001) and a Platform Intelligence architecture doctrine are also drafted. Overlap detection itself (B4 Slice 3) is not authorized. Separately, an Enterprise Programme Transition planning exercise produced `docs/PLATFORM_STRATEGY.md` and eight further planning-only documents (Partner, Enterprise, Government, Developer Platform, Commercial Architecture, Operating Model, Trust Framework, Network Growth Strategy) — architecture/business planning only, no code, no new bounded context, no ADR change. **`docs/LV-000-constitution.md` v1.0 — the LandVault Constitution — was adopted 2026-07-26** as the platform's supreme governing document; it modifies no accepted ADR, creates no bounded context, and introduces no implementation detail — it ratifies, at constitutional altitude, doctrine this platform's engineering discipline already operates under, and incorporates both entries previously logged in `docs/CONSTITUTIONAL_RECOMMENDATIONS.md`. See `CLAUDE.md`'s "B2 status"/"B3 status"/"B4 status" and `docs/audits/B2_RELEASE_NOTES.md`/`docs/audits/B3_RELEASE_NOTES.md` for exactly what's landed.

---

## Why a rebuild

Two prior builds of this product were audited in full (architecture, security, correctness) before any code here was written — see `docs/audits/`:

- **Base44 build** — full-featured but insecure: client-side-only authorization throughout, permissive/missing row-level-security on numerous entities (including a self-service financial-fraud vector on user wallets), and multiple "trust validation" functions confirmed to report a passing score regardless of actual data.
- **Emergent build** — a genuinely well-architected DDD/event-sourced backend (its authorization engine design is retained in this rebuild — see ADR-004) undermined by a parallel, undocumented legacy auth system and an unauthenticated admin-login bypass.

Every rule in `docs/ENGINEERING_RULES.md` and every non-negotiable in `docs/DOD.md` traces to a specific, confirmed finding from these audits — this isn't generic best-practice boilerplate.

---

## Documentation map

| Document | What it's for |
|---|---|
| [`CLAUDE.md`](./CLAUDE.md) | How Claude Code should operate in this repo — read this first |
| [`docs/LV-000-constitution.md`](./docs/LV-000-constitution.md) | **LV-000 v1.0 — the LandVault Constitution, adopted 2026-07-26.** The platform's supreme governing document (Preamble through 22 Articles: vision, mission, ten constitutional principles, platform/architecture/documentation/programme governance, security/trust/identity/data/evidence/marketplace/government/enterprise/innovation principles, amendment process, definitions, cross-reference index). Governs by precedence, not by duplicating any ADR |
| [`docs/ARCHITECTURE_HANDBOOK.md`](./docs/ARCHITECTURE_HANDBOOK.md) | v1.1 — the consolidated engineering reference: platform philosophy, architecture, DDD, engineering rules, security model, programme governance, documentation hierarchy, future programmes, architectural evolution, engineering culture. Not an ADR, subordinate to LV-000 — a navigation/interpretation document only |
| [`docs/REBUILD_PLAN.md`](./docs/REBUILD_PLAN.md) | The technical plan: target stack, 13 bounded contexts, backend/frontend build stages, feature-rollout milestones |
| [`docs/PHASE_GATES.md`](./docs/PHASE_GATES.md) | The process/quality-gate model (Phase 0–12), the Claude Code Loop, and the 10 standing review questions |
| [`docs/DOD.md`](./docs/DOD.md) | Definition of Done — Feature / Sprint / Product (MVP) tiers |
| [`docs/ENGINEERING_RULES.md`](./docs/ENGINEERING_RULES.md) | When Claude may act autonomously vs. must stop and ask; the non-negotiable engineering rules |
| [`docs/adr/`](./docs/adr/) | Architecture Decision Records — ADR-001 through ADR-019 and ADR-022 accepted; ADR-021 (Spatial Conflict Detection) proposed, pending review |
| [`docs/B3_FINAL_VERIFICATION_CHECKLIST.md`](./docs/B3_FINAL_VERIFICATION_CHECKLIST.md) | B3's verification evidence register — all items resolved, gate passed |
| [`docs/B4_DISCOVERY_AND_PLANNING.md`](./docs/B4_DISCOVERY_AND_PLANNING.md) | B4 (Spatial Intelligence) Phase 0 plan — accepted as the official planning baseline |
| [`docs/B4_THREAT_MODEL.md`](./docs/B4_THREAT_MODEL.md) | B4's accepted threat model/trust-boundary baseline — mandatory constraints on all B4 work |
| [`docs/B4_VERIFICATION_CHECKLIST.md`](./docs/B4_VERIFICATION_CHECKLIST.md) | B4's verification evidence register — Slice 1/2 items resolved and live-verified; overlap detection (Slice 3) not yet started |
| [`docs/SCDS-001-spatial-conflict-detection-specification.md`](./docs/SCDS-001-spatial-conflict-detection-specification.md) | Engineering specification beneath ADR-021 (not an ADR) — conflict taxonomy, severity, disclosure matrix, audit spec; no algorithm or code |
| [`docs/B4_SLICE3_PREIMPLEMENTATION_REVIEW.md`](./docs/B4_SLICE3_PREIMPLEMENTATION_REVIEW.md) | Pre-Slice-3 architectural review of ADR-021/SCDS-001 against every frozen/accepted ADR — no amendment required, Slice 3 still not authorized |
| [`docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md`](./docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md) | Names Platform Intelligence as a cross-cutting services layer (not a bounded context) — governs any future capability that reads across contexts/tenants |
| [`docs/MARKETPLACE_DISCOVERY_AND_PLANNING.md`](./docs/MARKETPLACE_DISCOVERY_AND_PLANNING.md) | Planning-only recommendation to open a Marketplace programme — no code, scoping question left open |
| [`docs/PLATFORM_STRATEGY.md`](./docs/PLATFORM_STRATEGY.md) | Planning only — vision, positioning, five-layer platform model, surveyors-as-partners, the strategic-layer document hierarchy |
| [`docs/PARTNER_PROGRAMME_STRATEGY.md`](./docs/PARTNER_PROGRAMME_STRATEGY.md) | Planning-only recommendation for a Partner programme (onboarding, accreditation, ratings, wallet, SLAs) |
| [`docs/ENTERPRISE_PROGRAMME_STRATEGY.md`](./docs/ENTERPRISE_PROGRAMME_STRATEGY.md) | Planning-only recommendation for an Enterprise programme (banks, law firms, developers, enterprise dispatch) |
| [`docs/GOVERNMENT_PROGRAMME_STRATEGY.md`](./docs/GOVERNMENT_PROGRAMME_STRATEGY.md) | Planning-only recommendation for a Government programme (registry interop, public verification, digital certificates) |
| [`docs/DEVELOPER_PLATFORM_STRATEGY.md`](./docs/DEVELOPER_PLATFORM_STRATEGY.md) | Planning-only recommendation for Developer Platform + API Ecosystem (SDKs, OAuth, webhooks, sandbox) |
| [`docs/COMMERCIAL_ARCHITECTURE.md`](./docs/COMMERCIAL_ARCHITECTURE.md) | Planning-only diversified revenue model — candidate revenue lines and pricing principles, no prices set |
| [`docs/OPERATING_MODEL.md`](./docs/OPERATING_MODEL.md) | Planning-only organizational functions (Partner Ops, Fraud Ops, Trust & Safety, Compliance, etc.) — none staffed |
| [`docs/TRUST_FRAMEWORK.md`](./docs/TRUST_FRAMEWORK.md) | Business-facing companion to the Handbook's Security Model — ties engineering trust mechanisms to ecosystem-facing claims |
| [`docs/NETWORK_GROWTH_STRATEGY.md`](./docs/NETWORK_GROWTH_STRATEGY.md) | Planning-only scaling narrative (100 → millions of surveyors/parcels) and the architectural prerequisites at each stage |
| [`docs/CONSTITUTIONAL_RECOMMENDATIONS.md`](./docs/CONSTITUTIONAL_RECOMMENDATIONS.md) | Historical register of principles proposed for LV-000 — both current entries now incorporated into LV-000 v1.0 |
| [`docs/LANDVAULT_BIBLE_VOLUME_I_EXECUTIVE_OVERVIEW.md`](./docs/LANDVAULT_BIBLE_VOLUME_I_EXECUTIVE_OVERVIEW.md) | **LandVault Bible™ Volume I** — 15–25 page executive narrative for governments, investors, enterprise clients, and procurement teams. Explanatory only, non-normative — decides nothing, supersedes nothing |
| [`docs/LANDVAULT_BIBLE_VOLUME_II_PRODUCT_STRATEGY_AND_ENTERPRISE_DEFINITION.md`](./docs/LANDVAULT_BIBLE_VOLUME_II_PRODUCT_STRATEGY_AND_ENTERPRISE_DEFINITION.md) | **LandVault Bible™ Volume II** — market analysis, expanded five-layer model, full Trust Network framework, Marketplace-as-enterprise-strategy, full commercial model, competitive position, long-term roadmap. Explanatory only, non-normative |
| [`docs/LV-013-market-intelligence-report.md`](./docs/LV-013-market-intelligence-report.md) | **LV-013 — Market Intelligence Report.** Web-researched (2026-07-29), every figure tagged VERIFIED/ESTIMATE/NOT VERIFIED — Nigeria land market, fraud landscape, survey profession, government digitisation, financial/enterprise opportunity, competitive landscape, TAM/SAM/SOM, international benchmarking. No fabricated statistics |
| [`docs/audits/`](./docs/audits/) | The full audit reports behind every decision above |
| [`docs/exports/AquaSavannah_LandVault_Combined_Plan.pdf`](./docs/exports/AquaSavannah_LandVault_Combined_Plan.pdf) | Single-file PDF export of this whole planning package, plus the superseded v3 snapshot preserved for provenance — see the PDF's own preface for which parts are current |

**Session history (`docs/session-logs/`):** plain narrative records of individual working
conversations, kept for context on why a document exists and in what order — **not governance
documents.** They are never cited by an ADR, by the Architecture Handbook, or by LV-000, and carry
no authority over any of them; where a session log and a governing document disagree, the governing
document is correct and the log is simply out of date.

---

## Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js + TypeScript, Tailwind + shadcn/ui |
| Backend | Python + FastAPI, DDD/hexagonal architecture |
| Database | PostgreSQL + PostGIS |
| Authentication | Keycloak (default) or Auth0 |
| Authorization | Custom PDP/PEP/PIP engine (retained from audit-validated Emergent design) |
| Object storage | S3-compatible, Object Lock (Compliance mode) |
| Payments | Paystack (Nigeria) + Stripe (diaspora) |
| Infrastructure | Docker, Terraform, AWS/Azure |
| Audit | Event sourcing + immutable hash-chained logs |

Full rationale for each choice: `docs/adr/`.

---

## Process at a glance

Every phase must pass its quality gates before the next one starts — see `docs/PHASE_GATES.md` for full detail.

| Phase | Exit criterion |
|---|---|
| 0 — Enterprise Planning | Vision, requirements, and scope approved and frozen |
| 1 — System Architecture | No unresolved architecture issues |
| 2 — Development Environment | Three isolated environments operational |
| 3 — Foundation | Zero critical vulnerabilities |
| 4 — Database | Database production ready |
| 5 — Core Services | 95% automated test coverage |
| 6 — AI Layer | AI quality above target threshold |
| 7 — Payments | Successful end-to-end payment tests |
| 8 — Security Hardening | No critical or high-severity findings |
| 9 — Performance | Performance targets achieved |
| 10 — Production Readiness | Go/No-Go decision |
| 11 — Launch | Live, monitored, reviewed |
| 12 — Growth | Ongoing |

Sprints are organized **one per bounded context** (13 total — see `docs/REBUILD_PLAN.md` §1), not by generic feature grouping.

---

## Quick start

See `CLAUDE.md`'s "Build/test/run commands" section for backend, frontend, and full-stack (Docker Compose) instructions.

---

## License

TBD.
