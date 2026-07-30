# LandVault — Development Plan (Execution)

## Working Edition, Revision H (Ratified)

*The execution instrument of the LandVault platform. Issued at `docs/EXECUTION_PLAN.md`. In force — not held, not conditional, not pending.*

## Document Control

| Field | Entry |
|---|---|
| **Title** | LandVault — Development Plan (Execution) |
| **Edition** | Working Edition, Revision H |
| **Status** | RATIFIED — in force. A working legal document of the LandVault governance framework |
| **Ratified** | 29 July 2026, by the Governance Authority |
| **Ratification instrument** | GD-004 (LV-000 v1.8, Article XVI) |
| **Conditions on force** | None. No hold, no suspensive condition, no "pending transcription" qualification |
| **Governed by** | LV-000 — The LandVault Constitution, Edition v1.8, Working Edition, Revision H |
| **Issued at** | `docs/EXECUTION_PLAN.md` |
| **Relationship to `REBUILD_PLAN.md`** | `REBUILD_PLAN.md` remains the plan of record for phase definitions and gates. This instrument governs the ordering and content of delivery work beneath those gates. Where the two speak to the same gate, `REBUILD_PLAN.md` governs and the divergence is raised as an amendment (GD-004) |
| **Files it does not create** | `docs/DEVELOPMENT_PLAN.md`. The prohibition in GD-002 stands undisturbed. `commit-development-plan.sh` remains retired unrun |
| **Depends on** | ADR-023 Registry Ownership and Status History · ADR-024 Delivery Platform Decisions · ADR-025 Pilot Non-Functional Targets (numbers subject to the floor at §11.2) |
| **Prime Directive** | LandVault preserves and verifies land evidence. It does not decide who owns land (LV-000 v1.8, Article I §3) |
| **Classification** | Public (Governance) |
| **Owner** | Office of the LandVault Constitution (Governance Authority) |

> **What changed at Revision H.** The four sections that the previous issue marked BLOCKED are now clear. They were blocked because they cited article numbers from a lineage that did not govern. Under LV-000 v1.8 those citations resolve correctly and unchanged — Article X §3 is still the single authorisation path, Article X §4 is still kernel-first — because the Constitution was numbered deliberately to keep them working. Nothing in the substance of the plan changed to achieve this. The governing instrument changed, and the plan became citable.

> **For Claude Code and any automated agent.** Read `CLAUDE.md`, then this instrument, then the bounded-context material for the work at hand. For each task run `/plan <bounded-context>`, build against the plan, run the tests, and `/review` before committing. One bounded context per change (LV-000 v1.8, Article XI §5). Nothing is done until its tests have been observed to pass (Article XI §2). Your authority under this instrument is explicit, recorded and revocable (Article XII §4); you have no implicit grant to change governance documents, CI configuration, or ADR numbering.

## 1. Constitutional anchors for this instrument

Every rule below that carries weight carries it from somewhere. The anchors are stated once, here, so that the rest of the document can cite rather than argue.

| Anchor | What it fixes | Where it appears below |
|---|---|---|
| Article I §3–§4 — Prime Directive, entrenched | Nothing built may adjudicate title | §3, §7.5, §8.6, §10 |
| Article IV — evidence over assertion; §4 mechanical enforcement | Ownership records are assertions with provenance, and a check enforces it | §7.5, §7.6 |
| Article V / Article X §2 — bounded context sovereignty; integration by contract | Contexts own their data; events between them; projections for unified views | §6, §9 |
| Article VII §2–§4 — WORM grade declared; escalation without code change; demonstrable integrity | Storage design and the Phase 3 gate | §4.2, §7.2, §9 |
| Article VIII §2–§3 — RLS in the same migration; audit chain | Every migration and every state change | §7.1, §7.3, §7.6 |
| Article IX §3 — the boundary of platform authority | The outer limit of everything in this plan | §3, §10 |
| Article X §3 — the single authorisation path | One PDP/PEP path, no exceptions | §3, §7.4, §9 |
| Article X §4 — kernel first | The phase order in §5 is constitutional, not merely convenient | §5, §9 |
| Article X §5–§6 — ports; seams declared | `StoragePort`, `GeometryPort`, and the honest description of the geometry adapter | §2, §4.2, §7.2 |
| Article XI §2–§4 — observed not assumed; reversible; governed dependencies | Re-observing the baseline, tested `down`, the `npm test` decision | §2, §6, §7.1 |
| Article XIII §1 — hierarchy of instruments | Why this instrument sits where it does | Document Control |

