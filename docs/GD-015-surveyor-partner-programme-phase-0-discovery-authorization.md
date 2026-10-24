# GD-015 — Surveyor Partner Programme Phase 0 Discovery and Demand-Validation Research Authorization

**Status:** **ACCEPTED — 8 October 2026, on explicit Governance Authority ratification. IN FORCE.**
This Decision authorizes exactly the research-only Phase 0A activities at §5.1, subject in full to
§§6–26 below. Ratification does not itself satisfy any Playbook §16 execution prerequisite: it does
not, by itself, authorize recruitment, respondent contact, data collection, payment or deposit
collection (beyond the narrow item 8 reviewer-commissioning exception at §17), dashboard or account
creation, production code changes, or the scheduling or execution of the demand test described at §13
and in the companion playbook, until every one of those prerequisites is independently satisfied.

**Date drafted:** 2026-09-29. **Ratified:** 8 October 2026.

**Drafting baseline:** `origin/main` at `a93fd2fe428758d0393a1e00d48e113575ed9f3c`, verified fresh by
`git fetch` immediately before this drafting began. Re-verified: no `GD-015` reference exists in any
branch, worktree, or the Article XVI Governance Decision Log (`docs/LV-000-constitution.md`) at this
baseline — GD-015 is confirmed the next available Governance Decision number, not assumed.

**Operative authority:** Article XVI §2 — a later numbered decision that:

1. explicitly names `docs/GD-008-surveyor-network-phase-0-principles-and-authorization-boundary.md`
   §17, to fill — with a categorically distinct, narrower, research-only decision, per §2 below,
   never as a partial opening of the same gate — the outstanding decision point GD-008 §17 identified
   ("`PARTNER_PROGRAMME_STRATEGY.md`'s own Approval Gate [is] not satisfied by this decision or by
   either Surveyor Network discovery document. Each is closed only by its own, later, separate
   Governance Decision that explicitly opens that programme's Phase 0"); and
2. explicitly names `docs/PARTNER_PROGRAMME_STRATEGY.md` and `docs/MARKETPLACE_DISCOVERY_AND_
   PLANNING.md` as the planning documents this Decision reads directly and does not open, satisfy,
   or discharge (§21 below states this precisely, having read both documents in full).

**Corrected framing (added on remediation of this draft's preliminary governance review, finding
C4).** Having now read `docs/PARTNER_PROGRAMME_STRATEGY.md` and `docs/MARKETPLACE_DISCOVERY_AND_
PLANNING.md` in full, this Decision does **not** claim to "open, in narrowly bounded form, the same
Partner Phase 0 gate" either document's own Approval Gate names. Both documents' own Approval Gates
concern a categorically different activity — an **architecture-discovery Phase 0** whose first
deliverable is an explicit, reviewed bounded-context map (`MARKETPLACE_DISCOVERY_AND_PLANNING.md`
"Bounded contexts" section) and a partner accreditation/lifecycle domain model
(`PARTNER_PROGRAMME_STRATEGY.md` Objectives 1–2) — from the **commercial/demand-validation research**
this Decision authorizes. GD-008 §17 left open only that a *decision point* remained outstanding; it
did not define that decision point's content. This Decision is Governance's own, separate act
filling that gap with a demand-research authorization — it is not, and does not purport to be, the
opening of either document's own architecture-discovery Phase 0, and satisfies neither document's
Approval Gate. §21 below restates this in full, with both documents' own Approval Gate text quoted.

This Decision does **not** amend the Constitution, is **not** proposed under Article XIV, and does
**not** reopen, narrow, or expand GD-008 in any respect beyond naming it as a dependency. GD-008 §2's
own two-bounded-context "direction" (Marketplace, Partner) remains exactly what GD-008 itself called
it — "directional governance guidance only," not a closed architecture decision — and this Decision
does not touch, rely upon, or advance that question in either direction. Nothing in this Decision
authorizes ADR drafting; GD-008 §5's authorization of ADR-028 drafting is unaffected and unrelated
(ADR-028 is already Accepted, per `docs/LV-000-constitution.md` Article XVI GD-012 §1).

**Terminology note.** This Decision's own "Phase 0A"/"Phase 0B" (§5 below) is Surveyor Partner
Programme demand-research terminology specific to this Decision. It is not, and must not be read as,
"the Partner Programme's own Phase 0" as `PARTNER_PROGRAMME_STRATEGY.md` and `docs/GD-008-...md`
use that phrase (an architecture-discovery stage). Where either meaning could be ambiguous in a
future document, the full phrase "Surveyor Partner Programme demand-research Phase 0A" should be
used in preference to the bare word "Phase 0."

---

## 1. Purpose

This Decision authorizes, subject to §§5–22 below, a narrowly bounded, research-only Phase 0A for a
prospective future **Surveyor Partner Programme**: a programme investigating whether an accountable
LandVault evidence workflow, built on the Partner/Professional Network direction GD-008 §2 already
named, would be adopted by registered surveyors and eligible institutional land professionals. This
Decision authorizes **discovery and reality validation only**. It does not authorize any Marketplace,
Partner, Job, Assignment, accreditation, payment, or other implementation named in GD-008 §15's
prohibition list, and does not narrow, broaden, or resolve GD-008 §2's own directional hedge.

## 2. Why this Decision exists, and why now

`docs/PARTNER_PROGRAMME_STRATEGY.md` (2026-07-25) and `docs/MARKETPLACE_DISCOVERY_AND_PLANNING.md`
(2026-07-24) have each carried an unactioned Approval Gate since their own drafting, each waiting for
"explicit direction before any [Marketplace/Partner] programme discovery begins" (each document's own
Approval Gate, verbatim in substance). GD-008 (2026-09-08) established the constitutional, tenant, and
evidence-independence boundaries for the eventual Surveyor Professional Network and authorized exactly
one piece of architecture work (ADR-028 drafting, since completed and Accepted) — it explicitly
declined to open either the Marketplace or Partner Phase 0 discovery gate, naming that as a decision
for "its own, later, separate Governance Decision" (GD-008 §17).

This Decision is not that act. Opening either document's own architecture-discovery Phase 0 —
resolving `MARKETPLACE_DISCOVERY_AND_PLANNING.md`'s bounded-context-count question, or
`PARTNER_PROGRAMME_STRATEGY.md`'s accreditation/onboarding/lifecycle domain-model questions — remains
entirely unauthorized by this Decision and requires its own, future, separate Governance act, exactly
as GD-008 §17 left it. This Decision instead authorizes a categorically prior, narrower activity that
neither planning document itself proposes or gates: **commercial and stakeholder demand research**,
answering whether surveyors and institutional professionals would use and pay for the eventual
programme at all — information no architecture decision, and neither existing planning document,
supplies. It exists now because that information is a sensible precondition for Governance to judge
whether opening either architecture-discovery Phase 0 is worth doing at all, not because either
document's own gate requires it as a step.

## 3. Constitutional boundary restated

This restates LV-000 v1.8 Article IV (non-adjudication) and Article IX §3 (the boundary of platform
authority), and GD-008 §1 (the identical restatement already made for the Surveyor Network programme),
applied by name to this Decision. It states no new principle:

> AquaSavannah LandVault records submitted evidence and verification events. It does not determine
> legal ownership, adjudicate disputes, or replace government title systems.

Neither this Decision, the Phase 0A research it authorizes, nor any future Surveyor Partner Programme
it may in time lead to, authorizes LandVault to determine legal ownership; adjudicate land disputes;
issue title; replace government title systems; certify a surveyor's licensure status on the issuing
body's behalf; or reward a professional for reaching a preferred ownership conclusion. **Uncertainty
and unresolved evidence inconsistency remain legitimate professional outcomes** (GD-008 §1, restated
verbatim in substance). Any future implementation, of any kind, that violates this boundary is void to
that extent regardless of what this Decision or any later instrument purports to authorize (LV-000
Article IX §2 — authority is never assumed from capability).

## 4. Programme purpose and commercial proposition

The proposed Surveyor Partner Programme's primary commercial and operational proposition is to
investigate — not to presume — whether registered Nigerian surveyors and eligible institutional land
professionals will participate in an accountable LandVault evidence workflow. This Decision does not
presume that any element of that proposition is already proven. The programme must remain consistent
with §3 above at every stage, including every research artefact, recruitment communication, and
reported finding. No proposed decision, discovery artefact, or research communication produced under
this Decision's authority may describe LandVault as a land registry, title system,
ownership-certification service, dispute tribunal, or government substitute.

## 5. Two-stage programme structure

GD-015 authorizes, if ratified, exactly **Phase 0A** below. **Phase 0B remains dormant** and is not
authorized by this Decision under any circumstance (§5.4).

### 5.1 Phase 0A — Discovery and reality validation: authorized activities

Subject to every other section of this Decision, Phase 0A may, upon ratification, be resourced to
undertake:

1. a read-only repository and deployed-system reality audit of the current state of any Surveyor
   Network-adjacent capability (mirroring the audit discipline GD-008's own Findings §1 already
   applied), **bounded as follows** (remediation of finding C5): the audit may inspect only (a)
   publicly accessible behaviour; (b) ordinary, already-authorized user behaviour within the
   reviewing researcher's own tenant or otherwise-authorized scope; (c) repository evidence already
   lawfully available to the research team; and (d) non-destructive rendered outputs and documented
   configuration. **This Decision does not authorize, for this audit or any other Phase 0A activity**:
   elevated or administrative production access; cross-tenant access; impersonation of any principal;
   direct production-database access; bypassing Row-Level Security or authentication; privileged log
   inspection; extraction of personal or land data beyond what §6–§11 and the companion playbook
   expressly authorize; or any modification of production state. If any Phase 0A activity is found to
   require access broader than this paragraph permits, that activity component stops, and the person
   or agent performing it seeks separate authority under LV-000 v1.8 Article IX §3 / ENGINEERING_RULES
   rule 9 (Controlled Platform Authority) before proceeding — this Decision does not itself supply
   that authority;
2. a composite-representation assessment, per §12 below;
3. surveyor and institutional stakeholder research, per §6–§7 below;
4. regulatory and operational discovery, extending the Nigeria external-validation checklist GD-008 §10
   already opened, without pre-empting any answer to it;
5. separately controlled retail research, per §8 below, strictly secondary and non-substitutable for
   the institutional hypothesis;
6. pricing and commitment-signal research, classified honestly per the playbook's terminology
   discipline (§13 below and the companion playbook document), never presented as concluded
   "willingness to pay" from a survey answer alone;
7. surveyor workflow research — how a registered surveyor or institutional professional would, if at
   all, incorporate the proposed workflow into existing practice;
8. manual sample-output testing — hand-constructed example outputs shown to research participants for
   reaction, never generated by, or presented as, production system behaviour;
9. a final Phase 0A evidence report, culminating in the governance checkpoint at §5.3.

### 5.2 Phase 0A — explicitly prohibited activities

Phase 0A does not authorize, and no activity conducted under it may include:

- public launch of any kind;
- production implementation of any Surveyor Partner Programme capability, Marketplace capability, or
  Partner capability (restating, not narrowing, GD-008 §15's own prohibition list, which remains fully
  in force and unaffected by this Decision);
- partner onboarding of any kind;
- creation of any government account, government dashboard, or government-facing system access;
- government archive ingestion of any kind;
- paid verification services of any kind;
- any public claim, in any research material, of government endorsement, partnership, or approval;
- surveyor accreditation of any kind;
- ownership or title determinations of any kind;
- production scoring changes of any kind;
- deployment of any new functionality, to any environment, tenant, or user;
- collection of payments, deposits, or financial commitments of any kind (§13, §20 of the companion
  playbook);
- collection of documents or personal information beyond what §6–§11 below and the companion playbook
  expressly authorize for research purposes, and then only under the retention, access, and deletion
  controls named at §17.

### 5.3 Governance checkpoint

Phase 0A shall conclude with a governance checkpoint. The checkpoint shall record exactly one of the
following five outcomes, determined against the evidence Phase 0A actually produced, not against a
target Phase 0A was hoped to meet:

- **PROCEED** — evidence meets or exceeds the thresholds at §14 for the institutional population,
  independent of retail-segment results (§9's non-aggregation rule governs).
- **PROCEED WITH CONDITIONS** — mixed institutional evidence per §14's thresholds, or evidence
  sufficient in substance but carrying a named, correctable defect (e.g., concentrated in one
  recruitment channel) that a further, bounded research step could resolve.
- **PIVOT** — institutional evidence indicates the researched proposition, as tested, does not hold,
  but suggests a materially different proposition (a different professional segment, workflow shape,
  or commercial model) may.
- **STOP** — institutional evidence indicates the researched proposition does not hold and no
  pivot is evident from the research conducted.
- **INDETERMINATE** — the checkpoint's default outcome wherever the assembled evidence is incomplete,
  contaminated (§10), insufficient in sample size or quality, or contradictory. **INDETERMINATE is not
  a failure state requiring justification to avoid — it is the correct, honest outcome whenever the
  evidence does not clearly support any of the other four**, and shall be recorded as such rather than
  forced toward PROCEED or STOP for the appearance of a clean result.

No outcome other than these five may be recorded. No outcome may be determined, in whole or in part,
by retail-segment evidence alone (§9).

### 5.4 Phase 0B — Conditional operational pilot: remains dormant

**Phase 0B is not authorized by this Decision.** This Decision does not automatically activate Phase
0B under any checkpoint outcome, including PROCEED. Any partner onboarding, live institutional
dashboard, document intake, government pilot, payment collection, or production change of any kind
requires its own, later, explicit Governance Authority approval, granted only after that later
decision's own review of Phase 0A's evidence — never as an automatic consequence of this Decision's
ratification or of any Phase 0A checkpoint outcome recorded under §5.3. A PROCEED or PROCEED WITH
CONDITIONS outcome makes Phase 0B something Governance **may** separately consider; it does not itself
authorize it, mirroring exactly the "prerequisite satisfaction is not implementation authorization"
discipline GD-009 §14, GD-011 §19, and GD-012 §1 already established for this repository's engineering
governance decisions, applied here to a research-and-commercial decision instead.

## 6. Primary institutional research population and hypothesis

The following rule is the operative substance of this Decision and governs every other section:

> Phase 0A shall treat registered surveyors and eligible institutional land professionals as the
> primary research population. Retail landowners and prospective buyers may be studied only as a
> separately recruited and separately analysed secondary demand segment. Results from the two
> populations must not be aggregated when determining whether the Surveyor Partner Programme should
> proceed.

The primary hypothesis Phase 0A shall test — without presuming any part of it already proven — is
whether registered surveyors and eligible institutional professionals would:

1. use a professional LandVault dashboard;
2. contribute or help digitise eligible historical survey documents;
3. collaborate on parcel mapping and evidence comparison;
4. provide attributable professional observations;
5. refer suitable cases;
6. integrate the workflow into their professional practice;
7. pay an appropriate professional charge; or
8. accept a defined revenue-sharing or referral model.

No proposition in this list may be treated, in any Phase 0A research artefact or report, as
independently established prior to the checkpoint at §5.3 concluding on the evidence actually
gathered.

## 7. Institutional eligibility and subtypes

The primary research population may include:

- registered Nigerian surveyors;
- authorised survey firms;
- institutional professionals directly involved in land evidence or due diligence;
- legal, estate, or compliance professionals whose work is directly relevant to the proposed workflow.

**No research activity conducted under this Decision may silently classify every agent, business,
community representative, or government official contacted as an institutional respondent.** Every
institutional respondent's subtype (per the list above) shall be recorded and reported separately,
not collapsed into a single undifferentiated "institutional" count. A respondent whose role does not
clearly fall within one of the four named subtypes is not institutional by default; classification
requires an affirmative, recorded basis, mirroring the evidentiary discipline Article IV requires for
Evidence generally, applied here to research-subject classification.

### 7.1 Registered-surveyor status — eligibility and classification check, not accreditation

*Added on remediation of this draft's preliminary governance review, finding M4, superseding that
review's own self-report-only recommendation.* The following distinction governs this subsection and
every reference to "registered surveyor" throughout this Decision and its companion documents:

> LandVault may check professional-registration status for research eligibility and segmentation.
> LandVault may not accredit, license, approve, certify, or endorse the surveyor.

A prospective institutional respondent claiming registered-surveyor status shall provide the minimum
identifier necessary to check that claim against an authoritative public Surveyors Council of Nigeria
(SURCON) source, **where such a source is available and practicably usable for this purpose**.
Substantively:

> Registered-surveyor status shall be established for Phase 0A research-segmentation purposes through
> a participant-supplied SURCON registration identifier checked against an authoritative public SURCON
> source where available. This is an eligibility and classification check only. AquaSavannah LandVault
> does not accredit, license, approve, certify, or endorse the participant. Where status cannot be
> authoritatively confirmed, the respondent must be classified as **UNVERIFIED SURVEYOR STATUS** and
> excluded from the registered-surveyor commitment sub-minimum at §14.

The check is subject to every one of the following safeguards, none of which is optional:

1. **Minimum necessary data only** — the identifier needed to perform the check, nothing further.
2. **Source and check date recorded** for every check performed.
3. **No copied register or bulk harvesting** — this Decision authorizes checking one individually
   volunteered identifier against a public source at the point that individual is being classified,
   never downloading, mirroring, or bulk-querying the register itself.
4. **No public claim that LandVault verified professional competence** — a passed check confirms
   registration status only, never skill, diligence, or the accuracy of anything the respondent has
   ever asserted or will assert about any parcel or evidence.
5. **No inference that registration proves the accuracy of any submitted land evidence.**
6. **Unresolved or inconsistent status remains unverified** — an ambiguous, partial, or contradictory
   check result is recorded as `UNVERIFIED SURVEYOR STATUS`, never resolved in the respondent's favour
   by assumption.
7. **No manual override** may silently recharacterize an `UNVERIFIED SURVEYOR STATUS` respondent as
   registered for threshold purposes at §14.
8. **If the public SURCON source cannot practically support the check** (unavailable, inaccessible, or
   unusable for this purpose at the time of research), the respondent is recorded as `UNVERIFIED
   SURVEYOR STATUS` — this Decision does not authorize falling back, silently or otherwise, to
   unchecked self-report for the §14 sub-minimum.
9. **This subsection authorizes consulting SURCON's own public register only** to support the
   existence and general nature of the public registration source for this classification purpose —
   it authorizes no legal conclusion about SURCON's regulatory authority, licensing regime, or any
   matter listed in GD-008 §10's Nigeria external-validation table, every item of which remains exactly
   as unresolved as GD-008 left it.

This subsection does not authorize contacting SURCON directly, requesting SURCON confirm any
individual's status by correspondence, or any interaction with SURCON beyond consulting whatever
register or lookup facility SURCON itself already makes publicly available. If no such public,
self-service facility exists or is usable, every institutional respondent claiming surveyor status
is recorded as `UNVERIFIED SURVEYOR STATUS` for this Decision's purposes, and that fact is itself
reported to the governance checkpoint at §5.3 as a limitation on the evidence gathered.

## 8. Retail secondary segment

The secondary retail segment may include:

- landowners;
- prospective buyers;
- diaspora buyers;
- people considering a particular parcel;
- people seeking help understanding existing land documents.

Retail respondents shall be:

1. recruited separately from institutional respondents where practicable;
2. assigned a distinct segment identifier at the point of recruitment, not inferred after the fact;
3. shown segment-appropriate questions and pricing — a retail respondent is never shown institutional
   pricing or vice versa;
4. analysed separately from institutional respondents;
5. reported separately from institutional respondents, in every Phase 0A output document.

**Retail demand does not substitute for evidence that surveyors or institutional partners will adopt
the Surveyor Partner Programme.** No Phase 0A report, finding, or recommendation may present strong
retail interest as evidence, partial or otherwise, of institutional adoption likelihood.

## 9. Non-aggregation rule

Institutional and retail results **must not be combined** when calculating or deciding any of the
following:

- response rates;
- comprehension rates;
- price acceptance;
- commitment rates;
- conversion rates;
- workflow adoption;
- programme viability;
- the PROCEED / PROCEED WITH CONDITIONS / PIVOT / STOP / INDETERMINATE outcome at §5.3.

**Controlling rule, restated here rather than left to the companion playbook alone** (remediation of
finding C1): institutional and retail results **shall be reported separately as the primary output of
every Phase 0A report**. A combined administrative count — for example, "N total interviews conducted
across both segments" — may be reported **only in addition to**, never in place of, that segment-
separated primary reporting, and only to disclose the total volume of research activity undertaken. A
combined figure shall never be presented, cited, or relied upon as evidence that either hypothesis
(institutional or retail) has been supported, shall never appear in any report from which the
segment-separated figures are absent, and any report using a combined figure shall carry an explicit
statement to that effect adjacent to the figure.

**Strong retail interest must not compensate for weak institutional participation.** The thresholds at
§14 apply to the institutional population independently; no
retail-segment result, however strong, may substitute for, average against, or offset a weak or absent
institutional result. **Retail evidence alone must never produce a PROCEED outcome for the Surveyor
Partner Programme**, under any circumstance, at any strength of retail result.

## 10. Chief Surveyor and intermediary referral controls

Every recorded response under Phase 0A shall identify its recruitment source at the point of intake,
not reconstructed afterward. Responses referred through a Chief Surveyor, a professional-body officer,
or any other influential intermediary shall be tagged with that referral source and analysed
separately from directly-recruited responses of the same segment.

No Phase 0A research material may present referred responses as independent market evidence without
disclosing the referral source and its potential effect on response character (a referred respondent
may, for example, feel social pressure to respond favourably in a way a directly-recruited respondent
does not). No Chief Surveyor, professional-body officer, or government official may be described, in
any Phase 0A material, as endorsing LandVault unless express, independently documented authority for
that specific claim exists and is attached to the claim. **Access supplied by a Chief Surveyor or
other intermediary is not, by itself, evidence of independent market demand.**

**Referral-concentration ceiling** (remediation of finding C3, replacing reliance on a judgment-based
trigger alone): no more than **50%** of the qualifying institutional commitments counted toward any
§14 threshold band may originate from a single referral source. Chief-Surveyor-referred and other
intermediary-referred respondents remain separately tagged and reported regardless. Where the 50%
ceiling is exceeded, the institutional evidence **cannot** be classified `STRONG` at §14, regardless
of the raw qualifying-commitment count — it is classified `MIXED` or `INDETERMINATE`, whichever the
remaining, non-concentrated evidence actually supports. No referral source, Chief Surveyor, or other
intermediary may select which responses are reported or excluded from any Phase 0A output.

## 11. Government participation research sub-hypothesis

Government participation is a **prospective institutional sub-hypothesis only**, subordinate to and
governed by every restriction in this Decision, and further and more narrowly restricted as follows.

Phase 0A may research whether Surveyor-General offices or competent public survey authorities would
potentially:

1. use a restricted, view-only dashboard;
2. inspect evidence provenance and archive coverage;
3. later consider contributing authorised archive material.

**This Decision does not authorize**, under any circumstance and regardless of any Phase 0A finding:

- a government dashboard, of restricted view or any other kind;
- government user accounts;
- archive uploads of any kind;
- government integrations of any kind;
- data-sharing agreements;
- memoranda of understanding;
- any claim, in any research or public material, of government approval or partnership.

A future government archive-contribution pathway — if Phase 0A research indicates one is worth
pursuing — is identified here as requiring its own, separate legal, privacy, security, institutional,
and governance authorization, obtained independently of this Decision and independently of any Phase
0A checkpoint outcome. Nothing in this Decision or in a PROCEED outcome at §5.3 advances that future
authorization by any degree.

## 12. Composite-representation assessment

Phase 0A shall include a read-only assessment of the combined meaning created by any existing or
proposed:

- public verification page;
- QR certificate;
- confidence indicator;
- completeness indicator;
- surveyor attribution;
- endorsement;
- consensus display;
- conflict status;
- "no conflict" wording;
- due-diligence report.

The assessment shall determine whether the combined presentation of these elements — however each one
individually reads — could reasonably imply ownership determination, title validity, official
approval, or adjudication, even where no single element does so on its own. This assessment addresses
composite meaning specifically because Article IV §2's prohibition on adjudicative wording, and
ENGINEERING RULES rule 10's non-adjudication scanner, are both element-level checks; a composite
presentation can read as adjudicative even where every individual element independently passes such a
check.

The assessment **shall not assume** that any of the listed capabilities is operational. Each shall be
classified, on direct inspection, as:

- **operational** — live and reachable in a deployed environment;
- **prototype** — implemented but not deployed to a production-equivalent environment;
- **proposed** — described in planning material but not implemented;
- **unverified** — claimed somewhere in repository or planning material but not confirmed by direct
  inspection during this assessment;
- **governance concern** — any classification above, combined with a composite-meaning risk this
  section identifies.

**This assessment is read-only.** It shall not change production behaviour, modify any existing
capability's classification status, or alter any user-facing text, regardless of what it finds. A
finding under this assessment that identifies a governance concern is reported to the checkpoint at
§5.3 and to any future, separate Governance act it may prompt — it is not self-remediating.

## 13. Demand-test methodology

The one-day demand test's full methodology is drafted, but not authorized for execution, in the
companion document `docs/GD-015_ONE_DAY_DEMAND_TEST_PLAYBOOK.md`. That document is subordinate to this
now-ratified Decision and is subject to every restriction in it; the playbook's own execution remains
gated on its §16 operational prerequisites, unaffected by this Decision's ratification beyond §16 item
1. In particular, and restated here because it governs how the term itself may be used throughout
Phase 0A:

**"One-day demand test" means one defined measurement or analysis day after controlled recruitment —
not that recruitment begins and ends in one day.** No Phase 0A material may use the term to describe or
imply a same-day recruitment-and-measurement design.

The playbook's methodology requirements — recruitment window, segment separation, one price per
respondent, prior/current price recording, the teach-back requirement, deduplication, referral
tagging, disclaimer placement, intake governance, segment-specific analysis, and the INDETERMINATE
default — are incorporated into this Decision's own authorization boundary by reference: Phase 0A
research is authorized, if ratified, only to the extent it follows that methodology, not as a
freestanding licence to conduct research by whatever method proves convenient.

## 14. Thresholds

*Rewritten in full on remediation of this draft's preliminary governance review, findings M1
(surveyor-specific sub-minimum), M2 (denominator), and M3 (recruitment-wave definition), and
incorporating §10's referral-concentration ceiling (finding C3). Further amended on remediation of
the second preliminary governance review (§14.0, §14.1 item 3, and §14.8 added; §14.3–§14.5 and §14.7
updated to match).* Provisional evidence bands, proportionate to the stated Phase 0 target of
approximately 10–50 prospective users, apply to the **institutional population only**, independent of
any retail-segment result (§9).

### 14.0 Minimum institutional sample — precondition for any band other than indeterminate

*Added on remediation of the second preliminary governance review, correcting a gap the review's
Case 7 identified: a shortfall on the interview-count floor alone had no named band under §14.1–§14.4
as previously drafted.*

> Where fewer than 12 completed eligible institutional interviews remain — after excluding any
> interview invalidated under §14.8 (ordered-sequence violations) and after deduplication (Playbook
> §7) — the institutional result is `INDETERMINATE`, because the minimum exploratory sample has not
> been reached.

This precondition governs before §14.1–§14.4 are applied, regardless of the number of apparent or
qualifying institutional commitments: 6, 60, or 600 qualifying commitments drawn from fewer than 12
valid completed eligible institutional interviews do not produce `STRONG`, `MIXED`, or `WEAK` — they
produce `INDETERMINATE`, because this precondition tests the interview-level sample itself, not the
commitment count. No retail-segment result, however strong, substitutes for or cures a shortfall
under this precondition (§9). Only once at least 12 valid completed eligible institutional interviews
are confirmed do §14.1–§14.4 apply to determine which band, if any, the qualifying-commitment evidence
supports.

### 14.1 Strong institutional evidence

Requires **all** of the following, simultaneously — no subset substitutes for another, and always
subject to the minimum-sample precondition at §14.0:

1. at least **12** completed eligible institutional interviews (the denominator; see §14.6);
2. at least **6** independently deduplicated qualifying institutional commitments (per the playbook's
   honest commitment-terminology classification, tier 2 or above);
3. *(added on remediation of the second preliminary governance review, correcting the review's Case 8
   finding that a raw count alone, however large its denominator, could otherwise satisfy this band)*
   qualifying institutional commitments reaching at least **50%** of completed eligible institutional
   interviews (the rate condition; the same figure §14.6 requires to be disclosed, now also a pass/fail
   condition for this band, not merely a disclosure item) — six qualifying commitments out of 12
   satisfies this item; six out of 20 or six out of 100 do not;
4. at least **4** of the qualifying commitments counted toward item 2 from respondents whose
   registered-surveyor status has been authoritatively checked per §7.1 — **not** `UNVERIFIED
   SURVEYOR STATUS`. Other eligible institutional professionals (§7's remaining three subtypes) may
   contribute to the remaining qualifying commitments, but do not substitute for this sub-minimum;
5. at least **two** recruitment waves, each meeting the prospective definition at §14.2;
6. at least **two** materially distinct recruitment sources (channel, intermediary, or outreach
   action — not two arbitrarily labelled subsets of one source);
7. no more than **50%** of the qualifying commitments counted toward item 2 from a single referral
   source, per §10's referral-concentration ceiling;
8. no interview or commitment counted toward any item above may be one excluded under §14.8
   (ordered-sequence violations) or one that fails the deduplication requirement at Playbook §7.

### 14.2 Recruitment wave — operative definition

A recruitment wave is a **prospectively documented, separately dated outreach batch** with:

- a defined opening and closing time, fixed before that wave's recruitment begins;
- a defined respondent population for that wave;
- a recorded recruitment source or outreach action;
- its own recruitment record, distinct from any other wave's.

**Two artificially separated portions of one continuous outreach action do not constitute two
independent waves.** A wave boundary drawn retrospectively — after recruitment data already exists,
for the purpose of satisfying §14.1 item 5 — does not qualify; only a boundary fixed prospectively,
before that wave's own recruitment began, counts. The wave schedule and definition must be settled as
part of the execution prerequisites (companion playbook §16) before any recruitment under this
Decision begins, not decided after the fact from however the data happened to arrive.

### 14.3 Mixed institutional evidence

Where the minimum-sample precondition at §14.0 is met, any of the following, where strong evidence
per §14.1 is not reached:

- 3–5 qualifying institutional commitments (denominator per §14.6 still reported); or
- 6 or more qualifying commitments that fail §14.1 solely on the rate condition (item 3), the
  registered-surveyor sub-minimum (item 4), the two-wave requirement (item 5), the distinct-source
  requirement (item 6), or the referral-concentration ceiling (item 7) — i.e., evidence sufficient in
  raw volume but carrying a named, correctable defect a further, bounded research step could resolve.

### 14.4 Weak institutional evidence

Where the minimum-sample precondition at §14.0 is met, 0–2 qualifying institutional commitments,
reported with its denominator (completed eligible institutional interviews) in every case.

### 14.5 Indeterminate

Insufficient sample (including any case falling under §14.0's minimum-institutional-sample
precondition), failed comprehension (per the teach-back requirement), contaminated recruitment (per
§10), an ordered-sequence violation triggering the consequence at §14.8, technical failure, or
contradictory evidence — restating §5.3's own default.

### 14.6 Denominator required for every reported figure

*Remediation of finding M2.* No commitment count may be reported without its applicable denominator.
Every Phase 0A report presenting a threshold-relevant figure shall report, at minimum, for the
institutional segment:

- qualifying commitments (count);
- completed eligible institutional interviews (denominator);
- the resulting segment-specific rate (qualifying commitments ÷ completed interviews) — see also
  §14.1 item 3, which makes this same rate a pass/fail condition for `STRONG`, not merely a disclosure
  item;
- registered-surveyor qualifying commitments (count) and the number of institutional respondents
  whose registration status was authoritatively checked (denominator for that sub-rate);
- the recruitment-source breakdown; and
- the recruitment-wave breakdown.

A figure such as "6 qualifying commitments" reported without its denominator is non-compliant with
this Decision and may not be used to support any §5.3 checkpoint outcome. "6 of 12" and "6 of 100" are
not the same evidentiary result and shall never be labelled identically without the denominator making
the difference visible.

### 14.7 Nature of these thresholds

These are **proposed, exploratory decision thresholds, not statistically validated population
estimates**, and shall be presented as such in every Phase 0A material that references them — this
sample is not, and is not claimed to be, statistically significant or representative of the general
population of Nigerian surveyors or institutional land professionals. This includes the 50%
qualifying-commitment rate at §14.1 item 3, which is a proposed exploratory Governance threshold, not
a statistically validated population estimate, exactly as the 4-of-qualifying-commitments
registered-surveyor sub-minimum and the 50% referral-concentration ceiling already are. Institutional
and retail commitments shall not be combined to reach any institutional band, restating §9. Where any
figure in this section proves inconsistent with authority outside this Decision's own drafting scope,
that conflict is reported to Governance rather than silently resolved by substituting a different
figure — none was identified during this or the prior remediation (§21 below records the two
documents read for this purpose and confirms neither contains a figure this section must reconcile
with).

### 14.8 Ordered-sequence violations — evidentiary consequence

*Added on remediation of the second preliminary governance review, correcting a gap the review's
Case 15 identified: no stated consequence previously existed for data collected outside the mandatory
ordered research sequence.* This subsection is an evidence-validity rule governing which records may
be counted toward any threshold in this section. **It does not authorize collecting any data before
the operational prerequisites at Playbook §16 are satisfied, and does not excuse any collection that
occurred in violation of them.**

1. Any respondent record collected before the privacy notice and documented informed-participation
   step (§25; Playbook §18 step 1) is completed shall not count as a completed eligible institutional
   interview or as a qualifying institutional commitment, for either segment.
2. Any substantive commitment response collected before a successful non-adjudication teach-back (§3;
   Playbook §6, §18 steps 3–5) shall not count toward any threshold in this section.
3. Data excluded under items 1–2 above shall be handled under the data-protection and
   incident-handling procedure the §17 item 8 Nigerian data-protection review establishes. This
   Decision does not itself determine a retention or deletion outcome for excluded data.
4. Every exclusion under this subsection, and the deviation that produced it, shall be documented in
   the final Phase 0A report (§16; Playbook §17, §19).
5. Following any exclusion under this subsection, every threshold and denominator in this §14 shall be
   recalculated using only the remaining valid records.
6. The institutional result shall be `INDETERMINATE` where, after that recalculation: the valid sample
   falls below the §14.0 minimum; the exclusion reflects a systemic or repeated failure rather than an
   isolated deviation; informed participation cannot be evidenced for the remaining sample; the
   integrity of the remaining data cannot otherwise be established; or the §17 item 8 Nigerian
   data-protection review requires suspension or invalidation of the research exercise.
7. An isolated, documented deviation affecting one or more records does not, by itself, invalidate the
   remaining, unaffected, compliant records, provided the procedure at item 3 above permits their
   continued use and every other applicable threshold in this section is independently satisfied using
   only those remaining records.

### 14.9 Governance Authority acceptance of thresholds (provisional, for drafting purposes)

*Added on Governance Authority parameter incorporation.* The Governance Authority accepts, provisionally
and for drafting purposes, the existing §14.1–§14.8 threshold figures as drafted — the 12-interview
minimum (§14.0, §14.1 item 1), the 6-commitment minimum (item 2), the 50% qualifying-commitment rate
(item 3), the 4-checked-registered-surveyor sub-minimum (item 4), the two-wave and two-source minima
(items 5–6), and the 50% single-referral-source ceiling (item 7) — together with every accompanying
safeguard already in force: institutional and retail results are never aggregated (§9); retail results
can never cure an institutional shortfall (§9); sequence-invalid responses are excluded from every
applicable numerator and denominator (§14.8); and fewer than 12 valid institutional interviews produces
`INDETERMINATE` regardless of commitment count (§14.0). This acceptance changes no figure, no formula,
and no safeguard already stated at §14.0–§14.8 — it is Governance's own confirmation that those figures
are the ones to apply, not a new rule.

**Purpose of each figure, stated for transparency, not as a new test:**

- **12** establishes a minimum evidence base appropriate to a narrow, relatively homogeneous
  exploratory population — not a statistically representative sample.
- **6** prevents a very small absolute commitment count from, by itself, supporting a strong result.
- **50%** prevents six commitments from appearing strong where the valid denominator has grown
  substantially larger (six of a hundred is not six of twelve).
- **4 checked registered surveyors** protects the primary professional hypothesis (§6) from being
  satisfied by non-surveyor institutional interest alone.

**What this threshold is not:** a statement of statistical representativeness; proof of national
market demand; an ownership, regulatory, or professional determination; or authority to proceed
automatically to Phase 0B (§5.4) on any outcome, including `PROCEED`.

**Outcome handling, restated from §5.3 and §14.1–§14.5, not altered by this acceptance:** every
condition at §14.1 satisfied simultaneously may support `STRONG`; one narrowly missed condition with
otherwise credible, uncontaminated evidence may support `MIXED` (§14.3); fewer than 12 valid
institutional interviews is `INDETERMINATE` regardless of any other figure (§14.0); an integrity,
registration-status, source-diversity, or privacy/sequence failure cannot be cured by a high commitment
count (§14.1 item 8, §14.8); and a `STRONG` outcome still leads only to the Phase 0A governance
checkpoint at §5.3 — never automatically to Phase 0B. **No threshold may be changed retrospectively
after results are known; any amendment requires separate Governance Authority approval** (§17 item 10).

## 15. Disclaimer placement

The non-adjudication statement at §3 above, or a Governance-approved equivalent, shall appear at every
material research touchpoint, including:

- the recruitment advert;
- the landing or registration page;
- the intake form;
- the interview introduction;
- the teach-back step;
- any sample output shown to a respondent;
- the commitment or reservation step, where one exists;
- the final research report.

**A disclaimer's presence at these touchpoints does not, by itself, cure an otherwise adjudicative
product presentation.** Where the composite-representation assessment at §12 identifies a governance
concern, a disclaimer present alongside the concerning presentation does not resolve that concern; the
concern is reported to the checkpoint regardless of disclaimer placement.

## 16. Discovery-artifact limitation

The following limitation governs every artefact Phase 0A produces, and shall be stated, in substance,
on or alongside every such artefact:

> Phase 0A interview notes, mock-ups, sample reports, workflow diagrams, pricing findings, user
> stories, survey results and other discovery artefacts are non-authoritative research materials. They
> do not constitute implementation specifications, accepted architecture, production requirements or
> authority to modify the LandVault system.

This restates, for Phase 0A's research artefacts specifically, the same discipline
`MARKETPLACE_DISCOVERY_AND_PLANNING.md` and `PARTNER_PROGRAMME_STRATEGY.md` already carry for their own
planning content (each, per GD-008 Findings §2, remains "unopened" with its own unactioned Approval
Gate), and the same discipline `docs/SURVEYOR_NETWORK_PHASE_0_GOVERNANCE_DISCOVERY.md`'s own header
already applies to itself ("Discovery and reconciliation only... does not alter" the documents it
reads).

## 17. Duration, effort, budget, and external engagement

*Rewritten on incorporation of Governance Authority parameter determinations (the parameter-
incorporation task following the consolidated mechanical corrections).* This Decision's previously
unresolved §17 questions — duration, internal effort ceiling, direct expenditure ceiling, permitted
research incentives, data-retention period, deletion and access controls, and authority for external
professional consultation — are now settled for drafting purposes by explicit Governance Authority
determination, incorporated below. **Incorporating these determinations does not ratify this Decision,
does not authorize Phase 0A execution, does not permit respondent contact, and does not authorize
expenditure or engagement.** Every figure and control below remains inoperative until GD-015 is
ratified **and** every execution prerequisite at Playbook §16 is independently satisfied; no activity,
payment, or engagement may begin merely because this Decision has been drafted, remediated, or
reviewed.

**One narrow, explicit exception to the "ratification and every §16 gate" sequencing above.** The
item 8 Nigerian data-protection review is itself one of the Playbook §16 execution prerequisites — it
cannot, by its own nature, already be satisfied before it can be commissioned. Accordingly, and solely
for that reason, **commissioning, instructing, and paying the item 8 reviewer, within the item 8
₦400,000 ceiling and for no other purpose, is authorized by ratification alone**, not by waiting for
every other §16 prerequisite first. Every other Phase 0A activity — recruitment, respondent contact,
SURCON inquiries, other spending, and the duration clock at item 1 — continues to require ratification
**and** every other Playbook §16 prerequisite, unaffected by this one exception. **Commissioning,
instructing, or paying the item 8 reviewer does not itself satisfy the item 8 gate.** That gate is
satisfied only when the required review has actually been completed and its protocol, privacy notice,
and lawful-basis output have actually been received (item 8 below; Playbook §16 item 6) — procuring the
review is not a substitute for the review having occurred.

1. **Phase 0A duration.** Maximum **35 calendar days**. The clock begins only once every execution
   prerequisite at Playbook §16 is satisfied — not on ratification alone, and never on drafting or
   review alone. One extension of no more than **14 additional calendar days** may be granted, and only
   by explicit, separate Governance Authority approval; no extension is automatic. Reaching day 35
   without an approved extension stops all Phase 0A activity. The following structure is indicative,
   for planning only, and does not convert into a mandatory daily quota — a wave or step finishing early
   or late within the 35-day ceiling is not itself a violation:

   | Days | Indicative activity |
   |---|---|
   | 1–7 | Controlled recruitment and scheduling |
   | 8–21 | Interviews conducted across at least two prospective recruitment waves (§14.1 item 5) |
   | (within 8–21) | One predefined demand-measurement day (§13's "one-day demand test") |
   | 22–28 | Eligibility checking, deduplication, and analysis |
   | 29–35 | Findings report and governance-checkpoint preparation (§5.3) |

   **"One-day demand test" still means the one predefined measurement day following controlled
   recruitment, as §13 above states — this duration determination schedules that day within the
   35-day ceiling; it does not change what the phrase means, and does not imply that recruitment,
   interviews, or analysis must all occur within a single day.** The 35-day clock may begin only after,
   in addition to every other Playbook §16 prerequisite: the Nigerian data-protection review at item 8
   below is complete; the privacy notice, informed-participation wording, and interview script are
   approved; secure research storage and access controls exist; the Project Lead (item 9 below) is
   named; and the incentive and expense-control mechanisms at items 3–4 below are ready.

2. **Internal effort ceiling.** A hard combined ceiling of **96 person-hours (12 person-days) across
   all contributors**, planned as:

   | Activity | Maximum hours |
   |---|---:|
   | Preparation, legal coordination, and controls | 20 |
   | Recruitment and scheduling | 20 |
   | Interviews and record completion | 28 |
   | Eligibility checks and deduplication | 10 |
   | Analysis and reporting | 18 |
   | **Total** | **96** |

   This is a **maximum, not a target.** Time shall be recorded by person, date, and activity. Reaching
   80 hours triggers an internal warning and a remaining-effort review; reaching 96 hours stops further
   activity. Unused hours in one category may be reassigned to another only within the overall 96-hour
   ceiling and only where no substantive control in this Decision is weakened by the reassignment. Any
   increase above 96 hours requires prior, separate Governance Authority approval.

3. **Direct-expenditure ceiling.** A maximum ordinary Phase 0A direct-expenditure ceiling of
   **₦600,000**, which *includes* the respondent-incentive exposure at item 4 below (₦150,000 maximum,
   not additional to this ceiling) and otherwise covers: respondent reimbursements; essential local
   travel; telephone and data costs; approved meeting costs; transcription or translation; research
   administration; and a limited contingency. It *excludes*, and may never be used for: the legal and
   data-protection professional costs governed by item 8 below (a separate ₦400,000 ceiling); software
   development; equipment purchases; partner onboarding; survey work; land-document acquisition;
   marketing campaigns; government fees; commissions; deposits or reservation payments (§5.2, §22 —
   prohibited outright regardless of budget); salaries or founder compensation; or any Phase 0B
   activity. Every expenditure shall be supported by a receipt or a written exception record.
   Expenditure above ₦600,000 requires prior written Governance Authority approval. Unused item 8
   legal-review authority may not be transferred into this research budget without separate Governance
   Authority approval. **Approval of this ceiling does not itself authorize spending** before GD-015 is
   ratified and every Playbook §16 execution gate is satisfied.

4. **Respondent-incentive policy.** Authorized, subject to ratification and every execution gate: a
   flat **₦10,000 airtime/data reimbursement** for each completed eligible interview, capped at **15
   reimbursements** (maximum incentive exposure **₦150,000**), included within, not additional to, the
   ₦600,000 ceiling at item 3 above. Controls, none of which is optional: the reimbursement is disclosed
   before the informed-participation step (§25); it is paid for completed eligible participation and
   never for a favourable answer; it is never made conditional on reaching a qualifying commitment; at
   most one reimbursement per respondent; no payment for referrals; no lottery or prize-draw mechanism;
   no undisclosed cash payment; no interviewer discretion to increase the amount; payment is made
   through a documented, auditable mechanism; the payment register is maintained separately from
   research responses; the interviewer may not change a respondent's recorded eligibility after seeing
   that respondent's answers; retail and institutional incentive records remain distinguishable (§8,
   §9); and the reimbursement is never described, in any material, as remuneration, a partnership
   benefit, a future commission, or compensation for endorsement.
5. **Data-retention period for research/respondent data.** Subject to item 8's categorical
   data-protection gate below, which may shorten any period here or impose stricter controls, the
   following maximum retention schedule is adopted provisionally:

   | Data category | Maximum retention |
   |---|---|
   | Unsuccessful recruitment contacts | Delete within 30 days after the Phase 0A checkpoint (§5.3) |
   | Participant contact details | Delete, or irreversibly separate from research responses, within 30 days after the checkpoint |
   | Audio or video recordings | Delete after verified transcription, and no later than 30 days after the interview |
   | Identifiable interview notes or transcripts | Delete or irreversibly de-identify within 90 days after the checkpoint |
   | Incentive/payment register (item 4 above) | Retain 12 months, or longer only where a documented Nigerian legal or financial obligation requires it |
   | Consent and withdrawal records (§25) | Retain 12 months, subject to the item 8 legal review |
   | Pseudonymised analysis dataset | Delete or irreversibly de-identify within 180 days after the checkpoint |
   | Fully de-identified aggregate findings | May be retained as governance evidence once re-identification risk has been assessed |

   Any proposal to lengthen a period above requires documented legal justification and separate
   Governance Authority approval; the item 8 review may shorten any period or impose stricter controls
   without needing that approval.
6. **Deletion and access controls for research/respondent data.** On the same basis as item 5, subject
   to item 8 below, the following safeguards govern throughout: no land document is collected during
   this demand-research exercise; no unnecessary parcel, ownership, or dispute information is
   collected; every respondent receives a unique identifier, with identity stored separately from
   research answers; stored and transmitted data is encrypted or equivalently protected; a deletion
   record is maintained; applicable withdrawal, access, rectification, and erasure rights (§25) are
   honoured; data is never reused for sales, marketing, onboarding, or any other purpose without a
   valid lawful basis and appropriate notice; and data is never retained merely because it might be
   useful later. **Access is least-privilege and two-tiered, to avoid conflict with item 9's own
   interviewing grant:**

   - **Collection-point handling.** An interviewer conducting a specific interview under §19's script
     and independence controls (Playbook §19) — including the Project Lead or the alternate, when
     either is personally conducting that interview — may handle that respondent's data only for the
     duration and purpose of that one assigned interview, and must hand it into the records system at
     §26 below immediately afterward; this is task-bound handling, not standing access.
   - **Retained-corpus access.** Once a record is in the records system, ongoing access to the
     identifiable, retained corpus — for analysis, deduplication, reporting, or any purpose beyond the
     single interview that produced a given record — is restricted to the Project Lead and one named
     authorized reviewer only. The alternate holds this same retained-corpus access only while formally
     substituting for the Project Lead (item 9 below), not as a standing, parallel grant; the operative
     record of who is currently substituting is itself retained with the deletion log at §26 below.
   - No other contributor to this playbook's activities — any other interviewer, any referral source,
     any Chief Surveyor or intermediary — is given retained-corpus access of any kind.
7. **Authority for external professional consultation** (legal counsel, regulatory consultants,
   external institutions, other than the item 8 data-protection review) — **not granted by this
   Decision.** Paid legal counsel, regulatory consultants, or external institutions may not be retained
   on the strength of this Decision alone beyond the specific, separately budgeted item 8 engagement.
   **For the avoidance of doubt, the item 8 engagement itself is the one exception this item carves
   out**: once GD-015 is ratified, the Project Lead may commission, instruct, and pay the qualified
   Nigerian reviewer item 8 describes, within item 8's own ₦400,000 ceiling and solely for item 8's own
   stated scope, under the preamble's commissioning exception above — no further, separate procurement
   act is required for that one engagement. Any retention of paid legal counsel, a DPCO, or any other
   consultant or institution beyond that single, specific item 8 engagement requires its own separate
   procurement and budget authority this Decision does not supply.
8. **Nigerian data-protection review — categorical gate, execution-blocking, with a separate
   determined budget.** *Gate text unchanged from remediation of finding M5; budget and reviewer
   controls added on Governance Authority parameter incorporation:*

   > **NIGERIAN DATA-PROTECTION REVIEW REQUIRED:** Before Phase 0A execution, the research protocol,
   > privacy notice, applicable lawful basis or lawful bases, data minimisation, retention, access,
   > deletion, secure handling, data-subject rights, and incident procedures must be reviewed against
   > the Nigeria Data Protection Act 2023, applicable Nigeria Data Protection Commission (NDPC)
   > guidance, and any continuing applicable regulations, by qualified Nigerian legal review. GD-015
   > does not itself make a final legal-compliance determination.

   This Decision does **not** claim that informed consent (§25 below) is necessarily the sole lawful
   basis available or required — which lawful basis or bases apply is exactly what the required
   review determines, not this drafting. Adding this gate's text does not itself constitute or imply
   legal compliance; compliance is established only by the review itself occurring. The companion
   readiness report identifies this item as **execution-blocking** until the required review occurs
   (playbook §16 restates this as an operational prerequisite).

   **Determined budget.** A separate ceiling of **₦400,000** for this focused Nigerian
   data-protection/legal review, distinct from and not drawn against the ₦600,000 ordinary research
   ceiling at item 3 above. The review must address: lawful basis; privacy notice; informed
   participation; data categories and minimisation; audio or video recording; respondent rights; access
   or transfers involving the United Kingdom; processors and storage arrangements; retention and
   deletion; security and breach handling; whether a data-protection impact assessment is required;
   whether controller or processor registration obligations apply; and whether any proposed control
   above must be strengthened. The reviewer must be suitably qualified in Nigerian data protection,
   including a licensed Data Protection Compliance Organisation (DPCO) where legally or practically
   appropriate. This ₦400,000 allocation cannot fund ordinary research activity without separate
   Governance Authority approval; expenditure above ₦400,000 requires prior Governance Authority
   approval; the reviewer may require controls stricter than those adopted at items 5–6 above, and
   relaxing an approved privacy control requires separate Governance Authority approval. Neither this
   budget nor this Decision authorizes legal or DPCO engagement, or any spending, before GD-015 is
   ratified. **Once ratified, this budget is the Governance Authority's own prior approval for
   commissioning, instructing, and paying this specific reviewer for this specific scope**, under the
   preamble's commissioning exception above and item 7's restatement of it — no further case-by-case
   approval is needed for that one engagement, though every other spending and activity boundary in
   this Decision continues to apply to it. **Commissioning this engagement is not itself completion of
   the review, and does not itself satisfy the item 8 gate** (restated from the preamble above).

   **Total maximum authorized Phase 0A cash exposure** — ordinary research (item 3, ₦600,000,
   inclusive of the item 4 incentive exposure) plus the focused legal/data-protection review (this
   item, ₦400,000) — is **₦1,000,000**. The ₦600,000 ordinary-research portion remains available only
   after ratification and satisfaction of every Playbook §16 execution gate; the ₦400,000
   legal/data-protection portion becomes available, for the single commissioning purpose this item
   describes, upon ratification alone, per the preamble's exception above. Neither portion is
   available, for any purpose, before ratification.

9. **External-engagement authority (Project Lead and Alternate).** Phase 0A must have one named
   Project Lead and one named written alternate before the duration clock at item 1 above may begin.

   **Narrow pre-clock exception.** Once GD-015 is ratified, and before every other Playbook §16
   prerequisite is satisfied, the Project Lead alone may commission, instruct, and pay the item 8
   reviewer, strictly as the preamble's commissioning exception and items 7–8 above describe, and may
   do nothing else under this item until every other Playbook §16 prerequisite is satisfied. This is
   the sole respect in which "procurement commitments" are permitted under this item; it does not
   broaden to any other consultant, institution, or purpose.

   **General authority, unchanged in timing.** After ratification and completion of every other
   Playbook §16 execution gate, the Project Lead and alternate may: recruit respondents using the
   approved script; explain Phase 0A accurately; conduct research interviews; consult SURCON's own
   public register for the eligibility checks §7.1 describes — never direct correspondence with, or a
   request made to, SURCON as an institution; check registration status using the authoritative
   sources §7.1 names; arrange the approved respondent reimbursements at item 4 above;
   and explain that participation creates no partnership, appointment, entitlement, or future work.
   They may **not**: offer employment, commissions, or future work; sign contracts, MOUs, partnership
   agreements, or letters of intent; promise platform access or onboarding; represent participation as
   professional, government, or institutional endorsement; claim that LandVault is government-approved;
   seek access to government archives, systems, or non-public records (§11); ask a government body or
   official to upload land records; make any procurement commitment beyond the one narrow exception
   above; collect payments, deposits, or reservations beyond item 4's approved reimbursement mechanism;
   make public or media statements on behalf of the programme; open Phase 0B (§5.4); or contact a
   Surveyor-General or any government institution in an official institutional capacity without
   separate, written Governance Authority approval. Public-source SURCON inquiries and registration
   checks under §7.1 are permitted research activities, consisting solely of consulting SURCON's own
   public register as §7.1 describes — they are not, and must not be read as, direct correspondence
   with or a request to SURCON as an institution; institutional proposals or requests to SURCON or any
   government body are not permitted. Chief-Surveyor referrals remain tagged and analytically separated
   under §10, and must never be represented as government endorsement.

10. **Amendment and escalation authority.** The operative model is **Default → Evidence → Decision →
    Amendment authority**: a default applies until evidence prompts a decision, and only a decision
    with the correct authority may amend a default. The Project Lead may make non-material
    administrative adjustments only where: every ceiling at items 1–8 above remains intact; respondent
    treatment does not change; the eligibility and analytical rules at §7, §7.1, and §14 do not change;
    privacy risk does not increase; external representations under item 9 above do not change; and
    programme scope does not expand. Prior, separate Governance Authority approval is required for any
    change affecting: the 35-day duration or its extension (item 1); the 96-hour effort ceiling (item
    2); either expenditure ceiling (items 3 and 8); incentive value, form, or eligibility (item 4);
    thresholds or outcome classifications (§14); external commitments or government engagement (item
    9); personal-data categories or retention periods (items 5–6); institutional/retail separation (§8,
    §9); or the Phase 0A/Phase 0B boundary (§5.4). **No person may amend a threshold retrospectively
    after seeing results** (§14.7).

**No financial or operational authority beyond the figures and controls determined above is invented
by this Decision.** These determinations settle drafting-stage parameters only. They do not ratify
GD-015, do not authorize Phase 0A execution, do not permit respondent contact, and do not authorize
expenditure or external engagement — ratification and full satisfaction of every Playbook §16 execution
gate remain required before any of the activity this section describes may begin.

## 18. Readiness-report neutrality

The companion readiness report, `docs/GD-015_READINESS_REPORT.md`, is required to state, and this
Decision requires it to state, that the report does not certify this proposal as compliant, accepted,
safe, or ready for ratification. It may state drafting completeness, the documents prepared, questions
requiring Governance Authority judgment, dependencies, unresolved risks, and a recommended review
sequence — using neutral language, and specifically the phrase:

> GD-015 PARAMETER-INCORPORATED DRAFT PACKAGE PREPARED FOR FORMAL GOVERNANCE REVIEW

*(Updated on incorporation of the Governance Authority's parameter determinations at §17 above and
§14.9, superseding the prior phrase, which stated only that the package was prepared for that
determination — that determination has now occurred, for drafting purposes, as recorded below. The
phrase does not claim acceptance, ratification, implementation readiness, or Phase 0A execution
readiness — it states only that the package, with its previously reserved parameters now incorporated,
is prepared for the Governance Authority's own formal review, which remains a separate, later step
from both parameter incorporation and ratification.)*

and no language implying self-approval.

## 19. Traceability

The companion document `docs/GD-015_REMEDIATION_TRACEABILITY_MATRIX.md` maps each of the seventeen
remediation requirements named in that document's own governing instruction to its exact location in
this draft package, recording document, section, disposition, and any unresolved question for each.
That matrix is incorporated into this Decision by reference as the authoritative index of where each
requirement is addressed; it does not itself grant any authority this Decision does not otherwise
grant.

## 20. Test date

**No retrospective or same-day test date is selected by this Decision or by the companion playbook.**
The playbook states, and this Decision requires it to state, that the actual demand-test date will be
scheduled only after GD-015 is ratified and every operational prerequisite the playbook names is
satisfied. Nothing in this Decision, in the playbook, or in any Phase 0A preparatory activity
authorizes fixing, announcing, or communicating to any prospective respondent an actual test date
before ratification.

## 21. No architecture or bounded-context decision is made; Partner and Marketplace Approval Gates preserved

This Decision makes no architecture decision and closes no bounded-context question. GD-008 §2's own
"directional governance guidance only" characterization of the Marketplace/Partner two-context model
stands exactly as GD-008 left it — this Decision does not rely on it being finally resolved, does not
resolve it, and does not authorize any implementation that would presuppose it resolved one way or
another. Any future ADR addressing Marketplace, Partner, Job, Assignment, Payment, or Rights
architecture remains gated exactly as GD-008 §14 and §17 already established, unaffected by this
Decision's ratification or by any Phase 0A checkpoint outcome.

**Added on remediation of finding C4, having now read both planning documents in full.**
`docs/MARKETPLACE_DISCOVERY_AND_PLANNING.md`'s own Approval Gate states: "No Marketplace programme
work — discovery, ADR drafting, or implementation — has begun... **Waiting for explicit direction
before any Marketplace programme work begins**." `docs/PARTNER_PROGRAMME_STRATEGY.md`'s own Approval
Gate states: "No Partner programme work has begun... it does not decide sequencing relative to
Marketplace, Enterprise, or any other future programme. **Waiting for explicit direction before any
Partner programme discovery begins**." Both gates concern opening that programme's own
architecture-discovery Phase 0 — for Marketplace, resolving whether "Marketplace" is one bounded
context or several and scoping Wallet/Escrow/Ratings/Enterprise Dispatch; for Partner, defining
accreditation, the onboarding→active→suspended→terminated lifecycle, compliance tracking, and the
Wallet/Earnings relationship to Marketplace's own candidate Wallet concept.

> **GD-015 authorizes only the research expressly described in Phase 0A. It does not satisfy,
> discharge, replace, or pre-approve any architecture, bounded-context, marketplace,
> partner-programme, implementation, or operational Approval Gate established by GD-008,
> `MARKETPLACE_DISCOVERY_AND_PLANNING.md`, `PARTNER_PROGRAMME_STRATEGY.md`, or another governing
> instrument.**

Neither planning document names, anticipates, or gates a commercial-demand-research stage of the kind
this Decision authorizes — this is not an oversight in either document; a demand-validation stage
preceding architecture discovery is simply outside what either document's own Approval Gate was
written to open or withhold. This Decision does not resolve the Surveyor Network bounded-context
question, and no future reader may cite this Decision, its ratification, or any Phase 0A checkpoint
outcome as having done so.

Consistent with `PARTNER_PROGRAMME_STRATEGY.md`'s own candidate scope (Onboarding, Accreditation,
Compliance, Ratings, Earnings/Wallet, Analytics, SLAs, Suspension, Performance management), §22 below
is extended to name several of these items explicitly, for the avoidance of doubt that this Decision's
research authorization does not reach any of them.

## 22. Explicit boundaries — this Decision does not authorize

For consistency with GD-008's, GD-012's, and GD-013's own exhaustive-exclusion convention, this
Decision does not authorize, and no activity under it may include:

- marking GD-015 ACCEPTED or IN FORCE (only the Governance Authority's own ratification act may do
  that);
- altering LV-000's operative Article XVI Governance Decision Log (§23 below governs the prospective
  text only);
- creating GD-016 or any other numbered decision;
- implementing any feature of any kind;
- creating or modifying a dashboard of any kind;
- modifying application code of any kind;
- modifying tests, migrations, or generated clients of any kind;
- changing Base44 in any respect;
- contacting any prospective respondent;
- recruiting any surveyor;
- contacting SURCON, any government official, or any other institution (§7.1 governs the one narrow,
  public-register-only exception for the eligibility-check mechanism itself, and does not authorize
  contact with SURCON as an institution);
- collecting any surveyor identifier or running any registration check against a real person (§7.1
  describes the mechanism this Decision would authorize on ratification; it does not itself authorize
  performing that check during this or any other pre-ratification drafting or remediation task);
- collecting any document or personal information beyond what §6–§11 above and the companion playbook
  expressly authorize for research purposes under the controls named at §17;
- collecting any payment, deposit, or reservation of any kind, or making any respondent-incentive
  payment of any kind (§17 item 4 determines the incentive policy that would apply on ratification; it
  does not itself authorize making any such payment during this or any other pre-ratification drafting
  or remediation task);
- creating any account of any kind;
- accessing production with elevated or administrative privileges (§5.1 item 1 above governs);
- retaining paid legal counsel, a DPCO, or other consultants of any kind (§17 items 7–9 describe the
  one narrow exception — commissioning the item 8 reviewer, and only that reviewer for only that
  purpose, once GD-015 is ratified; this Decision does not itself authorize performing that
  commissioning during this or any other pre-ratification drafting or remediation task, and does not
  authorize retaining any other consultant at any time);
- any Onboarding, Accreditation, Compliance tracking, Ratings, Earnings/Wallet, partner-facing
  Analytics dashboard, SLA, Suspension, or Performance-management capability of the kind
  `PARTNER_PROGRAMME_STRATEGY.md`'s own candidate scope names, in any implemented form (§21);
- any Git commit;
- any Git push;
- opening any pull request;
- any merge.

**Read-only consultation of official public sources.** This Decision permits read-only consultation
of an official, already-public source (for example, a public statutory or professional-body register
consulted per §7.1) solely to verify general institutional or statutory facts. Every such consultation
records the source, its URL, and the access date. No personal entry from any professional register may
be copied into this repository; only the fact of a match/no-match/inconclusive result, per §7.1's own
classification, is recorded.

**Stop-and-return condition.** If, during any later authorized drafting or research-preparation
activity, it is found that any of the above would be required to proceed, the person or agent
performing that activity must stop and return exactly:

**`GD-015 BLOCKED — [IMPLEMENTATION | RECRUITMENT | DATA-COLLECTION | FINANCIAL | ARCHITECTURE]
AUTHORITY REQUIRED`**

rather than improvise a workaround inside this Decision's own authority.

## 23. Article XVI entry (ratified — inserted into LV-000 under separate transcription authority)

The Governance Authority ratified this Decision, including the following text, on 8 October 2026. The
text below is inserted into `docs/LV-000-constitution.md`'s Article XVI Log as a distinct,
separately-authorized local documentation transcription of that ratification — mirroring GD-014 §8's
own separated-authority pattern — not performed by the act of ratification itself, and not, by that
transcription alone, a Git commit, push, pull request, or merge:

> **GD-015 — Surveyor Partner Programme Phase 0 Discovery and Demand-Validation Research Authorization.**
> *(Ratified 8 October 2026; full operative text at `docs/GD-015-surveyor-partner-programme-phase-0-
> discovery-authorization.md`.)* Operative authority: **Article XVI §2** — GD-015 is
> a later numbered decision that explicitly names `docs/GD-008-surveyor-network-phase-0-principles-and-
> authorization-boundary.md` §17 and `docs/PARTNER_PROGRAMME_STRATEGY.md`. GD-015 authorizes a
> distinct, narrowly bounded Phase 0A demand-research and system-reality exercise. It responds to the
> outstanding need for an express Governance decision that GD-008 §17 identified, but it does **not**
> open, partially open, satisfy, discharge, replace, or pre-approve the architecture-discovery,
> bounded-context, accreditation, onboarding, or lifecycle Approval Gates established by GD-008,
> `docs/MARKETPLACE_DISCOVERY_AND_PLANNING.md`, `docs/PARTNER_PROGRAMME_STRATEGY.md`, or any other
> governing instrument *(corrected on second-preliminary-review remediation: this entry previously
> read "to open, in narrowly bounded research-only form, the Partner Programme Phase 0 discovery gate"
> and named `PARTNER_PROGRAMME_STRATEGY.md` as "the planning document whose Approval Gate this Decision
> partially and narrowly opens" — language that contradicted this Decision's own header and §21 and is
> removed here to match them)*. It is not proposed under Article XIV and does not amend this
> Constitution.
>
> **Decision.** Authorization of a research-only Phase 0A for a prospective Surveyor Partner
> Programme: read-only, access-bounded reality/composite-representation assessment; separately
> recruited and separately analysed institutional and retail stakeholder research, with
> registered-surveyor status checked as an eligibility/classification matter only (never
> accreditation) and a referral-concentration ceiling on institutional evidence; and a one-day demand
> test (methodology per the companion playbook, gated on a required Nigerian data-protection review
> and an informed-participation/privacy-notice step), concluding at a governance checkpoint recording
> PROCEED, PROCEED WITH CONDITIONS, PIVOT, STOP, or INDETERMINATE (default on incomplete,
> contaminated, insufficient, or contradictory evidence). Institutional and retail research results
> must not be aggregated for any threshold, rate, or checkpoint-outcome purpose; retail evidence alone
> may never produce a PROCEED outcome; and the institutional threshold itself requires a minimum
> completed-interview sample below which the result is INDETERMINATE regardless of commitment count, a
> registered-surveyor-specific sub-minimum, a minimum qualifying-commitment rate rather than a raw
> count alone, a stated denominator, and prospectively defined recruitment waves, not a raw,
> undifferentiated institutional count. Phase 0B (any operational pilot, partner
> onboarding, live dashboard, document intake, government pilot, or payment collection) remains
> dormant and requires its own, later, explicit Governance Authority approval, not an automatic
> consequence of any Phase 0A outcome.
>
> **Scope excluded — no retroactive expansion.** This decision does not authorise implementation of any
> Marketplace, Partner, Job, Assignment, accreditation, payment, or Surveyor Dashboard capability
> (`GD-008` §15); any government dashboard, account, archive ingestion, integration, or endorsement
> claim; any architecture or bounded-context decision (`GD-008` §2 remains unresolved by this
> decision); any payment, deposit, or reservation collection; any elevated or cross-tenant production
> access; any contact with SURCON, government officials, or other institutions beyond the narrow
> public-register consultation §7.1 describes; or any of the activity `GD-015` §22 itself excludes.
> This decision does not satisfy, discharge, replace, or pre-approve `MARKETPLACE_DISCOVERY_AND_
> PLANNING.md`'s or `PARTNER_PROGRAMME_STRATEGY.md`'s own Approval Gate (`GD-015` §21).

## 24. Definitions

*Added on remediation of this draft's preliminary governance review (cross-document consistency,
§19 of that task). This section is the single operative source for each term below. The companion
playbook, readiness report, and traceability matrix cross-reference this section rather than
restating their own, divergent versions.*

