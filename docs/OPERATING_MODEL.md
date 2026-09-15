# Operating Model — Planning Recommendation

**Type:** Planning recommendation only. **No code, migration, API, bounded context, or ADR is
introduced by this document.** Documents the human/organizational functions this platform will
need as it scales beyond an engineering-only team — this is an organizational, not architectural,
planning exercise, though it references the architecture each function would operate against.

**Date:** 2026-07-25

**Governed by:** `docs/PLATFORM_STRATEGY.md` (the five-layer model and multi-sided platform this
operating model exists to run), `docs/PARTNER_PROGRAMME_STRATEGY.md` (Partner Operations' primary
subject), `docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md` (Fraud Operations' likely technical
counterpart, the future Fraud Engine), `docs/ENGINEERING_RULES.md` (Engineering's own operating
discipline, already established and unchanged by this document).

## Why an operating model matters at this stage

A platform with real partners, real transactions, and real institutional counterparties needs
people, not only code, to run it — accreditation review, dispute mediation, fraud investigation,
and government relations are not capabilities a codebase alone provides, no matter how well
architected. Naming these functions now, before any of Marketplace/Partner/Enterprise/Government
is authorized to begin, ensures each future programme's own discovery considers "who operates
this" alongside "what does the software do" — a gap this document exists to prevent, not an
organizational chart this document is authorized to actually staff.

## Candidate functions

- **Platform Operations** — day-to-day platform health: uptime, incident response, the existing
  engineering on-call/observability discipline (`docs/PHASE_GATES.md` Phase 9–11) extended to a
  team responsible for it beyond whoever is currently writing code.
- **Partner Operations** — the human side of `docs/PARTNER_PROGRAMME_STRATEGY.md`'s onboarding,
  accreditation review, and performance management — verifying credentials that a purely automated
  check cannot (e.g., confirming a licence document is genuine, not merely well-formed).
- **Fraud Operations** — investigating findings the future Fraud Engine
  (`docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md`) or Spatial Conflict Detection (ADR-021, proposed)
  surface — per those documents' own doctrine, an automated system produces a *finding*, never a
  fraud *determination*; Fraud Operations is the human function that makes that determination,
  named here for the first time as this platform's own answer to "who reviews a Confirmed
  Conflict" (`docs/adr/ADR-021-...md` §4).
- **Trust & Safety** — the broader function Fraud Operations sits within — dispute mediation
  (Marketplace's candidate Dispute concept), suspension decisions (Partner Programme), and the
  human judgment calls this platform's own fail-safe-scoring discipline
  (`docs/ENGINEERING_RULES.md` rule 3) deliberately defers to a human rather than an automated
  score.
- **Compliance** — the organizational function behind every "Compliance" reference scattered
  across this planning package (`docs/ENTERPRISE_PROGRAMME_STRATEGY.md`,
  `docs/GOVERNMENT_PROGRAMME_STRATEGY.md`, `docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md`'s
  Compliance Engine) — this document names Compliance once, as an operating function, rather than
  letting each programme document independently gesture at an undefined "compliance" concern.
- **Engineering** — this platform's existing function, unchanged — named here only to place it
  correctly alongside the newly-named functions above, per this document's own opening
  observation that engineering no longer leads the platform's evolution alone
  (`docs/PLATFORM_STRATEGY.md`'s "Strategic transition" section).
- **Customer Success** — the function supporting ordinary registrants and citizens (the Customer
  Portal, `docs/PLATFORM_STRATEGY.md`) through onboarding and ordinary use, distinct from Partner
  Operations' professional-relationship focus.
- **Marketplace Operations** — day-to-day marketplace health once Marketplace exists — match
  quality, dispute volume, SLA adherence trends — the operational counterpart to
  `docs/MARKETPLACE_DISCOVERY_AND_PLANNING.md`'s eventual domain model.
- **Government Relations** — the human/institutional relationship-management function underlying
  `docs/GOVERNMENT_PROGRAMME_STRATEGY.md`'s technical integration work — a Surveyor-General
  integration is as much a relationship to maintain as an API to build.
- **Legal** — contract, regulatory, and dispute-adjacent legal function; a prerequisite this
  document names for Escrow, digital certificates, and any government integration, each of which
  this planning package has already flagged as having legal dimensions beyond pure architecture
  (e.g., `docs/adr/ADR-021-...md`'s own Risks section: "no stakeholder/legal input has been sought
  on the minimal-disclosure default").
- **Finance** — the organizational counterpart to `docs/COMMERCIAL_ARCHITECTURE.md`'s revenue
  lines — billing operations, revenue recognition, and the actual pricing decisions that document
  explicitly declined to make.

## Relationship between functions and this platform's architecture

Every operating function above is expected to interact with the platform primarily through
existing or future governance roles (`GOVERNANCE_ROLES`, delegation, `docs/adr/ADR-011-...md`) —
this document does not propose a new authorization mechanism for staff, only names that staff
performing these functions will need *some* role-based access, designed per-function by whichever
future ADR governs the capability they operate (e.g., Fraud Operations' access to a Confirmed
Conflict finding is governed by `docs/adr/ADR-021-...md` §3's governance-tier disclosure rules,
not a new access model this document invents).

## Approval Gate

No Operating Model function has been staffed or formally established by this document. It names
candidate functions and their relationship to this planning package's other documents, for
organizational planning purposes; it does not decide headcount, reporting structure, or hiring
sequence. **Waiting for explicit direction before any Operating Model function is formally
established.**