## 2. Current state — to be re-observed, not inherited

Article XI §2 governs this section. Every figure below is a claim to be re-observed on the untouched tree, not a fact to be carried forward. Where re-observation disagrees with what is written here, the observation wins and this section is corrected.

- **Frozen and reported verified:** B1 Identity, B2 Tenant/Delegation, B3 Registry — parcel numbering, row-level security, audit chain, geometry seam. Reported at 119/119 backend tests. Re-run `pytest` on the untouched tree and confirm green **before Phase 1 opens**. Record the result with a date and a commit reference.
- **Geometry seam — a declared seam, not a defect.** The current adapter accepts every reference. It is a boundary, not a validation. This is recorded openly under Article X §6. B4 Spatial replaces the adapter behind `GeometryPort` **without changing Registry's domain contract**.
- **Frontend:** F0 shell only — landing page and component base. No authenticated portals, no API client, no parcel journeys.
- **Infrastructure gaps:** Keycloak running in dev mode; Terraform pinned with no provider or resources; no CI.
- **Working tree:** finish or revert any paused test or lockfile changes so the tree is clean before new work begins.

**Open finding.** LV-000 v1.8 Schedule 4 §S4.1 records an unresolved discrepancy about whether B4 has begun. Resolve it by reading the repository before Phase 2 planning, because it also fixes the ADR numbering floor at §11.2.

## 3. The MVP boundary

Deliver **four governed portals** — customer, survey partner, enterprise (read-only), and government operations — sharing one Next.js application and the **single PDP/PEP authorisation path** (LV-000 v1.8, Article X §3).

**In scope for the pilot:** authenticated parcel search and registration · spatial validation · evidence sealing · verification requests · licensed assignment · status tracking · secure vault access · payment.

**Out of scope, absolutely:** any claim of title, ownership determination, or resolution of a competing claim. This is not a scoping preference that a later decision may revisit — it is **Article I §4 and Article IX §3**, and it is entrenched.

**Deferred to post-pilot** — each requires a recorded decision before any work begins: full multi-signal Trust Engine scoring · Community Trust · Inheritance and Customary Law · Knowledge Graph · Marketplace escrow, ratings and disputes. *(Per LV-005 §4.2.)*

## 4. Binding delivery decisions

### 4.1 Registry ownership and status history

Keep the current owner reference on the Parcel aggregate — **the domain contract does not change**. Add an **append-only history table owned by Registry**. Emit domain events. History records **assertions with provenance, never a title determination** (Article IV). Row-level security ships **in the same migration** (Article VIII §2). The migration is reversible and its rollback is rehearsed (Article XI §3). Every change writes to the B1 audit chain. Cross-tenant tests are mandatory, positive and negative.

*To be recorded as an ADR — see §11.*

### 4.2 Storage

A provider-agnostic **`StoragePort`** with S3-compatible semantics and an object-lock capability. **Cloudflare R2** is the pilot default. Adapters for S3, Azure, GCS and MinIO follow. Sealed evidence is under WORM, and **the adapter declares its grade** (Article VII §2):

| Backend | Grade | Meaning |
|---|---|---|
| **Cloudflare R2** Bucket Locks | governance | Retention revocable by a privileged administrator |
| **S3 Object Lock** (compliance mode), Azure, GCS, MinIO | compliance | Irrevocable retention, with legal hold |

`wormGrade()` returns `compliance` or `governance`. **No bounded context calls a storage SDK directly** (Article X §5). The required grade is confirmed with the pilot partner and counsel; escalation to a compliance-grade backend happens **without code change** (Article VII §3).

### 4.3 Identity provider

**Keycloak**, confirmed. Move to production mode: database-backed, TLS, realm exported as code and committed, secrets in a manager. Dev mode does not reach staging.

### 4.4 Payments

**Paystack** only for pilot one. Stripe deferred; deferral is recorded, not assumed.

### 4.5 Non-functional targets

| Target | Value |
|---|---|
| Read latency | p95 under 300–500 ms |
| Search latency | under 1 s |
| Availability | 99.5% |
| Recovery | RPO ≤ 15 min · RTO ≤ 1 h |
| Accessibility | WCAG 2.1 AA |
| Security | Zero open critical or high findings |
| Pilot success | N parcels registered end to end · X% of verification requests fulfilled with recorded evidence · restore and rollback demonstrated |