- **Registered surveyor** — a research respondent claiming registration with the Surveyors Council of
  Nigeria (SURCON) or an equivalent recognized professional-registration authority, whose status is
  classified per §7.1 as either authoritatively checked or `UNVERIFIED SURVEYOR STATUS`.
- **Checked registration status** — a registered-surveyor claim confirmed against an authoritative
  public SURCON source per §7.1, with source and check date recorded.
- **Unverified surveyor status** — any registered-surveyor claim that is not, or cannot be,
  authoritatively checked per §7.1; excluded from the §14.1 registered-surveyor sub-minimum.
- **Eligible institutional interview** — a completed interview with a respondent falling within one of
  §7's four institutional subtypes, on an affirmative, recorded classification basis.
- **Qualifying institutional commitment** — a deduplicated, non-contaminated, institutional-segment
  respondent record reaching at least tier 2 ("costly non-financial commitment") per the companion
  playbook's commitment-terminology classification (Playbook §9).
- **Completed interview** — an interview that reached the end of the ordered research sequence
  (Playbook §18) for that respondent, including a recorded teach-back result, whether the teach-back
  passed or failed.
- **Recruitment source** — the specific channel or intermediary (including "direct," meaning no
  intermediary) through which a respondent was recruited, recorded at intake.
- **Recruitment wave** — as defined at §14.2.
- **Minimum institutional sample precondition** — the §14.0 rule requiring at least 12 valid
  completed eligible institutional interviews, after any §14.8 exclusions and deduplication, before
  any band other than `INDETERMINATE` may be recorded.
