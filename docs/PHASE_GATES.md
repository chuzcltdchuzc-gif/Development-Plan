# Phase Gates — Process & Quality Model

This document is the **process/governance layer**. It answers "how do we know work is done and safe to build on." For "what actually gets built, in what order," see `docs/REBUILD_PLAN.md` — the 13 bounded contexts and their B0–B14 / F0–F9 / M0–M7 sequencing.

**Binding rule:** Claude Code is not permitted to start a new production phase until the current phase has passed all mandatory quality gates. Every phase must end with successful architecture review, security review, automated testing, performance validation, documentation updates, and deployment readiness. If any gate fails, Claude must prioritize fixing the issue before implementing new features. **Progress is measured by verified quality, not by the number of completed features.**

---

## Reconciliation: how this relates to the bounded-context plan

Three ways of slicing this project were on the table during planning: a generic 13-phase delivery lifecycle, a generic business-capability sprint list, and the audit-derived 13 bounded-context plan. The decision, recorded here so no future session re-litigates it:

- **Phases (below) are the cross-cutting gate/process layer** — they define what "done" means at each stage of the whole platform's maturity, regardless of which bounded context is being worked on.
- **The generic Sprint 1–8 business-capability list is retired.** It was a thinner subset of the bounded-context plan (no Spatial Intelligence, no Trust Engine, no Knowledge Graph, minimal Inheritance/Customary Law depth) and having three overlapping taxonomies risked confusion rather than clarity.
- **Sprints = one per bounded context** (13 total, per `docs/REBUILD_PLAN.md` §1). Each sprint follows the Development Operating Model below and must pass the relevant Phase's gates before merge.

### Mapping: which bounded-context stage satisfies which phase

| Phase | Satisfied by |
|---|---|
| 0 — Enterprise Planning | This document + `docs/REBUILD_PLAN.md` + the ADR set in `docs/adr/` |
| 1 — System Architecture | `docs/adr/ADR-001` through `ADR-008` |
| 2 — Development Environment | New sub-stage **B0.0**: repo scaffold, Docker Compose, Terraform baseline, env-var conventions, Keycloak/Auth0 tenant setup, secrets manager wiring |
| 3 — Foundation | B0 (kernel) + B1–B2 (Identity/AuthZ) + F0 (frontend scaffold) |
| 4 — Database | B0 kernel schema + B3 Registry schema (PostGIS setup, Alembic migrations) |
| 5 — Core Services | B3 Registry, B4 Spatial Intelligence, B5 Evidence, B6 Survey, B8 Workflow, B12 Knowledge Graph (as a read-projection service) |
| 6 — AI Layer | Scoped concretely in `docs/adr/ADR-008-ai-integration-strategy.md`: OCR/document classification (Evidence uploads), AI-assisted signals feeding the Trust Engine as **advisory input only, never authoritative**, fraud-pattern detection over the Knowledge Graph |
| 7 — Payments | B11 Economic/Billing |
| 8 — Security Hardening | B13 Security — a dedicated pre-launch sweep, distinct from the per-sprint SECURITY TEST loop step below |
| 9 — Performance | Explicit checkpoint tied to B14 Operations + each context's own perf criteria in the DoD |
| 10 — Production Readiness | B14 Operations (job queue, monitoring, backup/DR) + M7 |
| 11 — Launch | M7 (pilot-ready milestone) |
| 12 — Growth | Beyond current plan scope — a v2 roadmap, new contexts, scaling work |

---

## Phase 0 — Enterprise Planning

**Objective:** Understand the business completely before writing code.

**Deliverables:** Business Vision · Product Vision · Stakeholders · Functional Requirements · Non-functional Requirements · Risk Analysis · Success Criteria

**Exit criteria:**
- ✔ Vision approved
- ✔ Requirements approved
- ✔ Scope frozen

No code yet.

---

## Phase 1 — System Architecture

**Deliverables:** C4 diagrams · Architecture diagrams · Technology selection · Repository strategy · Folder structure · Infrastructure · Security architecture

**Checks:** Architecture Review · Threat Model · Scalability Review · Performance Review · Cost Review

**Exit criteria:** No unresolved architecture issues.

---

## Phase 2 — Development Environment

**Deliverables:** GitHub · Claude Code · VS Code · Docker · Terraform · FastAPI + Next.js scaffolds · Keycloak (or Auth0) · Paystack · Stripe · AWS/Azure Secrets Manager · Development / Staging / Production environments

**Checks:** Environment validation · Secrets validation · Git branching · CI/CD · Rollback test

**Exit criteria:** Three isolated environments operational.

---

## Phase 3 — Foundation

**Claude builds:** Authentication (Keycloak/Auth0 integration) · Authorization (PDP/PEP/PIP) · Database · API · Logging · Monitoring · Audit

