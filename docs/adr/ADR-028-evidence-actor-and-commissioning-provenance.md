# ADR-028 — Evidence Actor and Commissioning Provenance

**Status:** **ACCEPTED — 2026-09-10, on explicit Governance Authority ratification. IN FORCE.**
This ADR authorizes exactly the domain model, migration shape, and repository port described
below (the same category of authorization ADR-026 gave B5.2 for `EvidenceRecord` itself) — it
does **not** authorize implementation of any of it; see "Explicit exclusions" under "Approval
Gate" below. Drafting was authorized by
`docs/GD-008-surveyor-network-phase-0-principles-and-authorization-boundary.md` (Accepted,
2026-09-08, IN FORCE), which authorized exactly one immediate technical activity — drafting this
ADR — and authorized nothing else (no Marketplace, Partner, Job, payment, or scoring
implementation; see "Out of scope" below for the complete list carried over verbatim from GD-008).

**Date:** 2026-09-10

## Ratification Record

Ratified by Governance Authority for AquaSavannah LandVault, 2026-09-10, as: "ADR-028 — Evidence
Actor and Commissioning Provenance," accepting the architecture drafted below following formal
Governance review and the required textual remediation that review identified (actor-state
representation, the immutable-snapshot requirement, supersession integrity, the `ORIGINATED_BY`
non-implication rule, and the ADR-023 semantic distinction — all five already applied to this
document's own text before ratification). The ratifying decision restates this document's
substance clause by clause and, in two places, sharpens or adds precision the drafted text already
implied but had not stated as directly:

- **On supersession enforcement** (ratification §8): the ratifying decision clarifies that
  acceptance does not prescribe an ordinary SQL `CHECK` constraint for an invariant the database
  engine cannot enforce that way — a single-row invariant (`id <> supersedes_id`) is a genuine
  `CHECK`-constraint candidate, but a cross-row invariant (a `supersedes_id` referencing a
  strictly earlier row; at most one active successor per superseded row) requires a trigger or
  constraint trigger, never a plain column `CHECK`. This document's "Supersession integrity" and
  "Implementation consequences" sections already said "a check constraint... an ordering check or
  trigger... a partial unique index (or equivalent trigger)" rather than naming a bare `CHECK` for
  the cross-row cases, so no correction to this document's text is required — the ratifying
  decision's precision is recorded here for clarity and binds future implementation work.
- **On the external/legal boundary** (ratification §16): the ratifying decision states explicitly
  that this ADR may be architecturally accepted without first resolving future Nigerian questions
  regarding professional registration, copyright, expert evidence, licensing, or commercial rights,
  because this ADR records only bounded provenance assertions and grants none of those statuses —
  those external matters remain mandatory gates before any future capability makes a corresponding
  professional, legal, or commercial claim. This restates
  `docs/ADR-028_READINESS_REPORT.md` §6 (unchanged, preserved as its own point-in-time record) and
  is recorded here as part of the ratified text.

Every other numbered point in the ratifying decision (uploaded-by distinctness; the four actor
states with no Party/Customer/Partner/Organisation aggregate; attribution ≠ authorization; recorded
assertion, not verification, with no numerical confidence mechanism authorized; historical Evidence;
append-only correction with no self-supersession/no cycles/one direct successor; the `ORIGINATED_BY`,
`REVIEWED_BY`, and `COMMISSIONED_BY` non-implication rules; the ADR-023 and ADR-026 relationships;
constitutional subordination; and the explicit exclusions) restates this document's own text
precisely, in the Governance Authority's own words rather than this document's drafting language.
Where phrasing differs only in wording, not substance, both are read as saying the same thing;
this document is not amended to match the ratifying decision's phrasing, since no divergence in
substance was found.

**Scope:** Decides how LandVault represents professional and commissioning actor provenance on
`EvidenceRecord` (`docs/adr/ADR-026-evidence-domain-model.md`) — specifically, the semantic
distinction between Uploaded By, Originated By, Reviewed By, and Commissioned By, and the minimum
data shape needed to record each without inventing a Party/Customer architecture, without
weakening tenant isolation, and without introducing ownership-adjudication semantics. This is the
same category of decision ADR-026 made for `EvidenceRecord` itself and ADR-023 made for Registry's
ownership/status history: a domain-model ADR decided before any migration exists, per LV-000 v1.8
Article VI §1 ("Architecture Before Code"). It does **not** decide Rights Holder, Licensor,
Custodian, Job-participant, or Assignment-participant modeling — those are named here only to be
distinguished from what this ADR does decide, and are explicitly deferred to their own, future,
separately-governed ADRs.

**Constitutional anchors:** LV-000 v1.8 Article IV (evidence over assertion, non-adjudication);
Article V §2 (bounded context sovereignty — this stays inside Evidence, no new context); Article
VI §1 (Architecture Before Code); Article VII §6 (corrections append, history retained and marked
superseded); Article VIII §2 (RLS ships with the migration); Article XII (evidence is structural,
not asserted).

## Context

`docs/GD-008-surveyor-network-phase-0-principles-and-authorization-boundary.md` §1 distinguishes
four actor concepts that Evidence's current domain model collapses into one field:

- **Uploaded By** — the authenticated principal who submitted bytes to LandVault. Already modeled:
  `EvidenceRecord.uploaded_by`, a `NOT NULL` foreign key to `identity_users.id`
  (`backend/app/contexts/evidence/adapters/orm.py`), set from `ctx.principal_id`
  (`EvidenceService.upload_evidence`). This ADR does not touch this field, its type, or its
  meaning.
- **Originated By** — the person or organisation responsible for creating the underlying evidence.
  Not modeled today. May be the same person as Uploaded By (a surveyor uploads their own field
  survey the same day), or may differ by years and by identity (a registrant today uploads a
  government survey plan drawn by a different, possibly long-retired, possibly never-registered
  surveyor decades ago).
- **Reviewed By** — a professional actor who later performed a defined professional review of
  already-recorded evidence. Not modeled today. Zero, one, or many reviews may occur after upload,
  by different professionals, at different times.
- **Commissioned By** — the party that instructed or commissioned creation of the evidence, where
  known. Not modeled today. Distinct from all three of the above: a landowner may commission a
  survey that a licensed surveyor (Originated By) performs and a field agent (Uploaded By) later
  digitises.

No field, table, or relationship for any of the latter three exists anywhere in this codebase today
(confirmed by direct inspection of `backend/app/contexts/evidence/domain/evidence_record.py`,
`adapters/orm.py`, and `application/evidence_service.py`). `EvidenceRecord.uploaded_by` is the only
actor-shaped field Evidence has ever had, and ADR-026 already decided, deliberately, that it means
exactly one thing: who submitted the request. Reusing it, overloading it, or renaming it to serve
double duty as "who created this evidence" would silently retrofit a meaning ADR-026 never gave it
and would be wrong for exactly the historical-evidence case above (`uploaded_by` is always today's
uploader; it is never the original 1987 surveyor whose plan they are digitising).

Three facts from the existing codebase constrain every option considered below:

1. **`EvidenceRecord` has no relationship to any Party, Customer, or Organisation aggregate,
   because none exists.** `User.organization_id` (`backend/app/contexts/identity/domain/user.py`)
   is a loose, optional string, not a foreign key to any aggregate — no `Organization` table or
   domain class exists in this codebase (confirmed by repository-wide search). Any design that
   requires a new Party/Customer aggregate to be correct is, by GD-008's own instruction, a reason
   to stop and raise that as a separate decision, not to smuggle it into this ADR.
2. **The codebase already has a proven, accepted precedent for recording an actor who is not
   necessarily a LandVault user at all: `Parcel.current_owner_name`/`current_owner_contact`
   (ADR-013) and `parcel_ownership_history.asserted_holder_ref` (ADR-023) are free-text fields, not
   foreign keys to `identity_users`.** A parcel's asserted owner has never been required to hold a
   LandVault account. This ADR extends that same, already-governed idiom to Evidence's originator/
   reviewer/commissioner, rather than inventing a new one.
3. **The codebase already has a proven, accepted precedent for append-only, correctable provenance
   records: `parcel_ownership_history`/`parcel_status_history` (ADR-023)** — rows that are never
   updated or deleted, only superseded by a new row referencing the one it corrects
   (`supersedes_id`), enforced at two independent layers (privilege grant, and a `BEFORE UPDATE OR
   DELETE` trigger that raises unconditionally). This ADR reuses that mechanism rather than
   inventing a different one for a structurally identical problem (an assertion, with a basis, that
   must never be silently rewritten).

## Decision

### Individual-versus-organisation and multi-actor provenance

Evidence may be originated by an individual professional, a surveying practice, more than one
professional jointly (a field crew plus the responsible licensed surveyor), a government or public
body, another organisation, or an actor with no LandVault presence at all. Origination and review
must support **one-to-many and many-to-many** attribution: more than one Originated-By actor per
`EvidenceRecord` (joint authorship), and more than one Reviewed-By actor over time (successive
peer reviews). A model that stores these as scalar columns on `EvidenceRecord` cannot express any
of this without either serialising a list into an opaque column (defeating queryability and
auditability) or adding an unbounded number of numbered columns (`originated_by_2`,
`reviewed_by_3`, ...) — both rejected below as Alternative A.

### The `EvidenceActorAttribution` relationship — one row per attribution claim

A new table, `evidence_actor_attributions`, records attribution claims against an `EvidenceRecord`,
one row per claim, following exactly the shape and discipline
`parcel_ownership_history`/`parcel_status_history` (ADR-023) already established and this
Governance Authority already accepted:

```
id                       UUID, primary key
tenant_id                String, FK -> tenants.id, NOT NULL
                         (copied from the referenced EvidenceRecord.tenant_id at write time by the
                         recording service — never independently supplied by a caller, so it can
                         never diverge from the Evidence it attributes)
evidence_id              UUID, FK -> evidence_records.id, NOT NULL
attribution_role         String, NOT NULL   -- ORIGINATED_BY | REVIEWED_BY | COMMISSIONED_BY
                         (a bounded, small enum, extended additively exactly as EVIDENCE_TYPES
                         is today — see "Future attribution roles" below for why extending it is
                         NOT always a mechanical non-event the way a new EVIDENCE_TYPES member is)
actor_reference_kind     String, NOT NULL   -- INTERNAL_PRINCIPAL | EXTERNAL_NAMED |
                         -- HISTORICAL_ASSERTED | UNKNOWN — see "Actor-state representation" below.
                         -- This field answers ONE question only — how is the actor identified? —
                         -- and is deliberately kept separate from three questions it must never
                         -- be conflated with: what is the factual basis for the claim (`basis`,
                         -- below), how confident is the recorder (not modeled — no confidence
                         -- field exists), and has LandVault professionally verified this actor
                         -- (not modeled — no verification field exists, matching ADR-026's own
                         -- refusal to add a `verified` boolean to EvidenceRecord).
actor_principal_id       UUID, nullable, FK -> identity_users.id
                         -- set ONLY when actor_reference_kind = INTERNAL_PRINCIPAL, and ONLY for
                         -- an authenticated LandVault principal in the SAME tenant as the Evidence
                         -- being attributed (see "Tenant isolation" below) — never a cross-tenant
                         -- live reference. Setting this field NEVER excuses the recorder from also
                         -- populating actor_name (see "Immutable snapshot" below) — this column
                         -- adds identity precision; it does not replace the snapshot.
actor_name               String, nullable   -- a display-name snapshot, captured at recording
                         -- time and never updated thereafter, REQUIRED whenever
                         -- actor_reference_kind is INTERNAL_PRINCIPAL, EXTERNAL_NAMED, or
                         -- HISTORICAL_ASSERTED (left NULL only for UNKNOWN, where no name exists
                         -- to snapshot). A later name change on the User aggregate must never
                         -- retroactively alter what this row asserted at the time — see
                         -- "Immutable snapshot requirement" below, which this column exists to
                         -- satisfy structurally, not only by convention.
actor_organization_name  String, nullable   -- free text, e.g. "Ministry of Lands", "ABC Surveying
                         -- Practice" — never a foreign key, for the same reason
                         -- current_owner_name is free text: no Organisation aggregate exists to
                         -- reference, and inventing one is explicitly out of this ADR's scope
actor_type               String, NOT NULL   -- INDIVIDUAL | ORGANIZATION | UNKNOWN — what kind of
                         -- actor this is, orthogonal to actor_reference_kind (how it is
                         -- identified); the two dimensions vary independently (an ORGANIZATION can
                         -- be INTERNAL_PRINCIPAL-adjacent via its registered contact user,
                         -- EXTERNAL_NAMED, or HISTORICAL_ASSERTED, exactly as an INDIVIDUAL can)
basis                    String, NOT NULL   -- the factual/source explanation supporting the
                         -- attribution — what this claim rests on, e.g. "asserted by uploader from
                         -- the document's own title block," "self-identified during field data
                         -- collection," "originator could not be determined from the historical
                         -- document; recorded as unknown rather than guessed" — the same honest,
                         -- non-adjudicating discipline ADR-023's and ADR-026's own basis fields
                         -- already require. Deliberately kept distinct from actor_reference_kind:
                         -- the kind field names WHICH of the four identification states applies;
                         -- basis explains, in free text, WHY. NEVER optional, including for an
                         -- UNKNOWN actor: "we don't know, and here is why" is itself a recordable
                         -- fact this field exists to carry.
review_method            String, nullable   -- meaningful only when attribution_role = REVIEWED_BY;
                         -- NULL for every other role
recorded_by              UUID, FK -> identity_users.id, NOT NULL
                         -- the authenticated principal who recorded this claim (may differ from
                         -- the actor itself — e.g. today's uploader recording a historical
                         -- originator who is not them)
recorded_at              TIMESTAMPTZ, NOT NULL, server_default now()
audit_ref                String, nullable   -- the audit entry's entry_id, same mechanism every
                         -- prior ADR in this codebase uses without exception
supersedes_id            UUID, nullable, FK -> self (same table)
```

No `verified`, `confirmed`, or similarly named boolean exists anywhere on this table, for the
identical reason ADR-026 already gave for `EvidenceRecord` itself: recording an attribution is not
proof LandVault has confirmed the actor's identity, professional registration, copyright, or legal
authority over the evidence — recording *that* level of confidence, if ever built, is a distinct,
future, separately-decided capability, not a bit flipped on this table. `actor_reference_kind`
answers only "how is this actor identified," never "how sure are we" or "has this been verified" —
those remain, respectively, unmodeled (no confidence scalar exists, by design) and unmodeled (no
verification mechanism exists, by design).

### Actor-state representation — four identification states, kept separate from basis, confidence, and verification

`actor_reference_kind` makes explicit, and structurally queryable, the four ways an attributed
actor's identity can be known, rather than leaving the distinction to free-text prose inside
`basis` alone:

- **`INTERNAL_PRINCIPAL`** — the attribution concerns a LandVault principal whose internal identity
  is known, and `actor_principal_id` carries an optional, same-tenant-only internal reference to
  that principal (see "Immutable snapshot requirement" below for why `actor_name` is still
  required even here).
- **`EXTERNAL_NAMED`** — a named person or organisation is recorded (`actor_name`/
  `actor_organization_name`) with no LandVault identity relationship at all — no
  `actor_principal_id`, because none exists to reference.
- **`HISTORICAL_ASSERTED`** — the actor's identity is drawn from historical or source material, or
  from an assertion the recorder is relaying rather than personally vouching for, and has not been
  independently established by LandVault. This is the state most easily lost if left only to prose:
  it is deliberately distinct from `EXTERNAL_NAMED` (where the recorder is naming a real, presently
  known actor with ordinary confidence) precisely because a name copied off a fifty-year-old survey
  plan carries a different evidentiary character than a name the uploader supplies from their own
  first-hand knowledge — a difference `basis`'s free text could describe, but that a governance
  reviewer, a future query, or an audit should not have to parse prose to detect.
- **`UNKNOWN`** — the originator, reviewer, or commissioner cannot reasonably be identified.
  `actor_principal_id`, `actor_name`, and `actor_organization_name` are all `NULL`; `basis` still
  states why, so "unknown" is a recorded fact, never a silent gap.

These four states answer exactly one question — *how is this actor identified* — and this ADR
deliberately keeps three other questions separate rather than conflating them into the same field,
each of which remains either free text or entirely unmodeled:

1. **Assertion source** (what this specific claim rests on) — carried by `basis`, free text, never
   collapsed into `actor_reference_kind`.
2. **Confidence** — not modeled at all. No numerical or ordinal confidence scalar exists on this
   table, deliberately, per this ADR's own instructions and per the same reasoning that already
   kept a `verified` boolean off `EvidenceRecord` (ADR-026).
3. **Professional verification** (has LandVault confirmed this person's registration, licence, or
   authority) — not modeled at all, for the identical reason. `INTERNAL_PRINCIPAL` means only "this
   row references a real `identity_users` row," never "LandVault has professionally verified this
   person" — those are unrelated facts a reader must not infer from one another.

### Immutable snapshot requirement — snapshot plus optional reference, never reference alone

Every attribution row that names an actor at all (every `actor_reference_kind` except `UNKNOWN`)
**must** capture `actor_name` (and, where applicable, `actor_organization_name`) as an immutable
snapshot at write time, independent of whether `actor_principal_id` is also set. `actor_principal_id`
is additional identity *precision*, layered on top of the snapshot when the actor happens to be a
known LandVault principal in the same tenant — it is never a substitute for the snapshot, and a
row must never rely on a live join to `identity_users` at read time to know who it names.

This matters concretely: if `actor_principal_id` were sufficient on its own, a later change to that
principal's name on the `User` aggregate (a legal name change, a correction of a typo, an account
merge) would silently and retroactively alter what a historical Evidence attribution *appeared* to
say, even though the attribution itself was never touched — a violation of the same historical-
integrity discipline Article VII §6 requires for Evidence generally. Requiring the snapshot
structurally, not merely by convention, closes this: `INTERNAL_PRINCIPAL` therefore means "an
immutable name snapshot, plus an optional, same-tenant, additional internal reference for
precision," never "resolve the name by following a live reference." Cross-tenant actors remain
snapshot-only, exactly as already decided in "Tenant isolation" below — no cross-tenant live
identity dereference is introduced by this requirement or by anything else in this ADR.