- **Qualifying-commitment rate** — qualifying institutional commitments ÷ completed eligible
  institutional interviews; the same figure serves as the §14.6 disclosure item and the §14.1 item 3
  pass/fail condition for `STRONG`.
- **Strong / mixed / weak / indeterminate institutional evidence** — as defined at §14.0–§14.5, §14.8,
  §14.9.
- **Retail separation** — the requirement at §8 that retail respondents be separately recruited where
  practicable, separately identified, separately priced, separately analysed, and separately reported.
- **Informed participation** — the privacy-notice-and-consent step defined at §25, distinct from the
  non-adjudication teach-back.
- **Non-adjudication teach-back** — the comprehension check defined at §3 and operationalized in the
  companion playbook, confirming a respondent's understanding of this Decision's §3 constitutional
  boundary, distinct from informed participation.
- **Costly non-financial commitment** — tier 2 of the companion playbook's three-tier commitment
  terminology: an action carrying real cost beyond a stated price acceptance (e.g., booking a specific
  follow-up meeting, or submitting an eligible document for review).
- **Payment-backed commitment** — tier 3 of that same terminology; **unavailable and unmeasurable
  under this Decision**, since §5.2 and §22 above prohibit all payment, deposit, and reservation
  collection outright (the companion playbook's §13/§20 state this in full for the demand-test
  methodology specifically); defined here only so the term is not silently redefined elsewhere.
