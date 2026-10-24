# LandVault Surveyor Professional Network & Commercial Architecture — Reality Audit and Governance Blueprint

**Type:** Planning and architecture analysis only. No code, migration, API, bounded context, or ADR
is introduced by this document. Follows the same "discovery and planning only, coding commences
only after explicit approval" pattern every prior programme in this repository has used
(`docs/MARKETPLACE_DISCOVERY_AND_PLANNING.md`, `docs/PARTNER_PROGRAMME_STRATEGY.md`, `docs/
COMMERCIAL_ARCHITECTURE.md`).

**Date:** 2026-09-07. **Baseline audited:** `main` at `5b8cdb08ff019949dae2aba55e3c8d6b16a8cd54`
(IMVP-5 merged, verified).

**Governed by:** LV-000 v1.8 (Article IV non-adjudication, Article VI Trust Network Doctrine,
Article IX Controlled Platform Authority, Article X §4 kernel-first sequencing, Article XII
scoring/automation, Article XV §1 Trust Neutrality Firewall) and LV-000 v1.0 Articles XIII/XVI
(Marketplace Principles; Professional Partnership and Trust Network Doctrine), incorporated by
reference under v1.8 Article II §4. `docs/MARKETPLACE_DISCOVERY_AND_PLANNING.md` and `docs/
PARTNER_PROGRAMME_STRATEGY.md` are this document's direct predecessors and remain the authoritative
scoping documents for their own named questions — this document does not re-decide what they
already left open, it builds the professional-network and commercial layer on top of them.

## Executive conclusion

The commercial thesis is sound and constitutionally compatible, provided three things hold without
exception: no scoring mechanism ever feeds back into or is fed by a verification/trust output
(Article XV §1); every professional-standing and commercial-contribution number is derived from
audited events, never a mutable persisted "score" a bug or a person could quietly change; and
implementation does not begin until the two standing, already-approval-gated discovery efforts this
repository already has waiting — Marketplace and Partner — are actually run. **Nothing in this
domain has been implemented.** The platform's kernel (Identity, Registry, Spatial partial, Evidence
partial) is real and largely solid; the entire Surveyor Professional Network and every commercial
mechanism described in this task exists today only as names in planning documents or as five RBAC
role strings. This is not a foundation defect — it is exactly the state a kernel-first platform
should be in before its first commercial programme begins. Several elements of the proposed design
(SECI, EQF, STI, HEMI, the rights lifecycle) are good ideas that need real corrections before they
are safe to build, most importantly around terminology that risks reading as an adjudication or
legal-certification claim this platform is not entitled to make.

## 1. Reality audit — verified against `main`, not inferred from planning documents

| Concept | Status | Evidence |
|---|---|---|
| User roles (RBAC) | **EXISTS** | `Role` enum (`backend/app/contexts/identity/domain/value_objects.py`): `general_user`, `field_agent`, `community_validator`, `government_observer`, `surveyor`, `surveyor_partner`, `licensed_surveyor`, `compliance_officer`, `surveyor_general`, `super_admin`, with `ROLE_RANK` and `GOVERNANCE_ROLES`/`SURVEY_ROLES` groupings |
| Surveyor roles specifically | **EXISTS, role-string only** | `surveyor`, `surveyor_partner`, `licensed_surveyor` (ordinary), `surveyor_general` (governance-tier) — role membership only; no accreditation, licence number, jurisdiction, or expiry field anywhere |
| Identity (authn) | **EXISTS** | Supabase Auth (ADR-025 E1), PDP/PEP/PIP engine (ADR-004), fully live |
| Tenant membership | **EXISTS, generic** | `Tenant` aggregate (ADR-010): id, name, owner, status, suspension — no professional/practice-type field of any kind |
| Parcels | **EXISTS** | Registry B3 (ADR-013), atomic numbering, ownership/status history (ADR-023) |
| Evidence records | **EXISTS** | ADR-026 aggregate; B5.1–B5.3 + IMVP-5 live-verified through `HASHED` |
| Evidence uploader attribution | **EXISTS, undifferentiated** | `EvidenceRecord.uploaded_by: str` — one flat field; no distinct originator, reviewer, or custodian reference |
| Audit | **EXISTS** | Kernel hash-chained `audit()` (ADR-007), used by every context including Evidence |
| Spatial data | **PARTIAL** | B4 Slices 1–2 accepted and frozen; Slice 3 (Spatial Conflict Detection, ADR-021) remains unauthorized |
| Invitations | **EXISTS** | Supabase invitation provisioning (IMVP-3A) |
| Professional/profile concepts | **NOT IMPLEMENTED** | No `SurveyorProfile`, no accreditation entity, no qualification/specialty/coverage field anywhere in the codebase |
| Payments | **NOT IMPLEMENTED** | ADR-006 names Paystack + Stripe as the *rail decision*; zero payment code exists. `docs/COMMERCIAL_ARCHITECTURE.md` explicitly states it "does not implement billing" |
| Assignments/jobs | **NOT IMPLEMENTED** | Named only as a candidate concept in `docs/MARKETPLACE_DISCOVERY_AND_PLANNING.md`'s own table; that document's own Approval Gate has not been actioned |
| Customer concepts | **NOT IMPLEMENTED** | No distinct `Customer` actor type exists; the closest analogue is an ordinary registrant/tenant user |
| Evidence originator | **NOT IMPLEMENTED** as a distinct concept | See "uploader attribution" above — the distinction this task asks for does not exist in the schema |
| Professional review | **NOT IMPLEMENTED** | The only "check" on Evidence today is the integrity read-back re-hash (ADR-007 decision 4) — a cryptographic check, not a professional QA judgment |
| Rights/licensing | **NOT IMPLEMENTED** | Zero fields, zero ADR, zero mention in `EvidenceRecord` |
| Quality scoring | **NOT IMPLEMENTED** | No code anywhere computes a quality signal for Evidence or a professional |
| Reputation | **NOT IMPLEMENTED** | "Ratings" exists only as a named-but-unresolved candidate concept, explicitly flagged as contested between Marketplace, Partner, and Community Trust ownership |
| Commercial analytics | **NOT IMPLEMENTED** | Named as a future Platform Intelligence Analytics Engine, explicitly "not designed" (`docs/TRUST_FRAMEWORK.md`) |

