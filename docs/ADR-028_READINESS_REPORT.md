# ADR-028 Readiness Report — Evidence Actor and Commissioning Provenance

**Type:** Point-in-time governance readiness review, produced against `main` at commit
`76727ffed370461121e93b3fad6a0f358357b710` (GD-008 active and post-merge verified). This report
independently tests `docs/adr/ADR-028-evidence-actor-and-commissioning-provenance.md`
("the ADR") against GD-008's authorization boundary. **The ADR's own text is authoritative for
its architecture; this report is authoritative only for the specific pass/fail questions below at
the time it was written**, exactly as `docs/SURVEYOR_NETWORK_GOVERNANCE_DECISION_READINESS_REPORT.md`
already established as this repository's convention for a readiness review's relationship to the
decision it reviews.

**Date:** 2026-09-10

**Status of the reviewed ADR:** Proposed — architecture only. Not accepted. This report is not,
and does not purport to be, a ratification.

## 1. Does ADR-028 remain inside GD-008's authority?

**Pass.** GD-008 §1 (per `docs/GD-008-surveyor-network-phase-0-principles-and-authorization-boundary.md`)
authorizes exactly one immediate technical activity: drafting ADR-028 for Evidence actor and
commissioning provenance. The ADR:

- decides only Evidence actor/commissioning provenance (Uploaded By/Originated By/Reviewed By/
  Commissioned By), matching GD-008's own naming exactly;
- contains an explicit "Out of scope" section repeating, in effect, every GD-008 exclusion
  (Marketplace, Partner, Job/Assignment, accreditation, payments, SECI/EQF/PPI, Rights/licensing,
  Legacy Vault, royalties, Surveyor Dashboard, ADR-021 implementation) and does not design,
  schema, or authorize any of them;
- names Rights Holder, Licensor, Custodian, Job-participant, and Assignment-participant only to
  distinguish them from what it decides, and explicitly declines to model any of their semantics;
- creates no migration, no ORM model, no repository, no API, no authorization change, and no
  application code — confirmed by inspection: the only two files this task produced are the ADR
  itself and this report, both left uncommitted, and no other file in the working tree was
  modified.

## 2. Does it preserve ADR-026 Evidence independence?

**Pass.** The ADR's "Relationship to the frozen baseline" section states `EvidenceRecord`'s
existing fields, invariants, and lifecycle are unchanged, and this was independently re-verified
against the actual current implementation, not assumed from the ADR's own claim:

- `backend/app/contexts/evidence/domain/evidence_record.py` — the ADR proposes zero changes to
  this file. No new field, mutator, or invariant on `EvidenceRecord` is introduced.
- `backend/app/contexts/evidence/adapters/orm.py` — the ADR proposes a **new, separate** table
  (`evidence_actor_attributions`) referencing `evidence_records.id`, not a column added to
  `evidence_records` itself.
- The new table has no foreign key to, and no schema dependency on, any Job, Assignment, or
  Marketplace table — none of which exist in this codebase today (confirmed: no such tables or
  domain classes exist under `backend/app/contexts/`). Evidence remains constructible and
  persistable with zero attribution rows, exactly as it is today; the ADR does not make any
  attribution mandatory.

## 3. Does it introduce a hidden Party/Marketplace/Partner architecture?

**Pass, with one explicit, named boundary.** The ADR was specifically tested against this
question because its own governing instructions required stopping rather than smuggling such a
dependency in if one were discovered. It was not discovered:

- No `Organization`, `Party`, or `Customer` aggregate is created. Free-text `actor_name`/
  `actor_organization_name` columns are used instead, which is the same idiom
  `Parcel.current_owner_name`/`current_owner_contact` (ADR-013) and
  `parcel_ownership_history.asserted_holder_ref` (ADR-023) already use for an actor who need not
  be a LandVault user — confirmed by reading both existing, accepted ADRs, not merely asserted by
  the new one.
- `actor_principal_id` references only `identity_users.id`, an aggregate that already exists and
  is already the target of `EvidenceRecord.uploaded_by` — no new identity concept is introduced.
- The one deliberate boundary: `actor_principal_id` is restricted to same-tenant principals only.
  A cross-tenant professional (including a future Partner-accredited one) must be recorded as a
  free-text snapshot, never a live reference. This is a restriction, not an expansion — it
  affirmatively **prevents** this ADR from becoming a de facto cross-tenant professional directory,
  which would have been the hidden-Party-architecture risk this check exists to catch.