**On N and X.** These are not yet bound, and an unbound success criterion is not testable — which would fail LV-000 v1.8, Article XIV §2, test 4. The criterion is therefore stated in a form that **is** testable today: *the Phase 6 gate may not be passed unless the pilot-targets ADR records concrete values for N and X, agreed with the pilot partner, before Phase 6 opens.* The check is on the record, not on the number, and it can be run now.

## 5. Phase plan

The order is constitutional (**Article X §4 — kernel first**), not a matter of convenience.

| Phase | Outcome | Main work | Gate to proceed |
|---|---|---|---|
| **0 — Stabilise delivery** | A baseline that can be trusted | Re-observe backend green; resolve `npm test`; CI for frontend and backend; branch and PR checks; verify local Docker end to end; Keycloak realm-as-code and secrets; `StoragePort` skeleton and R2 adapter; compute chosen at deploy | Clean tree · CI green · repeatable local environment · staging design approved |
| **1 — Registry contract** | B3 aligned with the PRD | Implement the ownership and status-history ADR: migration, RLS, events, audit, cross-tenant tests, non-adjudication check | ADR implemented · migration, RLS, rollback and cross-tenant tests observed passing |
| **2 — B4 Spatial, F1 and F2** | A real spatial registry | PostGIS geometry versions; CRS and topology checks; overlap and duplicate detection; spatial search behind `GeometryPort` with the Registry contract unchanged. F1 authenticated shell and API client, then F2 registration, search, map and parcel-detail UI | Invalid or missing CRS rejected · overlaps surfaced · RLS and performance pass · a real registration completes end to end through an authenticated portal |
| **3 — B5 Evidence and F3 vault** | Evidence-backed parcels | Sealed writes through `StoragePort` under WORM; streamed hashing with read-back verification; chain of custody; integrity verification; legal-hold hook; upload, evidence timeline and authorised vault UI | Sealed evidence demonstrably cannot be altered · integrity check demonstrated · storage, retention and break-glass pass security review |
| **4 — B8 Workflow and B6 Survey** | Verification requested and fulfilled | Verification state machine, events, SLAs, compensations; licensed surveyor and firm onboarding, assignment, survey-plan submission through Evidence; requester status tracking; work queues | A request is assigned only to an eligible surveyor, records evidence, and shows traceable status end to end |
| **5 — B11 Billing and payment UI** | Paid verification, safely | Atomic ledger; invoice lifecycle; webhook verification and idempotency; the payment-to-workflow contract; Paystack | No direct balance mutation · duplicate webhooks harmless · reconciliation and refund tested |
| **6 — Pilot hardening** | A staging-ready MVP | Security sweep; monitoring, alerts, audit review, backups and restore, load tests, runbooks, deploy and rollback rehearsal; public verification; responsive and mobile polish | No open critical or high · restore and rollback demonstrated · pilot UAT passes · N and X recorded in the targets ADR (§4.5) |

## 6. Phase 0 in detail

1. **Re-observe the baseline.** `cd backend && pytest`, plus Ruff and mypy. Confirm green now. Record the result, the date, and the commit.
2. **Resolve `npm test`.** Either set `"test": "tsc --noEmit && next lint"` as a zero-dependency placeholder, or adopt Vitest — which is a **governed dependency addition** requiring a recorded approval under Article XI §4. Choose deliberately; do not drift into one by writing code.
3. **CI.** Add `backend-ci.yml` and `frontend-ci.yml`. Make them green on a pull request. **Add them as reviewed files, one change at a time** — a bulk copy of workflow files is an unreviewed grant of automation authority and is prohibited by Article XII §4.
4. **Branch and PR checks.** Require CI and review before merge. One bounded context per change.
5. **Local Docker** workflow verified end to end by someone who has not run it before.
6. **Keycloak** realm exported as code and committed; secrets moved to a manager; dev mode off.
7. **`StoragePort` skeleton and R2 adapter** (§7.2), so Evidence has a seam from the first day rather than a retrofit on the last.
8. **Compute provider** chosen at deploy time — storage is already decoupled, so this decision is not urgent and should not be rushed. *Resolved administratively, 2026-07-30 (regularised under GD-006): **AWS**. `infra/terraform/versions.tf` declares the provider (region only, no resources). Formally captured at `docs/adr/ADR-024-delivery-platform-and-infrastructure-decisions.md` (Proposed, 2026-07-30) — see §11.1.*

