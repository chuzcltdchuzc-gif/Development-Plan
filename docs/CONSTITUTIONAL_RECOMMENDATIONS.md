# Constitutional Recommendations — Register

Cumulative, append-only register of principles recommended for inclusion in **LV-000**
(`docs/LV-000-constitution.md`, adopted 2026-07-26). Each entry records what was recommended,
when, and why. **As of LV-000 v1.0's adoption, both entries below have been incorporated** —
see each entry's own updated Status line for exactly where. This file remains the historical
record of *why* each principle was proposed; LV-000 itself is now the authoritative, adopted text.
Future recommendations (for a future LV-000 amendment, per LV-000 Article XX) continue to be
logged here first, exactly as these two were.

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

**Status:** **Incorporated into LV-000 v1.0, Article IX, Section 4** (2026-07-26), verbatim as
proposed above. `docs/ENGINEERING_RULES.md` rule 9 remains the operative engineering-level rule —
per LV-000 Article VI, Section 3 and Article XX, Section 2, this incorporation ratifies the
principle at constitutional altitude without reopening or modifying rule 9's own text.

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

**Status:** **Incorporated into LV-000 v1.0, Article IX, Section 1** (2026-07-26), verbatim as
proposed above, and further reflected in Article IV (listed first among the ten constitutional
principles) and the Preamble's own framing. `docs/PLATFORM_STRATEGY.md`'s positioning statement
remains that principle's product-facing restatement, unchanged and consistent with the now-adopted
constitutional text.