### Why not one-to-many via scalar columns, and why not a fully generic event log

See the decision table below. In short: scalar columns (Alternative A) cannot express multi-actor
or append-only correction without contortion, and were rejected first. A fully generic
provenance-event log (Alternative C) — an unbounded, schema-less predicate/object event stream —
was rejected as broader than the known requirement: it would let a caller assert *any* claim about
*any* subject, which is the shape a future Party/Rights/Marketplace event architecture might
eventually need, but Evidence's actual, present requirement is three named, bounded roles against
one aggregate. Building the general mechanism now, before a second concrete need for it exists,
is exactly the premature abstraction GD-008 and this ADR's own instructions warn against. The
normalized `EvidenceActorAttribution` relationship (Alternative B) is the smallest model that
satisfies every stated requirement using a pattern this Governance Authority has already reviewed
and accepted once (ADR-023), and is the one this ADR selects.

### Tenant isolation — attribution does not create authorization, and never crosses tenants live

Three rules, all mechanical, none merely conventional:

1. **`evidence_actor_attributions.tenant_id` is always copied from the attributed
   `EvidenceRecord.tenant_id` by the recording service, never accepted as caller input.** RLS on
   this table is identical in scope and strength to `evidence_records`' own policy (the same
   `parcels`-since-migration-0001 shape every tenant-scoped table in this codebase uses), plus the
   same independent application-layer tenant filter every prior context also applies —
   `EvidenceService`'s existing `_in_scope` check, unchanged.