- **Phase 0A** — the research-only stage this Decision authorizes on ratification, per §5.1–§5.3.
  Distinct from "the Partner Programme's own Phase 0" as `PARTNER_PROGRAMME_STRATEGY.md` and GD-008
  use that phrase (an architecture-discovery stage) — see the Operative Authority section's
  terminology note and §21.
- **Dormant Phase 0B** — the conditional operational-pilot stage this Decision does not authorize
  under any circumstance, per §5.4.

## 25. Informed participation and privacy notice

*Added on remediation of finding M6.* Before collecting any interview or respondent data, every
respondent shall receive, and shall be given a documented opportunity to respond to, all of the
following — distinct from, and in addition to, the non-adjudication teach-back at §3:

1. a clear explanation of the research purpose;
2. what information will be collected;
3. how it will be used;
4. who may access it;
5. the proposed retention and deletion arrangements (per §17 items 5–6, as resolved by the time of
   execution);
6. that participation is voluntary;
7. that the participant may decline individual questions or withdraw, subject to any clearly explained
   practical limits (for example, that data already anonymized or aggregated before a withdrawal
   request may not be fully separable from the aggregate);
8. a privacy notice;
9. identification of the applicable lawful basis or bases, determined only after the §17 item 8
   Nigerian data-protection review has occurred — this section does not itself determine that basis,
   and does not claim informed consent is necessarily the only lawful basis available.

