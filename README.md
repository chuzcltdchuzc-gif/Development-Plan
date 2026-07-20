# AquaSavannah LandVault

A land-registry and verification platform for Nigeria — parcel registration, GIS-backed spatial validation, evidence chain-of-custody, community/traditional-authority attestation, survey network management, inheritance & customary-law resolution, and an economic/billing layer, built around an explainable, continuously-recalculated per-parcel trust score.

**Status:** B1 and B2 are complete, verified against live infrastructure, and frozen (`docs/adr/ADR-009-b1-platform-freeze.md`, `docs/adr/ADR-012-b2-platform-freeze.md`), tagged `b2-freeze`. B3 (Registry) is in progress — Slice 1 (Parcel Aggregate, `docs/adr/ADR-013-parcel-aggregate-registry-domain-model.md`), Slice 2 (Atomic Parcel Number Allocation, `docs/adr/ADR-014-postgresql-atomic-parcel-number-allocation.md`), and Slice 3 (Mutation Commands & Authorization Hardening, `docs/adr/ADR-015-registry-mutation-authorization-model.md`) are implemented; Slice 4 is not yet authorized. Slice 3 onward defers comprehensive `ruff`/`mypy`/`pytest`/live verification to a single End-of-B3 Quality Gate rather than running it per slice — see `docs/B3_FINAL_VERIFICATION_CHECKLIST.md` for the cumulative, not-yet-executed list that gate must clear before B3 can be proposed for freeze. See `CLAUDE.md`'s "B2 status"/"B3 status" and `docs/audits/B2_RELEASE_NOTES.md` for exactly what's landed.

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
| [`docs/REBUILD_PLAN.md`](./docs/REBUILD_PLAN.md) | The technical plan: target stack, 13 bounded contexts, backend/frontend build stages, feature-rollout milestones |
| [`docs/PHASE_GATES.md`](./docs/PHASE_GATES.md) | The process/quality-gate model (Phase 0–12), the Claude Code Loop, and the 10 standing review questions |
| [`docs/DOD.md`](./docs/DOD.md) | Definition of Done — Feature / Sprint / Product (MVP) tiers |
| [`docs/ENGINEERING_RULES.md`](./docs/ENGINEERING_RULES.md) | When Claude may act autonomously vs. must stop and ask; the non-negotiable engineering rules |
| [`docs/adr/`](./docs/adr/) | Architecture Decision Records — ADR-001 through ADR-015 |
| [`docs/B3_FINAL_VERIFICATION_CHECKLIST.md`](./docs/B3_FINAL_VERIFICATION_CHECKLIST.md) | Cumulative deferred-verification register (Slice 3 onward) — what must pass before B3 freeze |
| [`docs/audits/`](./docs/audits/) | The full audit reports behind every decision above |
| [`docs/exports/AquaSavannah_LandVault_Combined_Plan.pdf`](./docs/exports/AquaSavannah_LandVault_Combined_Plan.pdf) | Single-file PDF export of this whole planning package, plus the superseded v3 snapshot preserved for provenance — see the PDF's own preface for which parts are current |

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
