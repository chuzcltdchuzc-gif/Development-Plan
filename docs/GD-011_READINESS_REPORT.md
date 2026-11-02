# GD-011 Readiness Report — GD-009 Batch 1 Resumption Authorization

**Type:** Point-in-time governance readiness review, produced against `origin/main` at commit
`54af267bda08e5dc88d052a3cac126567cea3b03` (the GD-010 DAG-aware audit verifier's squash-merge
commit, PR #33). Independently tests `docs/GD-011-gd009-batch1-resumption-authorization.md` ("the
draft GD") against the questions this drafting task was asked to answer. **The draft GD's own text is
authoritative for its content; this report is authoritative only for the specific findings below, at
the time it was written** — the same convention every prior readiness report in this repository has
already established.

**Date:** 2026-09-15

**Status of the reviewed draft:** Proposed — drafted for review. Not ratified. **This report is not a
ratification and does not itself authorize resumption of GD-009 Batch 1 or any implementation.**

## 1. Is the prerequisite actually satisfied?

**Pass, independently re-verified, not assumed.** `ADR-030` confirmed ACCEPTED/IN FORCE (2026-09-13).
`GD-010` confirmed ACCEPTED/IN FORCE (2026-09-14). Its implementation, PR #33, confirmed **MERGED**:
squash commit `54af267...`, single parent `a093c497...` (the GD-010 ratification squash, PR #32),
current tip of `main`, tree-identical (`git diff` empty) to the formally human-approved PR head
`73ea2ae...`, all required CI (`pytest / ruff / mypy`, `typecheck / lint / test / build`) green on the
squash commit itself, zero secret/credential material in the landed diff (400-line diff scanned
directly). Exact landed files: `backend/app/kernel/audit.py`,
`backend/tests/test_audit_dag_verifier.py` — nothing else. This session independently reached the
classification `POST-MERGE VERIFIED — GD-010 DAG VERIFIER ACTIVE ON MAIN` before this drafting began,
rather than accepting an assertion that it had.

## 2. Is the next GD number correct?

**Pass.** Direct search of every `docs/GD-0*.md` file and of `docs/LV-000-constitution.md`'s Article
XVI Log confirms entries GD-001 through GD-010 exist and no GD-011 or higher exists anywhere. GD-011
is the correct next number, confirmed by repository reality, not assumed from the task's own
suggestion.

## 3. Does the draft correctly scope itself as resumption-only, not re-authorization?

**Pass.** §5/§6 restate `GD-009` §5's original scope verbatim in substance (the transaction-coupled
capability, the exact two call sites) and explicitly state no broader authority is created. §2's
Purpose section states this in the negative as well ("does not re-authorize, expand, or narrow...").
The draft does not restate or duplicate `GD-009`'s full text — it names and relies on it, the same
citation discipline `GD-007`/`GD-009` themselves already established for qualifying a prior decision
without rewriting it.

## 4. Is the authority chain accurately stated?

**Pass, independently re-derived.** `ADR-029` → transaction semantics (unaffected). `GD-009` →
Batch 1 authorization + concurrency hard stop (§11). `ADR-030` → DAG topology (resolves the
architecture question the hard stop required). `GD-010` → verifier implementation authorization,
now merged and post-merge verified. This Decision → lifts the specific suspension, nothing more. Each
link checked directly against the cited document's own text in this session, not carried forward from
memory.

## 5. Does the draft correctly re-frame the concurrency-test evaluation criterion?

**Pass, and this is the one place this report independently verified the draft's reasoning rather
than accepting it at face value.** `GD-009` §15 item 10's original test cases were written against a
strict-linear evaluation criterion (a shared predecessor = failure). §15 of the draft correctly
identifies that the *test cases themselves* (transactional-vs-transactional,
transactional-vs-eager, repeated execution) remain valid and mandatory, but the *pass/fail criterion*
must change to the six DAG invariants `GD-010` now enforces — a shared `prev_hash` between two
independently valid entries is expected, not a defect. This is the correct, load-bearing distinction:
re-running `GD-009`'s original tests unchanged, under the original criterion, would necessarily
"fail" a legitimate fork and could wrongly suggest the prerequisite was not actually satisfied. The
draft avoids that trap explicitly.

## 6. Does the draft preserve the verifier/hash-semantics boundary?

**Pass.** §10/§11 state plainly that `verify_chain()`, its six invariants, and `_compute_hash`/
`GENESIS_HASH` are `GD-010`'s settled, merged, post-merge-verified implementation, not reopened by
this Decision, with an explicit stop-and-return instruction if implementation reality proves
otherwise — the same "extract, do not alter" / stop-and-return discipline `GD-009`/`ADR-030` already
established for adjacent boundaries.

## 7. Does the draft correctly treat the preserved branch as evidence, not production code?

**Pass.** §17/§18 state this explicitly and direct reconstruction in a fresh worktree/branch off
current `main`, using the preserved branch only as reference — consistent with `GD-010` §21's
identical treatment of the same branch, and consistent with this session's own repeated read-only
verification that the branch's uncommitted diff (5 files, ~225 insertions, pre-`ADR-030` vintage) has
not been touched. The draft does not authorize deleting, rewriting, or force-cleaning that branch.

## 8. Are the migration/dependency stop-gates preserved verbatim in effect?

**Pass.** §12/§13 restate `GD-009`'s own stop phrases with `GD-009 BATCH 1 BLOCKED —` prefixes
unchanged in substance, consistent with `GD-010` §14/§15's identical pattern for its own gates.

## 9. Is the ADR-028 gate still correctly restated as unaffected?

**Pass.** §19 grants no router/DTO/OpenAPI/generated-client/frontend authority and restates the
original `GD-009`/`ADR-028` sequencing (Batch 1 implement → test → formally review → squash merge →
post-merge verify, *then* a further separate Governance act) without shortening it.

## 10. Is the GD-010 8-vs-9 discrepancy handled correctly?

**Pass.** §22 records the discrepancy (confirmed independently in this report too: exactly 8
pre-existing files, re-confirmed by direct grep against current `main`) as non-blocking and explicitly
declines to correct `GD-010` inside this Decision, consistent with the task's own instruction not to
mix a documentation clerical correction into a substantive Decision.

## 11. Pre-mortem — findings against each named failure mode

- **Atomicity still false**: mitigated by §14's restatement of `GD-009` §8's transaction invariant as
  a required proof, not merely an implementation goal; the resumed implementation must demonstrate it
  with real-Postgres tests before being considered complete.
- **Ambient behavior leakage**: mitigated by §7's restatement of `GD-009` §5's explicit-opt-in
  requirement and its enumerated list of prohibited ambient mechanisms.
- **DAG regression** (Batch 1 accidentally restoring strict-linearity assumptions): mitigated by §9's
  explicit list of mechanisms this Decision does not authorize (locks, `SERIALIZABLE`, sequence,
  `UNIQUE(prev_hash)`, retry, outbox) and by §15's corrected evaluation criterion.
- **Prototype contamination** (stale pre-`ADR-030` code copied wholesale): mitigated by §17/§18's
  explicit reconstruction-not-incorporation directive.
- **Scope creep** (more than two events migrated): mitigated by §6's closed enumeration and §20's
  explicit restatement that the other 52 call sites remain out of scope.
- **Denial durability regression**: mitigated by §8's restatement of `GD-009` §9's regression guard
  and §14's inclusion of the same tests as a mandatory proof obligation.
- **API creep** (ADR-028 HTTP surfacing before the audit prerequisite completes): mitigated by §19's
  explicit restatement of the unshortened sequencing gate.

No pre-mortem finding identifies a gap in the draft's own text; each named risk has a corresponding,
specific mitigating clause. This does not substitute for the resumed implementation actually
satisfying those clauses — only for the draft correctly anticipating each risk.

## Summary

| Question | Result |
|---|---|
| Prerequisite (ADR-030 + GD-010 merged/post-merge-verified) actually satisfied | Pass |
| Next GD number correct (GD-011) | Pass |
| Scoped as resumption-only, not re-authorization | Pass |
| Authority chain accurately stated | Pass |
| Concurrency-test evaluation criterion correctly re-framed for DAG semantics | Pass |
| Verifier/hash-semantics boundary preserved | Pass |
| Preserved branch treated as evidence, not production code | Pass |
| Migration/dependency stop-gates preserved | Pass |
| ADR-028 gate correctly restated as unaffected | Pass |
| GD-010 8-vs-9 discrepancy handled correctly (recorded, not corrected here) | Pass |
| Pre-mortem failure modes each have a corresponding mitigating clause | Pass |

This report's authority is limited to the findings above, at this point in time, against the draft
GD's text as drafted. It does not ratify the draft, does not authorize resumption of GD-009 Batch 1 or
any implementation, and does not itself constitute the Governance Decision it reviews.