2. **`actor_principal_id` may reference only a principal within the same tenant as the Evidence
   being attributed.** A real, registered surveyor who happens to belong to a *different* tenant —
   including any future Partner-accredited professional — is recorded through `actor_name`/
   `actor_organization_name` only, as a free-text snapshot, never through a live cross-tenant
   foreign key. This is the direct, structural answer to the risk this ADR was asked to consider by
   name: referencing another tenant's professional as an Evidence originator must not automatically
   expose that tenant's private information, and it does not, because no live reference to another
   tenant's `identity_users` row is ever created. Building a governed, live cross-tenant
   professional-reference mechanism (which a future, accredited Partner directory would plausibly
   want) is exactly the kind of Partner/Marketplace capability GD-008 does not authorize here, and
   is left entirely to whatever future ADR that capability requires.
3. **Attribution never grants authorization.** Being named as Originated By, Reviewed By, or
   Commissioned By on an `EvidenceRecord` — whether via `actor_principal_id` or free text — confers
   no read, write, or mutation right over that record, the parcel it evidences, or anything else.
   Every existing authorization path (`_in_scope`, `_can_mutate`, the PDP/PEP) is completely
   unchanged by this ADR; attribution is authenticated-write-time metadata about who this row
   *says* is involved, never an access grant.