**Standing, already-approved-for-review planning documents this task must not duplicate**: `docs/
MARKETPLACE_DISCOVERY_AND_PLANNING.md` and `docs/PARTNER_PROGRAMME_STRATEGY.md` both carry an
unactioned Approval Gate reading "waiting for explicit direction before any programme work
begins," dated 2026-07-24/25. Neither has been opened. Their own candidate-concept tables (Job,
Assignment, Escrow, Wallet, Rating, Survey Request, Surveyor Profile, Availability) already name
most of what this task asks for and leave the same questions open this task also raises — this
document treats them as authoritative prior art, not as something to re-derive from scratch.

## 2. Constitutional constraints

Three provisions govern everything below, without exception:

- **Article IV (non-adjudication).** No schema field, score, label, or report may assert or imply
  a determination of ownership. Mechanically enforced today by the Engineering Rule 10 scanner,
  which will need its coverage extended to any new Marketplace/Professional-Network HTTP surface,
  exactly as it was extended for Evidence in IMVP-5.
- **Article VI / Article XV §1 (Trust Network Doctrine; Trust Neutrality Firewall).** Trust
  accumulates from recorded, attributable behaviour and fails safe on missing data — and, critically,
  **no pricing tier, partnership, promotional arrangement, or revenue consideration may influence a
  trust signal, a verification outcome, or the ordering of evidence, enforced by design, not by
  policy.** This is the single most load-bearing constraint on SECI/EQF/STI below: a professional
  contribution or performance metric may exist, but it must be architecturally incapable of
  reaching into, or being reached by, any code path that computes evidence trust or verification
  state. Two separate code paths, not one path with a policy note.
- **Article X §4 (kernel first).** Features that depend on the kernel may not ship ahead of the
  kernel capability they assume. Legacy Vault's integrity claims assume real immutable-storage
  infrastructure (B5.4/WORM) that does not exist yet — this is a constitutional sequencing
  constraint, not merely a suggestion (§27, §28).

## 3. Surveyor actor model

Avoiding role explosion means most of the nine named actors are **not** new RBAC roles:

| Named actor | Classification | Basis |
|---|---|---|
| Surveyor Professional | Existing RBAC role (`surveyor`/`licensed_surveyor`) | Already exists |
| Surveying Organisation/Practice | Commercial relationship — a `Tenant` sub-type or extension | ADR-010's `Tenant` is the correct home per Partner Programme's own stated question; not a new context |
| Evidence Uploader | Domain field on `EvidenceRecord` | Already exists (`uploaded_by`) |
| Evidence Originator | New domain reference field on `EvidenceRecord` | Not a role — see §14 |
| Professional Reviewer | Domain relationship on a future QA/Review entity | Reuses existing `surveyor`/`licensed_surveyor` roles filtered by domain state (assigned-as-reviewer), not a new RBAC role |
| QA Reviewer | **The one plausible new RBAC role** | Only if the PDP must gate a genuinely new authorization decision (who may transition Evidence through a professional-review state) that existing roles cannot express safely — decide during Phase S1, not now |
| Assignment Professional | Domain relationship (Job → surveyor link) | A child fact of the Job aggregate, not its own actor type |
| Regional Evidence Lead | Attribute (professional tier) on a Partner accreditation record | Not a role — a commercial/competency classification (§5) |
| Governance/Compliance Reviewer | Existing RBAC role (`compliance_officer`, `surveyor_general`) | Already exists, already governance-tier |