**Gate:** clean tree · CI green · repeatable local environment · staging design approved → Phase 1.

## 7. Phase 1 in detail — Registry ownership and status history

Implements the registry ownership ADR. **Do not touch B4 or Spatial in this phase.**

### 7.1 Data model and migration

New append-only tables owned by Registry — `parcel_ownership_history`, `parcel_status_history`.

Minimum columns: `id`, `tenant_id`, `parcel_id`, `asserted_holder_ref`, `basis` (the document or authority the assertion derives from), `recorded_by`, `recorded_at`, `audit_ref`, `supersedes_id` (nullable).

**Append-only. Corrections add a row** (Article VII §6). The Parcel aggregate keeps its **current** owner reference and its domain contract is **unchanged**. The migration ships its RLS and tenant policy **in the same migration** (Article VIII §2) and has a **tested `down`** (Article XI §3). Rehearse the rollback on a staging-like database before merge, not after.

### 7.2 StoragePort — introduced now, used by Evidence in Phase 3

Define `StoragePort`: `put` / `get` / `list`, plus `putImmutable(retention)` or an equivalent lock capability, plus `wormGrade()` returning `compliance` or `governance`. Implement the R2 adapter — Bucket Locks map to `governance`. **No context calls a storage SDK directly** (Article X §5).

### 7.3 Events and audit

Registry emits `ParcelOwnershipRecorded`, `ParcelOwnershipChanged`, `ParcelStatusChanged`. Every change writes to the **B1 audit chain**, attributable to an authenticated actor (Article VIII §1). Every history row carries a resolvable `audit_ref` (Article VIII §3).

### 7.4 Access

All reads and writes of history resolve through the **single authorisation path** — the PDP and its enforcement points (Article X §3). **No table-level bypass. No exempted internal caller.**

### 7.5 The non-adjudication safeguard

Schema, API and UI present history as **recorded assertions of ownership**, each with its basis and provenance. **No field, label, response, export, or notification asserts title.**

### 7.6 Test matrix — all observed, none assumed

- Duplicate and append correctness.
- Append-only enforced — an in-place update is rejected, and there is a test that proves it.
- **Cross-tenant isolation** — tenant A can neither read nor write tenant B's history. Positive **and** negative cases.
- An audit entry is created for every change, and `audit_ref` resolves.
- Events emitted with the correct payload against the published contract.
- Migration **up and down**; rollback rehearsed.
- Parcel aggregate regression — current-owner behaviour unchanged.
- **Non-adjudication wording check** — an automated check that fails the build on ownership-adjudication language in responses and user-facing text. This is required by Article IV §4; it is not optional and not deferrable.
- PII and retention — superseded rows retained, access audited. **Retention and erasure posture per counsel. Log the item; do not silently implement erasure** (Article VII §6).

**Gate:** every item in §7.6 observed green · `/review` clean → Phase 2.

## 8. Phases 2 to 6 — rules that hold throughout

9. **Kernel first** — identity, registry, spatial, evidence before marketplace, enterprise and growth (Article X §4).
10. **Integration by contract** — contexts own their data; events between contexts; no cross-context transactions; unified views are read-model projections (Article X §2, Article V).
11. **F1 before F2** — the frontend authenticates a real user through Keycloak and makes one authorised API call before any parcel-journey UI is built on top of it.
12. **Evidence through the port** — sealed writes go through `StoragePort`; the active WORM grade is recorded and escalated to a compliance-grade backend if the pilot requires it, without code change (Article VII §3).
13. **Seams declared** — any knowingly provisional component records that fact at the seam (Article X §6).
14. **The boundary holds at every phase** — no phase, however late and however pressed, ships a feature that adjudicates (Article IX §3).

## 9. Definition of Done and phase gates

*Carried by reference to `docs/DOD.md` and `docs/PHASE_GATES.md`, which govern. This section is a summary and, under LV-000 v1.8 Article XIII §3, it loses to those documents wherever it differs from them.*

