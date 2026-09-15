# Phase 9 Implementation Plan — Engineering Rules §10 (Non-Adjudication Automated Check)

**Status of this document:** Investigation and plan only. No §10 implementation code exists as a
result of this document. See §19.

**Date:** 2026-07-31
**Prior slice:** ADR-023 (Registry Ownership and Status History) — Accepted, Implemented, Merged
(`1601564`). Not reopened, not modified in substance by this document.

---

## 1. Purpose

Determine precisely what Engineering Rules §10 requires, verify what already exists against that
requirement, identify the exact gap, and propose a narrowly-scoped, evidence-traceable
implementation — without writing implementation code. This document is a plan submitted for
Governance Authority review, not an implementation.

---

## 2. Governing sources (read in full or by targeted section for this document)

- `docs/LV-000-constitution.md` — Article IV (Evidence over assertion, and non-adjudication), §§1–4;
  Article VI §4 (Trust Network Doctrine, foundation for `PLATFORM_INTELLIGENCE_ARCHITECTURE.md`);
  Article IX §3 (Controlled Platform Authority); Article XV §1 (Trust Neutrality Firewall).
- `docs/ENGINEERING_RULES.md` §10 (Non-adjudication check) and §9 (Controlled Platform Authority,
  for the false-positive boundary against cross-tenant intelligence).
- `docs/GOVERNANCE_BASELINE.md` Part C.3 — the rule's origin, verbatim-identical text to §10.
- `docs/EXECUTION_PLAN.md` §7.5 ("The non-adjudication safeguard") and §7.6 (test matrix item),
  and the traceability table at its top (Article I §3–§4, Article IV, mapped to §7.5/§7.6).
- `docs/adr/ADR-023-registry-ownership-and-status-history.md` — the "assertion, never a
  determination" data model this check protects; explicitly states the non-adjudication check is
  out of scope for that ADR and tracked separately (unchanged by this document).
