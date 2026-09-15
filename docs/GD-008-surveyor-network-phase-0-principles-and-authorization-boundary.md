# GD-008 — Surveyor Network Phase 0 Principles and Authorization Boundary

**Status:** **ACCEPTED — 2026-09-08, on explicit Governance Authority ratification. IN FORCE.**
Recorded here in the shape a Log entry takes (mirroring GD-007's structure) since no repository
convention holds a standalone Governance Decision file separately from Article XVI — on the next
occasion Article XVI itself is amended, this text should be copied into that Log as the GD-008
entry, not left to live only here in the meantime. Ratification does not itself constitute that
copy; see the Ratification Record below for exactly what was ratified and what remains a
housekeeping step.

## Ratification Record

Ratified by Governance Authority for AquaSavannah LandVault, 2026-09-08, as: "GD-008 — Surveyor
Network Phase 0 Principles and Authorization Boundary... establishes the governing principles,
authorization boundaries and sequencing constraints for the Surveyor Professional Network
programme." The ratifying decision restates and, in several places, sharpens the proposed text
below — most notably an explicitly labeled "Important qualification" under the bounded-context
direction (§2), a four-part tenant formulation naming a solo professional's own tenant status
separately from one operating through a practice (§3), and an expanded constitutional-boundary
list naming "issue title" and stating plainly that unresolved evidence inconsistency is a
legitimate professional outcome (§1). This document's §§1–17 below are updated to match the
ratified text precisely; where earlier drafting language differed only in phrasing, not substance,
the ratified phrasing is adopted as authoritative.

**Date drafted:** 2026-09-08.

**Operative authority (if ratified):** Article XVI §1 (a new numbered decision) and, where it
authorizes ADR-028's scope, Article X §1/§4 (kernel-first sequencing) and Article VI §1
(Architecture Before Code, incorporated). This decision does **not** amend the Constitution and is
not proposed under Article XIV.

**Governed by:** `docs/SURVEYOR_PROFESSIONAL_NETWORK_AND_COMMERCIAL_ARCHITECTURE.md` and `docs/
SURVEYOR_NETWORK_PHASE_0_GOVERNANCE_DISCOVERY.md` (both uncommitted, both treated as the discovery
record this decision acts on, neither altered by this decision), `docs/MARKETPLACE_DISCOVERY_AND_
PLANNING.md`, `docs/PARTNER_PROGRAMME_STRATEGY.md`, ADR-004, ADR-010, ADR-011, ADR-026, ADR-027,
GD-004, GD-007.

## Context

Phase 0 discovery for a future Surveyor Professional Network and its commercial architecture
concluded with a reality audit against `main` at `5b8cdb08ff019949dae2aba55e3c8d6b16a8cd54`, a
reconciliation of three planning sources, and a decision matrix identifying exactly one
architecture question mature enough for an ADR now. That discovery is not self-executing — a
discovery document authorizes nothing by itself, per this platform's established pattern
(`MARKETPLACE_DISCOVERY_AND_PLANNING.md` and `PARTNER_PROGRAMME_STRATEGY.md` themselves each carry
an unactioned Approval Gate for exactly this reason). This decision is the governance act that
authorizes the one piece of architecture work Phase 0 found ready, records the principles Phase 0
established as binding, and — equally importantly — records what remains unauthorized, so that no
later reader mistakes "Phase 0 discussed it" for "Governance decided it."

## Findings

1. No Surveyor Professional Network, Marketplace, Partner, Payment, or Rights capability exists in
   `main` today beyond five RBAC role strings (`surveyor`, `surveyor_partner`, `licensed_surveyor`,
   `surveyor_general`) and an undifferentiated `EvidenceRecord.uploaded_by` field.
2. `MARKETPLACE_DISCOVERY_AND_PLANNING.md` (2026-07-24) and `PARTNER_PROGRAMME_STRATEGY.md`
   (2026-07-25) remain unopened. Their own Approval Gates are not closed by this decision or by
   either discovery document produced this week.
3. Exactly one architecture question is ready for ADR drafting without depending on either
   unopened Phase 0 or on unresolved Nigerian legal input: how `EvidenceRecord` should represent
   professional and commissioning actor provenance, distinct from who performed the upload.
4. Every other named concept — Job, Assignment, Partner accreditation, Payment, Rights,
   Professional Performance scoring — depends on at least one of: the Marketplace or Partner Phase
   0 discoveries actually running, or a named Nigerian legal/professional-body question being
   answered. None of those dependencies are resolved by this decision.
5. A wording risk was identified and corrected before this decision reached this draft: an earlier
   candidate formulation ("every individual surveyor is a tenant") would have been incorrect
   against the existing tenant-isolation architecture and is explicitly not adopted (§3 below).

## Decisions

### 1. Constitutional boundary

Surveyors may produce, interpret, document and professionally review land evidence. AquaSavannah
LandVault may preserve, structure, compare, attribute and make that evidence available through
governed workflows. Neither the Surveyor Professional Network nor any future commercial, scoring,
marketplace, or professional-performance mechanism authorizes LandVault to: determine legal
ownership; adjudicate land disputes; issue title; replace government title systems; or reward
professionals for reaching a preferred ownership conclusion. **Uncertainty and unresolved evidence
inconsistency remain legitimate professional outcomes.**

This restates Article IV, applied to this programme by name, not a new principle. Any future
implementation that violates it is void to that extent regardless of what ADR or governance
decision purports to authorize it, per Article IX §2 (authority is never assumed from capability).

### 2. Professional/commercial context direction

Governance accepts the Phase 0 direction that the future programme is presently best understood
through a **Partner / Professional Network** responsibility for professional identity,
participation, qualification/accreditation evidence, affiliation and professional standing; and a
**Marketplace** responsibility for customer-facing work such as instruction, Job, Assignment,
scope, quotation and completion. Payments remain aligned to the existing Economic/Billing
architecture (`docs/REBUILD_PLAN.md` context #10) unless later architecture determines otherwise.
Rights/licensing is not silently absorbed into Marketplace.

**Important qualification.** This two-context model is directional governance guidance only. It
does not close or supersede the bounded-context discovery required by `MARKETPLACE_DISCOVERY_AND_
PLANNING.md` — that document's own Phase 0 names an explicit, reviewed bounded-context map as its
first deliverable, and a discovery document produced outside that process reaching a similar
conclusion does not substitute for it. If that formal discovery later demonstrates that Marketplace
requires a materially different decomposition, Governance may refine this direction through the
appropriate later decision/ADR. **GD-008 therefore governs the current authorization boundary; it
does not freeze the final Marketplace context map.**

### 3. Tenant principle

Governance does not adopt a rule that every individual surveyor is a separate LandVault tenant.
The governing direction is:

- a surveying practice may be a tenant where it represents the appropriate isolation/commercial
  boundary;
- an independent/sole professional may be a tenant where appropriate;
- an individual professional operating through a practice may instead be an identity/member within
  that practice tenant;
- Partner/accreditation status does not itself create a new tenant or tenant subtype.

Existing LandVault tenant-isolation architecture (ADR-010) remains authoritative and unchanged: no
new tenant subtype is introduced, and a Partner/accreditation record is a referencing record
against an existing tenant and, optionally, a specific user within it — never an independent
isolation primitive. This is supported directly by Phase 0's own findings (`SURVEYOR_NETWORK_
PHASE_0_GOVERNANCE_DISCOVERY.md` §4–§5), not introduced fresh here.

### 4. Evidence independence

ADR-026 remains authoritative for the Evidence domain. Evidence must remain independent of
Marketplace and commercial workflow. Evidence may originate during a future Job, outside a Job,
historically, from third parties, from professional review, or from other lawful evidence sources
— all first-class, equally valid states. Marketplace may reference Evidence but must not redefine
its evidential meaning or truth.

### 5. Evidence provenance ADR authorization

Governance authorizes preparation of ADR-028, subject to repository-number verification, for the
narrow architecture question:

> How shall LandVault represent professional and commissioning actor provenance on Evidence while
> preserving ADR-026 Evidence independence and the LandVault non-adjudication doctrine?

ADR-028 may evaluate Originated By, Reviewed By, Commissioned By, individual-versus-organisation
actors, multiple originators, provenance immutability, historical Evidence, and scalar references
versus normalized actor relationships. It must distinguish these from Uploaded By, Rights Holder,
Licensor, Custodian, and Job/Assignment participation. **GD-008 does not pre-decide the eventual
database schema.**

*(Repository re-verification at drafting time: `docs/adr/` contains ADR-001–019, 021–027; ADR-020
remains deliberately vacant. ADR-028 is confirmed the next available number.)*

### 6. ADR-028 exclusions

ADR-028 is not authorized to decide: Marketplace architecture; full Job architecture; Partner
accreditation architecture; payments; payouts; commissions; escrow; SECI; EQF; Professional
Performance Index; royalties; Legacy Vault; historical Evidence monetisation; Rights/licensing
architecture; or anti-circumvention economics.

### 7. Job / Assignment direction (provisional, subject to Marketplace discovery)

> Customer Instruction → Job → one or more Professional Assignments → Evidence → QA/Review →
> Deliverable

Job is the customer/commercial aggregate. Assignment is a subordinate lifecycle fact within Job
unless subsequent architecture work — the Marketplace Phase 0 this decision does not itself run —
demonstrates it needs its own aggregate boundary. This shape must support multiple professionals,
reassignment, multiple site visits, specialist participation, and a QA reviewer distinct from the
field surveyor, all as facts within the same Job, not as separate top-level aggregates. **This
direction remains subject to Marketplace discovery before any implementation.** No Job or
Assignment implementation is authorized by GD-008.

### 8. Professional scoring principles

Adopted for future investigation, not implementation: SECI measures professional contribution, not
evidential truth; EQF measures evidence/process quality, not truth; the term "Surveyor Trust Index"
is rejected; **Professional Performance Index** is the preferred working term unless later research
establishes a better neutral name; commercial value and professional competence must remain
separate dimensions. **No scoring implementation or persistent score field is authorized** — all
three should be event-derived read-model projections if and when built (`SURVEYOR_NETWORK_PHASE_0_
GOVERNANCE_DISCOVERY.md` §14).

### 9. Evidence discrepancy terminology

"Resolved evidence conflict" must not be used as a rewardable outcome where it may imply
adjudication. Safer concepts: "evidence discrepancy professionally documented"; "evidence
discrepancy professionally reconciled" (reconciliation meaning professional evidence comparison and
documentation, never a determination of legal ownership); "material inconsistency remains
unresolved" as a valid, undiminished professional outcome.

### 10. Nigerian external validation gates

| Item | Verify with Nigerian professional authority (e.g. SURCON) | Nigerian legal counsel required |
|---|---|---|
| Surveyor licensing/registration requirements | Yes | Yes (statutory basis) |
| Surveying practice/firm registration | Yes | Yes |
| Credential/seal representation format | Yes | — |
| Professional advertising/referral rules | Yes | Yes (consumer/competition law overlay) |
| Professional indemnity requirements | Yes (existence/scope) | Yes (enforceability, liability attribution) |
| Platform commission legality | — | Yes |
| Professional/client confidentiality | — | Yes |
| Ownership/copyright of survey plans | — | Yes |
| Historical survey reuse/licensing | — | Yes |
| Expert evidence standing | — | Yes |
| Consumer protection obligations | — | Yes |
| Nigeria Data Protection (NDPR) obligations | — | Yes |
| Payment/payout handling; whether LandVault may hold client funds | — | Yes |
| Escrow/regulatory implications | — | Yes |

Matters of professional-body fact must be verified with the relevant Nigerian professional
authority; matters of legal interpretation must be referred to qualified Nigerian legal counsel.
Relevant implementation remains blocked pending the applicable gate(s) closing. **Paystack's or any
other provider's technical availability does not itself resolve any regulatory question in this
table.**

### 11. Payment boundary

GD-008 does not authorize escrow; LandVault holding client funds; professional wallets; automated
payouts; revenue-sharing engines; or royalty engines. Availability of Paystack or another payment
provider is not itself authority to implement regulated payment functionality.

### 12. Historical Evidence and rights

Uploading Evidence does not establish copyright ownership, commercial reuse permission,
sublicensing authority, client consent, or lawful monetisation rights. Historical Evidence
monetisation and the proposed Surveyor Legacy Vault remain blocked until an appropriate
Rights/licensing architecture is governed (`SURVEYOR_NETWORK_PHASE_0_GOVERNANCE_DISCOVERY.md`
§16–§17).

### 13. Client relationships / anti-circumvention

LandVault does not claim ownership of legitimate professional-client relationships. Future policy
must distinguish platform-originated work, pre-existing professional clients, independently sourced
clients, enterprise relationships, and jointly developed business. The preferred model is auditable
platform transactions and positive economic incentives rather than intrusive surveillance
(`SURVEYOR_NETWORK_PHASE_0_GOVERNANCE_DISCOVERY.md` §13).

### 14. Phase sequencing

| Stage | Content | Gate before it may begin |
|---|---|---|
| **P0 — Governance and external discovery** | No product implementation | None — in progress now |
| **P1 — Professional profile/accreditation foundation** | Professional identity → practice affiliation → qualification/accreditation evidence → status/audit. No Job, payment, scoring, or marketplace economics | ADR-028 accepted; Partner Phase 0 opened (separately, §17) |
| **P2 — Marketplace Job/Assignment architecture and implementation** | Per §7 | Marketplace Phase 0 discovery complete; required Nigerian legal/professional validation obtained |
| **P3 — Professional QA and contribution/performance metrics** | SECI/EQF/PPI as event-derived projections | Sufficient real operational events exist from P2 |
| **P4 — Marketplace economics/payments** | Per §11 | Economic/Billing architecture and the §10 payment/legal questions resolved |
| **P5 — Historical Evidence rights and monetisation** | Legacy Vault, Rights context, HEMI-class metrics | A governed Rights model exists and B5.4 (WORM/sealing) is complete |

Each stage remains subject to its own architecture, governance, and external validation gates. This
sequencing does not itself authorize P1–P5 implementation.

### 15. Immediate implementation prohibition

GD-008 does not authorize creation of, and no later document may cite it as authorizing without a
new, explicit decision naming this one:

- A Surveyor Dashboard, or any frontend component for this domain.
- Any Job, Assignment, Partner, accreditation, or customer table or aggregate.
- SECI, EQF, or PPI in any implemented form.
- Any payment table, wallet, payout, commission, or royalty mechanism.
- Any escrow or client-money-holding mechanism, automated payout, revenue-share engine, or royalty
  engine.
- Legacy Vault, Rights schema, or any historical-evidence monetisation mechanism (HEMI, LEPI, PCR,
  SLV, or any equivalent).
- Any implementation of the Marketplace or Partner bounded contexts named in §2.

**The only technical architecture work this decision authorizes is the drafting of ADR-028**, per
§5, and drafting is not itself implementation.

### 16. Relationship to existing authority

GD-008 does not supersede LV-000 (any Article, any edition); the existing tenant architecture
(ADR-010, unchanged); ADR-004's authorization model (unchanged); ADR-026's Evidence domain
(extended only insofar as ADR-028, once drafted and separately accepted, amends it — this decision
does not perform that amendment); ADR-027's Storage pilot architecture and its hard gates
(unaffected, unrelated domain); or ADR-021's current Proposed status (unchanged — this decision
does not touch Spatial Conflict Detection in any way). GD-004 and GD-007 both remain in full force,
unqualified by anything here. Existing architecture must not be rewritten retrospectively to imply
that the Surveyor Network had already been decided — Findings §1 above records plainly that nothing
in this domain existed before this decision.

### 17. Authorized next work

The only immediate architecture work authorized by this decision is **ADR-028 drafting for
Evidence actor/provenance attribution** (§5–§6). Formal Marketplace and Partner Phase 0 discovery
gates remain independently outstanding — `MARKETPLACE_DISCOVERY_AND_PLANNING.md`'s and `PARTNER_
PROGRAMME_STRATEGY.md`'s own Approval Gates are not satisfied by this decision or by either
Surveyor Network discovery document. **Each is closed only by its own, later, separate Governance
Decision** that explicitly opens that programme's Phase 0 — this decision does not open either, and
no implementation stream dependent on them may begin until its own gate is separately and
explicitly closed. Those gates must be closed before their respective implementation work.

**Review condition:** this decision should be revisited if either the Marketplace or Partner Phase
0 discovery, once opened, produces a bounded-context conclusion materially different from §2 — in
which case a later numbered decision amends this one by name, per Article XVI §2; this decision is
never edited in place.

## Approval Gate

**GD-008 is hereby ACCEPTED and IN FORCE**, per the Ratification Record above. It authorizes P0
activity and ADR-028 drafting (§5–§6, §17) with immediate effect. It does not authorize P1 or any
later stage, and does not itself close the Marketplace or Partner Phase 0 gates (§17).
