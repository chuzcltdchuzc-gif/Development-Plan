# Session Log — B4 Slice 2 Review through the LandVault Bible Programme

**Type: historical record only. This is not a governance document, not an ADR, not part of the
Constitution, and not part of the Bible volume numbering.** It is a plain narrative account of one
Claude Code conversation, kept so a future reader has context on *why* certain documents were
produced and in what order — never as evidence of what any document currently says. If anything
below conflicts with the actual, current content of `docs/LV-000-constitution.md`,
`docs/ARCHITECTURE_HANDBOOK.md`, any ADR, or any other governing document, **those documents are
correct and this log is simply out of date.** This log is not updated retroactively when those
documents change after the fact; it records what happened at the time, not what is current now.

**Scope note:** this log covers only the conversation it was written from. Substantial additional
work has landed in this repository's git history — a Governance Baseline, an execution plan, an
LV-000 revision to "Edition v1.8, Working Edition, Revision H," a Bible numbering scheme (LV-001
through LV-017), and ADR-023 through ADR-025 among other changes — that did **not** happen in this
conversation and is not narrated here. That work should be understood from its own commits and its
own documents, not from this log. Where this log's own output (e.g., the original LV-000 v1.0 draft
described below) was later superseded or consolidated by that other work, this log still describes
only what happened *in this conversation*, at the time it happened.

**Date range covered:** 2026-07-23 through 2026-07-29.

---

## How this conversation started

The conversation picked up mid-stream on the B4 programme (Spatial Intelligence), continuing work
from an earlier session that was summarized before this one began. At that point: B1, B2, and B3
were already complete and frozen; B4 Slice 1 (Spatial Domain Foundation) was built; ADR-018
(Spatial Domain Model) and ADR-019 (GeometryPort Interface Amendment) were accepted; and B4 Slice 2
(Geometry Validation & Real Geometry Adapter) was mid-implementation, with the very next step being
a broken import (`InvalidGeometryError`) left over from moving code between modules.

## 1. Finishing B4 Slice 2

The immediate work was mechanical: fixing the broken import in `spatial_service.py` and
`test_b4_spatial.py`, then continuing Slice 2's actual scope — extending `ParcelExistencePort` to
return tenant/creator/status in one round trip, building `RealGeometryAdapter` (the first real
`GeometryPort` implementation), implementing ADR-022's creator-or-governance authorization model in
`SpatialService`, and fixing an ordering bug from Slice 1 (the old geometry was being superseded
*before* the new one was validated, which could have stranded a parcel with no active geometry on a
validation failure).

Two real defects surfaced during this work, not before:

- Two Slice 1 test fixtures (`VALID_POLYGON`, `OTHER_POLYGON`) turned out to be wound clockwise —
  invisible under Slice 1's placeholder regex validator, but caught immediately once Slice 2's real
  structural validator (ring closure, point count, coordinate bounds, OGC winding order) started
  enforcing it. Fixed by re-winding both fixtures counter-clockwise.
- A pre-existing `docker-compose.yml` gap: the backend service's environment block overrode
  `DATABASE_URL` for container-to-container networking but never overrode the three Keycloak URLs,
  which leaked `.env`'s host-oriented `localhost` values straight through — meaning the
  containerized backend could never actually reach Keycloak. This had been flagged, unfixed, since
  B3. It blocked this slice's own live-verification requirement, so it was fixed as part of this
  work rather than deferred again.

Live verification was run against real Postgres, real Keycloak, and RLS enforced as the actual
least-privilege `landvault_app` role (not the schema-owning superuser, which bypasses RLS
regardless of policy correctness) — covering all four authorization tiers, the archived-parcel
block, cross-tenant 404s, malformed/mis-wound geometry rejection, the real Registry↔Spatial
`GeometryPort` seam, and audit-chain integrity. 148/148 tests passed; `ruff`/`mypy` were clean.

## 2. Governance review and ADR-021

A governance-review message then accepted Slice 2 outright, declared its architecture frozen under
ADR-022, and authorized drafting — architecture only, no implementation — of ADR-021: Spatial
Conflict Detection & Controlled Cross-Tenant Intelligence, the doctrine required before any future
overlap/duplicate-geometry detection work could begin. That ADR was written to resolve the threat
model's own outstanding requirements (TB5): which single component may perform a cross-tenant
geometry read, a six-category conflict classification model, a minimal-disclosure default for
ordinary registrants versus a narrowly-extended governance-role exception, and full audit
requirements. It was left in **Proposed** status — not accepted — with B4 Slice 3 explicitly not
authorized to begin.

## 3. The pre-Slice-3 governance package

A follow-up directive asked for a full architectural review of ADR-021 against every frozen and
accepted prior decision, plus a set of supporting artefacts, all still architecture-only:

- A review confirming no contradiction between ADR-021 and any frozen B1–B3 decision or accepted
  B4 ADR, with one item (the exact RLS-bypass mechanism) noted as correctly deferred to a
  specification document rather than a defect in the ADR itself.
