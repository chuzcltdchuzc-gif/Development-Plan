# LandVault — Governance Baseline, Revision H

## Ratification instruments for steps 3 to 7

*Issued under LV-000 — The LandVault Constitution, Edition v1.8, Working Edition, Revision H. In force.*

## Document Control

| Field | Entry |
|---|---|
| **Title** | LandVault — Governance Baseline, Revision H |
| **Status** | RATIFIED — in force. A working legal document |
| **Ratified** | 29 July 2026 |
| **Ratification instrument** | GD-005 (Part E) |
| **Governed by** | LV-000 v1.8, Working Edition, Revision H |
| **Purpose** | To carry the ratified Constitution down through the document hierarchy, so that one governing authority is reflected in every subordinate instrument rather than only in the top one |
| **Covers** | Step 3 (Bible numbering and identities) · Step 4 (ADR references) · Step 5 (Engineering Rules) · Step 6 (`CLAUDE.md` and indexes) · Step 7 (baseline ratification) |
| **Execution note** | Parts B, C and D are issued as **patch specifications to be applied in the repository**, exact enough to apply without further interpretation, and marked where a value must be confirmed by inspection rather than assumed |
| **Classification** | Public (Governance) |

> **The problem this instrument solves.** A ratified constitution that nothing beneath it cites is a ratified constitution in name only. Steps 3 to 7 exist so that an engineer or an agent who opens any governed file arrives at **one** authority by following the references in front of them, rather than by knowing which of two lineages was meant.

---

# Part A — Bible numbering and document identities (Step 3)

## A.1 The register

| ID | Document | Kind | Status under this baseline |
|---|---|---|---|
| **LV-000** | The LandVault Constitution — Edition v1.8, Revision H | Constitution | **RATIFIED — in force, supreme** |
| LV-001 | Executive Overview | Bible volume | In the library |
| LV-002 | Vision, Mission and Principles | Bible volume | In the library |
| LV-003 | Product and Platform Strategy | Bible volume | In the library |
| LV-004 | Market Analysis | Bible volume | In the library |
| LV-005 | Product Requirements (PRD) | Bible volume | In the library. Cited by §4.2 of the execution instrument |
| LV-006 | Technical Requirements (TRD) | Bible volume | In the library |
| LV-007 | Security Architecture | Bible volume | In the library |
| LV-008 | Enterprise Architecture | Bible volume | In the library |
| LV-009 | Database and Data Governance | Bible volume | In the library |
| LV-010 | Design System | Bible volume | In the library |
| LV-011 | UX Standards | Bible volume | In the library |
| LV-012 | Monetization Strategy | Bible volume | In the library |
| **LV-013** | **Market Intelligence Report** | Repository document — adopted | **PROTECTED.** Not to be overwritten, renamed, or reassigned. `docs/LV-013-market-intelligence-report.md` |
| LV-014 | Growth Strategy | Bible volume | In the library |
| LV-015 | Operational Excellence | Bible volume | In the library |
| LV-016 | Governance and Compliance | Bible volume | In the library |
| LV-017 | Go-to-Market Strategy | Bible volume | **RENUMBERED from LV-013** |

## A.2 The collision, and how it was resolved

Two different documents claimed LV-013. One was the repository's adopted **Market Intelligence Report**; the other was an authored **Go-to-Market Strategy** written later.

The rule applied is the one at LV-000 v1.8, Article II §2 and GD-001: **where an authored document collides with an adopted one, the authored document yields.** The candidate moved to LV-017. The adopted document did not move, was not renamed, and was not touched.

This matters beyond tidiness. Had the numbers been resolved the other way, a citation to "LV-013" written before the collision would have silently begun resolving to a different document — the quietest and most damaging kind of governance failure, because nothing appears to break.

## A.3 File operations

| Operation | Action |
|---|---|
| `docs/LV-013-market-intelligence-report.md` | **Leave untouched.** No rename, no overwrite, no edit under this baseline |
| Authored Go-to-Market Strategy | Issue as `LV-017-go-to-market-strategy.md`. Any file bearing the old LV-013 name in a candidate pack is superseded by it |
| Adopted Bible Volumes I and II | **Restore any staged deletion** — `git restore --staged --worktree docs/LANDVAULT_BIBLE_VOLUME_I_EXECUTIVE_OVERVIEW.md` and the Volume II equivalent. Required by GD-001, which remains in force |

