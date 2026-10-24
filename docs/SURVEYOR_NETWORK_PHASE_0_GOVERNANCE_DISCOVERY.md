# Surveyor Network — Phase 0 Governance Discovery

**Type:** Discovery and reconciliation only. No code, migration, API, bounded context, or ADR is
introduced. Uncommitted per instruction; does not alter `docs/MARKETPLACE_DISCOVERY_AND_PLANNING.
md`, `docs/PARTNER_PROGRAMME_STRATEGY.md`, or `docs/SURVEYOR_PROFESSIONAL_NETWORK_AND_COMMERCIAL_
ARCHITECTURE.md`, all read in full and treated as source material, not rewritten.

**Baseline:** `main` at `5b8cdb08ff019949dae2aba55e3c8d6b16a8cd54` (unchanged since the prior
reality audit). **Date:** 2026-09-08.

## Executive decision summary

Two bounded contexts are the minimum needed for the pilot — Marketplace and Partner — not seven.
A Surveying Practice or individual surveyor is a `Tenant` (unchanged, undistorted); "Partner" is an
accreditation record referencing that tenant and, where an individual is being tracked within a
firm, a specific user inside it — never a new isolation primitive. Job and Assignment are separate:
Job is the customer-facing aggregate, Assignment is a child fact of it, which is what actually
supports multiple surveyors, reassignment, and a separate QA reviewer without new top-level
aggregates. Evidence stays fully independent, referenced by Job/Assignment, never owned by them.
One ADR is genuinely ready now — the Evidence Originator/Reviewer/Commissioned-by amendment to
ADR-026 — and nothing else is. Everything Job/Marketplace/Partner/Payment/Rights-shaped remains
blocked on two things that are not architecture questions: the two standing Phase 0 discoveries
this repository has never opened, and Nigerian legal counsel on a specific, named list of
questions this document does not attempt to answer itself.

## 1. Source authority

| Source | Status | Authority |
|---|---|---|
| `MARKETPLACE_DISCOVERY_AND_PLANNING.md` | Planning recommendation, 2026-07-24, unactioned Approval Gate | Names candidate concepts; decides nothing; does not override an Accepted ADR or current code |
| `PARTNER_PROGRAMME_STRATEGY.md` | Planning recommendation, 2026-07-25, unactioned Approval Gate | Same status; the two documents are each other's named dependency |
| `SURVEYOR_PROFESSIONAL_NETWORK_AND_COMMERCIAL_ARCHITECTURE.md` | New analysis, uncommitted | A proposal layered on top of the two above; does not supersede them |
| LV-000 v1.8 (+ v1.0 incorporated) | **Supreme, in force** | Article IV (non-adjudication), Article VI/XV§1 (Trust Neutrality Firewall), Article IX (Controlled Platform Authority), Article X §4 (kernel first) bind every decision below without exception |
| ADR-004, ADR-010, ADR-011, ADR-026, ADR-027 | **Accepted, implemented, in force** | Role model, Tenant aggregate, Delegation, EvidenceRecord, Storage authorization — the actual constraints any new design must fit inside, not negotiate with |
| Current `main` implementation | **Ground truth** | `Role` enum, `Tenant`, `EvidenceRecord.uploaded_by`, kernel audit — verified by direct inspection, not inferred |

No planning assumption in the first three rows is permitted to override anything in the last three.
Where a planning document's candidate concept conflicts with an Accepted ADR's actual shape (e.g.,
a document imagining a "Partner" aggregate independent of `Tenant`), the ADR and the code win, and
the planning document's assumption is recorded below as **OBSOLETE ASSUMPTION**, not silently
adopted.

## 2. Three-document reconciliation matrix