- `docs/adr/ADR-013-parcel-aggregate-registry-domain-model.md` — `current_owner_name`/
  `current_owner_contact` as a *current reference*, never a determination (invariant #12).
- `docs/adr/ADR-021-spatial-conflict-detection-and-controlled-cross-tenant-intelligence.md` — the
  six-category conflict classification model (`no conflict / boundary overlap / duplicate / near
  duplicate / suspicious pattern / confirmed conflict`) and its explicit "this ADR does not itself
  adjudicate" framing — the primary false-positive risk surface for this check, in both current and
  future form.
- `docs/adr/ADR-015-registry-mutation-authorization-model.md` — confirms Registry's mutation
  authorization is unrelated to and does not overlap with the wording-check concern.
- `docs/adr/ADR-022-spatial-authorization-model.md` — confirms Spatial's authorization model; no
  adjudication-adjacent wording found in its own text.
- `CLAUDE.md` — "6 non-negotiable rules" summary (§10 is not among the 6, i.e. not yet treated as
  load-bearing-enough to summarize there — consistent with it being unimplemented); B4 status notes
  confirming no spatial conflict-detection code exists yet.
- `docs/PHASE-1_IMPLEMENTATION_PLAN.md` — records §10 as explicitly out of scope for ADR-023,
  "tracked separately."
- `docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md` — the four-part "is this Platform Intelligence"
  test (cross-context/cross-tenant read, produces a finding never a domain mutation, one named
  Controlled Platform Authority exception, narrow signal-only downstream consumption) — read for
  the same false-positive boundary as ADR-021: findings/signals are not determinations.
- `AGENTS.md` — no §10-specific content found; general agent-operating rules only, consistent with
  `docs/ENGINEERING_RULES.md` governing.

No file above was skipped in favour of memory or a prior agent's claim; each citation below traces
to a specific section read during this investigation.

---

## 3. Current §10 requirement (exact text, not paraphrased)

`docs/ENGINEERING_RULES.md` §10:

> **Rule:** A build shall fail on ownership-adjudication wording in API responses and user-facing
> text. The check is automated and runs in CI.
>
> **Anchor:** LV-000 v1.8, Article IV §4.

`docs/LV-000-constitution.md`, Article IV:

> **§1.** The platform records **assertions with provenance**, never determinations of right.
> **§2.** No schema field, API response, user-interface label, report, export, notification, or
> marketing statement may assert, imply, or be reasonably read as asserting that LandVault has
> determined title, ownership, or the outcome of a competing claim.
> **§4.** Compliance with this Article shall be **mechanically enforced**, not merely asserted. The
> platform shall carry an automated check that fails the build on ownership-adjudication wording in
> API responses and user-facing text.

**Reading:** §2 names a broader set of surfaces (schema field, API response, UI label, report,
export, notification, marketing statement) as constitutionally *prohibited* from adjudicating.
§4's *mechanical-enforcement mandate* — and §10's rule text, which restates §4 verbatim in scope —
is narrower and specific: **API responses and user-facing text**. The automated check's required
scope is therefore API responses and user-facing text; the broader §2 list (reports, exports,
marketing copy) is constitutionally bound but not yet named as requiring an *automated* check by
§4/§10's own text. This plan does not expand §4/§10's stated scope to cover those other surfaces —
doing so would be a new decision this document is not authorized to make (see §6, §9 non-scope).

---

## 4. Current implementation state (observed, not assumed)

- `grep -rl "adjudicat" backend/ docs/` finds **zero occurrences inside `backend/app/`** — no
  application code anywhere references or implements this check.
- `backend/tests/test_registry_ownership_status_history.py` (lines 260–262) contains an explicit
  disclaimer comment: *"Non-adjudication wording check is tracked separately... this test matrix
  does not claim to satisfy it, exactly as ADR-023 itself states."* This is the one place in the
  codebase that currently acknowledges the gap in-line.
- `backend/app/contexts/registry/api/dtos.py` and `parcel_router.py`: response bodies are plain
  field dictionaries (`_parcel_view()` in `parcel_service.py`) — no free-text sentences are
  currently emitted by Registry's API. Field names (`current_owner_name`,
  `current_owner_contact`) use "owner" vocabulary but are documented, per ADR-013 invariant #12, as
  a *current reference*, never a determination — consistent with Article IV §1 today, by
  construction, not by any enforced check.
- `backend/app/contexts/registry/domain/history.py`: `OwnershipAssertion`/`StatusAssertion` are
  explicitly named and documented as assertions ("who asserted what, on what basis, when — never a
  determination of who owns the parcel", per the module docstring, citing LV-000 v1.8 Article IV) —
  the domain model is already aligned with Article IV's requirement, independent of any wording
  check.
- No spatial conflict-detection code exists anywhere in the codebase (`backend/app/contexts/
  spatial/` has geometry validation and parcel-existence adapters only — confirmed by direct
  listing). ADR-021's six-category classification model, the primary false-positive risk surface
  for adjudication-adjacent-sounding vocabulary ("confirmed conflict"), is architecture-only, not
  implemented, and explicitly unauthorized for implementation (`CLAUDE.md`: "B4 Slice 3 is not
  authorized... none begins until ADR-021 is reviewed and explicitly accepted").
- No frontend parcel-facing UI exists (`frontend/app`, `frontend/components` are scaffold only;
  `docs/EXECUTION_PLAN.md` requires F1 — authenticated API call — before any parcel-journey UI is
  built). A targeted grep of `frontend/` for ownership/adjudication-adjacent wording found nothing,
  because there is currently nothing there to find.
- `backend-ci.yml` / `frontend-ci.yml` (both post-Phase-8 CI-fix versions): no step of any kind
  references non-adjudication, wording checks, or content scanning.

---

## 5. Gap analysis

**Precise gap:** No automated, CI-executed check exists anywhere in this repository that would
fail a build on ownership-adjudication wording in Registry's (or any other context's) API
responses. The current absence of such wording is a byproduct of careful data modelling in
ADR-013/ADR-023, not of any enforced control. Article IV §4's own language — "a principle enforced
only by good intentions is not enforced" — describes exactly this state.

**What is NOT a gap** (already satisfied, no action needed):
- The domain model correctly represents assertions, not determinations (ADR-023, ADR-013).
- Registry's current API responses contain no adjudicating wording (verified by direct
  inspection of the only response-shaping code, `_parcel_view()`).
