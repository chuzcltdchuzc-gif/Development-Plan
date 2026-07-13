# Definition of Done (DoD)

Every feature, bounded context, sprint, and milestone must satisfy the same quality criteria before it is considered complete. Only then can Claude Code mark the task as complete. This document is invoked at three levels — see §4.

---

## 1. Tier 1 — Feature Done

A feature is only "Done" when:

**Functional**
- Requirements implemented.
- Acceptance criteria met.
- Edge cases handled.

**Code Quality**
- Passes linting (ESLint for TypeScript/Next.js, Ruff for Python/FastAPI).
- Proper typing (TypeScript strict mode; Python type hints, checked with mypy).
- No duplication.
- Follows `docs/adr/` decisions and this repo's coding standards.

**Testing**
- Unit tests pass.
- Integration tests pass.
- End-to-end tests pass where appropriate.

**Security**
- Authorization verified (goes through the PDP/PEP — see `docs/adr/ADR-004-authentication-authorisation-model.md`, never a bespoke check).
- Authentication verified.
- Input validation complete.
- Secrets not exposed.
- OWASP checks passed.
- **New entity/table? An RLS/authorization policy ships in the same commit — never a follow-up.** See `docs/ENGINEERING_RULES.md`.

**Performance**
- Meets agreed response-time targets.
- Database queries reviewed (no N+1, indexes checked against PostGIS/Postgres query plans where relevant).
- No obvious bottlenecks.

**Documentation**
- README updated if needed.
- API documentation updated (OpenAPI schema regenerated).
- Architecture updated if affected (`docs/REBUILD_PLAN.md`, relevant ADR).
- Changelog updated.

**Deployment**
- CI/CD pipeline passes.
- Deployable to staging.
- Rollback possible in under two minutes (see standing review question 7).

**Non-negotiable, audit-evidenced criterion:**

> Every signal contributor to a computed score (Trust Engine, Confidence Engine, consensus calculation, any automated readiness/health score) **must have a test asserting zero-data or missing-data input yields a low or `INSUFFICIENT_DATA` result — never a passing score.**

This traces directly to the Base44 audit's confirmed finding: the platform's trust validation engine returned `100/A_PLUS/GO` while having zero evidence, zero certificates, and multiple disabled automations — because every one of its sub-checks silently treated "nothing to check" as "check passed." This must never recur here.

---

## 2. Tier 2 — Sprint (Bounded Context) Done

All planned features for the bounded context are integrated, tested, documented, and accepted:

- Every feature in the sprint meets Tier 1.
- Cross-context integration tested against every dependent context (per `docs/REBUILD_PLAN.md`'s stage dependency ordering).
- The relevant Phase gate(s) in `docs/PHASE_GATES.md` pass.
- Deployed to staging and demonstrable.
- DoD review completed and logged before merge.

---

## 3. Tier 3 — Product Done (MVP)

LandVault is considered MVP-complete when a user can:

1. Register and authenticate (via Keycloak/Auth0).
2. Search for a property.
3. Request property verification.
4. Upload supporting documents.
5. Pay using Paystack (Nigeria) or Stripe (international).
6. Receive verification status and notifications.
7. Access a secure document vault.
8. Use the platform from desktop and mobile.

**Bounded-context coverage of this MVP list:** Identity (1), Registry + Spatial Intelligence (2), Workflow + Community Trust in a minimal form (3), Evidence (4, 7), Economic/Billing (5), Workflow/notifications (6), Frontend responsive design (8).

**Explicitly NOT required for this MVP definition:** Trust Engine's full multi-signal explainable scoring (M2.5), Knowledge Graph, and the deep Inheritance & Customary Law scope (death verification, family ownership chains, regime-based share calculation). These are real, substantial parts of the domain — confirmed by the audit to represent 8+ dedicated entities and significant UI in the Base44 build — and are deliberately sequenced after MVP, not silently dropped. **This scope-down requires the Operator's explicit sign-off; record any change to it as a Ratification Log entry or ADR amendment, not a silent edit to this file.**

At MVP, you have a real product, not a prototype.

---

## 4. Where this gate is invoked

- **Per PR** — Tier 1, mechanically checked by CI.
- **Per sprint (bounded context)** — Tier 2, human-reviewed before merge to main.
- **Per milestone (M0–M7 in `docs/REBUILD_PLAN.md`)** — rolls up to Tier 3 once all MVP-covering contexts are Sprint Done.

## 5. Non-negotiable blockers (never waivable)

- No entity/table without an RLS/authorization policy.
- No permissive fallback default on a security-relevant env var (CORS origin, signing secret, rate-limit toggle).
- No second/parallel authorization path outside the PDP/PEP.
- No scoring/validation function that can report a pass on zero/missing data.
- No feature marked complete without an *observed* passing test run.