## 4. Does tenant isolation remain intact?

**Pass.** Three independent points, each checked against the ADR's text and against this
codebase's existing tenant-isolation pattern (`docs/adr/ADR-010`, RLS since migration `0001`,
`EvidenceService._in_scope`):

- The new table's `tenant_id` is stated to be copied from the attributed `EvidenceRecord` by the
  recording service, never accepted as caller-supplied input — the identical non-divergence
  guarantee `parcel_ownership_history`/`parcel_status_history` already rely on.
- RLS on the new table is specified as identical in scope and strength to `evidence_records`' own
  policy — no weaker, no differently-shaped policy is proposed.
- Attribution is explicitly stated to confer no authorization — being named as an actor on an
  `EvidenceRecord` does not grant read, write, or mutation rights over anything. This was checked
  against `EvidenceService`'s actual authorization code (`_in_scope`, `_can_mutate`) to confirm the
  ADR's claim is consistent with how authorization actually works today, not merely a stated
  intention with no structural backing: neither existing function is proposed to change, and
  nothing in the ADR gives a new function a reason to consult attribution rows for an
  authorization decision.

## 5. Does the selected model handle historical and multi-originator Evidence?

**Pass.** Checked against both named scenarios explicitly:

- **Historical evidence** (a current uploader submitting a decades-old document created by someone
  else, possibly unidentifiable): supported via `actor_reference_kind = HISTORICAL_ASSERTED` (an
  identity named by the historical material itself, not independently established) or `UNKNOWN`
  (no identity can reasonably be assigned), with `actor_principal_id` left `NULL` in both cases and
  a mandatory `basis` explaining why — explicitly designed to avoid the two failure modes named in
  this task's own instructions (fabricating an identity, or silently omitting the fact that
  origination is unknown or unconfirmed).
- **Multi-originator evidence** (joint authorship, field crew plus responsible surveyor, or
  successive independent reviews over time): supported natively, because
  `evidence_actor_attributions` is a one-row-per-claim table, not a scalar column — an unlimited
  number of `ORIGINATED_BY` or `REVIEWED_BY` rows may reference the same `evidence_id`. This was
  the specific, structural reason Alternative A (scalar columns on `EvidenceRecord`) was rejected
  in the ADR's own alternatives analysis, and this report independently confirms that rejection is
  sound: a scalar column genuinely cannot express this without either serialising a list (breaking
  queryability and the append-only audit discipline) or an unbounded number of numbered columns.

## 6. Does any external/legal dependency block adoption?

**Pass — no blocking dependency found.** This ADR is a purely internal data-model decision about
how LandVault's own database represents attribution claims it is told. It does not:

- require outside counsel review (unlike, for example, the data-protection erasure procedure
  Article VII §6 requires counsel approval for — attribution correction here uses the existing
  append-only/supersede mechanism, already governed, not a new erasure path);
- touch legal hold, WORM sealing, or chain-of-custody mechanics (ADR-007/ADR-026's own domain,
  untouched);
- require a new external service, SDK, or credential (`docs/ENGINEERING_RULES.md` rule 5 — human
  approval, justification, pinned version — is not triggered; no new dependency is proposed);
- require resolving any live legal question about professional registration, copyright, or
  authenticity — the ADR explicitly declines to let attribution imply any such determination has
  been made.

No condition exists today that would make this ADR's architecture incorrect or unadoptable absent
some further external event; it is ready for governance review on its own architectural merits.

## 7. Governance Review Remediation Record

A formal Governance review of this ADR (2026-09-10) concluded **PASS WITH REQUIRED TEXTUAL
REMEDIATION** — the selected architecture (a separate, append-only `EvidenceActorAttribution`
relationship, no new `EvidenceRecord` fields, no Party aggregate) was accepted, with five specific
textual/architectural clarifications required before ratification. All five have been applied to
the ADR directly; this section records what changed and confirms none of the five required
revisiting the selected architecture itself.

