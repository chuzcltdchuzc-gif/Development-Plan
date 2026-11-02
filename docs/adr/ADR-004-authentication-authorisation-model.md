# ADR-004 — Authentication & Authorisation Model

**Status:** Accepted (Keycloak vs. Auth0 left as an explicit open sub-decision — see below).
**Preserved as historical record of what was decided on 2026-07-13 and confirmed 2026-07-30 — not
edited retroactively.** §1 (the identity-provider choice, Keycloak vs. Auth0) is superseded by
`docs/adr/ADR-025-supabase-platform-baseline.md` (Proposed, 2026-07-30) — Supabase Auth is now the
forward target. **§2–§5 (the PDP/PEP/PIP policy engine, single authorization path, role-hierarchy
check, rate limiting) are unaffected and remain in force**, per ADR-025 §"Context" and E2.
**Date:** 2026-07-13

## Context

The Emergent audit's single most consequential finding was architectural, not a line-level bug: a fully separate, undocumented session-cookie RBAC system (`core/security.py`) ran in parallel with an otherwise well-designed PDP/PEP/PIP authorization engine, and neither the security contract (`contracts/v1/security/role_matrix.json`) nor any test suite covered the legacy path. On top of that, a `dev-login` endpoint had **no environment gate at all** and minted valid admin sessions to any unauthenticated caller; `ENABLE_TEST_ENDPOINTS` defaulted to `true` rather than `false`; and `assign_role` had no check preventing a `compliance_officer` from promoting themselves to `super_admin`.

Base44 had no backend authorization at all — every "who can approve this" check was a client-side `if (user.role === ...)` with the corresponding backend entity either unprotected or protected by RLS with the same class of gaps described in ADR-003.

The PDP/PEP/PIP design itself — a Policy Decision Point evaluating registered policies per bounded context, a Policy Enforcement Point wrapping every route, a Policy Information Point supplying attributes — was audited as **structurally sound and fail-closed by design** (an unmatched or erroring policy denies, never permits). The defect was letting a second system exist beside it, and a handful of specific implementation gaps (rate limiting defaulted off in the actual app wiring despite the module defaulting on; tenant/country isolation policies silently no-opping when a resource descriptor omitted `tenant_id`; a 24-hour compromised-key grace window with no hard-revoke).

## Decision

1. **Authentication (who are you) is delegated to an external IdP** — **Keycloak** (self-hosted, open-source) as the default, with **Auth0** as a faster-to-bootstrap alternative if the team wants a managed option initially. This removes an entire class of custom-auth bugs (password hashing, MFA, OAuth flow correctness, JWT signing-key issuance and rotation) by not reimplementing them.
   - **Open sub-decision:** Keycloak vs. Auth0 is not yet finalized. Recommendation: Keycloak, because a land-registry platform handling government/citizen PII benefits from self-hosted data residency and avoids per-monthly-active-user pricing at pilot scale; Auth0 remains the fallback if faster initial setup outweighs those concerns. This ADR will be updated (not silently edited — see the Governance Amendment Procedure in `docs/PHASE_GATES.md`) once decided.
2. **Authorization (what can you do) — the PDP/PEP/PIP engine is retained in full**, ported from the Emergent design:
   - The PEP verifies every incoming request's JWT against the IdP's JWKS endpoint (not a self-issued KeyStore — Keycloak/Auth0 own key rotation now).
   - The PDP evaluates registered per-bounded-context policies (see each context's `authorization.py`-equivalent) and **fails closed**: no matching policy, an error, or ambiguity all result in denial, never permission.
   - Tenant and country scoping is enforced at **two independent layers** — the PDP resource descriptor AND the Postgres repository/RLS layer (ADR-003) — so a caller who forgets to populate one still cannot bypass the other.
3. **There is exactly one authorization path.** No session-cookie fallback, no `dev-login`, no test-mode-by-default endpoint ever ships. Test/seed data creation is always explicitly environment-gated (see `docs/ENGINEERING_RULES.md` §2 and §7).
4. Role assignment requires an explicit **hierarchy check**: a principal can never grant a role higher than their own, and never to themselves for the purpose of elevation. This is a direct fix for the confirmed Emergent `assign_role` privilege-escalation path.
5. Rate limiting is on by default with no override that silently disables it in production; the client-IP source used for rate limiting and audit logging is only trusted behind a configured reverse-proxy allowlist, never a raw `X-Forwarded-For` header.

## Consequences

- Significantly less custom authentication code to write and maintain than either prior build attempted (see `docs/REBUILD_PLAN.md` B1/B2 effort reduction).
- The PDP/PEP engine remains the one piece of genuine, reusable intellectual property from the Emergent codebase — its design survives the rebuild even though almost none of its literal code does (JWT issuance/KeyStore code is now Discard; PDP/PEP/PIP decision logic is Reuse).
- Requires role/tenant/permission data to be maintained in our own Postgres, joined to the IdP's stable subject (`sub`) claim — an explicit synchronization point (first-login provisioning or IdP webhook) that must itself be covered by the DoD's "every new entity ships with an authorization policy" rule.