A documented indication that the person agreed to participate shall be recorded. **This recorded
agreement does not, by itself, resolve every applicable legal requirement** — it is one element the
§17 item 8 review addresses, not a substitute for that review. No land document, parcel evidence, or
identifying information beyond what §6–§11 above require may be collected merely because a person
agreed to participate. The full operational detail of this step (its exact placement in the interview
sequence, and its place on the disclaimer-placement checklist) is in the companion playbook.

## 26. Interviewer independence and script discipline

*Added on remediation of finding C6.* Any Phase 0A interview or intake activity this Decision
authorizes on ratification shall be conducted under:

- a standardized, versioned interview script, fixed before recruitment begins;
- consistent core questions within each segment (§8);
- recorded interviewer identity for every interview;
- disclosure of any material relationship between an interviewer and a respondent;
- no outcome-linked reward (bonus, incentive, or otherwise) for any interviewer or recruiter tied to
  conversion, commitment, or threshold results;
- no coaching of a respondent toward a desired answer;
- no suppression of a negative, incomplete, or withdrawn response from the recorded dataset;
- a recorded log of any deviation from the approved script;
- separate reporting of responses gathered by a programme insider or an influential intermediary,
  consistent with §10's referral-tagging and referral-concentration requirements; and
- an INDETERMINATE classification, per §5.3 and §14.5, wherever interviewer influence is found to have
  materially compromised the evidence gathered.