- **SCDS-001** — an engineering specification beneath ADR-021 (not itself an ADR): a conflict
  taxonomy, a severity scale, risk-scoring extension points left deliberately unspecified, a
  disclosure matrix by participant tier, and a refined description of the Controlled Platform
  Authority mechanism's required shape.
- **Platform Intelligence**, named for the first time as a cross-cutting services layer — never a
  bounded context — with a four-part test for what belongs under it.
- An extension to the Marketplace planning document naming candidate domain concepts (Job,
  Assignment, Escrow, Wallet, Rating, Dispute, and others) as open questions, not a domain model.
- A first constitutional recommendation, logged rather than adopted, since no constitutional
  document existed yet at that point in the conversation.

## 4. The Architecture Handbook

A separate request then asked for a single consolidated engineering reference — the Architecture
Handbook — explaining how everything accepted so far related to everything else, without deciding
anything new or duplicating any ADR's own text. It was built with ten parts (Platform Philosophy
through Engineering Culture) plus a cross-reference appendix and a set of explicit triggers for
when the Handbook itself should be revised. Every part pointed back to the document that actually
governed the subject, rather than restating it.

## 5. The Enterprise Programme Transition

The next directive reframed the work from an engineering-led project to a platform-strategy-led
one, describing a governing hierarchy (Constitution → Handbook → Platform Strategy → Business
Strategy → Programme Documents → Engineering) and asking for a Platform Strategy document plus a
set of future-programme planning documents — all explicitly planning-only, none authorizing any
implementation:

- **Platform Strategy** — vision, the official positioning statement, a five-layer platform model,
  the "surveyors are partners, not users" framing, and network-effects reasoning.
- Eight further planning documents: Partner, Enterprise, Government, and Developer Platform
  programme strategies; Commercial Architecture; Operating Model; Trust Framework; and Network
  Growth Strategy — each ending in its own explicit approval gate.
- A second constitutional recommendation ("LandVault is a Trust Platform before it is a Software
  Platform"), again logged rather than adopted, since the Constitution still did not exist yet at
  this point in the conversation.

## 6. LV-000 — the first drafted Constitution

The next request asked for LV-000, the LandVault Constitution, to be authored for the first time:
a Preamble and 22 Articles covering vision, mission, an order of precedence, the ten constitutional
principles named across the conversation so far, and governance across platform, architecture,
documentation, and programme concerns, plus security, trust, identity, data, evidence, marketplace,
government, enterprise, and innovation principles, an amendment process, definitions, and a
cross-reference index. It incorporated both previously-logged constitutional recommendations by
name and citation, modified no accepted ADR, and created no bounded context. This is the version
later preserved in this repository as `docs/LV-000-constitution-v1.0-adopted.md` once a later
revision (outside this conversation, see the scope note above) consolidated it with a second,
separately-authored lineage.

## 7. The LandVault Bible, Volumes I and II, and LV-013

Two further requests asked for executive-facing documents explaining the platform to external
audiences — governments, investors, banks, enterprise clients — building on everything already
established:

- **Volume I — Executive Overview**: a 15–25 page narrative explaining what LandVault is, why it
  exists, and how it is governed, deliberately declining the "Uber for Land Verification"
  marketplace comparison in favor of a trust-infrastructure framing.
- **Volume II — Product Strategy & Enterprise Definition**: a deeper expansion covering market
  analysis, product philosophy, the five-layer model in full, the Trust Network as an
  eleven-participant framework, Marketplace as enterprise strategy, the full commercial model,
  competitive positioning, and a long-term roadmap. Its market-analysis section was deliberately
  written without inventing statistics — general, qualitative, hedged characterization only, with
  an explicit note that real figures would need dedicated primary research.

The following request pushed further: a genuine, evidence-based market intelligence report, not a
hedged narrative. That became **LV-013 — Market Intelligence Report**, built from real web research
performed during the conversation (not from prior training alone), with every figure tagged as
verified with a cited source, an explicitly labeled estimate, or flagged as requiring future
primary research. Concrete, sourced findings included Nigeria's National Land Digital System
(signed with the World Bank in September 2024), a widely repeated figure that roughly 65% of
Nigerian civil court cases are land-related, population and remittance data, and seven international
benchmarks (Rwanda, Estonia, the UK, Singapore, India, Kenya, and Brazil). Where sources conflicted
— Nigeria's housing deficit was reported at four different figures across four sources — all four
were reported side by side rather than resolved into one invented number. The report's own market-
sizing section (Part IX) explicitly declined to produce a TAM/SAM/SOM figure without a defensible
input, naming that refusal as the report's own most important finding.

## What this log is for

This document exists so that a future reader — human or another Claude Code session — can
understand *why* the Architecture Handbook, the original LV-000 draft, the Bible volumes, and
LV-013 exist and in what sequence, without needing the full conversation transcript. It is
deliberately kept separate from the governance hierarchy: it is never cited by an ADR, by
`docs/ARCHITECTURE_HANDBOOK.md`'s own cross-reference appendix, or by LV-000 itself, and it carries
no authority over any of them. If this log and a governing document ever disagree about what a
document currently says, the governing document is right.
