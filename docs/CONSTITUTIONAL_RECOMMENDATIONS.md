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