**Recommendation:** add at most one new RBAC role (`qa_reviewer`, if Phase S1 discovery confirms
it is genuinely needed) as an ADR-004-governed role amendment. Everything else is a domain
attribute or relationship, never a `Role` enum member — the same discipline `PARTNER_PROGRAMME_
STRATEGY.md` already flagged: "role membership alone is not accreditation tracking."

## 4. Professional progression model

The four levels should be a **competency/accreditation classification owned by the Partner
programme's future accreditation record**, not platform rank, not a permission, and never
conflated with professional licensure (an external legal fact — Nigerian surveyor registration —
LandVault records evidence of, but does not confer or itself verify beyond documentary review,
§22). Concretely: a `professional_tier` attribute on the accreditation record, with explicit
provenance (classified by whom, when, on what evidence), auditable and appealable exactly like EQF
(§9). It may gate **marketplace eligibility** — which Job categories a tier may be assigned to is
a legitimate commercial/workflow decision — but it must never itself be an RBAC authorization
input; PDP decisions stay role-based, with tier as an ordinary ABAC attribute the PDP can read
where a genuine authorization question (not merely a matching preference) requires it.

## 5. LV Job aggregate

Recommend **a new bounded-context aggregate**, matching `MARKETPLACE_DISCOVERY_AND_PLANNING.md`'s
own analysis that Job is plausibly its own context, not a Registry or Evidence extension.

- **Ownership.** A new Marketplace context owns Job's full lifecycle. Job references `Parcel`
  through a port (mirroring `ParcelExistencePort`, the exact pattern Evidence already uses), never
  a direct cross-context read.
- **Relationship to Evidence.** A Job can require or produce Evidence; Evidence stays its own
  independent, ADR-026-governed aggregate, referenced by ID, never owned or embedded by Job — the
  same boundary discipline that already keeps Evidence from directly joining `Parcel`.
- **Relationship to customer/surveyor.** Both are references to `User`/`Tenant`, not new copies of
  identity data.
- **Lifecycle.** Instruction → scope → quote → assignment → site visit → evidence production → QA
  → deliverable → payment → completion → review, each transition guarded (mirroring `Parcel.
  _ensure_mutable()`) and audited (kernel `audit()`, one event per transition, no second mechanism).
- **Cancellation/reassignment/variation.** Guarded lifecycle transitions on the same aggregate, not
  separate entities — a cancelled or reassigned Job is still one auditable record, never a deleted
  and recreated one, per the platform's append-only discipline.
- **Dispute.** Referenced, not embedded — Dispute is its own future concept (per Marketplace's own
  open question) so Job's aggregate does not grow into a god-object carrying dispute-resolution
  state that has nothing to do with survey delivery.
- **Payment boundary.** Job references a Payment/Payout event by ID only, exactly as it references
  Evidence — it never embeds payment state, mirroring how Evidence references a `storage_key`
  rather than embedding bytes.
- **Assignment.** Modeled as a child fact of Job (who is currently assigned, and the history of
  reassignment), not a separate top-level aggregate — it has no independent lifecycle.

## 6. Anti-circumvention architecture

Endorse the stated principle exactly: make platform-originated transactions commercially
advantageous and auditable, never surveilled. Concrete, economic mechanisms only:

- Declining marginal commission at volume (an incentive to route more work through the platform,
  not a penalty for not doing so).
- Faster/more convenient payment settlement on-platform than manual off-platform invoicing.
- Professional profile and portfolio accrue only from on-platform-recorded Jobs — a real, valuable,
  non-punitive reason to keep work on-platform.
- Priority access to platform-originated leads for surveyors with a consistent on-platform history.
- Enterprise eligibility requiring a minimum on-platform transaction history — a commercial gate,
  not a communications restriction.