- No conflict-detection or trust-scoring code exists yet that could introduce adjudicating
  language — there is nothing there to check yet, and building it is explicitly unauthorized
  pending ADR-021 acceptance (unrelated to this document).

---

## 6. Required investigation — answers

### 6.1 What is prohibited?

Per Article IV §2 and §10's rule text: any schema field, API response, or user-facing text that
**asserts, implies, or could reasonably be read as asserting** that LandVault has **determined**
title, ownership, or the outcome of a competing claim. The prohibition is on the *epistemic stance*
of the wording (LandVault speaking as the decider) — not on the underlying facts being described
(who currently claims what, per whose assertion). "Recorded as asserted by X, on basis Y" is
compliant; "confirmed as belonging to X" or "X is the rightful owner" is not.

### 6.2 What must be automatically checked?

From the rule's own text ("API responses and user-facing text") and `EXECUTION_PLAN.md` §7.6's
restatement ("an automated check that fails the build on ownership-adjudication language in
**responses** and **user-facing text**"): this is a **prohibited-terminology / wording check**,
not a static-analysis-of-logic check, not a schema-shape check, not an authorization check. It
must operate on the actual text a caller/user would see — i.e. rendered response content and
UI-facing strings — not on internal variable names, database column names in isolation, or
engineering documentation that discusses the concept of adjudication abstractly (this document and
the ADRs it cites use words like "confirmed" and "determine" routinely when *describing the rule
itself*; scanning documentation would be a false-positive generator with no constitutional basis —
§4/§10 name "API responses and user-facing text," not documentation).

### 6.3 Where should the enforcement live?

The narrowest appropriate point, per repository evidence: **inside the existing `pytest` step of
`backend-ci.yml`**, alongside the existing hermetic test suite. `backend-ci.yml` already runs on
every backend-touching PR/push and is a required branch-protection status check (`pytest / ruff /
mypy`) — satisfying §10's "runs in CI, fails the build" requirement with zero new CI
infrastructure. No new service, no new workflow file, no new external dependency is indicated by
any evidence gathered.

### 6.4 What existing implementation is already compliant?

- `OwnershipAssertion`/`StatusAssertion` (ADR-023) and the Parcel aggregate's
  current-owner-as-reference model (ADR-013) — the data model this check protects is already
  correctly shaped.
- Registry's actual current response payloads contain no adjudicating wording today (§4 above).

Nothing here should be duplicated or rebuilt by the §10 slice.

### 6.5 What is currently missing?

An automated, CI-executed, evidence-observed check — of any form — that would catch a *future*
regression (a new endpoint, a new error message, a new field description, or later a Spatial
Intelligence or Trust Engine output) that introduces adjudicating wording. Nothing currently
prevents this by mechanism; only by the absence, so far, of anyone writing such wording.

### 6.6 What would constitute a false positive?

Identified from direct repository evidence, not hypothetically:

- **ADR-021's six-category spatial classification vocabulary** — "confirmed conflict" describes a
  *geometric* finding (two geometries overlap), never an ownership determination; ADR-021 §5
  explicitly states the ADR "does not itself adjudicate" the Registry-level consequence. A check
  that flags the bare word "confirmed" or "conflict" would misfire on this legitimate, already-
  reviewed vocabulary the moment B4 Slice 3 is ever authorized and built.
- **`current_owner_name`/`current_owner_contact` as field identifiers or as echoed user-submitted
  data.** The word "owner" appearing as a schema/field name, or inside a value a user themselves
  typed in (e.g. a person legitimately named "Ade Owens", or a free-text address containing
  "Owner's Court Estate"), is not adjudicating wording — it is data, not a LandVault-authored
  assertion of determination. **The check's target must be developer-authored, static prose
  strings (docstrings, field `description=`, hardcoded messages, error `detail=` text) — never
  dynamic values a caller supplied and the API echoes back.** Conflating the two would make the
  check both useless (can't ship a "Name" field) and constantly triggering.
- **Trust/Platform Intelligence "signal" language** (`docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md`)
  — a finding, score, or signal is not a determination as long as it is presented as advisory input,
  per that document's four-part test. Words like "verified", "confirmed", or "trust score" used in
  that advisory sense are legitimate; the same words used to assert *ownership* specifically are
  not. The check must be scoped to ownership/title assertions, not to every occurrence of words
  like "confirmed" or "verified" platform-wide.
- **This document, the ADRs, and engineering-rule files themselves** — they discuss adjudication as
  a concept extensively. §10's scope is API responses and user-facing text, not documentation.

### 6.7 What would constitute a false negative?

- A developer builds an adjudicating string via runtime concatenation/formatting
  (`f"{prefix} owner"`) such that no single source-level literal contains the full banned phrase —
  a purely static source-grep check would miss this. **Mitigation:** the check must also exercise
  actual API responses at test time (hit real endpoints through the existing hermetic
  `TestClient` + fakes harness already used by every other Registry test) and scan the *rendered*
  response text, not only source literals.
- A developer adds adjudicating wording to a new context this check's file-scope doesn't cover
  (e.g. a future Spatial or Trust Engine endpoint) if the check is hardcoded to only scan Registry
  paths. **Mitigation:** scope the check to *all* API response text platform-wide (every router,
  every DTO description, every `HTTPException detail=`), not just Registry — the constitutional
  anchor (Article IV §2) is not Registry-specific, only today's *known instance* of the risk is.
- A developer adds the wording only to frontend copy, which this backend-CI-based check cannot see.
  **Mitigation:** explicitly recorded as a known, current scope boundary (§9), not silently missed
  — no frontend parcel UI exists yet to check, and this plan does not claim frontend coverage.
- The blocklist itself is incomplete (a new phrase not anticipated). **Mitigation:** this is
  inherent to any keyword/phrase-based mechanical check and cannot be fully eliminated by
  mechanism alone — recorded as a residual risk (§14), mitigated by the existing PR-review
  discipline (`ENGINEERING_RULES.md` §8) as defense-in-depth, consistent with Article IV §4's
  "mechanically enforced, not merely asserted" standard (mechanical enforcement as the floor, not
  a claim of perfection).

---

## 7. Traceability matrix

| Requirement | Constitutional/Governance Source | Engineering Rule | Existing Code | Existing Test | Gap | Proposed Enforcement |
|---|---|---|---|---|---|---|
| Records are assertions with provenance, never determinations | LV-000 Art. IV §1 | ENGINEERING_RULES §10 (context) | `domain/history.py` (`OwnershipAssertion`/`StatusAssertion`) | `test_registry_ownership_status_history.py` | None — already satisfied | N/A |
| No field/response/UI-label may assert determined title/ownership/claim outcome | LV-000 Art. IV §2 | ENGINEERING_RULES §10; EXECUTION_PLAN §7.5 | `_parcel_view()` (no adjudicating text today) | None dedicated | No automated guarantee this stays true | Static + response-content wording check (§10–13 below) |
| Compliance mechanically enforced, build fails on violation, runs in CI | LV-000 Art. IV §4 | ENGINEERING_RULES §10 | None | None | Check does not exist | New pytest-based check in existing `backend-ci.yml` `pytest` step |
| Current-owner fields are a reference, not a determination | ADR-013 invariant #12 | — | `Parcel` aggregate | Existing Parcel tests | None — already satisfied | N/A |
| Non-adjudication check explicitly out of scope for ADR-023 | ADR-023; PHASE-1 plan | — | — | — | N/A — correctly deferred, not this document's job to relitigate | N/A |
| Spatial conflict-classification vocabulary must not be misread as ownership adjudication | ADR-021 §5 (does not itself adjudicate); Art. IV §2 | ENGINEERING_RULES §9 (Controlled Platform Authority, adjacent doctrine) | None — B4 Slice 3 unauthorized, no code exists | None | N/A today; false-positive risk for §10's design, not a missing control | Design constraint on §10's blocklist (§6.6) — no code to check yet |
| Frontend user-interface labels must not adjudicate | LV-000 Art. IV §2 ("user-interface label") | ENGINEERING_RULES §10 ("user-facing text") | None — no parcel UI built yet | None | N/A today — nothing to scan | **NOT AUTHORIZED — deferred to when frontend parcel UI exists**, recorded as explicit non-scope (§9) |
| Reports, exports, marketing statements must not adjudicate | LV-000 Art. IV §2 | Art. IV §4 / §10 scope this narrower (API responses + user-facing text) | None exists | None | Not required by §4/§10's own stated automated-check scope | **NOT AUTHORIZED — outside §4/§10's stated scope**; expanding it would be a new decision, not this document's to make |

Every proposed enforcement above traces to an existing requirement. Nothing in this plan requires
inventing a new principle.

---

## 8. Scope

- One new automated check, added to the existing `backend-ci.yml` `pytest` step (no new CI
  workflow), that:
  1. Statically scans developer-authored string literals in Registry's (and, per §6.7's
     false-negative analysis, platform-wide backend) API-facing code — DTO field `description=`
     values, route/response docstrings intended as OpenAPI-exposed text, and `HTTPException
     detail=` string literals — against a reviewed blocklist of ownership-adjudication phrases.
  2. Exercises the existing hermetic API test harness (`tests/app_factory.py`) to call real
     Registry endpoints and scans the *rendered* JSON response text for the same blocklist, on
     both realistic legitimate inputs and adversarial inputs designed to probe for
     adjudication-shaped output.
  3. Fails the build (non-zero exit from `pytest`) if either scan matches.
- A documented, reviewed blocklist definition (exact phrases, not single bare keywords like
  "owner" or "confirmed" — see §6.6), committed as source alongside the check, so the boundary is
  auditable and amendable through normal PR review rather than opaque.
- Documentation updates: `docs/ENGINEERING_RULES.md` §10 marked implemented once the check is
  observed passing in CI; `CLAUDE.md` cross-reference if appropriate.

## 9. Non-scope (explicitly excluded)

- Ownership adjudication, title determination, or any legal-ownership decision logic — this slice
  detects *wording*, it does not add, remove, or alter any ownership-determination capability
  (none exists, and none is being proposed).
- Any new ownership-transfer command (ADR-015/ADR-023 leave this undecided; unrelated to §10).
- Any new AI decision authority of any kind.
- Any new constitutional doctrine, amendment, or reinterpretation of Article IV.
- Frontend/UI-layer scanning — no parcel-facing frontend exists yet to scan; deferred to whenever
  that UI is built, as its own future increment, not authorized here.
- Reports, exports, notifications, or marketing-copy scanning — named by Article IV §2 as
  constitutionally bound but not named by Article IV §4/§10 as requiring an *automated* check;
  expanding automated coverage to these surfaces would be a new decision, not made here.
- Spatial conflict-detection implementation of any kind (B4 Slice 3) — remains gated on ADR-021's
  own explicit acceptance, entirely unrelated to and not advanced by this document.
- Any unrelated Registry enhancement or infrastructure work.

## 10. Proposed architecture / enforcement point

No new architectural component. The check is two pytest test functions (static-scan +
response-content-scan) living under `backend/tests/`, executed by the existing `pytest -q`
invocation inside `backend-ci.yml`'s already-required `pytest / ruff / mypy` job. No new port, no
new adapter, no new bounded context, no new dependency (a phrase-match scan needs only the Python
standard library).

## 11. Test matrix

| # | Scenario | Expected result | Enforcement layer | Failure meaning |
|---|---|---|---|---|
| 1 | Static scan of current DTO/router/service source for blocklisted phrases | No match | Static source scan | A developer-authored string in source now contains adjudicating wording |
| 2 | `GET /v1/parcels/{id}` on a parcel with an ownership reference set | Response contains the reference fields, no adjudicating sentence | Response-content scan | Endpoint now emits adjudicating text |
| 3 | `POST /v1/parcels` create, `PATCH` update changing owner fields, `POST /archive` | All three responses free of blocklisted phrases | Response-content scan | A mutation response introduces adjudicating text |
| 4 | Deliberately inject a blocklisted phrase into a test-only DTO field description (adversarial probe, then reverted) | Check **fails** | Static scan | Proves the check actually detects a violation, not just absence of evidence |
| 5 | Deliberately inject a blocklisted phrase into a test-only response payload (adversarial probe via a test double, then reverted) | Check **fails** | Response-content scan | Proves the runtime scan actually detects a violation |
| 6 | `current_owner_name` set to a value containing a blocklisted *word* as ordinary data (e.g. a name or address containing "Owner") | Check **passes** — no false positive | Both layers | Confirms the check targets developer-authored strings, not user data |
| 7 | HTTPException `detail=` messages already in the codebase (403 "only the parcel's creator or a governance role may modify it", 404, 409, 400 messages) | Check **passes** | Static scan | Confirms existing legitimate error text is not misclassified |
| 8 | Hypothetical ADR-021-style vocabulary ("confirmed conflict") used in a Spatial-context test fixture, not an ownership context | Check **passes** — no false positive | Static + response scan | Confirms spatial classification language is not conflated with ownership adjudication |
| 9 | Full existing hermetic suite (158 tests) | All still pass, unaffected | `pytest -q` | Confirms the new check does not regress existing behaviour |

Items 1–3 and 9 are the required-passing baseline; items 4–5 are the adversarial "does it actually
detect" proof (mirrors the discipline used for the ADR-023 live-rollback rehearsal — observed
detection, not assumed); items 6–8 are the required false-positive proof.