The eventual script itself remains a non-authoritative discovery artefact under §16 above and gains no
implementation authority from this section. The companion playbook restates this section's
requirements within its own ordered research sequence.

## Approval Gate

**This Governance Decision is `ACCEPTED` and `IN FORCE`, ratified by the Governance Authority on 8
October 2026.** It authorizes exactly the research-only Phase 0A activities at §5.1, subject in full
to §§6–26 above — never anything broader, and never Phase 0B under any circumstance absent its own
future, separate authorization (§5.4). Execution additionally remains gated on the companion
playbook's own nine operational prerequisites at §16, including the §17 item 8 Nigerian
data-protection review; ratification satisfies Playbook §16 item 1 only and does not, by itself,
satisfy any other item, authorize Phase 0A execution, permit respondent contact, or authorize
expenditure or engagement beyond the narrow item 8 reviewer-commissioning exception at §17.

**Remediation and review status.** This document underwent two substantive remediation passes
following preliminary governance review, a subsequent mechanical accuracy correction, and a further
consolidated mechanical correction, none of which changed the programme, thresholds, or authorization
boundaries. The Governance Authority then incorporated its own parameter determinations at §14.9 and
§17 above — settling duration, effort, budget, incentive, retention, and external-engagement
parameters this document previously left reserved — a substantive act distinct from, and not itself, a
mechanical correction, which likewise changed no threshold, scope, or authorization boundary. A formal
governance review then found seven corrective findings (C-1 through C-7) and fourteen non-blocking
advisory notes; a narrowly authorized corrective pass resolved exactly those seven findings without
altering Parameters A–H or any threshold, scope, or authorization boundary; and an independent,
read-only post-corrective re-review confirmed all seven resolved and Parameters A–H unchanged,
concluding the package was ready for ratification consideration. The Governance Authority has now
ratified this Decision on that basis. Ratification does not itself satisfy any outstanding Playbook
§16 execution prerequisite, does not certify that the Nigerian data-protection review required by §17
item 8 has occurred, does not certify that a Project Lead or alternate has been named, and does not
certify that SURCON's public register is, in practice, usable for the §7.1 eligibility check — each of
these remains an outstanding execution/readiness matter, unaffected by ratification. Review history is
recorded in the companion readiness report and traceability matrix, and in external read-only review
reports, as historical evidence of the analysis that preceded ratification; neither source alters this
Decision's own operative authority as ratified.

See the companion readiness report, `docs/GD-015_READINESS_REPORT.md`, for the independent,
non-self-certifying challenge of this draft that preceded ratification; the companion playbook,
`docs/GD-015_ONE_DAY_DEMAND_TEST_PLAYBOOK.md`, for the full drafted-but-unexecuted demand-test
methodology, execution of which remains gated on §16; and the companion traceability matrix,
`docs/GD-015_REMEDIATION_TRACEABILITY_MATRIX.md`, for the requirement-by-requirement index across all
three documents.
