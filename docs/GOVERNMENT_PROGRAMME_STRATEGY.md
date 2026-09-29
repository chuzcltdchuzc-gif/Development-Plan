# Government Programme — Planning Recommendation

**Type:** Planning recommendation only. **No code, migration, API, bounded context, or ADR is
introduced by this document.** Sits beneath `docs/PLATFORM_STRATEGY.md`'s "Government Strategy"
layer, corresponding to Layer 5 of that document's five-layer platform model — the layer every
other layer exists in service of, per this platform's own positioning
(`docs/PLATFORM_STRATEGY.md`'s "Nigeria's trusted digital infrastructure" statement).

**Date:** 2026-07-25

**Governed by:** `docs/PLATFORM_STRATEGY.md` (Layer 5, positioning), `docs/ENGINEERING_RULES.md`
rule 9 (Controlled Platform Authority — any government-facing read/write is a named, narrow
exception, never a blanket grant), `docs/ARCHITECTURE_HANDBOOK.md` Part I ("Government-grade
architecture" — the bar this platform already committed to before this programme was named),
`docs/adr/ADR-007-audit-trail-evidence-model.md` (the audit mechanism any government-facing
compliance reporting would need to prove, not merely assert, its own completeness).

## Why this is the layer every other layer serves

This platform's positioning statement is explicit that trust between citizens, professionals,
enterprises, and government is the product (`docs/PLATFORM_STRATEGY.md`). Government integration
is not merely another enterprise-like consumer of this platform's data — it is the layer whose
endorsement (surveyor licensing recognition, registry interoperability, digital certificate
acceptance) is what ultimately makes every other layer's "verified" claim mean something beyond
this platform's own say-so. This is why Government is named as its own layer (5) rather than
folded into Enterprise (4), even though both are, mechanically, external institutional
consumers of this platform's data — the trust relationship is categorically different (regulatory
and evidentiary, not merely commercial).

## Objectives

1. Identify the specific government counterparties this programme would need to integrate with —
   named candidates: Surveyor-General offices (licensing/accreditation authority), state and
   federal land registries (the authoritative record this platform's own Registry context must
   ultimately reconcile with, not replace), planning authorities (zoning/permitted-use data this
   platform's own parcels may need to reference).
2. Define what "public verification" means without compromising this platform's tenant-isolation
   default — a citizen or third party verifying a digital certificate's authenticity is plausibly
   a narrow, read-only, non-tenant-identifying capability (analogous in shape to how a certificate-
   transparency log lets anyone verify a certificate without exposing the certificate holder's full
   account), not a general public API onto this platform's own tenant-scoped data.
3. Establish the Controlled Platform Authority posture for any government-facing compliance
   report or registry-interoperability read — every such capability needs its own named exception
   and its own ADR, per `docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md`'s "no exception inherits
   another's" doctrine; this programme inherits nothing from ADR-021's Spatial-specific exception
   or any Enterprise-programme exception.
4. Determine the relationship between this platform's own `Parcel`/`ParcelGeometry` and the
   government's own authoritative land records — is LandVault's registry a *complement* to
   government records (a faster, digitally-verified front end that ultimately reconciles with
   government registries) or does it aspire to *become* an authoritative record itself in
   partnership with government — a strategic question this document raises rather than answers,
   since it has significant legal and institutional-relationship implications beyond this
   document's own architectural scope.

## Scope (candidate, not final)

- **Government integration** — the umbrella capability; the specific mechanism (API, batch file
  exchange, manual reconciliation) is undetermined and likely varies by counterparty.
- **Registry interfaces** — the technical seam between this platform's own Registry context (B3)
  and an external government land registry. Likely a new, narrow, read/write-limited adapter at
  the Registry context's own boundary — not a reason to weaken Registry's own bounded-context
  isolation, per this platform's existing "no direct database access across bounded contexts"
  principle applied to *external* systems by the same reasoning.
- **Surveyor-General integration** — the authoritative source for the licence data this platform's
  own Partner Programme (`docs/PARTNER_PROGRAMME_STRATEGY.md`) needs for accreditation. This is
  this programme's most direct dependency relationship: Partner's accreditation tracking is only
  as trustworthy as its source data, and a real Surveyor-General integration is what would make
  that data authoritative rather than self-reported.
- **Compliance** — regulatory reporting; overlaps `docs/OPERATING_MODEL.md`'s Compliance function
  and `docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md`'s Compliance Engine, an open ownership question
  this document does not resolve.
- **Public verification** — see Objective 2.
- **Digital certificates** — a certificate this platform issues (e.g., a verified-parcel
  certificate) that a third party (a bank, a court, a citizen) can independently verify. Likely
  depends on Evidence (B5, unbuilt) for the underlying document/hash infrastructure, and on this
  platform's existing hash-chained audit model (ADR-007) for the tamper-evidence property a
  certificate would need to be credible.
- **Government APIs** — see `docs/DEVELOPER_PLATFORM_STRATEGY.md`; likely a specialized,
  more-tightly-scoped instance of that programme's general API capability, not a separate
  mechanism.

## Relationship to existing architecture

No change to any existing bounded context is proposed. Every government-facing capability named
above is expected to require its own Controlled Platform Authority justification and its own ADR,
consistent with `docs/ENGINEERING_RULES.md` rule 9's closing instruction that "any future bounded
context that believes it needs platform-wide or cross-tenant authority must satisfy this rule and
cite it, not invent a fresh argument."

## Approval Gate

No Government programme work has begun. This document names the counterparties, the trust
relationship's distinct character from Enterprise, and the open questions (public verification's
exact shape, LandVault's relationship to authoritative government records) its own future
discovery must resolve — it takes no position on timing or sequencing relative to Marketplace,
Partner, or Enterprise. **Waiting for explicit direction before any Government programme discovery
begins.**
