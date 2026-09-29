# Commercial Architecture — Planning Recommendation

**Type:** Planning recommendation only. **No code, migration, API, bounded context, or ADR is
introduced by this document.** Documents a diversified revenue model spanning every future
programme this planning exercise surveys — it does not itself decide pricing, does not implement
billing, and does not modify the existing `docs/adr/ADR-006-payment-architecture.md` (Paystack +
Stripe) decision.

**Date:** 2026-07-25

**Governed by:** `docs/PLATFORM_STRATEGY.md` (the multi-sided platform model this commercial
architecture prices across), `docs/adr/ADR-006-payment-architecture.md` (the existing, accepted
payment-rail decision this document extends commercially, not technically), `docs/
MARKETPLACE_DISCOVERY_AND_PLANNING.md`/`docs/PARTNER_PROGRAMME_STRATEGY.md`/`docs/
ENTERPRISE_PROGRAMME_STRATEGY.md`/`docs/GOVERNMENT_PROGRAMME_STRATEGY.md`/`docs/
DEVELOPER_PLATFORM_STRATEGY.md` (each programme this document's revenue lines are drawn from).

## Why revenue architecture beyond marketplace commissions

A pure commission model (a percentage of each marketplace transaction) ties this platform's
revenue entirely to marketplace transaction volume — a single point of commercial dependency that
does not reflect the actual breadth of value this platform's five-layer model
(`docs/PLATFORM_STRATEGY.md`) creates. Every layer beyond the transactional Marketplace layer
(Partner accreditation, Enterprise due-diligence, Government integration, Developer Platform
access) is itself a distinct value exchange, and each is named below as its own candidate revenue
line — not because all will necessarily be pursued, but because conflating them into "the
marketplace's commission rate" would understate this platform's actual commercial surface.

## Candidate revenue lines

| Revenue line | What it monetizes | Depends on |
|---|---|---|
| **Marketplace commissions** | A percentage of each transacted survey job/service — the traditional two-sided-marketplace take rate. | `docs/MARKETPLACE_DISCOVERY_AND_PLANNING.md`'s Job/Assignment/Payment concepts existing. |
| **Professional subscriptions** | A recurring fee for an accredited partner's continued platform participation, independent of transaction volume — analogous to a professional-association membership fee. | `docs/PARTNER_PROGRAMME_STRATEGY.md`'s accreditation/compliance tracking existing as a real, valuable status worth paying to maintain. |
| **Enterprise subscriptions** | A recurring fee for institutional access to due-diligence/verification capability at volume, independent of any single transaction. | `docs/ENTERPRISE_PROGRAMME_STRATEGY.md`'s due-diligence read capability. |
| **API access** | Usage-based or tiered fees for third-party developers consuming this platform's API surface. | `docs/DEVELOPER_PLATFORM_STRATEGY.md`'s API/OAuth capability. |
| **Certificate issuance** | A fee per digital certificate issued (e.g., a verified-parcel certificate a bank or court can independently verify). | `docs/GOVERNMENT_PROGRAMME_STRATEGY.md`'s digital-certificates concept; likely also depends on Evidence (B5, unbuilt). |
| **Escrow fees** | A fee for holding and releasing funds through the Marketplace's Escrow capability, distinct from the underlying transaction's own commission. | `docs/MARKETPLACE_DISCOVERY_AND_PLANNING.md`'s Escrow candidate concept. |
| **Wallet services** | Interest/float on held wallet balances, or a transaction fee on wallet-to-bank withdrawal — a distinct revenue mechanism from the escrow fee above, since a Wallet and an Escrow are different lifecycles (`docs/MARKETPLACE_DISCOVERY_AND_PLANNING.md`'s candidate-concept table). | Wallet existing as a real, funded balance, not merely a ledger entry. |
| **Compliance services** | A fee for enterprise/government-facing compliance reporting beyond what a basic subscription includes. | `docs/OPERATING_MODEL.md`'s Compliance function; `docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md`'s Compliance Engine, if built. |
| **Analytics** | A fee for aggregate, cross-context analytics access beyond what a basic Enterprise/Government subscription includes. | `docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md`'s Analytics Engine, not designed. |
| **Government SaaS** | A licensing/subscription fee for government counterparties to operate their own instance or integration of this platform's capability, distinct from the free/required public-verification capability (`docs/GOVERNMENT_PROGRAMME_STRATEGY.md`'s Objective 2) that this document assumes remains a trust obligation, not a revenue line. | `docs/GOVERNMENT_PROGRAMME_STRATEGY.md`'s integration work maturing to a reusable, licensable shape. |
| **White-label deployments** | Licensing this platform's technology stack (not its Nigerian data/network) to a different market or operator. | The most speculative line in this table — depends on the platform's architecture proving portable beyond its current single-country, single-tenant-model deployment, an open question this document does not resolve. |

## Pricing strategy — principles, not numbers

This document does not propose specific prices, tiers, or commission percentages — that is a
product/commercial decision requiring market data this architectural planning exercise does not
have. It does establish two binding principles for whichever future document sets actual pricing:

1. **No pricing decision may weaken this platform's trust guarantees.** A cheaper tier must never
   mean a less-audited, less-validated, or less-authorized code path — every mutation this
   platform performs goes through the same PDP/PEP/PIP engine and the same audit mechanism
   regardless of which commercial tier the requesting principal belongs to. Pricing differentiates
   *access* and *volume*, never *correctness* or *security*.
2. **No pricing decision may be enforced by a mechanism this platform's own architecture does not
   already support cleanly.** E.g., a "tiered API rate limit" is a natural extension of the
   existing rate-limiting middleware (`app/kernel/security/http_hardening.py`); a pricing model
   that instead required, say, degrading RLS enforcement for a "premium" tier would be rejected
   outright as a direct violation of `docs/ENGINEERING_RULES.md` rule 9 and this platform's
   tenant-isolation default.

## Marketplace economics — open questions, not answers

- Who bears the commission — the registrant, the surveyor, or both (a split)? This is a
  Marketplace-programme-level product decision, not resolved here.
- Does Escrow's fee scale with held amount, held duration, or a flat per-transaction rate? Depends
  on Escrow's own domain model (`docs/MARKETPLACE_DISCOVERY_AND_PLANNING.md`), not yet designed.
- Do Partner subscriptions replace or supplement marketplace commissions for a given partner, and
  does a higher subscription tier reduce the commission rate (a common two-sided-marketplace
  pattern)? Not resolved here.

## Relationship to existing architecture

No change to `docs/adr/ADR-006-payment-architecture.md`'s Paystack/Stripe decision is proposed —
this document assumes that decision remains the payment-rail foundation for every revenue line
above that involves an actual money movement. No billing code, subscription-management system, or
pricing engine is implemented by this document.

## Approval Gate

No Commercial Architecture implementation work has begun. This document surveys candidate revenue
lines and states two binding pricing principles; it does not set any actual price, tier, or
commission rate, and does not decide which revenue lines this platform will ultimately pursue.
**Waiting for explicit direction, and real market/product input, before any commercial
architecture is finalized or implemented.**
