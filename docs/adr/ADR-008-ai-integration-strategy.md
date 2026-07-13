# ADR-008 — AI Integration Strategy

**Status:** Accepted (scope may narrow further at Phase 6 kickoff — see `docs/PHASE_GATES.md`)
**Date:** 2026-07-13

## Context

Neither prior build implemented a real AI layer. Base44's job-queue inventory explicitly listed OCR processing as a defined job type with **no implementation behind it** ("OCR Jobs — MISSING, no function"). Its various "trust validation," "fraud detection," and "readiness scoring" functions were rule-based, not AI/ML, and — per ADR-002/`docs/DOD.md`'s non-negotiable scoring-honesty rule — several of them were confirmed to be actively dishonest (reporting a perfect score regardless of input), which is a cautionary example for *any* automated scoring this rebuild adds, AI-based or not.

Emergent's own Foundation Specification (an internal governance document found during the audit) already stated an immutable design principle directly relevant here: **"AI is advisory only, never authoritative."** The audit found no violation of that principle, because no AI feature had been built yet to violate it — but the principle itself is sound and worth carrying forward explicitly rather than rediscovering.

## Decision

Scope AI Integration concretely, rather than leaving Phase 6 generic:

1. **OCR / document classification** for Evidence uploads (survey plans, family agreements, death certificates, court orders) — extracting structured fields and a document-type classification to assist (not replace) human/community verification.
2. **AI-assisted signals feeding the Trust Engine as advisory input only, never authoritative.** The Trust Engine's score remains an explainable, rule-based aggregation of real signals (Evidence integrity, Spatial duplicate-geometry, Survey completion, Community consensus — see `docs/REBUILD_PLAN.md` B7); any AI-derived signal is one more named, weighted, *inspectable* input to that aggregation, never a black-box override of it. This directly enforces the non-negotiable rule in `docs/DOD.md` and `docs/ENGINEERING_RULES.md` §3 that no automated score may report a false pass — an opaque AI score would be impossible to test against that rule, so it is architecturally excluded from being authoritative.
3. **Fraud-pattern detection over the Knowledge Graph** (ADR-002) — relationship-based anomaly signals (e.g. one surveyor attesting an implausible number of unrelated parcels in a short window) surfaced to the Security bounded context (`docs/REBUILD_PLAN.md` B13) as investigation leads, not automatic actions.
4. **Explicit non-goals for MVP:** no AI-driven automated approval/rejection of any parcel, evidence item, or attestation; no AI feature ships without the Phase 6 checks in `docs/PHASE_GATES.md` (evaluation, hallucination testing, latency, cost, prompt-injection testing, a defined fallback chain, and model routing) passing first.

## Consequences

- Phase 6 in `docs/PHASE_GATES.md` has a concrete owner instead of remaining an unscoped placeholder that the 16-step Claude Code Loop's "AI REVIEW" step would otherwise have nothing real to review.
- Every AI feature is additive to, never a replacement for, the explainable rule-based Trust Engine — preserving the "not AI magic" requirement from the Operator's own framing of the Trust Engine concept.
- Any future proposal to make an AI signal authoritative (e.g. auto-approving evidence) requires a superseding ADR, not a quiet change to the Trust Engine's aggregation weights.
