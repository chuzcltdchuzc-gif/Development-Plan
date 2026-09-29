# Marketplace Programme — Phase 0 Recommendation

**Type:** Planning recommendation only. **No code, no migration, no API, no application logic
exists or is proposed by this document.** This is not the Marketplace programme's own Phase 0
discovery (the way `docs/B4_DISCOVERY_AND_PLANNING.md` was B4's) — it is a recommendation that
such a Phase 0 now begin, following the same "discovery and planning only, coding commences only
after explicit approval" pattern this platform has used for every context so far (B1→B2→B3→B4).

**Date:** 2026-07-24

**Governed by:** `docs/REBUILD_PLAN.md` §1 (context #10, "Economic / Billing" — the closest
existing scoped entry to what this document calls "Marketplace"), `docs/PHASE_GATES.md` (the
Phase 0–12 model this recommendation proposes applying to a new programme), the same
Discover→Define→ADR→Review→Implement→Verify→Freeze lifecycle B4 has followed throughout.

## Why now

B1 (Identity), B2 (Delegated Administration), B3 (Registry), and B4 Slices 1–2 (Spatial
Foundation & Validation) are complete, frozen or accepted, and live-verified. Every context built
so far has been a **record-of-truth** context — establishing who a principal is, what a parcel
is, what its boundary is. None of them has yet introduced **money changing hands, a
counter-party relationship between two tenants, or a service being delivered and paid for** —
the category of capability `docs/REBUILD_PLAN.md`'s own scope already gestures at (context #10,
Economic/Billing: "credit wallet, service catalog, invoicing, payments, surveyor revenue-share
consumption") but has not yet been given its own discovery treatment, the way Spatial Intelligence
was before B4 began.

The review that produced this recommendation named a broader set of terms than context #10's
original scope — **Payments, Escrow, Ratings, Wallet, Enterprise Dispatch** — several of which
(Escrow, Ratings, Enterprise Dispatch) do not appear anywhere in `docs/REBUILD_PLAN.md`'s existing
13-context list at all. This is itself the first finding this recommendation records: **"Marketplace"
is not simply a rename of context #10 — it is either a superset of it, or a sibling programme that
overlaps it, and which of those two is true is a scoping question the Marketplace programme's own
Phase 0 must resolve, not something this recommendation decides in advance.**

## Objectives (proposed, for the programme's own Phase 0 to confirm or revise)

1. Establish whether "Marketplace" is Economic/Billing (context #10) renamed and expanded, or a
   genuinely new, fourteenth bounded context sitting alongside it — mirroring the exact question
   B4's own discovery resolved for Spatial Intelligence (already context #3 in the original plan,
   but still required its own Phase 0 before implementation began).
2. Define what a "transaction" means on this platform for the first time — every context built so
   far records facts (identity, land, geometry); Marketplace is the first context whose core
   responsibility is an *exchange* between two parties, with money, timing, and dispute exposure
   none of B1–B4 have had to reason about.
3. Establish the authorization model for Marketplace mutations before any is built — per this
   platform's now-consistent discipline (ADR-005→ADR-015 for Registry, the coarse-gate→ADR-022
   escalation for Spatial), a Marketplace-specific authorization ADR should be planned for from
   the start, not discovered as a gap after an MVP ships.
4. Establish the audit and Controlled Platform Authority posture for anything Marketplace needs to
   read or write outside a single tenant's own scope (e.g., an escrow release plausibly involves
   two tenants; a rating plausibly needs to be readable by the party being rated without exposing
   the rater's full identity) — the same doctrine `docs/ENGINEERING_RULES.md` rule 9 and ADR-021
   established for Spatial should be treated as a platform-wide precedent Marketplace's own
   discovery must apply, not reinvent.

## Scope (proposed, not final — the programme's own Phase 0 discovery decides this)

**Named capabilities this recommendation identifies as plausibly "Marketplace," pending the
programme's own scoping decision:**

- **Wallet** — overlaps directly with `docs/REBUILD_PLAN.md` context #10's "credit wallet
  (atomic)." Likely the clearest case of "this is Economic/Billing, not a new context."
