# Surveyor Network Governance Decision Readiness Report

**Reviews:** `docs/GD-008-surveyor-network-phase-0-principles-and-authorization-boundary.md`
(uncommitted, PROPOSED). Cross-checked against `docs/SURVEYOR_NETWORK_PHASE_0_GOVERNANCE_
DISCOVERY.md`, `docs/SURVEYOR_PROFESSIONAL_NETWORK_AND_COMMERCIAL_ARCHITECTURE.md`,
`MARKETPLACE_DISCOVERY_AND_PLANNING.md`, `PARTNER_PROGRAMME_STRATEGY.md`, and LV-000 Article XVI.

## 1. Governance numbering — verified, not assumed

Every `GD-\d{3}` reference across the repository was enumerated directly: GD-001 through GD-007
all appear, fully defined, inside LV-000 v1.8 Article XVI — the constitutionally correct location
for a Governance Decision's authoritative text (GD-005 is the one exception in *placement*, its
full text living in `docs/GOVERNANCE_BASELINE.md` Part E.1 with only a pointer in the Log, which
GD-005's own Log entry says explicitly). No `GD-008` or higher exists anywhere. **GD-008 is
confirmed the next available number**, not assumed.

**File location note:** no repository convention exists for a standalone, permanent "GD file" the
way `docs/adr/` holds ADRs — every prior GD's authoritative text lives either directly in Article
XVI or inside the specific instrument it ratifies. GD-008 is drafted as a standalone document only
because it has no natural host instrument; on ratification, its text should be copied into Article
XVI as the Log entry, per GD-008's own opening note. This is a judgment call, not a rediscovered
convention, and is flagged as such rather than presented as settled precedent.

## 2. Is the proposed decision supported by Phase 0?

Yes, traceably. Each substantive clause was checked against a specific section of the discovery
document it claims to rest on:

| GD-008 clause | Discovery source |
|---|---|
| §2 Bounded-context direction | `PHASE_0_GOVERNANCE_DISCOVERY.md` §3 |
| §3 Tenant wording | `PHASE_0_GOVERNANCE_DISCOVERY.md` §4–§5 |
| §4 Job/Assignment | `PHASE_0_GOVERNANCE_DISCOVERY.md` §7 |
| §5 Evidence independence | `PHASE_0_GOVERNANCE_DISCOVERY.md` §8 |
| §6 ADR-028 scope | `PHASE_0_GOVERNANCE_DISCOVERY.md` §9, §19 |
| §7 Sequencing | `PHASE_0_GOVERNANCE_DISCOVERY.md` §18 |
| §8 Marketplace/Partner gates remain open | `PHASE_0_GOVERNANCE_DISCOVERY.md` §13, §20 |
| §9 Nigeria table | `PHASE_0_GOVERNANCE_DISCOVERY.md` §11 |

No clause introduces a conclusion the discovery document did not already reach.

## 3. Does it accidentally settle unresolved architecture?

**One genuine, disclosed nuance, not a defect.** GD-008 §2 records the two-bounded-context
conclusion (Marketplace, Partner) as a "direction" — but `MARKETPLACE_DISCOVERY_AND_PLANNING.md`
itself names "an explicit bounded-context map, reviewed and approved" as Marketplace's own Phase
0's **first deliverable**. A discovery document produced outside that formal process reaching the
same conclusion does not substitute for that review. GD-008's text already hedges this correctly —
"guides subsequent architecture... does not itself authorize any bounded context" (§2) and "This
direction remains subject to Marketplace discovery before any implementation" (§4) — but the risk
is real enough to name explicitly here: **if Marketplace's own Phase 0 is later opened and reaches
a different bounded-context conclusion, that is not a contradiction of GD-008, it is exactly what
GD-008's own hedging anticipated.** Recommend Governance read §2 with this in mind, not as a
settled fact. No other clause was found to over-settle anything — §4, §6, §7, and §8 all carry
equivalent explicit subject-to/gated-on language.

## 4. Is the tenant wording safe?

Yes. The adopted wording is the corrected formulation supplied for evaluation, verified against
ADR-010's actual `Tenant` shape (id, name, owner, status, suspension — no professional/practice
field) and against the existing two-layer tenant-isolation discipline (RLS + application check).
It introduces no new tenant subtype, no isolation-boundary change, and matches exactly what the
Phase 0 discovery independently concluded (an accreditation record referencing a tenant and,
optionally, a specific user within it). The rejected wording ("every individual surveyor is a
tenant") does not appear anywhere in GD-008.

## 5. Is ADR-028's scope sufficiently narrow?

Yes. GD-008 §6 states the single question ADR-028 may answer and separately lists eleven items it
may not decide (Marketplace architecture, full Job design, Partner accreditation, payments, payout,
SECI, PPI, royalties, Legacy Vault, rights/licensing, anti-circumvention economics) — an exhaustive
negative list, not a vague "keep it small" instruction. This matches the discovery document's own
§9/§19 conclusion verbatim.

## 6. Are the legal gates explicit?

Yes. Fourteen named items, each marked against two independent gate types (professional-authority
verification, Nigerian legal counsel), several requiring both. No item is left as an unmarked
placeholder, and the table explicitly states Paystack's technical availability does not resolve any
regulatory question in it.

## 7. Does implementation remain prohibited?

Yes. GD-008 carries an explicit, itemized "Explicitly prohibited by this decision" section covering
every item named in the task's own prohibition list (Dashboard, Job/Assignment/Partner/
accreditation/customer tables, SECI/EQF/PPI, payment/wallet/payout/commission/royalty, escrow,
Legacy Vault/Rights/HEMI/LEPI/PCR/SLV, and implementation of either new bounded context), and states
plainly that the only authorized technical work is *drafting* ADR-028, which is not itself
implementation.

## 8. Relationship to existing architecture

Checked directly: GD-008 does not touch LV-000's text, does not modify ADR-010/ADR-004/ADR-026/
ADR-027, does not move ADR-021 out of Proposed, and does not retroactively reinterpret GD-004 or
GD-007 (both stated as remaining in full, unqualified force). No existing ADR is rewritten to
predate this decision.

## Overall assessment

GD-008 is internally consistent, traceable to Phase 0 without inventing new conclusions, correctly
hedged on the one place (bounded-context direction) where it comes closest to pre-empting a future
formal discovery, safely worded on the tenant question, narrowly scoped on ADR-028, explicit on
legal gates, and exhaustive on implementation prohibition. No fundamental contradiction was found
between Phase 0's own two source discoveries or between Phase 0 and the two pre-existing planning
documents.

SURVEYOR NETWORK GOVERNANCE DECISION CONSISTENT — READY FOR GOVERNANCE RATIFICATION