## 12. False-positive protection

The check's target is restricted to **developer-authored static prose** (DTO field descriptions,
docstrings meant for OpenAPI exposure, hardcoded `detail=`/message strings) — never user-submitted
data values, however they're echoed back. The blocklist is **multi-word phrases expressing a
determination-of-right claim** ("confirmed owner", "rightful owner", "legally owns", "title is
valid", "ownership has been determined", etc.) — never bare single words like "owner", "confirmed",
"verified", or "conflict" in isolation, precisely because those single words are legitimate
elsewhere (field names, ADR-021's classification vocabulary, Platform Intelligence's advisory
signal language). Test-matrix items 6–8 make this an observed property, not an assumed one.

## 13. False-negative protection

Two independent layers (static source scan + rendered-response scan, §6.7) catch both
literal-string violations and runtime-constructed ones. Scope is platform-wide across backend API
surfaces, not hardcoded to Registry only, so a violation introduced in a future context is still
caught. Residual risk (a genuinely novel phrasing not on the blocklist) is named explicitly as a
limitation of any keyword-based mechanical check (§6.7, §14) — not claimed to be eliminated, only
mechanically enforced to the extent Article IV §4 requires, with PR review as the acknowledged
second layer.

## 14. CI integration

Add the two new test functions to the existing `backend/tests/` tree; no change to
`backend-ci.yml` itself is required — they run automatically as part of the already-required
`pytest / ruff / mypy` job's `pytest -q` step. No new workflow, no new required status-check
context, no branch-protection change.

## 15. Backward compatibility

No existing endpoint, DTO, domain object, or authorization path changes. The check is additive
(new tests only). All 158 existing hermetic tests, `ruff`, and `mypy` are expected to remain green
unchanged — this plan proposes no modification to B1–B4 behaviour of any kind.

## 16. Rollback

Revert the single commit/PR that adds the new test file(s) and blocklist definition. No migration,
no schema change, no data involved — rollback is a plain git revert with no follow-up steps.

## 17. Acceptance criteria

- The two new test functions exist, are collected by `pytest -q`, and pass against current `main`.
- Test-matrix items 4–5 (adversarial probes) are demonstrated to fail the check when the violation
  is present, and to pass once reverted — observed, not assumed (`ENGINEERING_RULES.md` §7).
- Test-matrix items 6–8 (false-positive proofs) pass.
- `ruff check .` and `mypy app tests` remain clean.
- Full `pytest -q` remains green (158 + new items, 1 skipped as before).
- `docs/ENGINEERING_RULES.md` §10 updated from "not yet implemented" to implemented, with the
  evidence location cited, only after the above is observed — never marked done in advance
  (`ENGINEERING_RULES.md` §7).

## 18. Definition of Done

- [ ] Implementation complete (pending authorization — not started)
- [ ] Tests complete
- [ ] Negative cases (adversarial probes) tested and observed failing pre-fix / passing post-fix
- [ ] Positive/legitimate cases (ADR-021 vocabulary, user data, existing error messages) tested and
      observed passing
- [ ] `ruff` clean
- [ ] `mypy` clean
- [ ] Full `pytest` green
- [ ] CI green
- [ ] Documentation updated (`ENGINEERING_RULES.md` §10, `CLAUDE.md` if warranted)
- [ ] Traceability complete (§7 matrix, no untraced control introduced)
- [ ] No constitutional drift — Article IV not reinterpreted or expanded beyond §4's own stated
      scope
- [ ] No architectural decision introduced without an ADR (§19 — none identified as necessary)

None of the above is checked yet. This is the plan, not the execution.

---

## 19. Governance / ADR determination

**Conclusion: (A) No new ADR required.**

Evidence:

- The *existence* of this check, its constitutional basis, its required scope ("API responses and
  user-facing text"), and its enforcement standard ("mechanically enforced... fails the build...
  runs in CI") are already fully and specifically decided — at constitutional level (Article IV
  §§1–4), at governance-baseline level (`GOVERNANCE_BASELINE.md` Part C.3, identical text), and at
  engineering-rule level (`ENGINEERING_RULES.md` §10, identical text again). Three independent,
  already-ratified documents state the same requirement in the same words. There is no decision
  left to make about *whether* or *what* — only *how*, mechanically, to implement it.
- The proposed mechanism (two pytest functions, phrase-blocklist scan, running inside the already-
  required `backend-ci.yml` `pytest` step) introduces: no new bounded context, no new authorization
  path, no new external dependency, no schema/migration change, no cross-context boundary crossing,
  and no change to authentication, authorization, payments, or evidence integrity. Per
  `ENGINEERING_RULES.md` §4, none of the "must stop and ask a human" triggers apply to the
  *mechanism* itself (though this document stops anyway, per this task's explicit instruction, for
  plan approval before any code is written).
- Where this plan's scope stops short of the constitution's full §2 list (reports, exports,
  marketing copy) or extends to a surface not yet built (frontend), it says so explicitly (§9) and
  declines to decide the question, rather than quietly deciding it either way.

> **No new architectural decision identified; implementation is directly governed by the existing
> constitutional and engineering requirements.**

---

**IMPLEMENTATION STATUS: NOT YET AUTHORIZED**

This plan is submitted for Governance Authority review. No §10 implementation code has been
authorized by this task.
