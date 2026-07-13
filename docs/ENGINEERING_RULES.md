# Engineering Operating Rules

This document defines how Claude Code works on this repository. Without these rules, every session starts making its own assumptions. `CLAUDE.md` restates the most load-bearing rules inline for every session; **this document is authoritative if the two ever diverge.**

Every rule below traces to a specific, confirmed defect found in the `landsecure-registry` (Base44) or `landverify-nigeria-101-NEW` (Emergent) audits — see `docs/audits/`. These aren't hypothetical concerns; they are the exact mechanisms that produced the worst findings in both prior builds of this product.

---

## 1. Authorization

**Rule:** No new entity/table ships without an RLS or PDP/PEP authorization policy in the *same commit* that creates it.

**Why:** Base44's `OrganizationWallet`, `ServiceRequest`, and `Invoice` entities all shipped with `update: {}` — an unconditional public-write policy — enabling any authenticated user to edit any organization's wallet balance or mark any invoice paid. Separately, 15 entities (including the entire inheritance/death-verification module) had **no RLS block at all**. Neither gap was ever caught because policy authoring was treated as a follow-up task, not part of the entity's definition.

**Rule:** There is exactly one authorization path: the PDP/PEP/PIP engine. No parallel or "legacy" auth system is ever introduced, for any reason, even temporarily.

**Why:** The Emergent build's audit found a fully separate, undocumented session-cookie RBAC system (`core/security.py`) running alongside its otherwise well-designed PDP/PEP engine, plus a `dev-login` endpoint with no environment gate at all that minted valid admin sessions to anyone. Two authorization systems means two places to get security right — this repo will only ever have one.

---

## 2. Secure-by-default configuration

**Rule:** No security-relevant environment variable may have a permissive fallback default. If it's unset, the application must fail to start, not silently degrade to an insecure default.

**Why:** Emergent's CORS origin defaulted to `"*"` combined with `allow_credentials=True` — meaning any website could make credentialed cross-origin requests unless an operator remembered to set `CORS_ORIGINS`. Its certificate-transparency-log signing key fell back to the literal string `"dev-signing-secret"` if unset. Both were exploitable purely by omission, not by any attacker action.

---

## 3. Scoring and validation honesty

**Rule:** Every automated scoring, validation, or health-check function must fail safe: missing or zero data yields a low/neutral/`INSUFFICIENT_DATA` result, never a passing score. See `docs/DOD.md` §1 for the corresponding test requirement.

**Why:** Both audited builds had this exact defect independently. Base44's trust validation engine reported `100/A_PLUS/GO` with zero real evidence because its sub-checks used `if (condition) { passed++ } else { passed++ }` — incrementing "passed" regardless of outcome. Its own permission auditor validated a hardcoded internal table against itself rather than reading real policy config, so it could never detect the RLS gaps above. This is not a one-off bug pattern to fix once; it's a category this repo tests against by rule.

---

## 4. When Claude may act autonomously vs. must stop and ask

**Claude may proceed without asking when:**
- The change is in-scope of the current bounded context/sprint.
- Tests are green before and after the change.
- No database schema change is involved.
- No new external dependency is introduced.

**Claude must stop and ask a human when:**
- The change crosses bounded-context boundaries.
- A database schema or migration change is involved.
- A new external dependency would be introduced.
- The change touches authentication, authorization, payments, or evidence integrity.
- Any data deletion is involved.
- Requirements are ambiguous or conflict with an existing ADR.
- Anything irreversible in production is about to happen.
- The work is legal/compliance-adjacent (e.g. customary-law share-calculation logic, death-verification handling).

---

## 5. Dependencies

**Rule:** Adding a new dependency requires explicit human approval, a justification in the PR description, and a pinned version.

**Why:** Both audited codebases accumulated dependencies without a consistent review discipline (mixed SDK versions calling the same backend inconsistently in Emergent; an `emergentintegrations`/vendor-specific package pulled from a non-PyPI URL). Unreviewed dependencies are both a security surface and a lock-in risk.

---

## 6. Schema changes

**Rule:** Migrations must be reversible. A schema change ships with its matching RLS/policy update in the same commit (see §1). Rollback is tested in staging before the change reaches production — this is what standing review question 7 ("can this be rolled back in under two minutes?") is actually checking.

---

## 7. Never mark something complete without observing it pass

**Rule:** A feature, automation, or gate is only "complete" after Claude has actually run the relevant test/check and observed it pass — not inferred from code inspection alone.

**Why:** This is the single rule that would have caught the largest share of both audits' findings. Both prior builds had features self-reported as "CONNECTED" or "PASSED" in their own dashboards that were confirmed, on live testing, to be broken, insecure, or fabricating their output entirely. Static confidence is not evidence.

---

## 8. Commit/PR discipline

- One bounded context per PR where feasible.
- The DoD checklist (`docs/DOD.md`) is required in the PR description.
- Git hooks are never skipped (`--no-verify` is not used without explicit human authorization for that specific instance).
- Commit messages describe *why*, not just *what*.