## A.4 Residual citations

Every citation of "LV-013" written before 28 July 2026 must be read against **which document was meant**, not against the number. Two are already known and corrected: the execution instrument's pending-decisions section, which meant the anchor-tenant material and now cites **LV-017**; and whichever `CLAUDE.md` carries an LV-013 reference, which is finding **S4.3** and is resolved by inspection.

## A.5 Standing identity rule

A document identity is **allocated once and never reused**. A superseded volume keeps its number and is marked superseded; it does not vacate the number for a successor. Renumbering is permitted only to resolve a collision with an adopted document, only in favour of the adopted document, and only with the move recorded — as it is here.

---

# Part B — Architecture Decision Records (Step 4)

## B.1 Citation form

Every ADR that cites the Constitution shall cite it **with its edition**:

> `LV-000 v1.8, Article IX §3`

not `LV-000 Article IX §3` and never `Article IX §3` alone. This is LV-000 v1.8, Article III §5. An unedition-ed citation was ambiguous across the two historical lineages, and ambiguity at Article IX is precisely what reached shipped code.

## B.2 The protected citation chain — no substantive change

| Step | Before | After |
|---|---|---|
| LV-000 | Article IX §3 (adopted v1.0) | **LV-000 v1.8, Article IX §3** |
| `ENGINEERING_RULES.md` rule 9 | cites Article IX §3 | **unchanged in substance**; edition tag added |
| ADR-021 | cites rule 9 and Article IX §3 | **unchanged in substance**; edition tag added |
| ADR-022 *(governs shipped B4 Slice 2 code)* | cites ADR-021 | **unchanged** |
| `PLATFORM_INTELLIGENCE_ARCHITECTURE.md` | cites the chain above | **unchanged in substance**; edition tag added |
| B4 Threat Model | cites the architecture document | **unchanged** |
| SCDS-001 | cites the threat model | **unchanged** |

**The change is to citation form only.** No ADR is reopened, re-argued, or invalidated by ratification. **In particular, ADR-022 is not disturbed** — the code it governs has shipped, and the doctrine it depends on is now anchored in a constitution that is actually in force rather than in one that was contested.

## B.3 Re-anchoring the previously vacant citations

These are the citations that had no resolvable home before ratification. They now resolve without amendment, because LV-000 v1.8 was numbered to receive them.

| Citation in circulation | Status before | Status now |
|---|---|---|
| **Article X.3** — single authorisation path | Vacant. Cited a lineage that did not govern | **LV-000 v1.8, Article X §3.** Resolves. Number preserved deliberately |
| **Article X.4** — kernel first | Vacant | **LV-000 v1.8, Article X §4.** Resolves |
| **Article X** — integration by contract | Vacant | **LV-000 v1.8, Article X §2** |
| **Article XV.1** — Trust Neutrality Firewall | Candidate, no adopted counterpart | **LV-000 v1.8, Article XV §1.** Adopted by amendment, subordinated to Article VI |
| **Article XV.2** — Delegated Authority | Candidate | **LV-000 v1.8, Article XV §2.** Adopted by amendment |
| **Article IX** — Engineering Principles (v1.7 sense) | Collided with the adopted Article IX | **Moved to LV-000 v1.8, Article XI.** The one deliberate displacement; recorded at Article III §3 |

**Any document citing "Article IX" in the v1.7 engineering sense must be repointed to Article XI.** This is the only repointing the ratification requires, and it should be done by search rather than by memory.

## B.4 The three ADRs to be raised

| Working title | Proposed | Constitutional anchors |
|---|---|---|
| Registry Ownership and Status History | **ADR-023** | Article IV; Article V; Article VII §6; Article VIII §2–§3; Article X §3 |
| Delivery Platform Decisions | **ADR-024** | Article VII §2–§4; Article X §5 |
| Pilot Non-Functional Targets | **ADR-025** | Article XIV §2 test 4; Article XI §7 |

