# Partner Programme — Planning Recommendation

**Type:** Planning recommendation only. **No code, migration, API, bounded context, or ADR is
introduced by this document.** Sits beneath `docs/PLATFORM_STRATEGY.md`'s "Business Strategy"
layer — this is that layer's Partner-specific instantiation.

**Date:** 2026-07-25

**Governed by:** `docs/PLATFORM_STRATEGY.md` (surveyors as strategic partners, not merely users;
the Partner Portal concept), `docs/adr/ADR-010-tenant-organization-aggregate.md` (the existing
`Tenant` aggregate this programme's individual-surveyor and firm representation would build on),
`docs/adr/ADR-011-delegated-administration.md` (delegation model a firm's own internal role
structure would likely reuse), `docs/MARKETPLACE_DISCOVERY_AND_PLANNING.md` (Marketplace is this
programme's most direct dependency and likely sibling — Availability is named in both documents
as a boundary question between them).

## Why a distinct programme from Marketplace

Marketplace (`docs/MARKETPLACE_DISCOVERY_AND_PLANNING.md`) is about the *transaction* — a survey
request, a job, a payment. Partner is about the *relationship* — who is allowed to participate as
a professional on this platform at all, how their standing is tracked over time, and what happens
when it degrades. A registrant can exist without ever being a marketplace counter-party; a partner
cannot meaningfully transact without an established, accredited relationship existing first. This
mirrors the same reasoning that kept Registry and Spatial as two contexts describing "the same
land" — Marketplace and Partner would describe "the same professional" from two different, both
legitimate, domain angles, and conflating them risks the same kind of aggregate overreach ADR-018
explicitly avoided by not putting geometry on `Parcel`.

## Objectives

1. Define what "accredited" means on this platform before any partner-facing capability is built
   — today, `PARCEL_REGISTRANT_ROLES` (Registry) includes `licensed_surveyor`/`surveyor_partner` as
   roles, but role membership alone is not accreditation tracking (expiry, licence tier,
   jurisdiction, standing) — a real gap this programme exists to close.
2. Establish a partner lifecycle distinct from an ordinary user's: onboarding → active →
   suspended (temporary, reversible) → terminated (per this platform's existing terminal-state
   discipline, e.g. `Parcel.ARCHIVED`/`ParcelGeometry.SUPERSEDED`, likely irreversible once
   reached) — not resolved here, but named as the shape a real domain model would need.
3. Establish performance/compliance measurement (SLAs, ratings, suspension triggers) with the same
   fail-safe-scoring discipline (`docs/ENGINEERING_RULES.md` rule 3) already binding on every other
   scoring mechanism this platform has or will build — a partner with no completed jobs yet must
   show "insufficient data," never a default score indistinguishable from a genuinely good one.
4. Determine Wallet/Earnings' relationship to Marketplace's own candidate Wallet concept
   (`docs/MARKETPLACE_DISCOVERY_AND_PLANNING.md`'s candidate-concept table) — a partner's earnings
   are plausibly the same underlying Wallet a registrant's payment draws from, viewed from the
   other side of a transaction, not necessarily two separate ledgers.

## Scope (candidate, not final)

- **Onboarding** — the process by which an individual surveyor or firm becomes eligible to accept
  marketplace work. Likely extends Identity's existing registration flow
  (`app/contexts/identity/application/auth_service.py`'s `register_local`) with partner-specific
  steps (credential submission, verification), not a parallel registration mechanism — this
  platform's "exactly one authorization path" discipline (`docs/ENGINEERING_RULES.md` rule 1)
  extends by analogy to "exactly one registration path, extended per partner type," not a second
  one.
- **Accreditation** — licence verification, jurisdiction/specialty tagging, expiry tracking. A
  genuinely new capability with no current equivalent in this platform; likely needs its own
  domain-model ADR before implementation, per this platform's now-standard discipline.
- **Compliance** — ongoing (not merely at-onboarding) tracking of a partner's standing — expired
  licences, unresolved disputes, suspension history. Overlaps conceptually with the future
  Compliance Engine named in `docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md` (Part II) — whether
  partner compliance tracking is a Partner-programme-owned capability or a Platform-Intelligence-
  consumed signal is an open scoping question, not resolved here.
- **Ratings** — see `docs/MARKETPLACE_DISCOVERY_AND_PLANNING.md`'s candidate-concept table; the
  same open Marketplace-vs-Community-Trust-vs-Partner ownership question applies.
- **Earnings/Wallet** — see Objective 4, above.
- **Analytics** — partner-facing dashboards (completed jobs, ratings trend, earnings) — a read
  model over data this programme and Marketplace jointly produce, not its own source of truth.
- **SLAs** — response-time and completion-time commitments a partner accepts as a condition of
  marketplace participation; likely the trigger mechanism for Suspension, below.
- **Suspension** — a temporary, reversible restriction on marketplace participation, analogous in
  shape (if not in specific trigger) to Identity's existing tenant suspension mechanism
  (`docs/adr/ADR-010-...md`) — whether this programme reuses that exact mechanism or needs its own
  is a design question its own future discovery must resolve, not assumed here either way.
- **Performance management** — the umbrella process connecting SLAs, ratings, and compliance into
  a single standing determination; the least-specified item in this list, deliberately, since
  defining it prematurely risks conflating Rating (a per-transaction signal), Compliance (a
  standing check), and SLA adherence (a contractual commitment) into one undifferentiated concept.

## Relationship to existing architecture

No change to Identity, Registry, or Spatial is proposed or required to produce this document.
`Tenant` (B2) and `Role`/delegation (B1/B2) are named as likely-reusable foundations, not as
already-decided implementation choices — whether a "partner" is a `Tenant` sub-type, a new field
set on the existing `Tenant`, or a genuinely new aggregate is this programme's own future Phase 0
question, mirroring exactly how `docs/B4_DISCOVERY_AND_PLANNING.md` had to resolve "is Spatial a
new context or a Registry extension" before ADR-018 could be drafted.

## Approval Gate

No Partner programme work has begun. This document identifies why Partner is distinct from
Marketplace and names its candidate scope; it does not decide sequencing relative to Marketplace,
Enterprise, or any other future programme. **Waiting for explicit direction before any Partner
programme discovery begins.**