- **Payments** — Paystack (Nigeria) + Stripe (diaspora), per `docs/REBUILD_PLAN.md`'s own stack
  table — already named as this platform's payment architecture (`docs/adr/
  ADR-006-payment-architecture.md`, if that ADR exists as referenced by the stack table) but not
  yet scoped as its own implementation slice.
- **Escrow** — not named anywhere in `docs/REBUILD_PLAN.md`'s existing 13 contexts. A genuinely
  new capability requiring its own domain model (an escrow has its own lifecycle — held, released,
  disputed, refunded — distinct from a wallet balance or a single payment event) and, given it
  structurally involves holding one tenant's funds pending a condition another tenant (or a
  governance decision) satisfies, likely its own authorization and Controlled Platform Authority
  questions from day one.
- **Ratings** — not named anywhere in `docs/REBUILD_PLAN.md`'s existing 13 contexts. Likely
  intersects with `docs/REBUILD_PLAN.md` context #8 (Community Trust — "honest consensus
  scoring") in spirit, but Community Trust's scoring is about parcels/attestations, not
  transacting-party reputation — the Marketplace programme's own discovery should determine
  whether Ratings is a Marketplace-owned concept or a Community-Trust extension, not assume either
  answer here.
- **Enterprise Dispatch** — not named anywhere in `docs/REBUILD_PLAN.md`'s existing 13 contexts,
  and the least-specified of the five terms named in the governing review. This recommendation
  does not speculate on its meaning beyond noting that it is the term most in need of the
  programme's own Phase 0 defining it at all before any scope decision is made.

**What this recommendation explicitly does not decide:** which of the above becomes its own
bounded context, which are absorbed into the existing Economic/Billing context, and whether any
of them depend on capabilities this platform has not built yet (e.g., Evidence, context #4, or
Workflow, context #7, both still unbuilt per `docs/REBUILD_PLAN.md`). These are exactly the
questions a real Phase 0 discovery resolves — this document only recommends that the resolution
process begin.

## Bounded contexts — the scoping question itself

The single most important open question this recommendation identifies, mirroring the format of
every prior programme's own discovery document:

> **Is "Marketplace" one new bounded context, or several?** Wallet/Payments plausibly stay inside
> a (renamed or expanded) Economic/Billing context. Escrow, given its distinct lifecycle and
> likely cross-tenant/governance-conditional release logic, plausibly deserves its own context, the
> same way this platform gave Spatial Intelligence its own context distinct from Registry despite
> both operating on "the parcel." Ratings and Enterprise Dispatch are the least well-specified and
> should not be scoped into any context prematurely.

This recommendation proposes that the Marketplace programme's own Phase 0 discovery treat this as
its first deliverable — an explicit bounded-context map, reviewed and approved, before any ADR
roadmap is drafted — mirroring exactly how `docs/B4_DISCOVERY_AND_PLANNING.md` §2 (Architectural
Scope) preceded §3 (ADR Roadmap) for Spatial Intelligence.

## Candidate domain concepts (illustrative, entity-level — not a domain model)

The Enterprise Programme Transition planning exercise (`docs/PLATFORM_STRATEGY.md`) named eleven
concepts at the entity level that a real Marketplace domain model would need to define. **Naming
them here is not modeling them** — no field, invariant, aggregate boundary, or lifecycle is
decided; each is listed with only the questions its eventual domain-model ADR would need to
answer, mirroring how ADR-013 first had to answer these same categories of question for `Parcel`:

| Candidate concept | What it would need to answer (not answered here) |
|---|---|
| **Survey Request** | Who may create one — any registrant, or only against their own parcel? Does it require an existing `Parcel` (Registry) to reference, per this platform's "Registry owns identity" rule? |
| **Job** | Is a Job the same thing as a Survey Request once accepted, or a distinct entity with its own lifecycle? Does "Job" duplicate "Survey Request," a question worth resolving before both are built. |
| **Assignment** | The link between a Job/Survey Request and a specific surveyor/firm — does assignment imply exclusivity (one surveyor at a time) or does it support competitive bidding before assignment? |
| **Match** | Is matching automated (a future Platform Intelligence-shaped capability, `docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md`) or manual (a registrant or governance role selects)? If automated, it inherits that layer's four-part test and needs its own Controlled Platform Authority review if it reads across tenants to find candidate surveyors. |
| **Escrow** | Already named above — its own lifecycle, cross-tenant/governance-conditional release. |
| **Wallet** | Already named above — overlaps `docs/REBUILD_PLAN.md` context #10. |
| **Payment** | Single-event vs. Wallet-mediated — does every Payment pass through a Wallet, or can some bypass it (e.g., a direct Paystack/Stripe charge for a one-off service)? |
| **Rating** | Already named above — Marketplace-owned vs. Community-Trust extension is the open question. Whichever it becomes, `docs/ENGINEERING_RULES.md` rule 3 (fail-safe scoring) applies without exception: a rating system with no data must report "insufficient data," never a default/neutral-looking score that could be mistaken for an actual rating. |
| **Dispute** | Does a Dispute require a prior Rating, Payment, or Job to exist, or can it be raised independently? Does dispute resolution require a new authorization tier beyond `GOVERNANCE_ROLES`, or does it reuse the existing governance model? |
| **Surveyor Profile** | Is this Identity's `User`/`Tenant` extended with Marketplace-specific fields (accreditation, specialty, coverage area), or a distinct Marketplace-owned entity referencing `User`/`Tenant` by identifier — the identical "extend vs. reference" question ADR-018 already resolved once for `ParcelGeometry` vs. `Parcel`, and the same discipline should apply here rather than growing `User` with Marketplace-specific fields it has no other reason to carry. |
| **Availability** | A surveyor's schedule/capacity — does this belong to Marketplace (it exists to inform matching/dispatch) or to the Partner Programme (it is partner lifecycle data, `docs/PARTNER_PROGRAMME_STRATEGY.md`)? Named here as an open boundary question between the two future programmes, not resolved by either. |

**This table's purpose is to demonstrate that a real Phase 0 has real, answerable-but-unanswered
questions to resolve** — it is evidence this recommendation has been thought through at the
concept level, not a substitute for the domain-modeling work itself.

## ADR roadmap (illustrative — the programme's own Phase 0 drafts the real one)

Named here only to demonstrate the kind of roadmap a real Phase 0 would produce, mirroring
`docs/B4_DISCOVERY_AND_PLANNING.md` §3's shape — **none of these are drafted, reserved, or
numbered**, since doing so before the bounded-context question above is resolved would repeat the
exact mistake this platform's own governance discipline exists to prevent (drafting an ADR before
the domain model it governs is settled):

- A domain-model ADR for whichever entity(ies) the bounded-context decision produces (mirroring
  ADR-013 for `Parcel`, ADR-018 for `ParcelGeometry`).
- An authorization-model ADR for Marketplace mutations, planned from the start rather than
  escalated to later (mirroring the ADR-005→ADR-015 and coarse-gate→ADR-022 pattern this
  recommendation explicitly wants Marketplace to avoid repeating).
- A Controlled Platform Authority-governed ADR for any cross-tenant read/write Escrow or Ratings
  turns out to require (mirroring ADR-021's role for Spatial).
- A payment/webhook integration ADR, if Payments is scoped as its own slice (the stack table
  already names Paystack/Stripe; whether a dedicated ADR beyond the existing payment-architecture
  ADR is needed is the programme's own question).

## Approval Gate

No Marketplace programme work — discovery, ADR drafting, or implementation — has begun. This
document is presented for review of: whether "Marketplace" should be scoped as an expansion of
existing context #10 or as one or more new contexts (§"Bounded contexts," above), and whether now
is the right time to formally open the Marketplace programme's own Phase 0, given B4 itself is
still mid-programme (Slice 3/ADR-021 not yet accepted). **This recommendation takes no position on
sequencing** — whether Marketplace's Phase 0 should begin now, in parallel with B4's remaining
work, or only after B4 is fully frozen, is a resource/priority decision, not an architectural one.

**Waiting for explicit direction before any Marketplace programme work begins**, consistent with
every prior programme's own initiation pattern in this codebase.