| # | Finding | Resolution |
|---|---|---|
| 1 | Actor-identification states (known internal / external / historical-asserted / unknown) were only distinguishable via free-text `basis`, not a structural field | Added `actor_reference_kind` (`INTERNAL_PRINCIPAL`/`EXTERNAL_NAMED`/`HISTORICAL_ASSERTED`/`UNKNOWN`) as a new bounded, non-numeric column, with a dedicated "Actor-state representation" section naming all four states and explicitly separating this dimension from assertion source (`basis`), confidence (deliberately unmodeled), and professional verification (deliberately unmodeled) |
| 2 | `actor_name` was nullable even when `actor_principal_id` was set, leaving a live-dereference path that could let a later `User` name change retroactively alter historical provenance | Added a dedicated "Immutable snapshot requirement" section requiring `actor_name` (and, where applicable, `actor_organization_name`) to be captured as an immutable snapshot at write time for every named actor state, independent of whether `actor_principal_id` is also set — an internal reference now explicitly adds precision, never substitutes for the snapshot |
| 3 | `supersedes_id` integrity (self-supersession, cycles, multiple successors) was undecided | Added three explicit invariants under "Append-only, corrections by superseding": no self-supersession (`id ≠ supersedes_id`), no cycles (`supersedes_id` must reference a strictly earlier row), and exactly one direct successor per superseded attribution (a later correction supersedes the currently active row in the lineage, never the original, so no ambiguous fork can exist) — with the reasoning stated and future database-constraint requirements named |
| 4 | No explicit non-implication list existed for `ORIGINATED_BY`, unlike `REVIEWED_BY`/`COMMISSIONED_BY`, leaving two constitutional red-team interpretations only inferable rather than stated | Added a new "Origination provenance — creation, not entitlement" section with an explicit non-implication list (no ownership, document ownership, copyright, licensing authority, beneficial interest, parcel interest, licence verification, or correctness/authoritativeness) and an explicit sentence that a professional attribution never makes Evidence legally authoritative |
| 5 | ADR-023's mechanism was reused without an explicit statement that its ownership *meaning* is not also reused | Added explicit wording under "Relationship to the frozen baseline" → ADR-023: the append-only mechanism is reused, the ownership-history *meaning* is not, and correcting an Evidence actor attribution never corrects, modifies, settles, or implies anything about a land-ownership assertion |

A sixth, non-blocking item (a worked four-actor example: uploader/originator/commissioner/reviewer
as four independent facts) was also requested and added as its own "Worked example" section,
directly demonstrating findings 4 and 5's non-implication rules against a concrete scenario rather
than only stating them abstractly.

**Post-remediation re-verification**, performed against the amended ADR text:

- Attribution still grants no authorization — the "Tenant isolation" section's third rule is
  unchanged by any of the five edits.
- No cross-tenant live reference is introduced — `actor_principal_id` remains same-tenant-only;
  the new `actor_reference_kind` field does not create or imply any cross-tenant lookup.
- No Party/Organization aggregate is introduced — `actor_organization_name` remains free text.
- `EvidenceRecord` still requires zero attribution rows to be valid; no field was added to it.
- ADR-026 remains authoritative and untouched by any of the five edits.
- Marketplace/Partner remain unnecessary dependencies — none of the five edits reference either.
- No Rights architecture is introduced — the new "Origination provenance" non-implication list
  explicitly excludes rights/licensing/copyright.
- No professional-accreditation architecture is introduced — `actor_reference_kind` records only
  how an actor is identified, never whether a professional credential was verified.
- No scoring or confidence metric is introduced — `actor_reference_kind` is categorical, not
  numerical, and the ADR explicitly states confidence remains unmodeled.

## Summary

| Check | Result |
|---|---|
| Inside GD-008 authority | Pass |
| ADR-026 Evidence independence preserved | Pass |
| No hidden Party/Marketplace/Partner architecture | Pass (one explicit same-tenant boundary drawn) |
| Tenant isolation intact | Pass |
| Historical/multi-originator Evidence handled | Pass |
| External/legal blocking dependency | None found |
| Files created | `docs/adr/ADR-028-evidence-actor-and-commissioning-provenance.md`, `docs/ADR-028_READINESS_REPORT.md` — both uncommitted |
| Application/runtime changes | None |
| ADR status | Proposed — architecture only (not Accepted) |
| Governance review (2026-09-10) | PASS WITH REQUIRED TEXTUAL REMEDIATION — all five findings resolved (§7 above) |

This report's ratified authority is limited to the six questions above, at this point in time,
against the ADR text as drafted. It does not itself authorize implementation, does not amend
GD-008, and does not accept the ADR — acceptance, as with every prior ADR in this codebase, is a
separate Governance Authority act.