**Numbering floor — confirm before raising.** The numbers above assume the highest existing ADR is 022. That is **unconfirmed** in this instrument's own text: the root `CLAUDE.md` reports 017 while the extraction record shows ADR-022 governing shipped code. This is finding **S4.1**. Read `docs/adr/` and renumber upward if the floor differs. Never renumber downward into an occupied range.

> **Resolved administratively, 29 July 2026, regularised under GD-006** (see LV-000 v1.8 Schedule 4, confirmed-by-observation note): the floor is **022**. ADR-023/024/025 as proposed require no renumbering.

## B.5 ADR-020

**ADR-020 remains vacant, deliberately.** It is not filled by the three above and not filled by any automatic allocator. The vacancy is the record that a question is open; consuming it destroys that record. No script may allocate ADR numbers (LV-000 v1.8, Article XII §4).

---

# Part C — Engineering Rules (Step 5)

*Issued as a patch specification. `ENGINEERING_RULES.md` was not present in the drafting environment; the amendments below are stated so they can be applied by inspection, and no rule text that was not observed is reproduced as though it had been.*

## C.1 Header amendment

Insert at the head of `ENGINEERING_RULES.md`:

> **Governed by:** LV-000 — The LandVault Constitution, Edition v1.8, Working Edition, Revision H (`docs/LV-000-constitution.md`). These rules are subordinate to it. Where a rule and the Constitution appear to conflict, **the Constitution governs and the rule is corrected**.
>
> **Citation form:** every reference to the Constitution in this file carries its edition — for example *LV-000 v1.8, Article IX §3*.
>
> **Relationship to `CLAUDE.md`:** the non-negotiable rules listed in `CLAUDE.md` are an operationally critical **subset** of the rules in this file. That is not a conflict. A document citing "Rule 1" or "Rules 6–7" must **name the file it means**.

## C.2 Rule-level amendments

| Rule | Amendment | Basis |
|---|---|---|
| **Rule 9** | Retain its text unchanged. Update its citation to **LV-000 v1.8, Article IX §3**. This rule is a step in the protected citation chain and must not be reworded while its citation is being retagged — **change one thing at a time** | Article III §4 |
| **Rule 1** (RLS ships with the migration) | Add the anchor **LV-000 v1.8, Article VIII §2** | — |
| **Rules 6–7** (reversible migrations, governed dependencies) | Add the anchors **Article XI §3** and **Article XI §4** respectively, confirming by inspection which rule carries which obligation | — |
| **All other rules** | Add the anchoring Article and section where one exists. **Where no anchor exists, add none** — an invented anchor is worse than an unanchored rule, because it makes a rule look constitutionally grounded when it is only conventional | Article XIV §2, tests 1 and 2 |

## C.3 New rules required by ratification

Two constitutional obligations are not yet expressed as engineering rules and should be added.

**Proposed new rule — the non-adjudication check.** *A build shall fail on ownership-adjudication wording in API responses and user-facing text. The check is automated and runs in CI.* **Anchor: LV-000 v1.8, Article IV §4.** This is required, not optional: Article IV §4 states that a principle enforced only by good intentions is not enforced.

**Proposed new rule — the single authorisation path.** *No code path may reach a protected resource except through the policy decision point and its enforcement points. There is no internal-caller exemption. Coverage is tested.* **Anchor: LV-000 v1.8, Article X §3.**

## C.4 What is not changed

**No existing rule is deleted, renumbered, or narrowed by this baseline.** Ratification adds anchors and edition tags. If applying this patch appears to require deleting a rule, stop: that is an amendment, and it goes through Article XIV rather than through a retagging exercise.

---

# Part D — CLAUDE.md and the documentation indexes (Step 6)

*Issued as a patch specification. Apply against the real file.*

## D.1 The gap being closed

`CLAUDE.md` is the always-loaded operational summary. Its pointer index names `REBUILD_PLAN.md`, `PHASE_GATES.md`, `DOD.md`, `ENGINEERING_RULES.md`, `docs/adr/` and `docs/audits/`.

