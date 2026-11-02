# GD-014 READINESS REPORT

**Type:** Point-in-time governance readiness review, produced against `origin/main` at commit
`0bcc18eae463ec30e8f846357858529686d16747`, preserved as the readiness record alongside the draft
`docs/GD-014-gd013-orm-rollback-exception-authorization.md`. GD-014 was subsequently ratified by the
Governance Authority on 23 September 2026 (ACCEPTED, IN FORCE) — see the "Note on ratification" in §1
below. This report's findings are preserved as a historical record of the pre-ratification review
process, not rewritten as a post-ratification implementation-completion report.

## 1. Baseline and Numbering

- `origin/main`: `0bcc18eae463ec30e8f846357858529686d16747` — the GD-013 ratification squash commit
  (PR #37), fetched fresh for this drafting, and re-fetched and re-confirmed unchanged during the
  subsequent formal review and this remediation pass.
- GD-014 availability: confirmed by direct search of every `docs/GD-0*.md` file and the Article XVI
  Log — highest existing entry is GD-013; no `GD-014` reference exists anywhere in the repository.
  Re-confirmed still unused at every subsequent pass.

**Note on document history**: this readiness report was first produced before a formal Governance
review of the draft occurred. That review returned `GD-014 GOVERNANCE REVIEW PASS WITH REQUIRED
TEXTUAL REMEDIATION`, identifying one factual defect (an incorrect pull-request citation in the
draft's §1) and requiring the draft's required-proof paragraph to name each mandatory obligation
explicitly. Both have since been corrected in the draft itself; this report is updated accordingly in
§5 and a new §5A below, preserving every original finding rather than deleting it. **At every point up
to and including the final ratification-readiness verification, ratification had not yet occurred** —
GD-014 remained Proposed throughout that history.

**Note on ratification.** The Governance Authority expressly ratified GD-014 on 23 September 2026,
against the exact remediated text that passed the final ratification-readiness verification described
above. GD-014's governance status is now **ACCEPTED — IN FORCE**. This local documentation transcription
of that ratification (this report and the draft's own Status line and Article XVI entry) is performed
under separate, bounded execution authority; no Git commit, push, pull request, or merge of this
documentation change has been authorized. Ratification does not itself certify that any implementation
relying on GD-014's exception has satisfied the seven mandatory proof obligations in §5/§5A below —
implementation acceptance remains outstanding, distinct from, and not established by, this ratification.

## 2. Why This Decision Exists

An independent, formal Governance review of the uncommitted GD-012/GD-013 implementation (not the
implementing engineer's own report, which the review explicitly declined to accept at face value)
traced the correction endpoint's exception-translation code against the actual source and concluded
the implementation, as written, is **not authorised** — it calls `await service.session.rollback()`,
a mechanism `GD-013` §4 explicitly states "none is authorized to add." The review also established,
using this session's own actual observed `sqlalchemy` behavior, that the rollback call is genuinely
necessary: without it, the losing request in a concurrent-correction race receives an unhandled 500
(`sqlalchemy.exc.PendingRollbackError`) instead of the 409 `GD-012`/`GD-013` require. This draft exists
to resolve that specific, narrow authority gap — not to relitigate any other part of the review's
findings, all of which classified the remainder of the implementation as compliant.

## 3. Sources Inspected

- `docs/GD-012-evidence-actor-attribution-http-implementation-authorization.md` — §4, §5, §6, §7, §8,
  §10, §11 re-read for this drafting.
- `docs/GD-013-gd012-commit-boundary-and-concurrent-correction-exception-authorization.md` — §3, §4,
  §5, §6 re-read in full.
- `docs/LV-000-constitution.md`, Article XVI — full Log, GD-001 through GD-013.
- The formal GD-012/GD-013 implementation governance review's own findings (this session's immediately
  preceding turn) — the sole basis for this draft's factual claims about the implementation; not
  independently re-verified against the implementation worktree during this drafting task, per this
  task's own instruction not to touch the implementation worktree.

## 4. Amendment and Supersession Analysis

**What is amended:** exactly one clause of `GD-013` §4 — the sentence "no code path in this exception
guarantees that, and none is authorized to add one." No other sentence, section, or provision of
`GD-013` is touched. `GD-012` is not amended at all; `GD-014` relies on it only for context (the
two-endpoint scope, the §7/§10 item 16 coherent-4xx requirement `GD-013` §4 already exists to satisfy).

**What is superseded:** nothing is superseded in the Article XVI §2 sense of a full prior decision
being qualified beyond one clause — `GD-013` remains, in every other respect, the operative text
governing the commit-boundary exception (§3) and the dual-diagnostic 409 predicate (§4's other
conditions). `GD-014` is best understood as a **correction-and-narrow-exception** decision, structurally
identical in kind to `GD-011`'s own relationship to `GD-009` (lifting one specific, named suspension
without reopening the decision it qualifies) and to `GD-013`'s own relationship to `GD-012` (granting
narrow exceptions to specific clauses while leaving the rest of the decision's text as the governing
authority).

**Why a full re-ratification of GD-013 is not proposed:** `GD-013`'s own drafting-time verification was
sound as far as it went (real PostgreSQL, real HTTP, a genuine three-case proof for the commit-boundary
exception) — it simply did not exercise the one code path (ORM `Session.flush()`, as opposed to a raw
Core connection) where the gap was later found. Re-drafting the entire decision would restate dozens of
paragraphs that remain accurate; a narrow, explicitly-scoped amendment is more precise about what
actually changed and why, consistent with Article XVI §2's "amended only by a later numbered decision
that names it" discipline, which does not require wholesale restatement.

**Textual precision check:** the amended clause is quoted verbatim in the draft's §3, and the draft's
§5 replaces it with an equally explicit, bounded authorization rather than a vague relaxation — anyone
reading `GD-013` §4 alongside `GD-014` §3–§5 can determine exactly what changed and what did not.

## 5. Test-Obligation Matrix

Updated to match the draft's own strengthened, numbered required-proof list (§5, items 1–7), added
during textual remediation. Every row below is an **implementation-acceptance obligation** — none is a
claim that the corresponding test already exists or has passed, except where explicitly marked
otherwise.

| # | Obligation | Applies to | Real PostgreSQL required? | Status per the formal review |
|---|---|---|---|---|
| 1 | Forced final-commit failure → non-2xx, no durable row/audit event | Record **and** correction endpoints | Yes | **Record endpoint only tested** (`test_forced_final_commit_failure_yields_non_2xx_and_no_durable_rows`); correction endpoint is an outstanding gap. |
| 2 | Commit completes before successful response | Record **and** correction endpoints | Yes | **Record endpoint only tested** (`test_commit_completes_before_successful_response_is_returned`); correction endpoint is an outstanding gap. |
| 3 | Exactly one shared session per endpoint's dependency graph | Record **and** correction endpoints | Yes | **Record endpoint only tested** (`test_one_shared_session_for_the_whole_request`); correction endpoint is an outstanding gap. |
| 4 | Matched conflict → 409, no durable losing row/audit event | Correction endpoint (the only one with a lineage-supersession race) | Yes | **Already tested and passing** (`test_competing_concurrent_corrections_one_wins_one_gets_409`), verified via an independent connection. |
| 5 | Rollback-call failure not suppressed/converted to a false 409 | Correction endpoint's exception handler, specifically the `rollback()` call §5.4 authorizes | No — hermetic sufficient | **Not yet tested** — confirmed by fresh grep during the formal review; an explicit outstanding obligation. |
| 6 | Unrelated `IntegrityError`s remain outside the translation | Correction endpoint's exception handler | Hermetic sufficient for the predicate; real PostgreSQL additionally required for the CHECK-constraint/cycle-trigger interaction | **Already tested and passing** at both layers (`test_matching_constraint_name_but_wrong_sqlstate_not_matched` et al.; `test_self_supersession_attempt_yields_5xx_not_409`). |
| 7 | Rejected mutations (400/401/403/404/422) leave nothing durable | Both endpoints, every rejection path | No — hermetic sufficient | **Not yet tested** — confirmed by fresh grep during the formal review; an explicit outstanding obligation. |

## 5A. Completed Technical Evidence vs. Outstanding Implementation Tests

**Completed, execution-verified evidence** (established before this draft existed, re-confirmed during
the formal review against this session's own actual recorded command output, not merely asserted):
the `sqlalchemy.exc.PendingRollbackError` finding itself (§4 of the draft); the dual-diagnostic
predicate's correctness (row 6 above); the concurrent-correction race, its winner/loser durability
outcome, and the 409 status (row 4 above).

**Outstanding — required before implementation acceptance, not before ratification** (per the formal
review's own resolution of "Question B," preserved here): rows 1, 2, 3, 5, and 7 above. Ratifying
GD-014 authorizes the mechanism these tests would exercise; it does not itself supply the tests. This
mirrors this repository's own established practice for `GD-009`, `GD-012`, and `GD-013`, each of which
was ratified against a stated test *obligation*, with actual execution verified at the subsequent
implementation-review stage.

## 6. Unresolved Governance Questions

1. **Whether a non-`HTTPException` exception-plus-handler alternative (routing through `get_db_session`'s already-authorized `except Exception: rollback()` branch, per the formal review's own §4.D) could achieve the same properties without any new authority at all.** This draft does not require that alternative be attempted first, and does not foreclose it — if the implementing engineer verifies it works, this Decision's own authorization becomes unnecessary for that specific mechanism, though the corrected factual record in §4 (about ORM `Session` behavior generally) would still be worth preserving for future implementations that might not use that alternative pattern. Governance should decide whether to require the alternative be attempted before ratifying this narrower fix, or to ratify this Decision now and treat the alternative as a possible future simplification.
   *Resolved by the formal review's own "Question A" analysis, preserved here rather than restated: the
   alternative would itself require touching `main.py`'s app-level exception-handler registration —
   arguably outside "entirely in the new router module" — and remains entirely untested. The review
   concluded it should not be required as a precondition to ratifying this narrower, transparent
   amendment. This question is treated as resolved for drafting purposes; Governance retains final say.*
2. **Whether the "rollback failure must not be hidden behind a misleading 409" condition (§5.4) is adequately specific.** The draft requires the failure to "propagate as-is," which the current (unratified) implementation already satisfies by construction (the `rollback()` call is not wrapped in its own try/except) — but this has not been proven by an executed test, only by code inspection. Governance may wish to require the test obligation in row 7 of §5 above as a condition of this Decision's own acceptance, not merely of a later implementation-readiness pass.
   *Resolved by the formal review's own "Question B" analysis, preserved here rather than restated: the
   test is a mandatory implementation-acceptance obligation (now item 5 in the draft's own numbered
   required-proof list), not a ratification precondition — consistent with how GD-009/GD-012/GD-013
   were each ratified against a stated obligation, verified later.*
3. **Whether this Decision's correction of GD-013's factual record (§4) should also prompt a documentation-only note on GD-013 itself**, or whether recording the correction here, in a later-numbered decision that names GD-013 per Article XVI §2, is sufficient on its own. This draft assumes the latter, consistent with how GD-013 itself corrected `_verify_actor_reference`'s behavior via its own text rather than editing GD-012.
   *Resolved by the formal review's own "Question C" analysis, preserved here rather than restated:
   GD-013's ratified text must not be edited — doing so would itself violate Article XVI §2's "never
   edited in place" discipline. GD-014 as drafted is the correct and sufficient mechanism.*

None of these three questions blocked the draft from formal review, and none was found, by that review,
to require a different resolution than originally proposed here. They remain recorded for the
historical completeness of this readiness record, not as open items still awaiting an answer.

## 7. Exact Files Created

As of the original drafting and formal-review passes: exactly two, both uncommitted, both new (no
existing file modified):
- `docs/GD-014-gd013-orm-rollback-exception-authorization.md`
- `docs/GD-014_READINESS_REPORT.md`

Created in a fresh, detached worktree (`Development-Plan-gd014-draft`, checked out at `origin/main`'s
`0bcc18e...`), consistent with the pattern already used for `GD-012`'s and `GD-013`'s own drafting, to
avoid placing uncommitted material inside the GD-012/GD-013 implementation worktree
(`Development-Plan-gd012-http`, branch `feat/gd012-evidence-attribution-http`, not touched by this
task) or the governance-protected preserved-prototype worktree
(`feat/gd009-batch1-transactional-audit`, likewise untouched).

**Update — ratification transcription.** Following the 23 September 2026 ratification, a separately
authorized transcription pass modified exactly one additional, previously-existing file in this same
worktree — `docs/LV-000-constitution.md` (a pure insertion of the GD-014 Article XVI entry, no other
line touched) — bringing the total changed/untracked file count in this worktree to three. Neither the
implementation worktree nor the protected GD-009 prototype worktree was touched by that transcription.

## 8. Working-Tree State

As of the original drafting task: the drafting worktree contained only the two new files above,
untracked, unstaged, uncommitted. No existing governance document, ADR, LV-000, backend code, frontend
code, test file, or migration was modified, staged, or committed. No branch was created; the worktree is
in a detached-HEAD state at `origin/main`. No push, commit, or PR was made. The implementation worktree
(`Development-Plan-gd012-http`) was not entered or modified during this drafting task.

**Update — ratification transcription.** The worktree now additionally contains a modification to
`docs/LV-000-constitution.md` (the GD-014 Article XVI insertion described in §7 above), made under
separate, bounded execution authority following ratification. As before: no branch was created or
changed, no file was staged, no commit was made, no push occurred, no PR was opened, and the
implementation and protected GD-009 prototype worktrees remain untouched.

## 9. Recommendation for Governance Review

The draft is narrowly scoped, textually precise about what it amends and what it leaves untouched,
grounded in the formal implementation review's own findings rather than assertion, and discloses three
open questions for Governance's own judgment rather than resolving them unilaterally. On that basis,
this report originally concluded:

**GD-014 READY FOR FORMAL GOVERNANCE REVIEW**

**Post-review update.** A formal Governance review of this draft has since been conducted and returned
`GD-014 GOVERNANCE REVIEW PASS WITH REQUIRED TEXTUAL REMEDIATION` (one factual defect — an incorrect
pull-request citation — and a request to state the required-proof obligations explicitly, item by
item). Both have been corrected in the draft itself, per §1 and §5/§5A above. At that point in this
document's history, GD-014 had not been ratified and remained marked Proposed; the accurate status of
this document at that time was:

**GD-014 TEXTUAL REMEDIATION COMPLETE — READY FOR FINAL VERIFICATION, NOT YET RATIFIED**

**Post-ratification update.** A final ratification-readiness verification was subsequently conducted
against this same baseline and returned `GD-014 FINAL VERIFICATION PASS — READY FOR GOVERNANCE AUTHORITY
RATIFICATION`. The Governance Authority then expressly ratified GD-014 on 23 September 2026. GD-014's
governance status is now **ACCEPTED — IN FORCE**; its Article XVI Log entry has been transcribed into
`docs/LV-000-constitution.md` under separate, bounded execution authority. This ratification does not
certify, and this report does not claim, that the seven mandatory proof obligations in §5/§5A above have
been satisfied by any implementation — those remain outstanding implementation-acceptance requirements.
The current, accurate status of this document is:

**GD-014 RATIFIED AND TRANSCRIBED — IMPLEMENTATION ACCEPTANCE OBLIGATIONS OUTSTANDING**
