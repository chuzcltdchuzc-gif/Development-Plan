# Constitutional Recommendations — Pending LV-000

Cumulative, append-only register of principles recommended for inclusion in **LV-000** (this
platform's eventual top-level constitutional document) whenever constitutional work resumes.
**LV-000 does not exist yet** — nothing in this file has been ratified, adopted, or incorporated
anywhere. This file exists solely so recommendations made during ordinary programme work (B1–B4
and beyond) are not lost before LV-000 is drafted. Each entry records what was recommended, when,
and why — never the recommendation's own adoption, which is LV-000's act, not this file's.

---

## 1. Platform Intelligence — cross-context observation boundary

**Recommended:** 2026-07-24, during B4 pre-Slice-3 governance review (`docs/adr/
ADR-021-spatial-conflict-detection-and-controlled-cross-tenant-intelligence.md`, `docs/
PLATFORM_INTELLIGENCE_ARCHITECTURE.md`).

**Proposed principle:**

> Platform Intelligence may observe across bounded contexts only through Controlled Platform
> Authority, using the minimum information necessary to fulfil an approved platform
> responsibility. Operational workflows remain tenant-isolated by default.

**Why recommended:** ADR-021 named the first Platform Intelligence-shaped capability this
platform has designed with the pattern made explicit (Spatial Conflict Detection); `docs/
REBUILD_PLAN.md`'s Trust Engine (B7) is a second, not-yet-built instance of the same shape. Both
rely on the same underlying doctrine already adopted operationally as `docs/ENGINEERING_RULES.md`
rule 9 (Controlled Platform Authority). Recording this as a *constitutional* principle — not
merely an engineering rule — reflects that it governs a category of architectural decision
(when may a platform capability see across the tenant-isolation boundary this platform otherwise
treats as absolute), not a single engineering practice. This is the same reasoning that elevated
tenant isolation itself, delegation, and audit-chain integrity to constitutional status in every
prior programme's own framing, even before LV-000 formally existed to hold them.

**Relationship to existing doctrine:** this principle does not introduce a new rule — it restates
`docs/ENGINEERING_RULES.md` rule 9 at constitutional altitude, generalized from "any cross-tenant
read/write" to the specific case of a named platform-services layer observing multiple bounded
contexts at once. When LV-000 is drafted, this entry and rule 9 should be reconciled into one
statement, not adopted as two independently-worded versions of the same idea.

**Status:** Recorded, not adopted. No amendment to any existing document has been made under this
entry — `docs/ENGINEERING_RULES.md` rule 9 remains the operative, binding rule until LV-000 exists
and formally supersedes or restates it.

---

## 2. LandVault is a Trust Platform before it is a Software Platform

**Recommended:** 2026-07-25, during the Enterprise Programme Transition planning exercise
(`docs/PLATFORM_STRATEGY.md`).

**Proposed principle:**

> LandVault is a Trust Platform before it is a Software Platform. Its long-term value derives
> from trust, standards, governance, evidence, auditability, its professional network, digital
> identity, verification workflows, platform rules, and institutional integration — not from
> software features considered alone. Every future engineering decision is evaluated first against
> whether it strengthens or weakens this trust ecosystem, not only against whether it ships a
> capability.

**Why recommended:** every architectural decision this platform has actually made, across B1
through B4, is explicable as a trust-preserving decision before it is explicable as a feature
decision: the entire discipline of validate-then-store, creator-or-governance authorization,
append-only history, and hash-chained audit exists because a claim ("this parcel exists," "this
boundary is valid," "this mutation was authorized") is worthless to a government partner, a bank,
or a citizen unless the platform can *prove* it, not merely assert it. Naming this as the
platform's own constitutional identity — rather than leaving it implicit in each ADR's individual
reasoning — is what lets every future programme (Marketplace, Enterprise, Government, Developer
Platform, per `docs/PLATFORM_STRATEGY.md`) inherit the same evaluative lens, instead of each
independently re-deriving why, say, a marketplace rating system needs the same evidentiary rigor
a parcel registration does.

**Relationship to existing doctrine:** does not introduce a new engineering rule and changes no
accepted ADR. It is the constitutional-altitude statement of what `docs/ENGINEERING_RULES.md`
rules 1, 3, 7, and 9 collectively already imply in practice (authorization discipline, fail-safe
scoring, "never mark complete without observing it pass," Controlled Platform Authority) — this
entry names the *why* behind that collection of rules, rather than adding an eleventh rule to the
`docs/ENGINEERING_RULES.md` list. When LV-000 is drafted, this principle is a natural candidate
for its opening/foundational section, with `docs/PLATFORM_STRATEGY.md`'s own positioning statement
("Nigeria's trusted digital infrastructure for land verification, powered by a nationwide network
of licensed land professionals") as its product-facing restatement.

**Status:** Recorded, not adopted. No amendment to any existing document has been made under this
entry. `docs/PLATFORM_STRATEGY.md` treats this principle as its own organizing frame for planning
purposes, but that document is itself planning-only and adopts no constitutional authority it does
not have — the principle becomes binding only once LV-000 exists and ratifies it.
