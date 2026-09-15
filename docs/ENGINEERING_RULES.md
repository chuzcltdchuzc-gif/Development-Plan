# Engineering Operating Rules

> **Governed by:** LV-000 — The LandVault Constitution, Edition v1.8, Working Edition, Revision H (`docs/LV-000-constitution.md`). These rules are subordinate to it. Where a rule and the Constitution appear to conflict, **the Constitution governs and the rule is corrected**.
>
> **Citation form:** every reference to the Constitution in this file carries its edition — for example *LV-000 v1.8, Article IX §3*.
>
> **Relationship to `CLAUDE.md`:** the non-negotiable rules listed in `CLAUDE.md` are an operationally critical **subset** of the rules in this file, renumbered for that shorter list. That is not a conflict — a document citing "Rule 1" or "Rule 9" must **name the file it means**.

This document defines how Claude Code works on this repository. Without these rules, every session starts making its own assumptions. `CLAUDE.md` restates the most load-bearing rules inline for every session; **this document is authoritative if the two ever diverge.**

Every rule below traces to a specific, confirmed defect found in the `landsecure-registry` (Base44) or `landverify-nigeria-101-NEW` (Emergent) audits — see `docs/audits/`. These aren't hypothetical concerns; they are the exact mechanisms that produced the worst findings in both prior builds of this product.

---

## 1. Authorization

**Rule:** No new entity/table ships without an RLS or PDP/PEP authorization policy in the *same commit* that creates it.

**Anchor:** LV-000 v1.8, Article VIII §2.

**Why:** Base44's `OrganizationWallet`, `ServiceRequest`, and `Invoice` entities all shipped with `update: {}` — an unconditional public-write policy — enabling any authenticated user to edit any organization's wallet balance or mark any invoice paid. Separately, 15 entities (including the entire inheritance/death-verification module) had **no RLS block at all**. Neither gap was ever caught because policy authoring was treated as a follow-up task, not part of the entity's definition.

**Rule:** There is exactly one authorization path: the PDP/PEP/PIP engine. No parallel or "legacy" auth system is ever introduced, for any reason, even temporarily.

**Anchor:** LV-000 v1.8, Article X §3.

**Why:** The Emergent build's audit found a fully separate, undocumented session-cookie RBAC system (`core/security.py`) running alongside its otherwise well-designed PDP/PEP engine, plus a `dev-login` endpoint with no environment gate at all that minted valid admin sessions to anyone. Two authorization systems means two places to get security right — this repo will only ever have one.

---

## 2. Secure-by-default configuration

**Rule:** No security-relevant environment variable may have a permissive fallback default. If it's unset, the application must fail to start, not silently degrade to an insecure default.

**Why:** Emergent's CORS origin defaulted to `"*"` combined with `allow_credentials=True` — meaning any website could make credentialed cross-origin requests unless an operator remembered to set `CORS_ORIGINS`. Its certificate-transparency-log signing key fell back to the literal string `"dev-signing-secret"` if unset. Both were exploitable purely by omission, not by any attacker action.

---

## 3. Scoring and validation honesty

**Rule:** Every automated scoring, validation, or health-check function must fail safe: missing or zero data yields a low/neutral/`INSUFFICIENT_DATA` result, never a passing score. See `docs/DOD.md` §1 for the corresponding test requirement.

**Anchor:** LV-000 v1.8, Article XII §3 (scoring fails safe on missing data, citing Article VI §3 and Article XI §1 in turn).

**Why:** Both audited builds had this exact defect independently. Base44's trust validation engine reported `100/A_PLUS/GO` with zero real evidence because its sub-checks used `if (condition) { passed++ } else { passed++ }` — incrementing "passed" regardless of outcome. Its own permission auditor validated a hardcoded internal table against itself rather than reading real policy config, so it could never detect the RLS gaps above. This is not a one-off bug pattern to fix once; it's a category this repo tests against by rule.

---

## 4. When Claude may act autonomously vs. must stop and ask

