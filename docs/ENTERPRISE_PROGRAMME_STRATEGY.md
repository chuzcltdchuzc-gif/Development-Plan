# Enterprise Programme — Planning Recommendation

**Type:** Planning recommendation only. **No code, migration, API, bounded context, or ADR is
introduced by this document.** Sits beneath `docs/PLATFORM_STRATEGY.md`'s "Business Strategy"
layer — the Enterprise-specific instantiation, corresponding to Layer 4 of that document's
five-layer platform model.

**Date:** 2026-07-25

**Governed by:** `docs/PLATFORM_STRATEGY.md` (Layer 4 — Enterprise Services; the Enterprise Portal
concept), `docs/ENGINEERING_RULES.md` rule 9 (Controlled Platform Authority — the doctrine any
enterprise-scale cross-tenant read/write must satisfy), `docs/
PLATFORM_INTELLIGENCE_ARCHITECTURE.md` (the layer any enterprise-facing analytics/due-diligence
capability would sit under, not inside Registry or Spatial), `docs/
MARKETPLACE_DISCOVERY_AND_PLANNING.md` (Enterprise Dispatch is named there as a Marketplace
candidate concept — this document treats it as the boundary question between the two program's,
not a settled ownership decision).

## Why a distinct programme from Marketplace

An individual registrant transacting with an individual surveyor is a fundamentally different
shape of relationship than a bank's mortgage-underwriting team requiring due-diligence
verification on thousands of parcels, or a property developer dispatching hundreds of survey
assignments across a new estate simultaneously. The difference is not merely volume — it is
**relationship structure**: an Enterprise participant is typically itself an organization
transacting with the platform under its own commercial terms (a subscription, an API contract), not
a peer counter-party to an individual surveyor in the way an ordinary registrant is. This mirrors
why this platform distinguishes a Customer Portal from an Enterprise Portal
(`docs/PLATFORM_STRATEGY.md`) rather than treating "enterprise" as merely "a registrant with a lot
of parcels."

## Objectives

1. Define the enterprise participant types this platform actually intends to serve — named
   candidates: banks, mortgage providers, law firms, property developers, insurance companies,
   and valuation firms — and, for each, what "verification" or "due diligence" concretely means to
   them (a bank's collateral-verification need is not identical to a law firm's title-search need),
   without assuming they are interchangeable.
2. Establish enterprise-scale dispatch as an explicit non-functional requirement
   (`docs/PLATFORM_STRATEGY.md`'s "Enterprise dispatch" section) — hundreds or thousands of survey
   assignments issued simultaneously by one enterprise participant — and determine whether this is
   a Marketplace capability an enterprise tenant simply uses at volume, or a genuinely distinct
   dispatch mechanism Enterprise itself must own.
3. Establish the authorization and Controlled Platform Authority posture for any enterprise-facing
   read that spans multiple tenants' parcels (e.g., a bank's due-diligence query plausibly needs to
   read verification status across parcels it did not itself register) — this is structurally the
   same category of question ADR-021 resolved for Spatial Conflict Detection, and this programme's
   own future ADR should cite that precedent rather than re-derive its own justification for
   elevated reach from nothing (`docs/ENGINEERING_RULES.md` rule 9's own closing instruction).
4. Determine the API surface enterprise participants need (`docs/DEVELOPER_PLATFORM_STRATEGY.md`'s
   relationship to this programme) — an enterprise integration is likely API-first (a bank's own
   loan-origination system calling LandVault, not a human using LandVault's own UI), distinguishing
   Enterprise's needs from an ordinary registrant's browser-based workflow.

## Scope (candidate, not final)

- **Banks** — collateral/loan-origination verification use case. Likely the first, clearest
  Enterprise use case, since it maps directly onto this platform's existing "verified parcel"
  concept without requiring new domain modeling beyond a read/query capability.
- **Mortgage providers** — closely related to Banks; may be the same participant type or a
  distinct one depending on Nigerian market structure this programme's own discovery should
  investigate, not assume.
- **Law firms** — title-search/due-diligence use case; likely a read-heavy participant type with
  minimal write needs, simplifying its authorization model relative to a transacting participant.
- **Property developers** — the clearest enterprise-dispatch use case (many parcels, many survey
  assignments, at once) — likely the participant type whose needs most directly drive the
  enterprise-dispatch non-functional requirement (Objective 2).
- **Insurance companies** — risk-assessment use case; likely depends on Trust Engine (B7,
  unbuilt) signals more than any other named enterprise type, since insurance underwriting is
  fundamentally a risk-scoring exercise.
- **Valuation firms** — professional-service use case structurally closer to a Partner-programme
  participant (`docs/PARTNER_PROGRAMME_STRATEGY.md`) than a pure data-consumer — named here because
  the review that produced this document named it as Enterprise, but this programme's own
  discovery should resolve whether Valuation Firms are better modeled as Enterprise (a consuming
  institution) or Partner (a professional-services provider), not assumed either way by this
  document.
- **Enterprise dispatch** — see Objective 2.
- **Enterprise APIs** — see Objective 4 and `docs/DEVELOPER_PLATFORM_STRATEGY.md`.
- **Due diligence** — the read-side capability underlying Banks/Law Firms/Insurance's primary use
  case — likely the first Enterprise capability worth prioritizing precisely because it requires
  no new write path, only a carefully-scoped, audited read (Objective 3).
- **Compliance services** — overlaps `docs/OPERATING_MODEL.md`'s Compliance function and
  `docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md`'s Compliance Engine — an open ownership question
  this document does not resolve.

## Relationship to existing architecture

No change to any existing bounded context is proposed. Every enterprise read this programme would
eventually need is expected to be a Controlled Platform Authority exception in the sense
`docs/ENGINEERING_RULES.md` rule 9 already defines — named, narrow, fixed at the call site,
audited — never a general-purpose "enterprise tenants can query anything" grant, which this
document explicitly does not propose and which would directly contradict this platform's absolute
tenant-isolation default (`docs/ARCHITECTURE_HANDBOOK.md` Part V).

## Approval Gate

No Enterprise programme work has begun. This document surveys candidate participant types and
names the authorization/dispatch questions its own future discovery must resolve; it does not
decide which enterprise participant type to serve first, or how this programme sequences against
Marketplace, Partner, or Government. **Waiting for explicit direction before any Enterprise
programme discovery begins.**