> **Confirmed by inspection, 29 July 2026 (regularised under GD-006):** `docs/LV-000-constitution.md` is **not** absent from this index as originally assumed — it is present, described as "the platform's supreme governing document," but as the *second* entry (after the Architecture Handbook), not the first. The correction below is therefore reordering plus the new patch content, not a bare addition.

## D.2 Patch — add the Constitution to the pointer index

Insert as the **first** entry of the index, above every existing entry (including the Architecture Handbook):

```markdown
- **`docs/LV-000-constitution.md`** — **The LandVault Constitution, Edition v1.8, Working Edition,
  Revision H. RATIFIED and in force. Supreme.** Every other document here is subordinate to it.
  Read it before proposing any change to governed behaviour. The Prime Directive is Article I §3:
  *LandVault preserves and verifies land evidence. It does not decide who owns land.*
```

## D.3 Patch — add the execution instrument

Insert immediately after the `REBUILD_PLAN.md` entry:

```markdown
- **`docs/EXECUTION_PLAN.md`** — LandVault Development Plan (Execution), Revision H. Ratified under
  GD-004. Governs the ordering and content of delivery work. `REBUILD_PLAN.md` remains the plan of
  record for phase definitions and gates; where the two speak to the same gate, REBUILD_PLAN wins
  and the divergence is raised as an amendment.
```

## D.4 Patch — the precedence block

Replace whatever precedence list the file carries with:

```markdown
## Precedence

1. `docs/LV-000-constitution.md` — the Constitution, Edition v1.8 Revision H. Supreme.
2. The Bible volumes, LV-001 – LV-017.
3. Ratified ADRs in `docs/adr/`.
4. `ENGINEERING_RULES.md`.
5. `PLATFORM_INTELLIGENCE_ARCHITECTURE.md` and the architecture documents.
6. `REBUILD_PLAN.md`, `EXECUTION_PLAN.md`, `PHASE_GATES.md`, `DOD.md`.
7. Implementation and code.

This file is a **pointer, not the source of truth**. Where it conflicts with a document it points
to, that document wins and this file is corrected.

On *current state* — what is frozen, what tests pass, what has shipped — the repository and an
observed test run govern. On *what to build and how*, the hierarchy above governs. Do not confuse
the two.
```

## D.5 Patch — one governing authority

Add, near the top:

```markdown
## One constitution

As of 29 July 2026 there is exactly one governing constitution: **LV-000 Edition v1.8, Working
Edition, Revision H**, at `docs/LV-000-constitution.md`. The authored v1.7 no longer governs
anything. The adopted v1.0 continues *through* v1.8 by incorporation (v1.8 Article II §4) and its
principles remain in force verbatim.

Cite the Constitution **with its edition** — `LV-000 v1.8, Article X §3` — never by bare article
number. Bare article numbers are ambiguous across the historical lineages.
```

## D.6 The other CLAUDE.md variants

Three variants exist in the candidate packs. They are **not** the repository's file and must not be copied over it. Their governing-blueprint import lists reference `LV-000-The-LandVault-Constitution-v1.7.md`; **every such import is repointed to the ratified `docs/LV-000-constitution.md`**, and the v1.7 file is retained as a historical source rather than deleted (LV-000 v1.8, Article XVII §3).

## D.7 Confirm, do not assume

Finding **S4.3** — which `CLAUDE.md` cites LV-013, and which LV-013 it means — is resolved (regularised under GD-006): `CLAUDE.md` already cites `docs/LV-013-market-intelligence-report.md`, the protected document. No repair needed on this point.

---

# Part E — Ratification of the governance baseline (Step 7)

## E.1 GD-005 — the baseline

**GD-005 — Ratification of the Governance Baseline, Revision H.** *(Approved 29 July 2026.)*

The Governance Baseline set out in Parts A to D is ratified. The Bible register at Part A is the authoritative document-identity register. The ADR treatment at Part B is the authoritative citation treatment. Parts C and D are authoritative patch specifications to be applied in the repository, and their application is **administrative** — it changes citation form and adds pointers, and it makes no substantive change to any rule.

**No ADR is reopened. No engineering rule is deleted. No adopted document is renamed or overwritten. No shipped code is invalidated.**