**Explicitly rejected:** reading private messages, penalizing a surveyor for having outside
clients, or treating a pre-existing client relationship as suspect. **Attribution rule:** a
transaction counts as platform-originated only from a recorded platform-origination event (the
Job's own instruction record) — never inferred retroactively from a surveyor's business
relationships. This single rule does most of the anti-gaming work §12 and §24 also need.

## 7. Surveyor Evidence Contribution Index (SECI)

Endorsed as a professional-contribution metric, explicitly not money and not evidence truth,
subject to the Trust Neutrality Firewall (§2). Components as proposed (field evidence,
completeness, reproducibility, professional review, discrepancy identification, professional
reports, difficult assignments) are reasonable **provided none of them can be satisfied by
reaching a particular ownership conclusion.**

**Rejected wording, corrected:**

| Dangerous | Safe |
|---|---|
| Resolved evidence conflict | Evidence discrepancy professionally documented / reconciled |
| Conflict Resolution | Discrepancy Documentation |

**"Material inconsistency remains unresolved" must be a valid, high-quality, well-scored outcome
by design** — the alternative (rewarding apparent resolution over honest uncertainty) is precisely
the incentive structure Article IV exists to prevent, restated at the scoring layer rather than
only at the schema layer.

## 8. Evidence Quality Factor (EQF)

`SECI = Base Contribution × EQF` is an acceptable multiplicative structure only if EQF is bounded
(e.g. 0–1, never able to zero out or wildly amplify a contribution on one reviewer's say-so) and
its inputs are objectively observable: completeness, provenance completeness, reproducibility
(does independent field data reconcile), methodological clarity, correction-rate history. **EQF is
never a truth signal** — it never asks or answers whether the evidence's content is correct about
ownership, only whether the evidence *package* is complete, reproducible, and professionally
sound.

**Governance:** dual-scored — an automated, checklist-derived component (completeness/attachment
presence) plus a human QA component, with conflict-of-interest exclusion (no self-review, no
review of a close commercial relation), an appeal path (a second, different reviewer on contest),
and full audit of every scoring event (who, when, rubric version) per Article XII §2's
explainability requirement.

## 9. Surveyor Trust Index — recommend renaming

**Recommend "Professional Performance Index" (PPI), not "Trust Index."** "Trust" already has a
specific, constitutionally load-bearing meaning on this platform (Article VI — evidence trust);
naming a commercial-performance metric "Trust" invites exactly the reader confusion Article XV §1
structurally exists to prevent. Dimensions: SLA adherence, completion rate, correction rate,
responsiveness, platform-transaction compliance (an anti-circumvention signal, legitimate since it
measures platform conduct, not evidence truth), customer satisfaction (structured, fail-safe on
thin data per Engineering Rule 3), credentials-on-file (a fact, not a score). PPI must never be
described, exposed, or usable as implying the surveyor's ownership conclusions carry legal weight.

## 10. Compensation architecture

Three ledgers, kept strictly separate, with no equation crossing between them:

1. **Surveyor Professional Earnings** — money owed for delivered work: fixed professional fee by
   job type/complexity, a separate QA/reviewer fee (paid for review work, distinct from the
   surveyed work's own fee, avoiding a reviewer profiting from a particular review outcome),
   complex-assignment premium, travel/remote-site uplift.
2. **LandVault Platform Revenue** — commission, declining at volume (§6), enterprise negotiated
   rates.
3. **Evidence Contribution Points (SECI)** — professional standing only. Not currency, not
   redeemable 1:1 for cash, not a revenue proxy.

SECI may gate **eligibility** (minimum tier required for certain job categories) without being a
direct multiplier on money — this keeps the Trust Neutrality Firewall intact between
contribution-recognition and cash.

## 11. Platform Capture Rate (PCR)

Endorsed, cautiously, **only if "known value" is defined exclusively from platform-recorded
events** (a Job's own instruction and completion records) — never from external surveillance of a
surveyor's business, bank statements, or off-platform earnings disclosure. This single definitional
choice removes most of the surveillance risk by construction rather than by policy promise, and
necessarily redefines PCR as "platform-originated transactions that stayed on-platform to
completion," not "total professional income captured." Reporting: quarterly/rolling, aggregated;
never used punitively against an individual surveyor absent a specific, evidenced circumvention
complaint, investigated case-by-case.

## 12. Surveyor Lifetime Value (SLV)

An internal financial-planning metric only — never shown to the surveyor, never used to justify a
professional-standing or tier decision, explicitly separate from PPI/competence. A commercially
valuable professional is not automatically a more competent one, and the architecture must keep
these two judgments in separate systems so one can never silently substitute for the other. Derived
from ledger events on demand, not a persisted per-surveyor field.

## 13. Evidence Originator

**Recommend distinguishing, as separate nullable reference fields on `EvidenceRecord`:**
`uploaded_by` (already exists), `originated_by` (who actually produced the underlying observation —
may differ from the uploader, e.g. a firm employee uploads a senior surveyor's field data),
`reviewed_by` (professional QA reference, may be null until reviewed), `custodian` (who currently
holds physical/original custody, relevant for historical material). **Rights Holder** and
**Licensor** are deliberately deferred to the rights/licensing model (§16) rather than added here —
they carry legal complexity (multi-party rights, expiry) that does not belong on the core
integrity-focused aggregate.

**ADR treatment:** this is an **amendment to ADR-026**, not a new standalone ADR — it is squarely
about `EvidenceRecord`'s own aggregate shape, the exact subject ADR-026 already governs. The
broader rights/licensing lifecycle (§16) is different enough in kind (a legal state machine, not a
core integrity concept) to warrant its own, later ADR.

## 14. Surveyor Legacy Vault

A sound future capability, but **sequenced after B5.4 (WORM/sealing), not before or parallel to
it** — Article X §4 (kernel first) applies directly: a private historical archive that feels
permanent to contributors should not be built on an infrastructure whose actual immutability
guarantee (`put_immutable`/`worm_grade`) is still `NotImplementedError` on every adapter that
exists today. **Do not assume the uploading surveyor owns all rights** to historical material
(survey plans, photographs, CAD, GIS, GNSS, reports, drawings, remote-sensing outputs) — rights
assessment (§16) must run before anything is treated as commercially eligible.

## 15. Historical Evidence rights lifecycle

The proposed L0–L5 lifecycle is sound and already avoids the dangerous word "Verified" at L4
("Quality/Provenance Reviewed," not "Verified"). Extend that discipline everywhere: **"Verified"
should not appear anywhere in this domain's terminology** — it too easily reads as a legal or
ownership conclusion (§21). Rights dimensions to track explicitly: copyright, client
confidentiality, personal data (NDPR implications, §22), third-party rights, contractual
restrictions from the original commissioning engagement, commercial-reuse permission, withdrawal
right, already-authorized downstream uses, and any retention obligation. Each dimension needs its
own recorded attestation with legal consequence disclosed to the contributor, audit-logged, not a
single unexplained checkbox.

## 16. Evidence Asset Passport

Sound structure. The passport must always preserve historical statements as **what was observed,
when, by whom, using what method, with what limitations** — and never automatically compute or
imply "therefore Person X owns the land," restating Article IV at the data-model layer for
historical material exactly as ADR-026 already does for live Evidence.

## 17. Historical Evidence monetisation

All three models (accepted-asset licence, attributable revenue share, evidence royalty) are
evaluable without hard-coding a percentage at architecture stage, per instruction. The
architectural requirement common to all three: an **event-sourced usage/royalty ledger** keyed by
individual usage events, not a static percentage field on the asset — this is what actually
handles multi-originator evidence, derivative products, and double-counting cleanly, none of which
a flat field can represent. Minimum payout, withdrawal, rights expiry, and tax/payment handling are
Payment-context concerns layered on top of this ledger, not Evidence-context concerns.

## 18. Historical Evidence Monetisation Index (HEMI)

`commercially activated eligible historical evidence / eligible historical evidence` is **easily
gamed by shrinking the denominator** — reclassifying inconvenient evidence as "ineligible" raises
HEMI without growing real activation. **Recommend: monitoring metric only, never a target with
individual or team consequences attached**, paired with a second, unshakeable metric tracking
eligibility-classification drift over time, so denominator gaming becomes visible rather than
invisible.

## 19. Commercial indices — recommended minimum set

| Proposed | Recommendation | Owner |
|---|---|---|
| LRI (Revenue Index) | Keep | Finance |
| VER | Rename to **Attributed Evidence Revenue (AER)** — "Verified" removed | Finance |
| PCR | Keep, narrowly defined (§11) | Product/Marketplace |
| SLV | Keep, internal-only (§12) | Finance |
| HEMI | Keep as monitoring-only (§18) | Product |
| LEPI | **Drop** — duplicates SECI/contribution reporting without new information | — |
| EREI | **Drop** — a simple derived ratio (Revenue ÷ active contributors), computable ad hoc, not worth a standing named KPI | — |

Smallest useful executive set: **LRI, AER, PCR, SLV (internal), HEMI (monitored)** — five, not
seven, with LEPI and EREI folded into existing reporting rather than tracked as separate indices.

## 20. Terminology corrections

| Flagged | Risk | Recommended |
|---|---|---|
| Verified Evidence | Implies legal/ownership truth | Evidence Reviewed / Integrity-Confirmed Evidence |
| Surveyor Trust Index | Collides with Article VI's own "Trust" meaning | Professional Performance Index |
| Evidence Verification | Same as above | Evidence Review / Integrity Check |
| Conflict Resolution | Implies LandVault settles disputes | Discrepancy Documentation |
| Expert-level report | "Expert" is a legal term of art with jurisdiction-specific standing implications | Senior Professional Report / Enhanced Evidence Report, with an explicit disclaimer that it is not expert-witness testimony unless separately and specifically commissioned outside the platform's own claim |
| Court/mediation-grade evidence | LandVault cannot certify admissibility in any court | Evidence prepared to LandVault's Enhanced Documentation Standard, with an explicit no-admissibility-guarantee disclaimer |

## 21. Professional / regulatory boundary — Nigerian counsel required, not assumed

This document makes an architecture recommendation only; the following are open legal questions
requiring Nigerian counsel and, where relevant, the Surveyors Council of Nigeria (SURCON), not
resolved by this document and not answerable from UK RICS practice by analogy:

- Whether SURCON registration is required for any "Evidence Collector"/Level 1 field activity this
  platform would facilitate, and what a non-licensed contributor may lawfully do.
- Professional indemnity insurance requirements for licensed surveyors operating through a
  platform intermediary.
- Whether LandVault's commission model constitutes a regulated referral-fee arrangement under
  Nigerian professional-conduct rules for surveyors.
- Whether any report tier could be construed as a licensed survey deliverable requiring a licensed
  surveyor's seal/signature under Nigerian law.
- Consumer protection obligations toward customers using the platform.
- VAT/withholding tax treatment of commissions, payouts, and royalties.
- NDPR (Nigeria Data Protection Regulation) obligations for customer and professional data,
  including historical-material personal data in the Legacy Vault.
- Default copyright ownership rules under Nigerian law for commissioned survey work product — this
  single answer materially shapes the entire rights-assessment workflow (§16) and should be
  obtained before that workflow's domain model is finalized, not discovered mid-implementation.
- Advertising/solicitation rules applicable to licensed professionals using the platform.
- Dispute-handling obligations specific to licensed professional services.

## 22. Payment architecture (analysis only, not implemented)

Concepts required, none built: `Payment` (a single money-movement event), `Payout` (money to a
surveyor), `PlatformFee`, `Refund`, `Dispute` (referenced, not embedded, per §5), `RevenueShare`/
`Royalty` (Legacy Vault, later). **Escrow is the one item requiring a legal answer before an
architecture answer**: whether LandVault may lawfully hold client funds pending a condition is a
Central Bank of Nigeria / payment-service-provider licensing question, not assumed here.
**Recommend defaulting to a non-escrow model** — direct payment release on milestone completion via
the existing Paystack/Stripe rails (ADR-006), no funds held by LandVault itself — unless and until
counsel confirms an escrow-like holding mechanism is viable. This is both the safer architecture and
the only honest answer available at this stage.

## 23. Fraud and gaming red-team

| Threat | Control (economic/audit, not surveillance) |
|---|---|
| Fake uploads for SECI | EQF completeness/reproducibility check; Evidence must attach to a real Job with a real customer-instruction event, raising fabrication cost |
| Surveyor/customer collusion | Statistical anomaly review of repeat identical-pair transactions, surfaced to human governance review — never automated punishment, mirroring ADR-021's own fraud-detection doctrine |
| Unnecessary repeat surveys | Job history visible to Governance; review triggers, not blocking rules |
| Inflated complexity classification | Self-declared, subject to spot-audit by a Regional Evidence Lead/QA reviewer; correction affects future EQF, not immediate punishment |
| QA-review rings | Conflict-of-interest exclusion, reviewer rotation, audited reviewer-approval-pattern monitoring |
| Duplicate historical evidence | Hash-based duplicate detection before accepting a "new" historical asset, reusing ADR-007's existing integrity mechanism |
| Fabricated rights claims | Explicit attestation with disclosed legal consequence, audit-logged; egregious cases handled by the existing break-glass/governance escalation doctrine, not a new mechanism |
| False customer satisfaction | Signal tied to a real completed-Job event, rate-limited per customer-job pair, fail-safe on thin data |
| Revenue attribution manipulation | PCR's platform-events-only definition (§11) removes most of the gaming surface by construction |
| Off-platform payment hiding | Addressed economically (§6), not by surveillance — some leakage is an accepted cost of not building a surveillance platform |
| Deliberate evidence fragmentation | SECI weights by Job-level contribution, not raw per-upload count, removing the incentive to split uploads |
| Scoring bias | Reviewer-blind assignment where practical, appeal path, Governance monitoring of reviewer-decision distribution for statistical outliers |

## 24. Minimum domain primitives

Genuinely new aggregates only — no table created merely because a KPI exists:

- **Professional Accreditation** (Partner context) — references `User`/`Tenant`, does not extend them.
- **Job** (Marketplace context) — new aggregate, per §5. Assignment is a child fact of Job, not its
  own aggregate.
- **Payment / Payout / PlatformFee** — Economic/Billing (context #10) ledger events.
- **Evidence Originator/Reviewer/Custodian** — new fields on the existing `EvidenceRecord`
  aggregate (§13), not a new aggregate.
- **Rights** — a new, small aggregate referenced by Evidence, not embedded, given genuine legal
  complexity (multi-originator, expiry, withdrawal).
- **SECI / EQF / PPI** — **explicitly derived, never persisted score fields.** Computed on demand
  or via a scheduled/event-driven read-model projection from Job/Evidence/Review events. A mutable
  "score" column is a bug and a governance risk a derived projection structurally cannot become.
- **Historical Evidence Asset** (Legacy Vault) — its own aggregate, deliberately separate from live
  parcel Evidence, given its different provenance/rights shape.

## 25. ADR requirements — determined by repository reality, not assumed

**Next available ADR number, verified: `ADR-028`.** `docs/adr/` contains ADR-001 through ADR-019,
ADR-021 through ADR-027; ADR-020 remains deliberately, permanently vacant and must not be filled.

**Do not draft four ADRs speculatively.** Applying Engineering Rule 5 and this platform's
Architecture-Before-Code discipline:

1. **Run the two standing, already-approval-gated Phase 0 discoveries first** — `docs/
   MARKETPLACE_DISCOVERY_AND_PLANNING.md` and `docs/PARTNER_PROGRAMME_STRATEGY.md`. Neither has
   been opened. No ADR for Job, Assignment, or Professional Accreditation should be drafted before
   these resolve their own named open questions (is Marketplace one context or several; is a
   partner a `Tenant` sub-type or a new aggregate).
2. **ADR-028 candidate (amendment path):** Evidence Originator/Reviewer/Custodian fields — an
   amendment to ADR-026, narrower and ready sooner than the others (§13).
3. **A Job/Marketplace domain-model ADR** — emerges from the Marketplace Phase 0, not drafted now.
4. **A Marketplace authorization-model ADR** — planned from the start per that document's own
   Objective 3, not escalated later.
5. **A Professional Contribution/Reputation (SECI/EQF/PPI) ADR** — recommend as its **own** ADR,
   separate from the Job ADR, given how much constitutional weight (Trust Neutrality Firewall)
   rests on getting this one right; it deserves dedicated review, not a subsection.
6. **A Rights & Historical Evidence Licensing ADR** — sequenced after B5.4/WORM, per §14.
7. **A Marketplace payment/escrow ADR** — gated on the legal analysis in §21/§22; do not draft this
   blind to the legal answer on escrow viability.

## 26. Delivery sequencing — challenged and refined

The proposed S0–S5 shape is directionally right; refined as follows:

- **Phase S0 — Governance/Foundation.** Must explicitly include *running* the Partner and
  Marketplace Phase 0 discoveries — they are not optional preliminaries, they are standing,
  already-approved-to-request gates sitting unactioned in this repository.
- **Phase S1 — Professional Profiles & Assignments.** As proposed, following the Accreditation ADR.
- **Phase S2 — Professional QA & Contribution.** As proposed, following the SECI/EQF/PPI ADR.
- **Phase S3 — Marketplace/Transactions.** As proposed, gated on the escrow legal answer (§22).
- **Phase S4 — Legacy Evidence.** **Explicitly gated behind B5.4 (WORM/sealing) completion**, per
  Article X §4 — not proposed in the original sequence, but constitutionally required.
- **Phase S5 — Commercial Monetisation.** **Recommend collapsing into "S3+, contingent on real
  usage data"** rather than a fixed phase — KPI/monetisation-index work performed before real
  transaction volume exists is speculative and, per §18's own HEMI finding, more likely to be
  gamed or meaningless than useful.

## 27. Explicit non-goals of this document

No code, migration, frontend component, Surveyor Dashboard, payment integration, or points table is
created by this analysis. No ADR is drafted or numbered beyond identifying that `ADR-028` is the
next available slot. No percentage, fee, or price is set (§10, §17).

## 28. Pre-mortem

| Failure mode | Cause | Early warning | Mitigation | Architectural implication |
|---|---|---|---|---|
| Constitutional failure | A scoring or commercial mechanism leaks into evidence trust | A trust/verification code path reads a commercial field, or vice versa | Two structurally separate code paths, enforced by review and, where possible, an automated boundary check (Engineering Rule 6 style) | The Trust Neutrality Firewall is a build-time constraint, not a code-review reminder |
| Professional/regulatory failure | Nigerian licensing/indemnity obligations not met | Counsel flags a gap after launch, not before | Engage Nigerian counsel and SURCON liaison at S0, before Phase S1 domain modeling | §21 questions must be closed, not deferred, before Job/Assignment implementation |
| Surveyor rejection | Fees/terms feel extractive, or Level system feels like unpaid ranking | Low sign-up conversion, high early churn | Fee structure and tier system co-designed with real surveyors before build, not imposed | Product decision, not purely architectural, but the SECI/PPI separation from money (§10) directly affects perceived fairness |
| Customer circumvention | Anti-circumvention model too weak or too aggressive | High off-platform completion rate, or surveyor complaints about surveillance | Economic incentives (§6) tuned iteratively, never escalated to monitoring | Attribution stays platform-event-only (§11) regardless of pressure to do more |
| Platform leakage | Same as above, systemic | PCR trending down over multiple periods | Investigate case-by-case, not via blanket policy change | PCR's definition (§11) must not be redefined to justify surveillance later |
| Low evidence quality | EQF too lax or gameable | Correction-rate rising, customer complaints | Tighten EQF rubric, add reviewer rotation | EQF must stay derived and auditable so tightening doesn't require a data migration |
| Scoring manipulation | Gaming per §23's table | Statistical anomalies in reviewer or SECI patterns | Governance-facing anomaly dashboards, human review, never automated penalty | Every score stays a read-model projection an anomaly investigation can recompute and compare |
| Rights/copyright disputes | Rights assessment skipped or rushed | A contributor or third party disputes an eligible-for-monetisation classification | Legal-consequence-disclosed attestation (§16) plus a withdrawal right | Rights aggregate must support correction/withdrawal from day one, not as a later patch |
| Payment/regulatory problems | Escrow built without legal clearance | A regulator inquiry, or a payment-rail partner objection | Non-escrow default (§22) until counsel confirms otherwise | Architecture must not assume escrow is available |
| Marketplace liquidity failure | Too few surveyors or too few customers to match | Low Job-fill rate | Product/growth problem; architecture should not over-build matching automation (§4's "Match" question) before liquidity is proven | Keep matching manual/governance-assisted until volume justifies automation, per Platform Intelligence's own four-part test |
| Excessive complexity | Building all of SECI/EQF/PPI/HEMI/PCR/SLV/rights/Legacy-Vault at once | Long time-to-first-real-transaction | Sequence per §26; nothing in S4/S5 before S0–S3 prove out | This is the primary risk this document exists to prevent |
| Premature dashboard development | A Surveyor Dashboard built before the domain model it displays is stable | UI churn, wasted frontend work | Explicitly out of scope for this task and for any phase before S1's domain model is ADR-accepted | No dashboard work until the underlying aggregates exist and are stable |
| Economic model failure | SECI/PPI/fees don't actually produce the intended surveyor behavior | Contribution quality doesn't track intended incentives | Treat the economic model as a hypothesis to test with real data (S3+), not a fixed design | KPIs (§19) stay monitoring tools during this period, not targets with consequences |

## 29. Recommended immediate next governance decision

Open the two standing Phase 0 discoveries — `docs/MARKETPLACE_DISCOVERY_AND_PLANNING.md` and
`docs/PARTNER_PROGRAMME_STRATEGY.md` — as the actual next step, not a new document. In parallel,
engage Nigerian legal counsel on the §21 open questions, since the copyright-default and
escrow-legality answers materially shape the Rights and Payment ADRs before they can be drafted
responsibly. Do not draft ADR-028 or any Job/Professional/Rights ADR until at least the
bounded-context question in Marketplace's own Phase 0 ("is Marketplace one context or several") is
answered.

## Approval Gate

No Surveyor Professional Network or Commercial Architecture implementation work has begun, and none
is authorized by this document. This report answers the architecture question the task posed; it
does not open Marketplace's or Partner's own Phase 0 discoveries, which remain separately gated by
their own existing Approval Gates. **Waiting for explicit Governance direction before any of this
programme's work — discovery, ADR drafting, or implementation — begins.**
