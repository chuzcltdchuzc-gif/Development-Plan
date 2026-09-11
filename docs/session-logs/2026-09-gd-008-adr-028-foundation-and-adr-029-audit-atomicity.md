# Session Log — GD-008 Article XVI Reconciliation, ADR-028 Evidence Attribution (Drafting Through
Foundation Implementation), and the ADR-029 Audit-Atomicity Architecture Decision

**Type: historical record only. This is not a governance document, not an ADR, not part of the
Constitution, and not part of the Bible volume numbering.** It is a plain narrative account of one
Claude Code conversation, kept so a future reader has context on *why* certain documents and code
changes were produced and in what order — never as evidence of what any document or the codebase
currently says. If anything below conflicts with the actual, current content of any governing
document, any ADR, or the code itself, **those are correct and this log is simply out of date.**
This log is not updated retroactively when things change after the fact; it records what happened
at the time, not what is current now.

**Date range covered:** 2026-09-08 through 2026-09-11.

---

## 1. GD-008 Article XVI reconciliation (PR #24)

The conversation opened mid-stream on a governance-authority instruction to implement GD-008's
record into `docs/GD-008-...md` and Article XVI, on the premise that four related documents existed
as uncommitted local files. Verification found that premise false: the four documents already
existed, already committed, on an existing branch with an already-open PR (#24), and the working
tree was clean. This was reported as a **governance record conflict** rather than silently proceeding
to open a second, competing PR for the same decision. Governance Authority resolved the conflict by
naming PR #24 as the sole canonical vehicle and authorizing a reconciliation commit onto its
existing branch, adding only the Article XVI log entry (GD-008, one paragraph, following the same
convention GD-006/GD-007 already used) without touching GD-001 through GD-007. PR #24 was reviewed,
approved, and squash-merged; post-merge verification confirmed the squash commit landed cleanly,
Article XVI held exactly one GD-008 entry, and no application/runtime file was touched.

## 2. ADR-028 — drafting, review, remediation, and ratification (PR #26)

GD-008 authorized exactly one further technical activity: drafting ADR-028 (Evidence Actor and
Commissioning Provenance). The draft settled on a separate, append-only `EvidenceActorAttribution`
relationship — bounded to `ORIGINATED_BY`/`REVIEWED_BY`/`COMMISSIONED_BY` — rather than adding
scalar actor fields to `EvidenceRecord` itself, reusing ADR-023's own append-only/correction
mechanism rather than inventing a new one, and distinguishing four actor-identification states
(`INTERNAL_PRINCIPAL`/`EXTERNAL_NAMED`/`HISTORICAL_ASSERTED`/`UNKNOWN`).

A formal Governance review found the draft architecturally sound but requiring five textual
clarifications: a bounded field distinguishing the four identification states more explicitly, an
explicit "immutable snapshot, optional reference" rule, explicit supersession-integrity invariants
(no self-supersession, no cycles, one successor per row), an `ORIGINATED_BY` non-implication list
matching the ones already given for the other two roles, and an explicit statement that ADR-023's
*mechanism* was reused without its *ownership meaning*. All five were applied directly to the ADR
text; the remediation was independently re-verified rather than assumed complete.

Governance Authority then ratified ADR-028 in its own words, restating (not amending) the drafted
text and adding two points of genuine precision — a distinction between a single-row `CHECK`
constraint and a genuinely cross-row invariant no plain `CHECK` can express, and an explicit
external/legal boundary statement. The ratification was written into the ADR file itself (status
line, a new Ratification Record section, an expanded Approval Gate), and — since the ADR had been
drafted as uncommitted local files with no branch yet — committed to a fresh branch and opened as
PR #26. It was reviewed, approved, and squash-merged; post-merge verification confirmed the ADR's
`ACCEPTED` status, its explicit exclusions, and GD-008's continued authority were all intact on
`main`.

## 3. ADR-028 foundation implementation, the cycle-defect red-team, and two remediation rounds
(PR #27)

Governance next authorized a bounded, non-HTTP implementation "foundation" for ADR-028: the
`EvidenceActorAttribution` domain value object, migration `0014` (the `evidence_actor_attributions`
table with RLS, append-only enforcement, and the actor-shape/uniqueness constraints the ADR
specified), a Postgres repository plus an in-memory fake, a `PrincipalTenantPort` mirroring the
existing cross-context read pattern, and an `EvidenceActorAttributionService` reusing
`EvidenceService`'s existing creator-or-governance authorization unchanged. Domain and service
tests were written and run hermetically; a live rehearsal against a local throwaway Postgres
database (the repository's already-established "create a throwaway DB, run the real Alembic chain,
drop it" convention) proved the append-only trigger, the self-supersession check, and — critically
— genuine concurrent-write behavior: two real concurrent transactions each attempting to supersede
the same row, with exactly one committing. This work was opened as PR #27.

A pre-human-review invariant red-team then tested the database layer directly rather than only
through the application service, and found a real defect: a single multi-row `INSERT` could
persist a two-row `supersedes_id` cycle, because PostgreSQL checks a non-deferrable foreign key at
the end of a statement rather than per row within it, and the `UNIQUE(supersedes_id)` constraint
does not catch a mutual pair (the two referenced values differ). This was reproduced directly
against real Postgres, not merely reasoned about, and reported as blocking human review rather than
downplayed. Governance authorized remediation on the same PR branch: a `BEFORE INSERT` trigger
walking the new row's ancestry and rejecting any lineage that would cycle back to itself, exploiting
the fact that PostgreSQL's per-row command counter makes each already-processed row of the *same*
multi-row statement visible to a later row's trigger — the exact mechanism the original defect had
exploited, now used to close it. The fix was verified by re-running the original attack.

A second, final database-boundary review then found two further gaps by testing directly rather
than trusting the first remediation's own claims: nothing enforced
`evidence_actor_attributions.tenant_id` matching the `tenant_id` of the `evidence_records` row its
`evidence_id` named (proven live: the ordinary application role, scoped correctly to its own
tenant, could still persist a row claiming to describe another tenant's Evidence), and the
cycle-rejection trigger's own depth ceiling failed *open* rather than *closed* — a lineage that
happened to exceed the bound would be silently permitted rather than rejected. Both were fixed: a
third trigger binding `tenant_id` to the referenced Evidence's own tenant, and a corrected
depth-ceiling check that rejects whenever the ancestry walk cannot be proven safe within the bound
rather than assuming it is. A first attempt at the depth fix itself introduced a real regression —
breaking the original cycle-detection comparison by requiring a not-yet-inserted row to exist for
the check — caught immediately by the existing regression test failing, and corrected before
proceeding. Both fixes were proven with controlled, non-destructive live tests (a temporarily
lowered depth bound on a throwaway database, never touching the real constant) and folded into the
permanent regression suite. PR #27 was reviewed, approved, and squash-merged; post-merge
verification re-ran every proof — the tenant-binding attack, the mutual-cycle attack, the
fail-closed depth ceiling, and the one-successor concurrency race — fresh against the merged `main`
state, not carried over from memory.

## 4. The audit-kernel atomicity reality audit and the ADR-029 architecture decision

With the ADR-028 foundation merged, Governance asked whether an audit-integrity issue flagged
during the PR #27 red-team — and explicitly deferred as "inherited... separately governable" —
actually needed its own architecture decision. A reality audit read the audit kernel's actual code
(`app/kernel/audit.py`, `audit_postgres.py`, `uow.py`) rather than relying on the prior report,
confirmed every one of 55 audit call sites across every bounded context resolves to the same
independently-committing store, and directly reproduced the concerning failure mode against real
Postgres: a business mutation was flushed, a real audit call committed, the surrounding transaction
was then forced to fail — and the audit entry survived, permanently, describing a row that never
existed. The audit also found this contradicted `ADR-007`'s own Accepted text, which promises every
domain event is written "atomically with the state change that produced it," and that the
repository already has a named convention (GD-006, GD-007) for reconciling exactly this kind of
discovered divergence, rather than a silent patch.

Governance then authorized drafting ADR-029 (Audit Transaction Semantics and Outcome Integrity) as
architecture only. The draft distinguishes four classes of audit information LandVault actually
produces — successful-mutation, denial, failure, and (unused) operational logging — argues ADR-007
Decision 1 was only ever a coherent requirement for the first class, and selects a split
architecture: successful-mutation audit rows stage into the caller's existing transaction with no
intermediate commit, while denial/failure audits keep the existing independent path unchanged. The
draft traced the *exact* mechanism behind the historical decision to avoid a shared session — not
merely restating it — finding that the real risk was an intermediate commit silently clearing a
transaction-scoped Postgres RLS setting for the rest of a request, a more precise account than the
reality audit's own looser description, and confirmed structurally that the selected design cannot
reintroduce it. A companion readiness report independently tested each of the ADR's central claims
against the actual code and an existing repository precedent (ADR-026's own accept/implement split)
before concluding the architecture was ready for review. Both documents were left uncommitted, as
architecture-only drafts requiring their own future ratification, and were not bundled into this
log's own commit.

## Files produced in this conversation, and their disposition at the time of writing

- Committed to `main` via PR #24: the Article XVI GD-008 entry.
- Committed to `main` via PR #26: ADR-028's ratification.
- Committed to `main` via PR #27: the ADR-028 evidence-attribution foundation (domain, migration
  `0014`, repository, service, and both regression-test suites), across three commits including two
  remediation passes.
- Left uncommitted, pending their own future governance action: `docs/adr/
  ADR-029-audit-transaction-semantics-and-outcome-integrity.md`,
  `docs/ADR-029_READINESS_REPORT.md`, and `docs/AUDIT_KERNEL_ATOMICITY_REALITY_AUDIT.md`.