**Checks:** Authentication · OWASP · RLS · JWT (verification against IdP JWKS) · Logout · Permission testing · Session expiry · Rate limiting · Dependency audit

**Exit criteria:** Zero critical vulnerabilities.

---

## Phase 4 — Database

**Claude builds:** Schema · Indexes · Relationships · Migrations (Alembic) · RLS · Audit logs

**Checks:** Performance · Query analysis · Load testing · Backup · Recovery · Data integrity

**Exit criteria:** Database production ready.

---

## Phase 5 — Core Services

**Claude builds:** Property/Parcel Registry · Spatial Intelligence · Evidence · Survey · Search · Document Upload · Verification · Dashboard · Knowledge Graph projection

**Checks:** Integration testing · API testing · Performance · Edge cases · Validation

**Exit criteria:** 95% automated test coverage.

---

## Phase 6 — AI Layer

**Claude builds:** Classification (Evidence OCR/document type detection) · Document AI · Verification-assisting AI signals (feeding the Trust Engine as advisory input) · Recommendations

**Checks:** Evaluation · Hallucination testing · Latency · Cost · Prompt injection · Fallback chain · Model routing

**Exit criteria:** AI quality above target threshold. AI output is never treated as authoritative — see `docs/adr/ADR-008-ai-integration-strategy.md`.

---

## Phase 7 — Payments

**Claude builds:** Paystack · Stripe · Invoices · Credits · Subscriptions

**Checks:** Sandbox testing · Webhook verification · Duplicate protection · Refund flow · Currency testing

**Exit criteria:** Successful end-to-end payment tests.

---

## Phase 8 — Security Hardening

**Claude executes:** OWASP ZAP · Burp Suite · GitGuardian · Snyk · Secret scan · API penetration testing · Threat modelling

**Checks:** No SQL Injection · No XSS · No CSRF · No broken authentication · No privilege escalation

**Exit criteria:** No critical or high-severity findings.

---

## Phase 9 — Performance

**Claude performs:** Load tests · Caching · Redis · CDN · Compression · Image optimization · Database tuning

**Checks:** Page load · API latency · Database latency · Memory · CPU · Cost

**Exit criteria:** Performance targets achieved.

---

## Phase 10 — Production Readiness

**Claude verifies:** Environment variables · Secrets · Monitoring · Alerts · Logging · Backups · Recovery · Canary deployment · Rollback

**Checks:** Deployment rehearsal · Rollback rehearsal · Disaster recovery

**Exit criteria:** Go/No-Go decision.

---

## Phase 11 — Launch

Production deployment · Monitoring · Analytics · Incident management · Daily health checks · Weekly review · Monthly audit

---

## Phase 12 — Growth

AI optimisation · Infrastructure optimisation · Scaling · Government APIs · GIS · Machine Learning · Fraud Detection · Enterprise customers

---

## The Claude Code Loop

Every sprint (= one bounded context) follows this cycle:

```
PLAN
  ↓
DESIGN
  ↓
BUILD
  ↓
UNIT TEST
  ↓
INTEGRATION TEST
  ↓
SECURITY TEST
  ↓
PERFORMANCE TEST
  ↓
AI REVIEW
  ↓
BUG FIX
  ↓
REFACTOR
  ↓
DOCUMENT
  ↓
APPROVE
  ↓
DEPLOY TO STAGING
  ↓
USER ACCEPTANCE TEST
  ↓
DEPLOY TO PRODUCTION
  ↓
LOCK PHASE
  ↓
NEXT PHASE
```

**No shortcuts.** The "AI REVIEW" step maps to this repo's `/code-review` and `/security-review` tooling — it is a real, run step, not aspirational text.

---

## 10 Standing Review Questions

Ask these at every gate check:

1. **Foundation:** Is the architecture still aligned with the business goals?
2. **Security:** Have OWASP Top 10 risks been checked?
3. **Performance:** Will this support (a) 10,000 users? (b) 100,000 users? (c) 1 million users?
4. **Cost:** Can infrastructure costs be reduced without sacrificing quality?
5. **Quality:** Has every feature been tested?
6. **Documentation:** Is documentation complete and up to date?
7. **Deployment:** Can this version be rolled back in under two minutes?
8. **Bugs:** Are there any known critical bugs?
9. **AI:** Has AI behaviour been evaluated?
10. **Future:** Will today's decisions block tomorrow's features?

---

## Development Operating Model (per sprint = per bounded context)

```
Sprint Planning
      │
      ▼
Claude reads CLAUDE.md
      │
      ▼
Implements ONE bounded context
      │
      ▼
Runs tests
      │
      ▼
Runs security checks
      │
      ▼
Runs performance checks
      │
      ▼
Updates documentation
      │
      ▼
Deploys to staging
      │
      ▼
Definition of Done review (docs/DOD.md)
      │
      ▼
Merge
      │
      ▼
Next Sprint
```

Documentation and quality are part of development, not something left until the end.
