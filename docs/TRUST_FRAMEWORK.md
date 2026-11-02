# Trust Framework — Planning Recommendation

**Type:** Planning recommendation only. **No code, migration, API, bounded context, or ADR is
introduced by this document.** This is the product/business-facing consolidation of this
platform's trust mechanisms — it names what each mechanism *means to the ecosystem* (a citizen, a
bank, a government partner) rather than how it is engineered. **Where this document and
`docs/ARCHITECTURE_HANDBOOK.md` Part V (Security Model) or `docs/
PLATFORM_INTELLIGENCE_ARCHITECTURE.md` overlap, those documents are the engineering-authoritative
source** — this document explains their significance to the trust ecosystem, it does not
re-specify them.

**Date:** 2026-07-25

**Governed by:** `docs/CONSTITUTIONAL_RECOMMENDATIONS.md` entry 2 ("LandVault is a Trust Platform
before it is a Software Platform" — this document is that principle's operational expression),
`docs/ARCHITECTURE_HANDBOOK.md` Part V, `docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md`, `docs/
SCDS-001-spatial-conflict-detection-specification.md` (Risk Scores/Fraud Detection's only
currently-specified instance).

## Why a Trust Framework document distinct from the Security Model

`docs/ARCHITECTURE_HANDBOOK.md` Part V answers "how does this platform enforce security" —
authentication, RLS, Controlled Platform Authority, audit chains. This document answers a
different question: **what does each of those mechanisms let this platform credibly *claim* to
the outside world**, and how do those claims compose into the trust ecosystem
`docs/PLATFORM_STRATEGY.md` names as this platform's actual product. A bank does not care that
`ParcelGeometry` uses `FORCE ROW LEVEL SECURITY` — it cares that a verified parcel's boundary can
be trusted as collateral. This document is the translation layer between the two.

## Trust mechanisms and what they let this platform claim

| Mechanism | Engineering source | What it lets LandVault credibly claim |
|---|---|---|
| **Identity** | `docs/adr/ADR-004-...md`, ADR-009 | "The principal who registered/verified this parcel is a real, authenticated individual, not an anonymous or spoofed actor." |
| **Evidence** | `docs/REBUILD_PLAN.md` context #4 (unbuilt) | "This claim is backed by an original document/artifact, not merely a typed-in assertion." |
| **Verification** | B3/B4 (Registry, Spatial) | "This parcel's boundary is structurally valid and, once ADR-021/Slice 3 exists, checked against competing claims — not merely stored as submitted." |
| **Audit** | `docs/adr/ADR-007-...md` | "Every action taken against this record is permanently, tamper-evidently logged — nothing can be silently altered after the fact." |
| **Certificates** | `docs/GOVERNMENT_PROGRAMME_STRATEGY.md` (not built) | "A third party can independently verify this specific claim's authenticity without needing to trust LandVault's word alone." |
| **Chain of Custody** | `docs/REBUILD_PLAN.md` context #4 (Evidence, unbuilt) | "This evidence has an unbroken, provable history from its original creation to its current state." |
| **Digital Signatures** | Not yet built — a likely Evidence-context or Certificate-issuance mechanism | "This document/certificate was genuinely produced by the party it claims to be from." |
| **Risk Scores** | `docs/SCDS-001-...md` §3 (specified, unimplemented); future Trust Engine (B7) | "This platform can give an explainable, evidence-based confidence signal about a parcel or transaction — never a fabricated 'always passes' score (`docs/ENGINEERING_RULES.md` rule 3)." |
| **Fraud Detection** | `docs/adr/ADR-021-...md` §2/§6; `docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md` | "Suspicious patterns are surfaced for human governance judgment — never an automated accusation, per ADR-021's own explicit doctrine." |
| **Compliance** | `docs/OPERATING_MODEL.md`, `docs/GOVERNMENT_PROGRAMME_STRATEGY.md` | "This platform can demonstrate, to a regulator or institutional partner, that its own rules were followed — not merely assert it." |
| **AI governance** | `docs/adr/ADR-008-ai-integration-strategy.md`; `docs/adr/ADR-021-...md` §6/§8's intelligence-boundary doctrine | "Any AI/ML capability this platform ever deploys operates under the same Controlled Platform Authority and audit discipline as every other cross-context capability — it is never an unaudited, ungoverned black box." |

## The trust framework as a single, composable claim

Individually, each mechanism above is a specific engineering guarantee. **Together, they compose
into this platform's actual product claim**: that a piece of information LandVault presents about
a parcel, a professional, or a transaction can be relied upon by a party who was not present for
its creation — a citizen relying on a surveyor's credential, a bank relying on a verified
boundary, a government relying on this platform's own audit trail during a dispute. This is the
concrete meaning of `docs/PLATFORM_STRATEGY.md`'s "trust network is the product" insight, restated
mechanism-by-mechanism rather than as a single slogan.

## AI governance — a standing constraint on every future intelligence capability

Every mechanism in the table above that involves any form of automated inference (Risk Scores,
Fraud Detection, and any future AI/ML capability named in `docs/ARCHITECTURE_HANDBOOK.md` Part
VIII) is bound, without exception, by doctrine already established rather than newly invented
here:

- It operates under Controlled Platform Authority (`docs/ENGINEERING_RULES.md` rule 9) if it
  reads across contexts or tenants — no exception inherits another's
  (`docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md`).
- It fails safe (`docs/ENGINEERING_RULES.md` rule 3) — insufficient data produces an explicit
  "insufficient data" result, never a fabricated confident one.
- It produces a finding or signal, never an automated adjudication of fraud or wrongdoing
  (`docs/adr/ADR-021-...md` §2/§6) — a human governance function (`docs/OPERATING_MODEL.md`'s
  Fraud Operations/Trust & Safety) makes any determination with real consequences.
- It is auditable — every automated finding and every human review of it produces a
  hash-chained audit record (`docs/adr/ADR-007-...md`).

**This document does not add a new AI governance rule** — it names the above as a coherent
"AI governance" framing for a set of constraints this platform's ADRs already impose piecemeal, so
that a future AI-capability proposal can be evaluated against one named framework rather than
requiring its proposer to rediscover four separate ADRs' worth of constraints independently.

## Relationship to existing architecture

This document introduces no new mechanism. Every row in the table above already has (or, where
unbuilt, already has a named future home for) its own engineering-authoritative source; this
document's only original content is the *framing* connecting engineering mechanism to ecosystem
trust claim, and the AI-governance consolidation above.

## Approval Gate

No Trust Framework implementation work is proposed — every mechanism named is either already built
(Identity, Verification, Audit) or already named as a future programme's responsibility elsewhere
in this planning package. This document records the framing that ties them together as a single
product narrative. **No further action is required to "approve" this document beyond acknowledging
its framing** — unlike the programme-planning documents above, it authorizes no future work of its
own; it is a lens for evaluating that future work.