### Append-only, corrections by superseding — reusing ADR-023's mechanism exactly, not a new one

`evidence_actor_attributions` is append-only, enforced identically to `parcel_ownership_history`/
`parcel_status_history`: `GRANT SELECT, INSERT` only (no `UPDATE`/`DELETE` grant) to the
application role, plus a `BEFORE UPDATE OR DELETE` trigger that unconditionally raises, regardless
of which role executes the statement. A mistaken attribution is corrected by inserting a new row
whose `supersedes_id` points at the row it corrects — the superseded row is retained, readable, and
never rewritten, exactly satisfying LV-000 v1.8 Article VII §6 ("corrections append"). This
distinguishes **correction** (a new, better-informed claim, both rows kept) from **deletion**
(erasing a historical provenance claim entirely), which this table structurally cannot do — no
`DELETE` path exists, matching every other append-only table in this codebase without exception.

**Supersession integrity — three invariants a future implementation must enforce, and one explicit
governance choice made now:**

1. **No self-supersession.** A row's `supersedes_id` must never equal its own `id`. ADR-023's own
   precedent never states this explicitly either (checked directly against
   `docs/adr/ADR-023-registry-ownership-and-status-history.md`), but its absence there is not a
   reason to leave it unstated here — a future migration must add a `CHECK (id <> supersedes_id)`
   constraint (or equivalent), not rely on application code alone, matching this codebase's
   consistent two-layer-enforcement habit.
