# Network Growth Strategy — Planning Recommendation

**Type:** Planning recommendation only. **No code, migration, API, bounded context, or ADR is
introduced by this document.** Documents how the platform's network (per
`docs/PLATFORM_STRATEGY.md`'s network-effects/flywheel reasoning) is expected to scale, and what
architectural properties that scaling depends on — this document does not commit to a timeline or
growth target; it names what must already be true, architecturally and operationally, at each
named scale.

**Date:** 2026-07-25

**Governed by:** `docs/PLATFORM_STRATEGY.md` (network effects, flywheel, competitive moat),
`docs/PARTNER_PROGRAMME_STRATEGY.md` (the surveyor-network this document scales),
`docs/B4_VERIFICATION_CHECKLIST.md`/`docs/B3_FINAL_VERIFICATION_CHECKLIST.md` (this platform's
only real, live-tested concurrency/performance evidence so far — the honest basis for what is
known vs. assumed about scale readiness).

## What "scale" means here — network size, not merely request volume

This document is about *network* growth (surveyors, parcels, institutional integrations), not
purely infrastructure capacity — though the two are related, since a larger network eventually
implies larger request volume. `docs/PLATFORM_STRATEGY.md`'s flywheel reasoning (more verified
parcels → more institutional trust → more institutional requirement → more registrants → more
verified parcels) is the mechanism this document assumes is operating; this document names what
must be true, at each stage, for that mechanism to keep working rather than stalling or breaking.

## Stage 1 — 100 surveyors

**Characteristic:** a small, closely-managed partner network, likely onboarded manually or with
light-touch Partner Programme tooling (`docs/PARTNER_PROGRAMME_STRATEGY.md`).

**What must be true:** Partner Programme's Onboarding/Accreditation exists in at least a manual or
semi-automated form — 100 surveyors can plausibly be accredited with meaningful human review per
applicant, so this stage does not yet stress-test the Partner Programme's own scalability
assumptions. This platform's existing engineering (B1–B4) is already sufficient for this stage's
technical demands — no new infrastructure capacity concern is introduced by 100 partners alone.

**What is not yet tested:** anything about Marketplace matching quality at scale, since 100
surveyors across a national geography likely means most registrants have very few nearby
candidate surveyors to match against — a small-network cold-start problem, not a technical scaling
problem.

## Stage 2 — 1,000 surveyors

**Characteristic:** onboarding volume starts to matter — fully manual accreditation review becomes
a real operational bottleneck (`docs/OPERATING_MODEL.md`'s Partner Operations function).

**What must be true:** at least partial automation of credential verification (per
`docs/GOVERNMENT_PROGRAMME_STRATEGY.md`'s Surveyor-General integration, if it exists by this
stage) or a scaled-up Partner Operations team — this document names the tension (manual review
quality vs. onboarding throughput) without resolving it, since the resolution depends on whether
Government integration or headcount growth arrives first, a sequencing question outside this
document's own scope.

**What is not yet tested:** genuine geographic density in most regions — 1,000 surveyors
nationally is still likely sparse outside major urban centers, meaning Marketplace matching
quality (`docs/MARKETPLACE_DISCOVERY_AND_PLANNING.md`'s candidate Match concept) remains an
open design question, not yet a proven mechanism.

## Stage 3 — 10,000 surveyors

**Characteristic:** the first stage at which this platform's existing, real infrastructure
constraints (named honestly in `docs/B3_FINAL_VERIFICATION_CHECKLIST.md` and
`docs/B4_VERIFICATION_CHECKLIST.md`, not hidden) plausibly start to matter for genuine concurrent
load, not merely theoretical capacity.

**What must be true, and is not yet proven:** this platform's own verification checklists have
already, honestly, flagged **SQLAlchemy's default connection-pool ceiling** (`pool_size=5` +
`max_overflow=10` = 15) as "a genuine, documented operational constraint for future capacity
planning" since B3's own Quality Gate — this document restates that flagged, known limitation as
directly relevant at this stage, not a new finding. **Live concurrency testing of the partial
unique index and RLS under real concurrent load** (also still deferred per
`docs/B4_VERIFICATION_CHECKLIST.md`'s own deferred-items list) becomes a genuine prerequisite,
not an optional nice-to-have, once 10,000 surveyors plausibly imply meaningfully concurrent
geometry submissions in the same geography.

**What this document does not do:** propose a specific connection-pool size, caching layer, or
infrastructure change — that is an implementation decision for whichever future engineering work
addresses the already-flagged limitation, not a network-growth-strategy decision.

## Stage 4 — 100,000 surveyors

**Characteristic:** a scale at which this platform's single-database-instance architecture
(`docs/adr/ADR-003-database-choice.md`) is worth explicitly re-examining, not assuming still holds.

**What must be true:** `docs/SCDS-001-...md` §6 already named this platform's current scaling
assumption explicitly: "this specification assumes single-database-instance operation... —
distributed/sharded operation is explicitly out of scope and not assumed." At 100,000 surveyors
and a proportionally larger parcel/transaction volume, this assumption becomes the single most
important open architectural question this document identifies — not resolved here, since it
depends on real production load data this platform does not yet have, but named now so a future
re-architecture is not a surprise discovered only once the constraint is actually hit.

## Stage 5 — Millions of parcels, nationwide institutional adoption

**Characteristic:** the network-effects flywheel (`docs/PLATFORM_STRATEGY.md`) is, by this stage,
either genuinely operating (institutional adoption reinforcing registrant growth) or the platform
has stalled below this scale for reasons this document cannot predict in advance.

**What must be true:** every trust mechanism named in `docs/TRUST_FRAMEWORK.md` must have actually
scaled *without degradation* — an audit chain that is hash-chained but never load-tested at
millions-of-entries scale, or a Trust Engine (B7) whose explainability holds for a demo dataset
but not for millions of real, messy parcels, would each independently undermine the trust claim
this entire platform is built to make. This is this document's single most important standing
observation: **network growth without proportional trust-mechanism validation at each stage is
not growth this platform's own constitutional principle (`docs/
CONSTITUTIONAL_RECOMMENDATIONS.md` entry 2) can credibly claim to have earned.**

## Cross-cutting principle: scale claims require the same evidence discipline as everything else

Consistent with `docs/ENGINEERING_RULES.md` rule 7 ("never mark something complete without
observing it pass") and this platform's entire live-verification discipline (every programme from
B1 through B4 Slice 2 verified against real infrastructure before being considered done): **a
"we can handle N surveyors" claim is not credible until it has been load-tested against real or
realistic data at that scale, the same way every authorization/validation claim in this codebase
has been live-verified, not merely reasoned about.** This document names the stages; it does not
claim any of them are currently proven.

## Approval Gate

No Network Growth Strategy commitment (a target surveyor count, a target date, an infrastructure
investment) is made by this document. It names what must be true, architecturally and
operationally, at five illustrative scale points, several of which reference already-known,
already-documented limitations rather than new findings. **Waiting for explicit direction —
informed by real growth data once the network exists — before any of the open questions this
document names (connection-pool capacity, distributed-database readiness, Trust Engine validation
at scale) is resolved.**
