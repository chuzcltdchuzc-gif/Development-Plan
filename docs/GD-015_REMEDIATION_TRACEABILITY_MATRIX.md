# GD-015 Remediation Traceability Matrix

**Status:** This matrix indexes a package whose Decision is now `ACCEPTED` and `IN FORCE`, ratified by
the Governance Authority on **8 October 2026** (Part H below records this). It is not itself a
governance decision and grants no authority independent of the documents it indexes. Parts A–G below
remain an accurate historical index of the pre-ratification review and remediation passes they each
record, and are not rewritten by ratification; historical outcome quotations within them (for example,
a prior review's own closing classification) are preserved as accurate records of what that review
concluded at the time, not as claims about GD-015's current status.

**Type:** Requirement-by-requirement index, mapping each of the seventeen original remediation
requirements, the five cross-cutting structural requirements, the thirteen findings from the first
read-only preliminary governance review (M1–M6, C1–C6, A3), the six corrections from the second
read-only preliminary governance review's closure-remediation pass, and the Governance Authority
parameter determinations incorporated at Readiness event 10 (Part F below), to their exact location
across the GD-015 draft package. This matrix does not itself grant any authority the documents it
indexes do not otherwise grant, and is not itself a governance decision. No row below is marked resolved
unless the
underlying operative document was independently confirmed, by re-reading it, to actually contain the
control claimed. **Part B's "Article XVI entry" row and Part C's C4 row were marked resolved
prematurely in the version of this matrix produced after the first remediation pass — the underlying
document (Decision §23) did not in fact contain the claimed correction until the closure remediation
(event 5). Both rows are
corrected below, and Part E records the error and its closure, consistent with this paragraph's own
verification standard.**

**Indexed documents:**

- **Decision** = `docs/GD-015-surveyor-partner-programme-phase-0-discovery-authorization.md`
- **Playbook** = `docs/GD-015_ONE_DAY_DEMAND_TEST_PLAYBOOK.md`
- **Readiness** = `docs/GD-015_READINESS_REPORT.md`

## Part A — Original seventeen numbered requirements (unchanged disposition, cross-references updated)

| # | Requirement | Document | Section | Disposition | Unresolved question |
|---|---|---|---|---|---|
| 1 | Phase 0A/0B split | Decision | §5, §5.1–§5.4 | **Addressed.** | None. |
| 2 | Institutional/retail separation | Decision | §6–§8 | **Addressed.** | None. |
| 3 | Composite-representation assessment | Decision | §12 | **Addressed**, now with the access boundary at §5.1 item 1 for the deployed-system audit component. | Manual control, not automated (unchanged from original disposition). |
| 4 | Honest commitment terminology | Playbook | §9–§10, §20 | **Addressed**, now with explicit statement that tier 3 is unreachable under this authorization (§20). | None. |
| 5 | Proportionate thresholds | Decision | §14.1–§14.7 | **Addressed**, substantially rewritten — see Part B rows M1–M3. | See M1–M3 below. |
| 6 | Teach-back | Playbook | §6, §18 step 4–5 | **Addressed**, now sequenced explicitly relative to informed participation and price questions. | None. |
| 7 | One price per respondent | Playbook | §4, §18 step 7 | **Addressed.** | None. |
| 8 | Previous/current price question | Playbook | §5, §18 step 6 | **Addressed.** | None. |
| 9 | Parcel/case and respondent deduplication | Playbook | §7 | **Addressed.** | None. |
| 10 | Chief Surveyor referral tagging | Decision, Playbook | Decision §10; Playbook §8 | **Addressed**, now with the 50% concentration ceiling — see C3 below. | See C3 below. |
| 11 | Disclaimer placement | Decision, Playbook | Decision §15; Playbook §14 | **Addressed**, now with the informed-participation checkpoint added as a distinct item — see M6 below. | See M6 below. |
| 12 | Managed intake or residual-risk disclosure | Playbook | §15 | **Addressed.** | None. |
| 13 | Duration, budget and external-engagement boundaries | Decision | §17 | **Addressed by explicit reservation at drafting, then by Governance Authority determination and incorporation** at Readiness event 10 — see Part F below for each item's exact value and location. | Whether Governance confirms these determined values at ratification (Readiness §6 item 4). |
| 14 | Indeterminate default | Decision, Playbook | Decision §5.3, §14.5; Playbook §12 | **Addressed.** | None. |
| 15 | Discovery artefacts have no implementation authority | Decision | §16 | **Addressed.** | None. |
| 16 | Neutral readiness-report wording | Readiness | Entire document; closing line | **Addressed.** The closing line was first drafted at original drafting (event 1), then revised to track Decision §18's then-current required phrase at the targeted remediation (event 3, which the row previously described only as "this remediation task" — resolved here to event 3 since that pass first produced a phrase naming a "second" review), the closure remediation (event 5), the mechanical corrections (event 7), the chronology-coherence correction (event 9), and the parameter incorporation (event 10, Readiness §10). The line currently in force matches Decision §18's phrase as last amended; neither is restated here verbatim to avoid this row going stale again at the next amendment. | None. |
| 17 | Prospective test date after ratification | Playbook | §16, §20 (Decision §20) | **Addressed**, now gated on nine operational prerequisites instead of five. | None. |

## Part B — Cross-cutting structural requirements (original)

| Item | Document | Section | Disposition |
|---|---|---|---|
| Non-aggregation rule | Decision | §9 | **Addressed**, strengthened per C1 below. |
| Government sub-hypothesis kept research-only | Decision | §11 | **Addressed**, unchanged. |
| No architecture or bounded-context decision made | Decision | §21 | **Addressed**, substantially strengthened per C4 below. |
| Exhaustive "do not" boundary list, stop-and-return phrase | Decision | §22 | **Addressed**, extended with new items per the targeted remediation's (event 3) own governing instruction §20. |
| Article XVI entry drafted but not inserted into LV-000 | Decision | §23 | **Addressed, but only as of the second closure-remediation pass.** The version produced after the first remediation pass claimed this row was addressed; it was not — §23 still carried the pre-remediation framing the second preliminary review's finding (recorded as Part E row 1 below) identified. §23 is now corrected to match the header and §21. |

## Part C — Preliminary-review findings remediated in the targeted remediation (event 3)

| Finding | Source | Disposition | Exact document/section | Rationale | Remaining dependency |
|---|---|---|---|---|---|
| **M1** — no registered-surveyor-specific sub-minimum; threshold could pass with zero surveyors | Preliminary review §5, Findings | **ACCEPTED WITH MODIFICATION** | Decision §14.0, §14.1 items 1–8 (≥12 completed interviews, tested first against the §14.0 minimum-sample precondition; ≥6 qualifying commitments; a ≥50% qualifying-commitment rate added by the second-review closure pass, item 3; **at least 4 from checked registered surveyors**, item 4; ≥2 waves, item 5; ≥2 sources, item 6; ≤50% one referral source, item 7; no tainted records, item 8) | This remediation's own governing instruction specified the exact figures; adopted as instructed, not independently re-derived. Items 3, 8, and §14.0 itself were added by the later closure-remediation pass, not this one | Whether Governance accepts these exact figures, including the rate condition added later (Decision §14.7) |
| **M2** — no denominator for reported counts | Preliminary review §5, Findings | **ACCEPTED** | Decision §14.6; Playbook §17 | Every commitment figure now requires its denominator; "6 of 12" vs. "6 of 100" made explicit | None |
| **M3** — "recruitment wave" undefined | Preliminary review §5, Findings | **ACCEPTED** | Decision §14.2; Playbook §2, §16 item 7 | Prospective, dated, non-retrospective definition adopted | Actual wave schedule remains to be fixed at execution time |
| **M4** — registration-status verification tension unresolved (self-report only) | Preliminary review §5, Findings | **ACCEPTED WITH MODIFICATION** | Decision §7.1; Playbook §3 | This remediation's own governing instruction explicitly superseded the preliminary review's self-report-only recommendation with an authoritative-check-where-available approach and an `UNVERIFIED SURVEYOR STATUS` fallback | Whether SURCON's public register is, in practice, usable for this check (Readiness §6 item 2) |
| **M5** — soft "with reference to NDPR" wording | Preliminary review §5, Findings | **ACCEPTED** | Decision §17 item 8; Playbook §16 item 6 | Replaced with a categorical "NIGERIAN DATA-PROTECTION REVIEW REQUIRED" gate citing the Nigeria Data Protection Act 2023 and NDPC guidance, mirroring GD-008 §10's own gate convention | The review itself remains outstanding and execution-blocking |
| **M6** — no informed-consent/privacy-notice requirement | Preliminary review §5, Findings | **ACCEPTED** | Decision §25; Playbook §18 step 1, §21, §14 checklist | Added as a step distinct from the non-adjudication teach-back | Content depends on the M5 review's own output (lawful basis) |
| **C1** — segment-primary requirement lived only in playbook | Preliminary review §5, Findings | **ACCEPTED** | Decision §9 (restated as controlling text); Playbook §11 | Decision itself now states segment-separated reporting is primary, not merely implied by the playbook | None |
| **C2** — interview sequence inferable, not explicit | Preliminary review §5, Findings | **ACCEPTED** | Playbook §18 (11-step ordered sequence) | Makes explicit what was previously spread across §§4–6, §14 | None |
| **C3** — referral-concentration control judgment-based only | Preliminary review §5, Findings | **ACCEPTED** | Decision §10 (50% ceiling, forces MIXED/INDETERMINATE if exceeded); Playbook §8 | Numeric ceiling added alongside the existing INDETERMINATE-on-concentration trigger, which is retained, not replaced | None |
| **C4** — Operative Authority framing risked overstating discharge of Partner/Marketplace gates | Preliminary review §5, Findings | **ACCEPTED WITH MODIFICATION — closed only as of the second closure-remediation pass** | Decision header (Operative authority), §2, §21, and **§23** (the location the second preliminary review found still uncorrected; see Part E row 1) | Resolved by reading both planning documents in full (Readiness §3) and rewriting the framing substantively in the header and §21 during the first remediation, and in §23 during the second closure-remediation pass — not merely adding a disclaiming sentence | None |
| **C5** — deployed-system audit access scope unstated | Preliminary review §5, Findings | **ACCEPTED** | Decision §5.1 item 1 | Explicit permitted/prohibited access list added, with a stop-and-seek-separate-authority clause citing Article IX §3 / rule 9 | None |
| **C6** — no interviewer-influence/conflict-of-interest control | Preliminary review §5, Findings | **ACCEPTED** | Decision §26; Playbook §19 | Standardized script, recorded interviewer identity, no outcome-linked incentive, INDETERMINATE-on-compromise | None |
| **A3** — tier-3 unreachable but not prominently flagged | Preliminary review §5, Findings | **ACCEPTED** | Playbook §20; Decision §24 (Definitions) | Dedicated section states tier 3 is unavailable and unmeasurable, controlling over any other reading of §9 | None |

*A1 (PIVOT definition not acknowledging retail as a pivot-direction input) and A2 (no literal
interview script exists yet) were advisory-only findings in the preliminary review and were not
required to be addressed by the targeted remediation's (event 3) own governing instruction; neither
was actioned in that pass. This is recorded here rather than silently dropped.*

## Part D — Cross-document consistency (the targeted remediation's own §19, event 3)

A single operative Definitions section was added (Decision §24), covering: registered surveyor,
checked registration status, unverified surveyor status, eligible institutional interview, qualifying
institutional commitment, completed interview, recruitment source, recruitment wave, strong/mixed/
weak/indeterminate institutional evidence, retail separation, informed participation, non-adjudication
teach-back, costly non-financial commitment, payment-backed commitment (unavailable), Phase 0A, and
dormant Phase 0B. The playbook, this matrix, and the readiness report cross-reference that section
rather than restating divergent definitions of the same terms. Direct re-reading of the playbook and
readiness report during the targeted remediation (event 3) confirmed no divergent definition of any of
these sixteen terms was introduced.

## Part E — Second preliminary review closure-remediation pass (this pass)

Each row below was independently re-read against the operative Decision/Playbook text, as amended in
this pass, before being marked resolved — consistent with this matrix's own verification standard
stated at the top, which Part B's and Part C's C4 row previously (and, as row 1 below records,
wrongly) treated as already satisfied for one of these same items.

| # | Source finding | Previous defect | Disposition | Exact operative section | Corresponding Playbook section | Remaining dependency | Verification status |
|---|---|---|---|---|---|---|---|
| 1 | Second-review §8 (C4 reopened) | Decision §23's proposed Article XVI entry retained wording substantively equivalent to "to open, in narrowly bounded research-only form, the Partner Programme Phase 0 discovery gate" and named `PARTNER_PROGRAMME_STRATEGY.md` as "the planning document whose Approval Gate this Decision partially and narrowly opens," contradicting the corrected header and §21 in the same document | **RESOLVED** | Decision §23 (operative-authority clause rewritten; contradiction disclosed inline) | n/a (Decision-only) | None | Confirmed by re-reading Decision §23 in full after the edit |
| 2 | Second-review §17, finding 2 | This matrix's Part B "Article XVI entry" row, and Part C's C4 row, certified §23 as already updated when it was not | **RESOLVED** | Traceability matrix Part B, Part C (C4 row) | n/a | None | Confirmed by re-reading both corrected rows against the corrected Decision §23 |
| 3 | Second-review §19, finding 3 | Decision §5.3 cited "the thresholds at §9" (twice) where §14 was meant; Decision §14.1 item 1 and §14.3 each cited "§14.4" (Weak institutional evidence) where "§14.6" (the denominator section) was meant | **RESOLVED** | Decision §5.3, §14.1 item 1, §14.3 | n/a | None | Confirmed by re-reading all four corrected citations against the sections they now name |
| 4 | Second-review §19, Case 7 | No band covered an interview-count shortfall alone (11 interviews, 6 otherwise-qualifying commitments had no named disposition) | **RESOLVED** | Decision §14.0 (new); §14.1 preamble, §14.3, §14.4 cross-reference it | Playbook §12 (INDETERMINATE default, cross-references §14.0) | Whether Governance accepts 12 as the minimum (Decision §14.7) | Confirmed by re-reading §14.0 and tracing it into §14.1–§14.5 |
| 5 | Second-review §19, Case 15 | No stated evidentiary consequence existed for data collected outside the mandatory ordered research sequence | **RESOLVED** | Decision §14.8 (new) | Playbook §22 (new, restates §14.8) | The §17 item 8 data-protection procedure that §14.8 item 3 defers to is itself still outstanding (Decision §17 item 8) | Confirmed by re-reading Decision §14.8 and Playbook §22 together for consistency |
| 6 | Second-review §19, Case 8; §10 (surveyor-centred validity) | `STRONG` was a volume-floor test only; six qualifying commitments from 100 interviews could nominally satisfy it despite the document's own denominator/rate rhetoric (Decision §14.6) | **RESOLVED** | Decision §14.1 item 3 (new rate condition); §14.3 (rate-failure-only forgiven into `MIXED`); §14.7 (rate condition stated as exploratory, not validated) | Playbook §17 (reporting requirement extended to state whether the rate condition is met) | Whether Governance accepts 50% as the rate (Decision §14.7) | Confirmed by re-reading §14.1 item 3, §14.3, and §14.7 together, and by re-running the second review's own Case 8 (100 interviews / 6 commitments) and Case 7 (11 interviews / 6 commitments) against the amended text |

No row above was marked resolved solely because the readiness report states it is resolved; each was
independently re-read against the operative Decision or Playbook text after this pass's edits were
made.

## Part F — Governance Authority parameter determinations (event 10)

Each row below was independently re-read against the operative Decision and Playbook text, as amended
by the parameter-incorporation event, before being marked resolved.

| # | Parameter | Determined value | Decision | Playbook | Remaining dependency |
|---|---|---|---|---|---|
| 1 | Phase 0A duration | Maximum 35 calendar days; one Governance-approved extension of up to 14 days; clock starts only once every Playbook §16 gate is satisfied | §17 item 1 | §23 | Whether Governance confirms this figure at ratification (Readiness §6 item 4) |
| 2 | Internal effort ceiling | 96 person-hours (12 person-days) combined, by activity category; 80-hour warning; 96-hour stop | §17 item 2 | §23 | Same as row 1 |
| 3 | Direct-expenditure ceiling (ordinary research) | ₦600,000, inclusive of respondent incentives | §17 item 3 | §24 | Same as row 1 |
| 4 | Respondent-incentive policy | ₦10,000 per completed eligible interview, capped at 15 (₦150,000), within the ₦600,000 ceiling | §17 item 4 | §24 | Same as row 1 |
| 5 | Demand-threshold acceptance | Existing 12/6/50%-rate/4-surveyor bands and safeguards provisionally accepted, unchanged in figure | §14.9 | n/a | Same as row 1; no figure was altered by this acceptance |
| 6 | Data-retention period | Per-category maximum retention table | §17 item 5 | §26 | The item 8 legal review may shorten any period (no Governance approval needed for that direction) |
| 7 | Deletion and access controls | Unique identifiers; identity separated from answers; Project-Lead-and-one-reviewer access; encryption; deletion log | §17 item 6 | §26 | Same as row 6 |
| 8 | External professional consultation (legal/DPCO) | Not granted beyond the item 8 budget; further retention needs separate procurement authority | §17 item 7 | n/a | None |
| 9 | Nigerian data-protection review budget | Separate ₦400,000 ceiling, distinct from the ₦600,000 research ceiling | §17 item 8 | §16 item 6, §26 | The review itself remains outstanding and execution-blocking (Readiness §6 item 6) |
| 10 | Total maximum authorized cash exposure | ₦1,000,000 (₦600,000 + ₦400,000), after ratification and every execution gate | §17 item 8 | n/a | Same as row 1 |
| 11 | External-engagement authority | Named Project Lead and alternate; permitted/prohibited-action lists; prohibited-list requests are declined and logged locally; Governance escalation is reserved for a government-institutional engagement request beyond §7.1's narrow exception | §17 item 9 | §25 | No Project Lead has actually been named in reality (Readiness §6 item 7) |
| 12 | Amendment and escalation authority | Default → Evidence → Decision → Amendment authority model; Project Lead limited to non-material adjustments | §17 item 10 | n/a | None |

**Boundary confirmed by re-reading, not assumed:** incorporating rows 1–12 above changed no figure at
Decision §14.0–§14.8 (the demand thresholds themselves), no Phase 0A/Phase 0B boundary at §5, no
SURCON-checking rule at §7.1, no NDPA/NDPC gate text at §17 item 8's own quoted requirement, and no
payment-backed-commitment prohibition at §5.2/§22/§24 — row 5 above is an acceptance of existing
figures, not a new rule, and rows 1–4 and 6–12 add ceilings and procedures within the boundaries those
sections already fixed.

## Part G — Formal governance review corrective findings (C-1–C-7) and post-corrective independent re-review

**Review lineage.** A formal governance review — independent of the drafting and remediation passes
recorded in Parts A–F above — evaluated the parameter-incorporated draft package (Part F) and found no
BLOCKING defect, but seven CORRECTIVE findings (C-1 through C-7) and fourteen ADVISORY notes not
requiring correction. Closing classification: **GD-015 FORMAL GOVERNANCE REVIEW CONDITIONAL
PASS — CORRECTION REQUIRED BEFORE RATIFICATION.** A narrowly authorized corrective pass then addressed
exactly C-1 through C-7, with Parameters A–H explicitly frozen and the fourteen advisories explicitly
out of scope. Closing status: **GD-015 CORRECTIVE REMEDIATION COMPLETE — READY FOR INDEPENDENT
READ-ONLY RE-REVIEW, NOT RATIFICATION.** A subsequent independent, read-only post-corrective re-review,
with no role in either the formal governance review or the corrective pass, then independently
verified all seven correctives, Parameters A–H, and the absence of any new governance authority.
Closing classification:

> GD-015 POST-CORRECTIVE INDEPENDENT RE-REVIEW PASS — READY FOR RATIFICATION CONSIDERATION, NOT RATIFIED

None of these three passes altered GD-015's status; it remains `PROPOSED` and unratified throughout,
consistent with the Governance-status record at Part A and the Decision's own Approval Gate.

| # | Finding | Concise description | Resolved at | Disposition | Verification status |
|---|---|---|---|---|---|
| C-1 | Legal-review / DPCO commissioning deadlock | The ₦400,000 legal/data-protection review budget could not practicably be used until the review it funds was already complete, compounded by a general DPCO-retention prohibition and unclear signer authority | Decision §17 preamble, items 7–9; Playbook §16 item 6 | **RESOLVED.** A narrow, textually-grounded pre-clock exception lets the existing Project Lead role commission, instruct, and pay the item-8 reviewer on ratification alone; explicit text states commissioning/payment does not itself satisfy the item-8 gate; the general DPCO-retention prohibition is preserved outside that one named engagement | Independently confirmed by the post-corrective re-review |
| C-2 | One-day demand-test schedule | Apparent conflict between the Playbook's one-day/one-window demand-test definition and the incorporated multi-wave days-8–21 duration schedule | Decision §17 item 1; Playbook §1–§2 | **RESOLVED.** Both documents state, in matching language, that the one predefined demand-measurement day is a single named day inside the existing multi-wave days-8–21 window, not a second or additional day | Independently confirmed by the post-corrective re-review |
| C-3 | Respondent-data access | Apparent contradiction between a narrow, named retained-access list and interviewers/alternate handling respondent data | Decision §17 item 6; Playbook §26 | **RESOLVED.** A two-tier model distinguishes task-bound collection-point handling (any interviewer, including the Project Lead or alternate when personally interviewing) from ongoing retained-corpus access (Project Lead and one named reviewer only; alternate only while formally substituting) | Independently confirmed by the post-corrective re-review |
| C-4 | Playbook §17 stale header | Playbook §17's header described its own content as "reserved," no longer matching the operative reporting-requirements content it carried | Playbook §17 | **RESOLVED.** Header reads "Reporting requirements," matching the substantive content beneath it; no policy change accompanied the header correction | Independently confirmed by the post-corrective re-review |
| C-5 | Stale Matrix cross-reference | This matrix cited "item 4" where "item 2" was meant | This document, Part F (parameter rows) | **RESOLVED.** Cross-reference corrected; every Part F row's cited Decision §17 item number independently re-checked against that item's actual content | Independently confirmed by the post-corrective re-review |
| C-6 | SURCON wording | Wording conflict between a reference to "inquiries to SURCON" and the governing boundary that this Decision does not authorize contacting SURCON directly | Decision §7.1, §17 item 9, §22; Playbook §3, §25 | **RESOLVED.** SURCON-facing language reworded at its source to state consistently, wherever it appears, that only consulting SURCON's own public register is authorized, never direct correspondence with or a request to SURCON as an institution | Independently confirmed by the post-corrective re-review |
| C-7 | Escalation-rule alignment | The Readiness Report's and this matrix's own description of the escalation rule was broader than Playbook §25's actual, narrower trigger | Readiness Report §6; this matrix, Part F row 11 | **RESOLVED.** Readiness Report and Matrix descriptions narrowed to match Playbook §25's actual single trigger (a government-institutional engagement request beyond §7.1's narrow exception); §25 itself was not broadened and no new trigger was invented | Independently confirmed by the post-corrective re-review |

This matrix records the post-corrective independent re-review's outcome as the current state of C-1
through C-7's traceability. It does not itself constitute ratification, does not authorize Phase 0A
execution, and does not alter GD-015's `PROPOSED` status.

**Parameter A–H pre-ratification carry-forward confirmation.** The Governance Authority parameters at
Part F above are carried forward **unchanged** for ratification consideration. This is confirmation of
already-determined values, not re-determination, and changes no figure:

| Parameter | Carried-forward value | Decision | Playbook |
|---|---|---|---|
| A — Duration | Maximum 35 calendar days; one Governance-approved 14-day extension | §17 item 1 | §23 |
| B — Effort allocation | 20 / 20 / 28 / 10 / 18 person-hours across the five named activity categories | §17 item 2 | §23 |
| C — Total effort ceiling | 96 person-hours (20+20+28+10+18 = 96) | §17 item 2 | §23 |
| D — Ordinary expenditure ceiling | ₦600,000, inclusive of the item-E incentive allocation | §17 item 3 | §24 |
| E — Incentive allocation | ₦150,000 (₦10,000 × up to 15), a subset of the ₦600,000 ceiling, not additional to it | §17 item 4 | §24 |
| F — Legal/data-protection review budget | ₦400,000, separate from and not drawn against the ₦600,000 ceiling | §17 item 8 | §16 item 6, §26 |
| G — Total governed budget | ₦1,000,000 (₦600,000 + ₦400,000) | §17 item 8 | n/a |
| H — Retention periods / demand threshold | Per-category retention table (30/30/30/90/365/365/180 days); 12-interview minimum / 6-commitment minimum / 50% rate / 4-checked-surveyor sub-minimum | §17 item 5; §14.0–§14.1, §14.9 | §26; §9–§12 |

No Parameter I or equivalent is introduced by this confirmation. No value above differs from Part F's
own recorded values.

**Outstanding execution/readiness prerequisites, unaffected by this carry-forward confirmation**
(restated from Readiness Report §6–§7, not altered here): the Nigerian data-protection/legal review
required by Decision §17 item 8 has not occurred; no Project Lead or alternate has actually been named;
whether SURCON's public register is, in practice, usable for the §7.1 eligibility check has not been
verified. None of these outstanding matters changes any Parameter A–H value above, and none is treated
here as satisfied.

**Advisory matters, not modified by this Part.** The day-35 stop-timing boundary, the
isolated-vs-repeated §14.8 interpretation question, the title's proximity to Partner Programme "Phase
0" terminology, retention soft spots, and citation-only advisory observations remain exactly as
previously preserved — unresolved and out of scope for this traceability-completion task.

## Part H — Ratification record (added 8 October 2026)

*This Part is appended after ratification. It does not rewrite Parts A–G above, each of which remains
an accurate historical record of the review or remediation pass it documents, including historical
outcome quotations such as Part G's own record of the post-corrective independent re-review's closing
classification (`READY FOR RATIFICATION CONSIDERATION, NOT RATIFIED`), which was that review's
accurate conclusion at the time it ran, not a claim about GD-015's current status.*

The Governance Authority ratified the GD-015 Decision on the basis of the complete package indexed in
Parts A–G above — including Part G's confirmation that all seven formal-review corrective findings
(C-1–C-7) were resolved and that Parameters A–H were unchanged. GD-015 is now:

> **`ACCEPTED` / ratified, effective 8 October 2026.**

Parameters A–H (Part G above) were carried forward into ratification **unchanged**; no figure, formula,
or safeguard was reopened or altered by ratification. The fourteen advisory findings from the formal
governance review, and A1–A2 from the first preliminary review, remain non-blocking and unresolved,
exactly as Part G and Parts A–C above record — ratification does not convert any of them into a new
rule.

**Outstanding execution prerequisites, unaffected by ratification:** the Nigerian data-protection/legal
review required by Decision §17 item 8 has not occurred; no Project Lead or alternate has actually been
named; whether SURCON's public register is, in practice, usable for the §7.1 eligibility check has not
been verified. Ratification satisfies Playbook §16 item 1 only. No Git commit, push, pull request, or
merge has occurred for any document in this package.

## Summary

All seventeen original numbered requirements, the five original cross-cutting requirements, the
thirteen first-preliminary-review findings (M1–M6, C1–C6, A3), the six second-preliminary-review
closure corrections (Part E above), the twelve Governance Authority parameter determinations (Part F
above), the seven formal-governance-review corrective findings C-1–C-7 (Part G above), and the
ratification record (Part H above) are addressed somewhere in the five-document package (including
`docs/LV-000-constitution.md`'s Article XVI entry), with exact section citations above. Two advisory
findings from the first review (A1, A2), and the fourteen advisory findings from the formal governance
review, remain unactioned, as disclosed rather than silently dropped. No row in this matrix was marked
resolved without independently re-reading the cited section during the pass that claims to resolve it —
including, at the closure-remediation pass, a correction to two rows (Part B's Article XVI-entry row and
Part C's C4 row) that had previously been marked resolved without that verification actually holding.
This matrix no longer has the formal-review indexing gap the post-corrective independent re-review
identified: Part G provides traceability for the formal governance review's seven corrective findings
and the post-corrective independent re-review's outcome, and Part H records GD-015's ratification on 8
October 2026, alongside the original remediation history (Parts A–E) and the parameter-determination
event (Part F). GD-015 is now `ACCEPTED` and `IN FORCE`; the package's remaining outstanding execution
prerequisites are consolidated in `docs/GD-015_READINESS_REPORT.md` §11, and nothing in this matrix
authorizes Phase 0A execution or satisfies any outstanding Playbook §16 gate.