## E.2 The Governance Decision Log after ratification

| # | Decision | Status |
|---|---|---|
| **GD-001** | Adopted Bible Volumes I and II preserved | **In force.** Restoration confirmed — working tree is clean, no staged deletions present |
| **GD-002** | `REBUILD_PLAN.md` is the plan of record; `commit-development-plan.sh` retired unrun | **In force**, as amended by GD-004 |
| **GD-003** | Ratification of LV-000 v1.8, Revision H. The HELD status lifted and not to be reinstated | **In force** |
| **GD-004** | *Development Plan (Execution), Revision H* ratified as the execution instrument at `docs/EXECUTION_PLAN.md` | **In force** |
| **GD-005** | This Governance Baseline ratified | **In force** |

## E.3 The seven steps

| Step | Instrument | State |
|---|---|---|
| **1. Constitutional Reconciliation, Revision H** | *LV-000 v1.8 Reconciliation Working Edition, Revision H* | **Complete and ratified.** Retained as the ledger of record — how the divergence was found, what was assumed, and what was corrected |
| **2. LV-000 Constitution v1.8, Revision H (not held)** | *LV-000 — The LandVault Constitution, Edition v1.8, Working Edition, Revision H* | **Complete. RATIFIED and in force.** GD-003 |
| **2b. Execution instrument** | *LandVault — Development Plan (Execution), Revision H* | **Complete. RATIFIED and in force.** GD-004 |
| **3. Bible numbering and identities** | Part A | **Complete.** File operations confirmed in the repository (A.3) |
| **4. ADR references** | Part B | **Complete as specification.** Numbering floor confirmed at 022 |
| **5. Engineering Rules** | Part C | **Complete as specification.** Apply to `ENGINEERING_RULES.md` |
| **6. `CLAUDE.md` and indexes** | Part D | **Complete as specification.** Apply to the repository's own `CLAUDE.md` |
| **7. Governance baseline ratified** | Part E | **Complete.** GD-005 |

## E.4 What ratification achieved, stated plainly

**Before.** Two constitutions, one adopted and one authored, using the same article numbers for different content — including at Article IX, on which shipped code depends. Four live citations pointed at articles that did not exist in the governing lineage. The whole corpus was held pending a transcription that had not arrived and had no date attached to it.

**After.** One constitution, in force, with the adopted principles incorporated so that none of their authority was lost. The protected citation chain unbroken. Every previously vacant citation resolving. Every displacement recorded on the face of the instrument that made it. The outstanding transcription reclassified from a blocker into a register, so that work proceeds while it is completed.

**What is still owed** — and it is owed honestly rather than hidden: seven adopted principles are incorporated but not restated; three patch specifications (Parts B, C, D) await application to `docs/adr/`, `ENGINEERING_RULES.md`, and `CLAUDE.md` respectively. **None of these holds anything still.**

## E.5 The residual risk, named

The restatements at LV-000 v1.8 Articles V, VI and IX were drafted from each principle's **name**, its adopted article number where known, and the subordinate instruments depending on it. **They are not transcriptions.** If the adopted wording differs, **the adopted wording prevails** and the restatement is corrected — Article II §6 makes that automatic and requires no further decision.

This is a real risk and it is stated rather than smoothed over. It is also a **bounded** one: incorporation under Article II §4 means the adopted principles govern in their adopted form whether or not this Edition describes them well. **The worst case is an inaccurate description sitting above an accurate incorporation — not a loss of authority.** That was the point of building it this way.

## E.6 Standing obligations

1. Close Schedule 1 Part B as adopted text becomes available, by copying it unchanged. Never by authorship.
2. Apply Parts B, C and D in the repository, one reviewed change at a time.
3. Record every future amendment in the Governance Decision Log, and never edit a logged decision in place.

---

## Enactment

This Governance Baseline is ratified on 29 July 2026 under GD-005 and is in force from that date.

From this date, an engineer or an agent who opens any governed file in the LandVault repository and follows the references in front of them arrives at **one** constitution. That was the object of the exercise, and it is met.

**Amend, never erase.**

*LandVault preserves and verifies land evidence. It does not decide who owns land.*