| Concept | Marketplace-plan | Partner-strategy | Blueprint | Classification |
|---|---|---|---|---|
| Marketplace bounded-context count | Open question, explicitly unresolved | Assumes Marketplace exists as a sibling | Recommends decomposition (§3 below) | **UNDECIDED** — this document resolves it |
| Professional identity | Not addressed | Central concern (accreditation) | Elaborated (actor model) | **CONSISTENT** — no conflict, different depth |
| Tenant model | Not addressed | Assumes `Tenant`/delegation as "likely-reusable," not decided | Recommends Tenant unchanged, Partner as referencing record | **CONSISTENT** once resolved here (§4) |
| Customer/client model | Names "Survey Request" without defining requester | Not addressed | Names the gap explicitly | **UNDECIDED** — resolved §6 |
| Jobs | Names as candidate, "Job vs Survey Request" left open | Not addressed | Proposes full lifecycle aggregate | **OVERLAPPING** — this document resolves Job-vs-Survey-Request (§7) |
| Assignments | Named as candidate, exclusivity-vs-bidding left open | Not addressed | Names as Job child fact | **CONSISTENT** once scoped (§7) |
| Qualifications/accreditation | Not addressed | Central concern, "genuinely new capability" | Elaborates discovery items | **CONSISTENT** |
| Evidence originator | Not addressed | Not addressed | New proposal, ADR-026 amendment | **NEW PROPOSAL** — no prior conflict to reconcile |
| Professional review | Not addressed | "Performance management," deliberately under-specified | Names as QA/EQF input | **CONSISTENT**, both deliberately vague pending Phase 0 |
| Pricing | "Open questions, not answers" (Commercial Architecture) | Not addressed | Names three-ledger separation | **CONSISTENT** |
| Payments | Names Wallet/Payment as candidate, overlap with context #10 unresolved | Names Earnings/Wallet, same overlap | Recommends non-escrow default | **CONFLICTING with nothing accepted** — genuinely open, resolved §15 |
| Payouts | Same as above | Same as above | Distinguishes from platform revenue | **CONSISTENT** |
| Commissions | Not modeled | Not modeled | Names as one of three ledgers | **NEW PROPOSAL** |
| Reputation/performance | "Ratings" — ownership contested between Marketplace/Community Trust | "Ratings" — same contest, adds Partner as a third claimant | Recommends Partner owns standing, Marketplace contributes events | **CONFLICTING** between the two plans, **resolved** here (§3) |
| Evidence contribution scoring (SECI) | Not addressed | Not addressed | Central new proposal | **NEW PROPOSAL** |
| Historical Evidence | Not addressed | Not addressed | Central new proposal (Legacy Vault) | **NEW PROPOSAL** |
| Rights/licensing | Not addressed | Not addressed | Recommends separate Rights context | **NEW PROPOSAL** |
| Enterprise relationships | Named as a sibling programme, not integrated here | Not addressed | Not addressed | **UNDECIDED**, out of scope for this discovery, noted not ignored |

**Obsolete assumption flagged:** no source document ever proposed a Partner aggregate independent
of `Tenant`, so there is no actual conflict with ADR-010 to correct — this is recorded to confirm
the check was performed, not because a correction was needed.

## 3. Marketplace bounded-context decision

Tested against the seven named domains:

| Candidate domain | Decision | Reasoning |
|---|---|---|
| Demand / Customer Instruction | **Inside Marketplace** | Tightly coupled to Job's own opening lifecycle step; splitting it out now is premature decomposition of a context with zero implementation |
| Job / Assignment | **Marketplace's core aggregate** | See §7 |
| Commercial Terms / Quotation | **Inside Marketplace** | Same reasoning as Demand — part of one Job's lifecycle, not an independent transaction |
| Professional Network | **Separate context (Partner)** | A standing relationship independent of any single transaction — `PARTNER_PROGRAMME_STRATEGY.md`'s own "why a distinct programme" reasoning is correct and stands |
| Payments / Payouts | **Existing Economic/Billing context (#10), not Marketplace** | Marketplace references payment events by ID, exactly as Evidence references `storage_key` — never embeds payment state |
| Reputation / Professional Performance | **Partner owns the standing record; Marketplace contributes the events** | Resolves the ownership contest both plans left open — same "two contexts, integration by event" pattern Registry/Spatial already use |
| Evidence Rights / Legacy Evidence | **Deferred entirely for the pilot; own context when built** | Not needed for the minimum viable slice (§18); must never become part of Marketplace when it is built, per Article V |

**Recommended minimum decomposition for the pilot: two new bounded contexts — Marketplace (Demand,
Job, Assignment, Quotation) and Partner (professional identity, accreditation, standing/PPI).**
Payments stay in the already-named Economic/Billing context. Evidence Rights, Legacy Vault, and
Enterprise integration stay explicitly outside the first implementation.

## 4. Partner / tenant decision

**A Partner is not a new isolation primitive.** Tested directly against the existing two-layer
tenant-isolation architecture (RLS + application-layer check, Article VIII §2): inventing a
professional actor with no tenant association would break that discipline for the first time in
this platform's history, since every existing RLS policy and PDP check keys off `tenant_id`.

**Decision:** `Tenant` remains exactly what ADR-010 already made it. A new **Partner Accreditation**
record is added, referencing `tenant_id` and an optional `user_id`:

- `user_id` **null** → practice-level accreditation, covering the whole tenant (a firm's own
  registration).
- `user_id` **populated** → an individual professional's accreditation within that tenant.

This single shape covers a solo practitioner's own one-person tenant and a firm tenant with
multiple accredited individual employees without inventing a second tenant concept, and it sits as
a *referencing* record exactly the way Evidence already references Parcel — no distortion of the
tenant model to fit a commercial label.

## 5. Individual professional vs. surveying practice

| Question | Answer |
|---|---|
| Who holds the platform account? | The `Tenant` — a firm or a solo practitioner's own tenant |
| Who receives the assignment? | A specific `User` (`assigned_user_id` on the Assignment child record, §7) — always an accountable individual, whether the tenant is a firm or a solo practice |
| Who performs the field work? | The assigned user, or a subordinate they direct — not assumed identical to the originator |
| Who originates Evidence? | A distinct reference (§9) — may differ from the assigned professional (a junior field agent under supervision) |
| Who reviews it? | A distinct professional reference, same or different tenant depending on whether review is internal QA or platform governance QA |
| Who invoices/receives payout? | The `Tenant` by default — the commercial/billing unit ADR-010 already established; a solo practitioner is the degenerate one-person case, not a second payee concept |
| Whose qualifications are represented? | The specific `User`'s — a licence belongs to a person under essentially every professional-licensing regime, Nigeria's almost certainly included (external confirmation required, §11) |
| Whose professional liability attaches? | **External legal question, not answered here** — flagged in §11 |

Do not assume these are always the same actor; the data model above deliberately keeps each
question separately answerable per Job.

## 6. Customer / Party decision

**LandVault needs a first-class, minimal Party concept before Job can exist** — an authenticated
`User` is not automatically a commercial customer, per instruction. Two cases:

1. **Existing platform user/tenant** — the common case (a registrant instructing work on their own
   already-registered parcel). No new identity primitive needed; Job simply references the existing
   `User`/`Tenant`.
2. **External instructing party** — a solicitor, bank, developer, or government body without
   (or not requiring) a full platform account, and a surveyor's own pre-existing client in the
   common real-world case. **Recommend a lightweight `Contact`/`Instructing Party` value object on
   the Job itself** (name, contact detail, organisation type) — not a new Identity-context actor,
   not a login-capable account. This deliberately keeps "who can authenticate" and "who commissioned
   this Job" as separate facts, exactly as instructed.

## 7. Job vs. Assignment — recommended aggregate boundaries

**Not the same aggregate.** `Job` is the customer-facing transaction aggregate: instruction, scope,
quote, overall status, deliverable reference, payment reference. `Assignment` is a **child fact of
Job**, not a separate top-level bounded-context aggregate — it has no independent lifecycle beyond
the Job's own.

This boundary handles every named scenario without new top-level aggregates:

- **Multiple surveyors on one Job** — multiple `Assignment` children.
- **Reassignment** — an `Assignment` is cancelled and a new one created; the `Job`'s own identity
  and history are untouched.
- **Specialist subcontractor** — a distinct `Assignment` with its own role/type on the same Job.
- **QA reviewer separate from field surveyor** — a second `Assignment` with `role = QA_REVIEW` on
  the same Job.
- **Cancelled assignment while Job remains active** — `Assignment` state changes independently of
  the Job's own overall status.
- **Multiple parcels** — recommend one Job references one Parcel; a multi-parcel instruction
  becomes multiple linked Jobs sharing one customer instruction reference, mirroring Registry's
  own one-parcel-per-aggregate discipline rather than growing Job into a multi-parcel object.
- **Repeat site visits** — tracked as events/sub-records under an `Assignment`, not a new aggregate.

## 8. Evidence relationship

Evidence stays exactly what ADR-026 already made it — **not** made subordinate to Marketplace.
A Job/Assignment **references** Evidence by ID via a new optional, nullable field on
`EvidenceRecord` (mirroring how `parcel_id` already references Registry), never the reverse:
Evidence must never require a Job to exist.

- **Evidence created during a Job** — the reference is populated at upload time.
- **Evidence submitted independently of a Job, historical Evidence, third-party Evidence** — the
  reference is null; this is a legitimate, first-class state, not a special case requiring its own
  code path.
- **Evidence reused by multiple Jobs** — "reuse" means a later Job *points to* an existing
  `EvidenceRecord`, never copies or re-parents it. The reference stays single-owner at creation;
  later reference is a separate, additive relationship, not a rewrite.
- **Evidence reviewed by another professional** — the `reviewed_by` field (§9), independent of
  which Job or Assignment produced the evidence.

## 9. Evidence Originator decision

**A Party reference — a new nullable field on `EvidenceRecord`, added by amending ADR-026** —
not necessarily a Professional-role-holder (historical evidence may originate from a party who
never held a LandVault role at all).

Three new fields, kept deliberately separate:

- `originated_by` — who actually produced the underlying observation. Distinct from `uploaded_by`
  (who performed the HTTP upload — a system fact) exactly because a firm employee may upload a
  senior surveyor's field data.
- `reviewed_by` — the professional QA reference, nullable until reviewed.
- `commissioned_by` — a reference to the Job/Assignment that caused the evidence to be produced,
  nullable for independently-submitted or historical evidence.

`rights_holder` and `licensor` are **deliberately not added here** — they carry legal complexity
(multi-party rights, expiry, withdrawal) that belongs in the future Rights context (§16), not on
the core integrity-focused aggregate. Multi-originator support (a historical plan with two
co-surveyors) is **not solved now** — `originated_by` stays single-reference for the immediate
scope; multi-originator is a documented future extension only if and when Legacy Vault is actually
built, avoiding a table built for a hypothetical.

**This requires evolving ADR-026** — a narrow amendment adding three nullable fields, not a new
standalone ADR.

## 10. Accreditation / qualification discovery

Represent, without claiming to grant status: registration/licence number (as submitted), issuing
body, qualification description, claimed validity period, practice/firm affiliation (a reference to
`Tenant`), specialty/competence tags. **Recommend storing the submitted credential document itself
as an ordinary `EvidenceRecord`** (a new `evidence_type`, e.g. `PROFESSIONAL_CREDENTIAL`) — reusing
the existing, already-live pipeline (server-side hashing, integrity read-back, audit) rather than
inventing a second document-storage mechanism. The accreditation record's own status field must
read as **"credential submitted and reviewed by LandVault for completeness,"** never "LandVault
confirms this person is licensed" — that determination belongs exclusively to the issuing body
(SURCON or equivalent), and no field, label, or API response may imply otherwise, per Article IV
applied to this domain exactly as it already applies to ownership.

## 11. Nigeria research/legal checklist

| Item | Classification |
|---|---|
| Surveyors Council of Nigeria (SURCON) registration framework applicability | **NIGERIAN LEGAL COUNSEL REQUIRED** |
| Individual surveyor licensing requirements | **NIGERIAN LEGAL COUNSEL REQUIRED** |
| Firm/practice registration requirements | **NIGERIAN LEGAL COUNSEL REQUIRED** |
| Professional seal/signature requirements on deliverables | **NIGERIAN LEGAL COUNSEL REQUIRED** |
| Permissible referral/platform commission arrangements | **NIGERIAN LEGAL COUNSEL REQUIRED** |
| Professional advertising rules | **NIGERIAN LEGAL COUNSEL REQUIRED** |
| Professional liability / indemnity attribution (individual vs. firm) | **NIGERIAN LEGAL COUNSEL REQUIRED** |
| Client confidentiality obligations | **NIGERIAN LEGAL COUNSEL REQUIRED** |
| Copyright default ownership in survey plans/work product | **NIGERIAN LEGAL COUNSEL REQUIRED** — shapes the entire Rights context (§16) |
| Reuse/licensing of historical surveys | **NIGERIAN LEGAL COUNSEL REQUIRED** |
| Expert evidence / court-admissibility standing | **NIGERIAN LEGAL COUNSEL REQUIRED** |
| Consumer protection obligations | **NIGERIAN LEGAL COUNSEL REQUIRED** |
| Data protection (NDPR) for customer/professional/historical-material data | **NIGERIAN LEGAL COUNSEL REQUIRED** |
| Escrow / holding client funds (CBN, payment-service-provider licensing) | **NIGERIAN LEGAL COUNSEL REQUIRED** — blocks §15's escrow option outright |
| Whether Paystack subaccounts/split payments satisfy the above without LandVault holding funds | **EXTERNAL PROFESSIONAL VERIFICATION** (Paystack's own current capability, then legal confirmation) |
| Credential-submission storage mechanism (reusing Evidence pipeline) | **REPOSITORY DECISION** — resolved §10, no external input needed |
| Party/Contact model shape | **REPOSITORY DECISION** — resolved §6 |

None of the counsel-required items are answered by this document, and none should be assumed from
UK/RICS practice, per instruction.

## 12. Transaction boundary — minimum system-of-record events

| Event | Requirement |
|---|---|
| Instruction | **Must be recorded** — the origin fact for platform-origination attribution (§13) |
| Acceptance | **Must be recorded** — defines when a Job becomes committed |
| Assignment | **Must be recorded** — establishes accountability |
| Evidence submission | Already a system-of-record event (ADR-026) |
| Completion | **Must be recorded** — triggers payment and PPI-contributing events |
| Invoice/payment status | **Must be recorded as a reference/status** — actual payment processing lives in Economic/Billing, referenced not embedded (§3) |
| Dispute existence/outcome | **Must be recorded**, at minimum as a flag and reference — required for anti-circumvention and PPI integrity |
| Scope negotiation detail, quotation back-and-forth, variation discussion, routine scheduling chat | **Optional/communication-only** — only the *final* accepted figure needs a recorded fact; the conversation producing it may stay off-platform |

The rule: an on-platform **event** is required for each system-of-record item, even when the
conversation that produced it happened off-platform — auditable, not surveilled, exactly per §13.

## 13. Anti-circumvention policy boundary

| Rule | Belongs in |
|---|---|
| A transaction counts as platform-originated only from a recorded instruction event; never inferred retroactively | **Software architecture** — a hard fact, not negotiable |
| Fee schedules, volume discounts, priority-access thresholds | **Commercial policy** — pricing decisions, not architecture (matches `COMMERCIAL_ARCHITECTURE.md`'s own "principles not numbers") |
| The actual circumvention prohibition/permitted-exception language a partner agrees to | **Partner agreement** — a legal/contractual document, not code |
| PCR monitoring and trend reporting | **Analytics** — reporting only, never a blocking mechanism |

**Restated without exception:** LandVault does not claim ownership of all client relationships. No
architectural mechanism may block a surveyor from servicing a non-platform-originated client. The
platform tracks and economically incentivizes platform-originated work; it does not prevent
anything else.

## 14. SECI / EQF / PPI boundary — reconfirmed

- SECI is contribution, not truth. EQF is evidence/process quality, not truth. Both stay outside
  any code path that computes evidence trust or verification state (Article XV §1) — reconfirmed,
  unchanged from the prior blueprint.
- "Surveyor Trust Index" is rejected; **Professional Performance Index (PPI)** is the recommended
  term, for the reason already given: "Trust" is already constitutionally load-bearing (Article VI)
  and must not be reused for a commercial-performance metric.
- Commercial value (SLV) stays distinct from professional competence (PPI) — never one substituting
  for the other in any decision.
- **None of SECI, EQF, or PPI need a persisted score field.** All three should be event-derived
  read-model projections, recomputed from Job-completion, Evidence, and Review events — a mutable
  score column is a governance risk a derived projection cannot become, and this is practical, not
  merely aspirational, given no real transaction volume exists yet to make persistence necessary.

## 15. Payment discovery

| Option | Assessment |
|---|---|
| Direct customer → surveyor payment, LandVault fee charged separately | Simplest; avoids LandVault holding client funds at all; safest starting point |
| Marketplace split payment (Paystack subaccounts, if available) | **Recommended primary candidate** — a single charge routes automatically to the surveyor's subaccount and LandVault's own account, without an intermediary holding balance; matches ADR-006's existing Paystack rail |
| Payout after completion (LandVault collects the full amount first, then transfers the surveyor's share) | **Not recommended** — this means LandVault holds funds even briefly, which is functionally close to the escrow question and should not be adopted without the same legal clearance |
| Third-party regulated escrow | **Explicitly deferred, not designed** — per the prior blueprint, and reconfirmed here |

**Can be safely evaluated under Paystack without prematurely designing escrow:** the subaccount/
split-payment option — its architecture doesn't require LandVault to hold funds, so it can be
investigated (confirm current Paystack Nigeria capability, §11) without waiting on the escrow legal
question. **Requires Nigerian payments/legal analysis before any implementation regardless of which
option:** all of them, at minimum for VAT/withholding treatment and whether split payments
themselves have any CBN licensing implication.

## 16. Rights bounded context decision

**Yes — a separate, small Rights context, referenced by Evidence, not folded into Evidence and not
folded into Marketplace.** Minimum issues it must resolve before any royalty design begins:
copyright owner, creator/originator (distinct from copyright owner), client confidentiality, licence
grant, permitted use, commercial-use permission, expiry, withdrawal, downstream rights already
granted, territory, derivative-work treatment, multiple rights holders. **Do not design royalties
before this context exists and has actually been used to classify real historical evidence** —
reconfirmed from the prior blueprint's §17/§18 finding that HEMI-style monetisation metrics
designed before real classified data exists tend to be either gamed or meaningless.

## 17. Legacy Vault relationship

**Not a separate product, and not a second Evidence repository** — that would directly violate
Article V (Bounded Context Sovereignty) by creating two sources of truth for the same kind of
record. **It is a combination**, built entirely on top of ADR-026's existing aggregate:

- An **ingestion workflow** — ordinary `EvidenceRecord` creation, with `evidence_type` extended to
  cover historical categories.
- A **private collection** — an access-control scope (only the originator and governance can see
  un-cleared historical evidence), not a new storage mechanism.
- A **rights-assessment staging area** — the new Rights context (§16) doing its classification work
  before the evidence becomes commercially eligible, referenced from the Evidence record, not a
  parallel status field invented on Evidence itself.

This preserves ADR-026 as the single source of truth for every piece of evidence this platform
ever holds, historical or current.

## 18. Minimum viable Surveyor Network — challenged

The task's proposed slice (profile → qualification evidence → Job assignment → surveyor-originated
Evidence → QA → audit) is directionally right but **can be made smaller, and should be**, given the
reality audit shows zero Job/Assignment/Customer concept exists yet and Marketplace's own Phase 0
bounded-context question is still open.

**Recommended MVP-S1 (smaller than proposed): Professional Accreditation only.** Profile,
qualification-evidence submission (reusing the existing Evidence pipeline per §10), and LandVault
review status — **with no Job concept at all.** This delivers real value (a queryable directory of
accredited professionals) without requiring Marketplace's bounded-context question to be resolved
first, and gives the Partner Programme's own Phase 0 a real running system to learn from before the
harder cross-tenant Job/Payment questions are tackled.

**MVP-S2 (the task's originally proposed slice)** — Job/Assignment, Evidence linkage, QA — follows
only once MVP-S1 is live and Marketplace's Phase 0 has actually run. Payments, scores, royalties,
and Legacy Vault remain deferred past both, exactly as already recommended.

## 19. ADR-028 readiness

**One question is genuinely ready now: the Evidence Originator/Reviewer/Commissioned-by amendment
to ADR-026** (§9). It is self-contained — three new nullable fields, no dependency on Job,
Marketplace, or Partner existing — and its maturity does not depend on either standing Phase 0
discovery resolving first.

**Everything else is not ready.** Job, Assignment, Partner Accreditation, Payment, and Rights all
depend on at least one of: the Marketplace bounded-context decision being formally adopted (not
merely recommended in a discovery document), the Partner Phase 0 discovery actually running, or
Nigerian legal counsel input (§11). Forcing any of those into an ADR now would mean drafting
architecture against an unresolved dependency, exactly what this platform's Architecture-Before-Code
discipline exists to prevent.

**ADR-028 candidate: the ADR-026 Evidence Originator amendment. Everything else: ADR-028 NOT READY.**

## 20. Governance Decision requirements

The following are business/process policy, not architecture, and should be resolved as Governance
Decisions (per LV-000 v1.8 Article XVI's existing GD log pattern), never drafted as ADRs:

- A GD formally opening the two standing Phase 0 discoveries (`MARKETPLACE_DISCOVERY_AND_PLANNING.
  md`, `PARTNER_PROGRAMME_STRATEGY.md`) — a sequencing/authorization decision, matching the
  precedent GD-002 already set for "the plan of record."
- A GD adopting this document's terminology corrections (Professional Performance Index, Evidence
  Reviewed, Discrepancy Documentation, etc.) as a binding naming standard for all future work in
  this domain — naming is not itself an architecture decision, but is governance-enforceable.
- A GD stating the anti-circumvention **policy** (§13) as commercial policy, distinct from and not
  requiring the ADRs that will eventually implement its recorded-event mechanism.
- A GD extending the non-adjudication safeguard (Engineering Rule 10's scanner) to cover any future
  Marketplace/Partner HTTP surface, mirroring exactly how it was extended for Evidence in IMVP-5 —
  recorded as a standing requirement now, before that surface exists, not discovered as a gap after.

## 21. Delivery recommendation and hard gates

| Stage | Content | Hard gate before proceeding |
|---|---|---|
| **Discovery** | This document; opening the two standing Phase 0s | Governance must formally open Marketplace/Partner Phase 0 — not assumed by this document |
| **Governance** | The four GDs in §20 | GDs recorded before any ADR drafting begins |
| **Legal/professional validation** | Nigeria checklist (§11), run in parallel with Discovery | Payment and Rights ADRs blocked until this returns |
| **ADR** | ADR-028 (Evidence Originator) now; Job/Marketplace/Partner/Payment/Rights ADRs only after their Phase 0 and legal inputs land | No ADR for Job/Partner/Payment/Rights before its named dependency closes |
| **Implementation** | MVP-S1 (Accreditation only, §18) first | Job implementation blocked until its own ADR is Accepted |
| **Commercial pilot** | MVP-S2 (Job/Marketplace), only after MVP-S1 proves out and the payment legal answer is in hand | Monetisation (HEMI, royalties) blocked until the Rights context is live **and** real transaction data exists |

## 22. Full decision matrix

| Question | Repository position | Blueprint recommendation | Marketplace-plan position | Partner-strategy position | Conflict? | Recommended decision | Decision type | Blocking external research? | Blocks ADR-028? | Blocks implementation? |
|---|---|---|---|---|---|---|---|---|---|---|
| How many bounded contexts for Marketplace? | None exist | Decompose into named domains | Explicitly open | Assumes a sibling exists | No | 2 contexts: Marketplace, Partner (§3) | ADR (future) | No | No | Yes — blocks Job ADR |
| Is Partner a new tenant type? | `Tenant` is generic | No — referencing record | Not addressed | Assumes reuse, undecided | No | Accreditation record referencing tenant + optional user (§4) | ADR (future) | No | No | Yes |
| Individual vs. practice split | Not modeled | Elaborated | Not addressed | Assumes distinction, undecided | No | Per §5 table | ADR (future) | Partial (liability) | No | Yes |
| Customer/Party model | Does not exist | Names the gap | Names "Survey Request" requester unresolved | Not addressed | No | Contact/Party value object on Job (§6) | ADR (future) | No | No | Yes |
| Job vs. Assignment | Neither exists | Proposes both | Both named as candidates, boundary open | Not addressed | No | Job aggregate, Assignment as child fact (§7) | ADR (future) | No | No | Yes |
| Evidence–Job relationship direction | N/A | Evidence independent | Not addressed | Not addressed | No | Job references Evidence, never owns it (§8) | ADR (future) | No | No | Yes |
| Evidence Originator model | `uploaded_by` only | New proposal | Not addressed | Not addressed | No | 3 nullable fields, ADR-026 amendment (§9) | **ADR-028** | No | **Ready now** | No |
| Accreditation credential storage | No mechanism | Names discovery items | Not addressed | Central concern, undecided | No | Reuse Evidence pipeline (§10) | Repository decision | Some (SURCON) | No | Yes |
| SURCON/licensing applicability | Unknown | Flags as external | Not addressed | Not addressed | No | Not decidable here | Legal | **Yes** | No | Yes |
| Copyright default ownership | Unknown | Flags as external | Not addressed | Not addressed | No | Not decidable here | Legal | **Yes** | No | Blocks Rights ADR |
| Escrow legality | Unknown | Recommends non-escrow default | Names Escrow as candidate, undecided | Not addressed | No | Non-escrow default; subaccounts as primary candidate (§15) | Legal + Repository | **Yes** | No | Blocks Payment ADR |
| "Trust"/reputation naming | N/A | Recommends PPI | Names "Ratings," ownership contested | Names "Ratings," same contest | **Yes**, between the two plans | Professional Performance Index; Partner owns standing (§3, §14) | Governance Decision | No | No | No |
| SECI/EQF/PPI persistence | N/A | Not fully specified | Not addressed | Not addressed | No | Event-derived, no persisted score field (§14) | ADR (future) | No | No | Yes |
| Anti-circumvention mechanism | N/A | Names economic incentives | Not addressed | Not addressed | No | Split by type per §13 table | Mixed (architecture + commercial policy + GD) | No | No | Partial |
| Legacy Vault architecture | Does not exist | Names as future capability | Not addressed | Not addressed | No | Ingestion workflow + access scope + Rights staging, on top of ADR-026 (§17) | ADR (future) | No | No | Gated on B5.4 |
| Rights context existence | Does not exist | Recommends separate context | Not addressed | Not addressed | No | Yes, separate, referenced by Evidence (§16) | ADR (future) | **Yes** (copyright default) | No | Gated on legal input |
| Minimum viable slice | N/A | Proposes profile→Job→Evidence→QA | Not addressed | Not addressed | No | Smaller: Accreditation only first (§18) | Governance Decision | No | No | Defines the actual next build |

## 23. Recommended next action

Record the four Governance Decisions in §20, with the first — formally opening the Marketplace and
Partner Phase 0 discoveries — as the actual next step, not a document. Engage Nigerian legal counsel
on the §11 checklist in parallel; do not wait for it to begin the Phase 0 discoveries themselves,
since those do not depend on the legal answers. Draft the one ready ADR (Evidence Originator
amendment) only once Governance confirms it wants that amendment now rather than bundled with a
later, larger Evidence-domain change. Do not draft any Job/Marketplace/Partner/Payment/Rights ADR
before its named dependency in §22 closes.

## Approval Gate

No Surveyor Network implementation, Marketplace/Partner Phase 0 discovery, or ADR drafting is
authorized by this document. This is a reconciliation and readiness assessment only. **Waiting for
explicit Governance action on §20's four decisions before any further work in this domain begins.**