2. **No cycles.** `supersedes_id` must reference a row with a strictly earlier `recorded_at` than
   the referencing row's own. Because rows are append-only and `recorded_at` is server-assigned at
   insert time, a correction can only ever point backward in time, which makes a cycle
   (A supersedes B supersedes A) structurally impossible **provided** this ordering rule is
   enforced; a future implementation must not skip enforcing it merely because the append-only
   property alone feels sufficient.
3. **One direct successor per superseded attribution — the explicit governance choice.** At most
   one row may supersede any given attribution row. If two independent corrections to the same
   attribution are proposed, the second correction must supersede the *currently active* row in
   that attribution's lineage (i.e., the most recent, not-yet-superseded row), not the original —
   producing one linear correction history per attribution, never a fork with two simultaneously
   "active" corrections of the same original claim. This is chosen over allowing forks because a
   fork would leave "what does this Evidence record currently say about its originator" ambiguous
   without an additional rule to resolve it, and this ADR would rather decide that now, plainly,
   than defer an ambiguity into implementation. A future implementation must enforce this (e.g. a
   partial unique index or trigger ensuring no row is referenced by `supersedes_id` more than
   once), not merely document it as an intended usage pattern.

### Origination provenance — creation, not entitlement

An `ORIGINATED_BY` row records that a named actor is understood to have created the underlying
evidence — nothing more. **`ORIGINATED_BY` does not mean or establish:** legal ownership of the
land the evidence concerns; ownership of the evidence document itself; copyright ownership;
licensing authority over the evidence; a beneficial interest of any kind; a legal interest in the
parcel; that the named actor's professional licence (if any) has been verified by LandVault; or
that the evidence is correct, complete, or legally authoritative. A licensed surveyor named as
originator of a survey plan is recorded as having (asserted to have) drawn it — nothing about who
owns the land it depicts, who owns the plan as a document, or whether the plan is right, follows
from that alone. **A professional attribution — on any of the three roles this ADR defines — does
not make the underlying Evidence legally authoritative merely because a named professional is
attached to it.** This is the same non-adjudication doctrine (Article IV) `EvidenceRecord` itself
already applies to `status`/`worm_grade` (ADR-026), extended here to the actor who is said to have
created it.

### Professional review — a recorded event, not an endorsement

A `REVIEWED_BY` row records that a named professional actor performed a review, when, and by what
`review_method` (free text — e.g. "desk review against the uploaded scan," "field re-inspection") —
nothing more. It does not change `EvidenceRecord.status`, does not imply the reviewer certifies the
evidence's authenticity or legal validity, and does not imply the reviewer has any authority over
the parcel. Multiple `REVIEWED_BY` rows may exist for one `EvidenceRecord`, from different
reviewers, at different times; each is independent, and none supersedes another unless explicitly
recorded as a correction (`supersedes_id`) rather than an additional review. Whether review method,
confidence, or outcome should later feed a professional-QA workflow is explicitly deferred — that
is a future, separate decision (and, per GD-008, one that must not become a scoring shortcut; see
"Red-team" below).

### Commissioning provenance — who asked, not who benefits

A `COMMISSIONED_BY` row records that a named actor instructed or commissioned the evidence's
creation, where known. It carries no implication of customer status, payment obligation, rights
ownership, beneficiary status, landownership, or Marketplace-client status — each of those, if ever
modeled, is its own future concept potentially referencing this attribution, never assumed by it.
An `EvidenceRecord` with no `COMMISSIONED_BY` row is exactly as valid as one with several; this ADR
does not make commissioning provenance mandatory.

### Worked example — four independent facts, none implying the others

A current LandVault user, User A, uploads a 1998 survey plan today. The plan was originally drawn
by a different, unregistered surveyor, Surveyor B, was commissioned at the time by a landowner's
organisation, Client C, and has since been reviewed once by a currently licensed professional,
Professional D. This ADR represents all four as independent facts, none implying any other:

| Fact | Where recorded | Implies |
|---|---|---|
| User A submitted the bytes today | `EvidenceRecord.uploaded_by` (unchanged, ADR-026) | Nothing about creation, commissioning, or review |
| Surveyor B drew the plan in 1998 | one `ORIGINATED_BY` row, `actor_reference_kind = HISTORICAL_ASSERTED` (Surveyor B has no LandVault account), `actor_name` = Surveyor B's name as it appears on the plan, `basis` = "named in the plan's own title block; not independently confirmed" | Nothing about ownership, rights, or licence verification (see "Origination provenance" above) |
| Client C commissioned the original survey | one `COMMISSIONED_BY` row, `actor_reference_kind = HISTORICAL_ASSERTED` or `EXTERNAL_NAMED` depending on how the commissioning fact is known, `actor_organization_name` = Client C | Nothing about customer status, payment, beneficiary status, or rights (see "Commissioning provenance" above) |
| Professional D reviewed it later | one `REVIEWED_BY` row, `actor_reference_kind = INTERNAL_PRINCIPAL` if D is a LandVault principal in the same tenant (with `actor_principal_id` set and `actor_name` still snapshotted per "Immutable snapshot requirement" above), `review_method` describing what D did | Nothing about certification, legal validity, or authority over the parcel (see "Professional review" above) |

None of the four rows/fields implies Rights Holder status, ownership, payer status, beneficiary
status, or title-certifier status for any of the four people involved. Each is exactly what it
says and nothing more — the direct, worked demonstration of this ADR's own non-implication rules
above, not a new rule in itself.

### Future attribution roles — an explicit non-decision

`attribution_role`'s enum may one day gain members for Rights Holder, Licensor, Custodian, Job
participant, or Assignment participant, exactly as `EVIDENCE_TYPES` gained members additively per
ADR-026. **This ADR explicitly does not decide any of those roles' semantics, and flags — unlike a
new `EVIDENCE_TYPES` member — that some future roles (Rights Holder and Licensor in particular)
carry legal/commercial weight this ADR's three roles deliberately do not, and should not be added
as a routine additive change without their own governance review**, even though the column
mechanically supports it. This is a documentation and future-governance-process flag, not a
technical control, and it is recorded here because GD-008 specifically asked this ADR to
distinguish these future concepts rather than silently leave the door open to collapsing them into
the same mechanism without a second look.