**Anchor:** LV-000 v1.8, Article XII §4 (an agent's grant of authority is explicit, recorded, and revocable; bulk or implicit grants of automation authority are prohibited).

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

**Anchor:** LV-000 v1.8, Article XI §4 (governed dependencies).

**Why:** Both audited codebases accumulated dependencies without a consistent review discipline (mixed SDK versions calling the same backend inconsistently in Emergent; an `emergentintegrations`/vendor-specific package pulled from a non-PyPI URL). Unreviewed dependencies are both a security surface and a lock-in risk.

---

## 6. Schema changes

**Rule:** Migrations must be reversible. A schema change ships with its matching RLS/policy update in the same commit (see §1). Rollback is tested in staging before the change reaches production — this is what standing review question 7 ("can this be rolled back in under two minutes?") is actually checking.

**Anchor:** LV-000 v1.8, Article XI §3 (reversible by default).

---

## 7. Never mark something complete without observing it pass

**Rule:** A feature, automation, or gate is only "complete" after Claude has actually run the relevant test/check and observed it pass — not inferred from code inspection alone.

**Anchor:** LV-000 v1.8, Article XI §2 (observed, not assumed).

**Why:** This is the single rule that would have caught the largest share of both audits' findings. Both prior builds had features self-reported as "CONNECTED" or "PASSED" in their own dashboards that were confirmed, on live testing, to be broken, insecure, or fabricating their output entirely. Static confidence is not evidence.

---

## 8. Commit/PR discipline

**Anchor:** LV-000 v1.8, Article XI §5 (one bounded context per change) for the first bullet below; the remaining bullets have no dedicated constitutional anchor and none is invented for them.

- One bounded context per PR where feasible.
- The DoD checklist (`docs/DOD.md`) is required in the PR description.
- Git hooks are never skipped (`--no-verify` is not used without explicit human authorization for that specific instance).
- Commit messages describe *why*, not just *what*.

---

## 9. Controlled Platform Authority

**Anchor: LV-000 v1.8, Article IX §3.** This rule is a step in the protected citation chain (LV-000 v1.8, Article III §4: *LV-000 Article IX §3 → `ENGINEERING_RULES.md` rule 9 → ADR-021 → ADR-022 → `PLATFORM_INTELLIGENCE_ARCHITECTURE.md` → B4 Threat Model → SCDS-001*). Its citation is retagged with this Edition; its text below is unchanged.

**Rule:** Any code path that needs authority beyond a single tenant's own RLS-scoped view — a
platform-wide or cross-tenant read or write — must be a **named, narrow, explicitly justified
exception**, never an implicit or general-purpose bypass. Every such exception must satisfy all
of:

- **Fixed at the call site** — its scope is not parameterized by arbitrary caller input; it does
  one specific, bounded thing, not an open-ended query shaped by whatever the request contains.
- **Read-only wherever possible** — a write requiring platform-wide authority is a strictly
  higher-risk case needing its own explicit justification beyond satisfying this rule.
- **As narrow as the task allows** — never "cross-tenant access" as a blanket grant; the
  narrowest operation that accomplishes the specific task, nothing broader.
- **Audited**, unless auditing that specific path is itself infeasible for a stated, reviewed
  reason. The one existing exception (below) is not a precedent for skipping audit elsewhere by
  default — it required its own explicit reasoning, and any new exception needs the same.

**Why:** This codebase already had two instances of this pattern before it was named as a
doctrine: the `super_admin` RLS bypass (`tenant_id = current_setting('app.tenant_id') OR
is_super_admin`, present in every tenant-scoped table's policy since migration `0001`) and the
context-hydration service-account's one fixed, read-only, rolled-back lookup
(`app.contexts.identity.context_hydration.build_production_context_hydrator` — not audited,
because it runs on every single authenticated request, an explicit, reasoned exception, not a
default). `docs/B4_THREAT_MODEL.md` §5 (trust boundary TB5) found that Spatial Intelligence's
overlap-detection feature needs a *third*, genuinely new instance of cross-tenant read access —
and in analyzing it, generalized what the first two already implied into this explicit,
platform-wide rule, rather than each future context re-deriving its own justification for
elevated reach from nothing. Any future bounded context that believes it needs platform-wide or
cross-tenant authority must satisfy this rule and cite it, not invent a fresh argument.

---

## 10. Non-adjudication check

*Added under `docs/GOVERNANCE_BASELINE.md` Part C.3, required by LV-000 v1.8 Article IV §4.*

**Rule:** A build shall fail on ownership-adjudication wording in API responses and user-facing text. The check is automated and runs in CI.

**Anchor:** LV-000 v1.8, Article IV §4.

**Why:** Article IV of the Constitution requires that the platform record assertions with provenance, never determinations of right, and that this be mechanically enforced rather than merely asserted — "a principle enforced only by good intentions is not enforced." It is required at minimum wherever ownership-related records are exposed — currently the Registry context's parcel endpoints, and any future Registry ownership/status-history work (see `docs/EXECUTION_PLAN.md` §7.5–7.6).

**Status: Implemented** (Phase 9, `docs/PHASE-9_IMPLEMENTATION_PLAN.md` / `docs/PHASE-9_ACCEPTANCE_PACKAGE.md`). Two independent scanning layers — a static AST-based scan of developer-authored source (`HTTPException detail=`, `description=` keyword arguments, and `api/`-directory docstrings, platform-wide across `backend/app/`) and a runtime scan of real API response content — run as part of the existing, already-required `pytest / ruff / mypy` CI job (`backend/tests/test_non_adjudication_check.py`, blocklist in `backend/tests/support/non_adjudication.py`). Both scanners' actual detection capability is proven by adversarial probes, not merely inferred from the absence of a hit; both are proven not to misfire on ADR-021's spatial classification vocabulary or on caller-submitted data. See the acceptance package for full observed evidence.