- **Feature (Tier 1)** — requirements met; authorisation through the single PDP/PEP path; unit, integration and end-to-end tests observed green; RLS shipped with any new entity; performance targets met; documentation updated in the same change; scoring fails safe on missing data; deployable to staging with a rollback.
- **Context (Tier 2)** — every feature at Tier 1; cross-context integration tested; phase gate passed; the DoD review logged before merge.
- **Pilot (Tier 3)** — the MVP journeys at §3 complete end to end; deferred items still out of scope; pilot targets met; restore and rollback demonstrated; zero open critical or high findings.
- **Phase gates** — no phase begins until the current phase has passed architecture, security, testing, performance, documentation and deployment review.

## 10. Decisions still owed

These are decisions, not code. **The build proceeds around them and stops only at the gate that needs them.**

| Decision | Needed by | Note |
|---|---|---|
| Pilot jurisdiction, surveyor eligibility, source-data-authority MOU | Phase 4 | From the anchor-tenant conversation. *Previously cited as "LV-013" — that citation is withdrawn and re-anchored to LV-017, the Go-to-Market Strategy. LV-013 is the repository's protected Market Intelligence Report and was never the source of this item* |
| Data residency and required WORM grade | Phase 3 | Selects the sealed-evidence adapter. Note that the escalation itself needs no code change (§4.2) |
| N and X pilot-success numbers | Before Phase 6 opens | Recorded in the pilot-targets ADR. The gate check is that the record exists (§4.5) |

## 11. Architecture Decision Records

### 11.1 The three to be raised

| Working title | Content | Proposed number |
|---|---|---|
| Registry Ownership and Status History | §4.1 and §7 | ADR-023 — raised, Accepted 2026-07-30 |
| Delivery Platform & Infrastructure Decisions | §4.2 to §4.4 — StoragePort, R2, WORM grades, Keycloak, Paystack, the AWS compute decision, and the secrets manager (undecided) | ADR-024 — raised, Proposed 2026-07-30 |
| Pilot Non-Functional Targets | §4.5, including the N and X recording obligation | ADR-025 — not yet raised |

### 11.2 The numbering floor

The proposed numbers **assume the highest existing ADR is 022**. LV-000 v1.8 Schedule 4 §S4.1 records that this is unconfirmed: the root `CLAUDE.md` reports the highest at 017, while the extraction record shows ADR-022 governing shipped B4 Slice 2 code. **Confirm by reading `docs/adr/` before raising these**, and renumber upward if the floor is different. Do not renumber downward into an occupied range.

> **Resolved administratively, 29 July 2026, regularised under GD-006** (per LV-000 v1.8 Schedule 4, confirmed-by-observation note): the floor is **022** (`docs/adr/` contains ADR-001 through ADR-019, ADR-021, and ADR-022; ADR-020 is deliberately vacant). ADR-023/024/025 as proposed above are therefore the correct next numbers and require no renumbering.

### 11.3 ADR-020 stays vacant

ADR-020 is **not** to be filled by these three, and **not** to be filled by any automatic numberer. **The vacancy is the record that a question is open.** Anything that quietly consumes it destroys that record.

### 11.4 No automated numbering

No script may allocate ADR numbers. Allocation is a governed act performed by a person who has read `docs/adr/` (Article XII §4).

## 12. Start here

15. **PR-0.1** — re-observe backend green (`pytest`, Ruff, mypy); record the result with date and commit.
16. **PR-0.2** — set the `npm test` script (placeholder, or Vitest with a recorded approval); clean the working tree.
17. **PR-0.3** — add CI workflows, reviewed individually; make them green.
18. **PR-0.4** — branch protection and PR checks; Keycloak realm-as-code and secrets.
19. **PR-0.5** — read `docs/adr/` and settle the numbering floor (§11.2) and finding S4.1.
20. **PR-1.x** — implement the ownership and status-history ADR per §7: one change carrying the migration, RLS, events, audit and tests. `/review` before merge.

**Phase 1 does not begin until Phase 0's gate is met. B4 Spatial does not begin until Phase 1's gate is met.** That sequence is Article X §4, and it is not negotiable against a delivery date.

## Enactment

This instrument is ratified on 29 July 2026 under GD-004 and is in force from that date. It carries no hold and no condition.

It supersedes the withdrawn *Proposed Amendment to `docs/REBUILD_PLAN.md`* issued 28 July 2026, which is retained as a historical record of the four blocked citations and how they came to be cleared.

**Amend, never erase.**

*LandVault preserves and verifies land evidence. It does not decide who owns land.*