## Alternatives considered

### Alternative A — direct scalar references on `EvidenceRecord`

Add `originated_by`, `reviewed_by`, `commissioned_by` columns directly to `evidence_records`,
mirroring `uploaded_by`'s existing shape.

- **For:** simplest possible schema change; no new table; trivially matches existing `uploaded_by`
  precedent for the single-actor case.
- **Against:** cannot express multiple originators or multiple reviewers without either serialising
  a list (defeats queryability, defeats the append-only audit discipline entirely) or adding
  unboundedly many numbered columns. Cannot express a correction without mutating a sealed-adjacent
  field on the aggregate itself (`EvidenceRecord`'s own invariant #4 already forbids most
  post-`SEALED` field changes; retrofitting a mutable actor field onto the aggregate root would
  either violate that invariant's spirit or require yet another aggregate-level exception).
  Provides no natural place for `basis`, `review_method`, or `recorded_by` per claim — either those
  become three more sets of columns, or are lost entirely. **Rejected.**

### Alternative B — normalized `EvidenceActorAttribution` relationship (selected)

The design decided above: a separate, append-only table, one row per attribution claim, reusing
ADR-023's exact append-only/correction mechanism.

- **For:** supports one-to-many and many-to-many attribution natively (multiple rows); supports
  historical/external/unknown actors via free-text snapshot fields, the same idiom
  `current_owner_name` already uses; supports correction without deletion or aggregate mutation;
  keeps `EvidenceRecord` itself completely unchanged (zero new fields, zero invariant changes);
  tenant isolation is enforced by the same RLS shape every table in this codebase already uses,
  plus one explicit new rule (same-tenant-only live actor reference) that is easy to state and
  easy to review; reuses a mechanism this Governance Authority has already accepted once, so the
  review burden is "does this reuse apply correctly," not "is this novel mechanism sound."
- **Against:** one new table, one new migration, one new repository port — more moving parts than
  Alternative A for the common single-originator case. Requires an explicit invariant (same-tenant
  actor reference) that does not enforce itself without a deliberate check in the recording
  service and, ideally, a database-level constraint at implementation time.
- **Selected** as the smallest model that satisfies every stated requirement without premature
  generality.

### Alternative C — general provenance-event log

A schema-less or near-schema-less append-only event stream recording arbitrary provenance claims
(subject, predicate, object, basis, recorded_by, recorded_at), of which `ORIGINATED_BY`/
`REVIEWED_BY`/`COMMISSIONED_BY` on `EvidenceRecord` would be three special cases among arbitrarily
many possible future ones.

- **For:** maximally future-proof; a single mechanism could eventually serve Rights, Marketplace,
  Job/Assignment provenance, and anything else, without a new table per future concept.
- **Against:** this is precisely the premature abstraction this ADR's own instructions warn
  against — Evidence's actual, present requirement is three named, bounded roles against one
  aggregate, not an open-ended claims graph. A schema-less design is harder to enforce invariants
  against (what makes a claim valid becomes an application-code concern instead of a database
  constraint), harder to review for constitutional compliance (a generic "claim" object hides
  exactly the kind of ownership-adjudication risk this platform's non-adjudication check is built
  to catch in named fields, not free-form predicates), and would require inventing the general
  mechanism's own governance (who may write which predicates, against which subjects) as a
  side effect of an ADR whose charter is Evidence provenance specifically. **Rejected** — if a
  second, unrelated bounded context later needs the same general shape, that observation is the
  trigger to design the general mechanism then, with two real cases informing it, not now with one.

### Decision table

| Dimension | A — Scalar columns | B — Attribution table (selected) | C — Generic event log |
|---|---|---|---|
| Auditability | Weak — no per-claim basis/recorded_by without more columns | Strong — one row per claim, full metadata | Strong in principle, weak in practice (schema doesn't constrain what "valid" means) |
| Historical evidence | Poor — one scalar can't hold "unknown, and here's why" alongside a real name | Good — `actor_reference_kind` (`HISTORICAL_ASSERTED`/`UNKNOWN`) + mandatory `basis` | Good, but via a generic mechanism harder to review |
| Multi-originator | Not supported without contortion | Native — multiple rows | Native — multiple events |
| Actor types (individual/org/external/unknown) | Cramped into one column, no room for org name separately | Explicit columns, mirrors `current_owner_name` precedent | Supported, but type-checking pushed into application code |
| Tenant isolation | Same RLS as `evidence_records`, no new cross-tenant risk surface | Same RLS + one explicit same-tenant-FK rule, clearly reviewable | Same risk exists but harder to spot in a generic subject/object shape |
| Migration complexity | Lowest — column additions only | Moderate — one new table, one new repository port | Highest — a new general-purpose subsystem |
| Future Rights/Marketplace compatibility | Poor — would need redesign | Good — new roles are additive enum members (with a governance flag on weightier ones) | Best in theory, but "compatible with everything" is also "decided nothing specific" |
| Domain clarity | Muddies `EvidenceRecord` with actor-list logic it wasn't designed for | Clear — Evidence still owns one row per document; attribution is its own concern | Blurs Evidence's bounded-context edges into a general claims mechanism |
| Constitutional risk | Moderate — cramped columns invite ad hoc semantics later | Low — every field is bounded and named | Moderate-high — a generic "claim" is easy to misuse for exactly the adjudication risk Article IV guards against |

## Red-team

- **False originator attribution** (uploader names the wrong person/organisation as originator,
  in error or deliberately). Mitigated structurally, not prevented: `basis` is mandatory and
  records what the claim rests on, `recorded_by` always identifies who actually made the claim
  (distinct from the actor named), and the append-only/`supersedes_id` mechanism means a later
  correction is itself a recorded, auditable event rather than a silent overwrite. This ADR cannot
  and does not claim to prevent a false claim from being made in the first place — no automated
  identity-truth mechanism exists on this platform for any actor reference, exactly as ADR-023
  already accepted for `current_owner_name`.
- **Impersonation** (someone falsely claims to be, or falsely names another authenticated user as,
  an originator/reviewer). `actor_principal_id`, when set, references a real `identity_users` row,
  but the row's mere existence is not proof that person consented to being named — this ADR
  records an assertion, not a confirmation. A future "actor acknowledgement" or dispute mechanism,
  if ever needed, is out of scope here.
- **Cross-tenant information leakage.** Addressed structurally above ("Tenant isolation"): no live
  `actor_principal_id` reference may cross a tenant boundary; a cross-tenant actor is recorded only
  as a free-text snapshot, which carries no queryable link back to that tenant's `identity_users`
  row, roles, or any other private data.
- **Retrospective rewriting of provenance.** Structurally prevented for recorded rows: no `UPDATE`/
  `DELETE` path exists (privilege layer plus trigger layer, per ADR-023's mechanism). A correction
  is always a new, additional, auditable row.
- **Uploader falsely claiming authorship** (naming themselves as Originated By when they did not
  create the evidence). Same mitigation as false attribution generally — `basis` and audit trail
  make the claim reviewable after the fact, but do not prevent it from being made.
- **Reviewer mistaken for legal certifier.** Addressed by explicit design constraint above: a
  `REVIEWED_BY` row is defined here as a recorded review event, never a certification, and this ADR
  requires that any future API/UI presentation preserve that distinction — carried forward as a
  requirement on later implementation work, not resolved by this document alone (this ADR does not
  design the API).
- **Commissioner mistaken for owner.** Same pattern — explicitly enumerated in "Commissioning
  provenance" above as a non-implication, carried forward as a requirement on later presentation
  work.
- **Unknown historical actor handling.** Explicitly supported: `actor_reference_kind = UNKNOWN`
  (with `actor_type` also `UNKNOWN` where even the kind of actor cannot be determined) and
  `actor_principal_id`/`actor_name`/`actor_organization_name` all `NULL`, with a mandatory `basis`
  explaining why the actor is unknown rather than silently omitted or fabricated.
- **Duplicate identities** (the same real-world person recorded under two different `actor_name`
  spellings/free-text variants across different `EvidenceRecord`s, or a person later registering as
  a LandVault user distinct from an earlier free-text mention of them). Not resolved by this ADR —
  free-text actor snapshots are not deduplicated or reconciled against `identity_users` or against
  each other. A future identity-reconciliation or Party-directory capability, if ever built, would
  address this; this ADR neither builds nor blocks it, and explicitly does not treat two free-text
  mentions of a plausibly-same person as automatically the same actor.
- **Provenance used later as a scoring shortcut** (e.g. treating "has an Originated-By attribution"
  or "was Reviewed-By a senior professional" as an input to a future trust/performance score).
  GD-008 §1 already forbids rewarding professionals for a preferred *ownership* conclusion; this ADR
  extends the same caution structurally by recording attribution with no `verified`/`confidence`
  scalar a future scoring mechanism could cheaply consume as a proxy for truth. Any future scoring
  or Professional Performance Index design (explicitly not authorized here or by GD-008) would have
  to build its own evidentiary basis rather than reading a shortcut off this table — noted here as
  a design property, not a technical lock this ADR can itself enforce against a future, differently
  authorized change.

## Implementation consequences (future work — not authorized here)

Everything below describes what a **later, separately authorized** implementation phase would
likely need to build. None of it is created, modified, or scaffolded by this ADR.

- **Domain:** a new `EvidenceActorAttribution` value object/entity
  (`app.contexts.evidence.domain`), likely immutable-by-construction (no mutator methods at all,
  since correction is always a new row, never an in-place change) — structurally simpler than
  `EvidenceRecord` itself, which does have guarded mutators.
- **Persistence:** a new migration (the next available number at implementation time — `0014` as
  of this drafting, to be re-verified against `main` when that slice actually begins, since other
  work may claim it first) adding `evidence_actor_attributions`, its RLS policy (in the same
  migration, per Article VIII §2), its append-only privilege grant, its `BEFORE UPDATE OR DELETE`
  trigger mirroring migration `0011`'s two triggers exactly, and the "Supersession integrity"
  constraints decided above: `CHECK (id <> supersedes_id)`, an ordering check or trigger that
  rejects a `supersedes_id` pointing at a same-or-later `recorded_at` row, and a partial unique
  index (or equivalent trigger) on `supersedes_id` ensuring no row is ever superseded twice.
- **Application service:** an `EvidenceActorAttributionRepository` port (`add`, `get`,
  `list_for_evidence`, `supersede` — no generic update/delete, mirroring `EvidenceRepository`'s own
  narrow shape) and application-service methods to record and correct attributions, each enforcing
  the same-tenant-actor-reference rule explicitly (and, ideally, backed by a database-level
  constraint verified against `evidence_records.tenant_id` at implementation time, not left to
  application code alone — mirroring this codebase's consistent two-layer-enforcement habit).
- **Authorization:** who may record which attribution role is a role-gating decision this ADR
  explicitly defers, exactly as ADR-026 deferred Evidence's own upload authorization to a later,
  separate decision (which IMVP-5 then made by extension, not invention). Not decided here.
- **Audit:** new action names (e.g. `evidence.actor_attribution.recorded`,
  `evidence.actor_attribution.corrected`), reusing the existing kernel `audit()` function unchanged
  — no new audit mechanism, matching every prior ADR without exception.
- **API contract:** whether and how attribution rows are exposed in any response — including
  whether personal data (`actor_name`, `actor_organization_name`) requires its own disclosure
  authorization separate from Evidence's own read authorization — is not decided here, mirroring
  ADR-026's own deferral of Evidence's API shape entirely.
- **Tests:** unit coverage of the domain invariants above, plus a live rehearsal of the append-only/
  trigger enforcement and RLS/tenant-isolation behavior, following this codebase's established
  "never mark complete without having observed it pass against real infrastructure" discipline
  (`docs/ENGINEERING_RULES.md` rule 7) — not performed by this ADR.

## Out of scope (carried forward from GD-008, verbatim in effect)

This ADR does not design, authorize, or take any step toward: Marketplace architecture; Partner
programme implementation; Job or Assignment domain modeling; accreditation/profile tables; payments,
payouts, or escrow; SECI, EQF, or Professional Performance Index scoring; Rights or licensing
schema; Legacy Vault; royalties; historical Evidence monetisation; the Surveyor Dashboard; or
ADR-021/B4 Slice 3 implementation. Rights Holder, Licensor, Custodian, Job-participant, and
Assignment-participant concepts are named above only to be distinguished from what this ADR does
decide — none of their semantics, schema, or authorization model is decided here.

## Relationship to the frozen baseline

- **ADR-026** — extended, not amended. `EvidenceRecord`'s existing fields, invariants, and
  lifecycle are completely unchanged; `uploaded_by`'s meaning is unchanged. This ADR adds one new,
  separate table referencing `EvidenceRecord.evidence_id`, the same additive relationship ADR-023
  established between its history tables and `Parcel` without amending ADR-013. No existing
  ADR-026 text requires correction or restatement.
- **ADR-023** — its append-only/correction/RLS **mechanism** is reused by name and by shape, not
  redecided; this ADR treats that mechanism as already-proven precedent. **Its meaning is not
  reused, and the two must not be conflated:** `parcel_ownership_history` records assertions
  concerning land-ownership history — the core subject Article IV's non-adjudication doctrine
  exists to guard. `evidence_actor_attributions` records assertions concerning who originated,
  reviewed, or commissioned a piece of Evidence — a different subject entirely. **Correcting an
  Evidence actor attribution therefore never corrects, modifies, settles, or implies anything
  about any land-ownership assertion**, and superseding a `parcel_ownership_history` row never
  requires, triggers, or is triggered by a correction here. The two tables share a historical-
  integrity mechanism; they do not share a constitutional meaning, and this ADR's reuse of ADR-023
  is a reuse of engineering discipline, not of subject matter.
- **ADR-010** — `Tenant`'s aggregate and existing tenant-isolation architecture are unchanged; no
  new tenant subtype is introduced, consistent with GD-008 §3's tenant principle.
- **ADR-004** — no new authorization mechanism; attribution recording composes from the existing
  PDP/PEP exactly as every prior context's role-gating decision has.
- **GD-008** — this ADR is the one piece of technical work GD-008 §1 authorizes; it stays inside
  that authorization by deciding Evidence actor/commissioning provenance only, and by explicitly
  not deciding any of the excluded programmes listed above.
- **No frozen decision requires amendment.**

## Consequences

- A future, separately authorized implementation slice has a reviewed, accepted domain model to
  build `EvidenceActorAttribution` against, exactly as ADR-026 gave B5.2 a reviewed model for
  `EvidenceRecord` itself.
- Historical evidence (originator differing from uploader, by identity and by years) becomes
  representable without fabricating identity and without treating "unknown" as a data-quality
  defect rather than a legitimate, recordable state.
- Multi-actor origination and multiple successive professional reviews become representable
  without contorting `EvidenceRecord`'s own schema or violating its post-`SEALED` immutability
  invariant.
- Cross-tenant professional/organisation referencing remains explicitly ungoverned pending its own,
  future, separately gated ADR — this ADR does not authorize it, by omission or implication,
  mirroring how ADR-026 left the break-glass cross-tenant mechanism explicitly ungoverned pending
  its own ADR.
- No ownership-adjudication capability is introduced: attribution records who is asserted to be
  involved in creating, reviewing, or commissioning evidence, never who owns, or is legally
  entitled to, anything.

## Approval Gate

This ADR is **ACCEPTED**, per the Ratification Record above. Acceptance authorizes only the
domain model, migration shape, and repository port described above (the same category of
authorization ADR-026 gave B5.2 for `EvidenceRecord` itself) — never the
Marketplace/Partner/Job/scoring/Rights capabilities this ADR and GD-008 both explicitly exclude.

**Explicit exclusions.** Acceptance of this ADR does not authorize implementation of: this ADR's
own database tables or migrations; ORM/domain code; API endpoints; frontend functionality;
Marketplace; the Partner programme; Customer; Job; Assignment; accreditation; professional
profiles; payments; payouts; SECI; EQF; Professional Performance Index; Rights/licensing; Legacy
Vault; royalties; historical Evidence monetisation; or ADR-021 functionality. Implementation of
this ADR's own domain model, migration, and repository — exactly as much as ADR-026 gave B5.2, no
more — requires its own, separate Governance authorization before any code, migration, or ORM
model is written, exactly as every prior ADR in this codebase has required.

**External/legal boundary.** This ADR is accepted without first resolving future Nigerian
questions regarding professional registration, copyright, expert evidence, licensing, or
commercial rights, because it records only bounded provenance assertions and grants none of those
statuses. Those external matters remain mandatory gates before any future capability makes a
corresponding professional, legal, or commercial claim — they are not resolved, and are not
required to be resolved, by this ADR's acceptance.
