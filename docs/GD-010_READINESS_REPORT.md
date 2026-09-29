# GD-010 Readiness Report — Audit DAG Verifier Implementation Authorization

**Type:** Point-in-time governance readiness review, produced against `origin/main` at commit
`0275b483d1c4fcdd5de2cfeada3f8407cb6d8dd8` (the `ADR-030` ratification squash commit, PR #31).
Independently tests `docs/GD-010-audit-dag-verifier-implementation-authorization.md` ("the draft
GD") against the twelve questions this drafting task was asked to answer. **The draft GD's own text
is authoritative for its content; this report is authoritative only for the specific pass/fail
questions below, at the time it was written** — the same convention every prior readiness report in
this repository has already established.

**Date:** 2026-09-13

**Status of the reviewed draft:** Proposed — drafted for review. Not ratified. **This report is not
a ratification and does not itself authorize implementation.**

## 1. Can the six ADR-030 invariants be implemented with the current schema?

**Pass.** Re-checked directly, not merely restated: `audit_log`'s columns (`id`, `action`,
`resource_type`, `resource_id`, `decision`, `principal_id`, `payload`, `prev_hash`, `hash`,
`created_at`) already carry everything genesis/root validity, per-entry hash validity, referential
validity, reachability, acyclicity, and branch legitimacy each need — `hash` (unique, already
indexed as the primary lookup key by its constraint) and `prev_hash` (a plain string column) are
sufficient to build an in-memory hash-to-entry map and walk it. No invariant in §3 of the draft
requires a column, type, or constraint that does not already exist.

## 2. Is no migration required?

**Pass, independently re-derived.** `PostgresAuditStore.all_entries()` already returns every column
the six invariants need, in one query; nothing about validating referential integrity or reachability
requires a database-level constraint — both are read-time, in-memory checks against the already-
fetched entry set. The draft's own §14 stop-and-return condition
(`AUDIT DAG VERIFIER BLOCKED — MIGRATION AUTHORITY REQUIRED`) is a correct safety valve, not a
concession that one is expected.

## 3. Is no runtime dependency required?

**Pass.** The verifier is a pure, in-memory graph-validation pass over a single query result already
being fetched today — no queue, cache, or external service is needed for that. The draft's §17
correctly names, and correctly declines to introduce, Redis/background-workers/graph-databases/
external services/caching infrastructure as unnecessary for this problem's actual size (a hash-log
whose full content already fits in one `all_entries()` result set).

## 4. Do valid linear histories remain valid?

**Pass, structurally guaranteed, not merely hoped for.** A strictly linear history is the special
case where every entry's `prev_hash` matches exactly one other entry's `hash`, with a single root and
no branching — every one of the six invariants (§3 of the draft) is satisfied trivially by such a
structure, by construction, since a DAG-validating check is strictly more permissive than a linear-
only check, never less. The draft's §4 requiring this be *proven*, not merely assumed, against the
actual future implementation is the correct posture — a logically necessary property is still worth
testing explicitly, since an implementation bug could violate a property the *design* guarantees.

## 5. Can legitimate branches be accepted?

**Pass.** This is the ADR-030 property the entire GD-009 Batch 1 stop condition existed to restore;
the draft's §5 test requirement (the exact `A→{B,C}` shape from ADR-030's own red-team) is the
correct, minimal proof that the new implementation does not regress to the old linear-only behavior
by accident.

## 6. Can cycles be detected safely?

**Pass, and this is the one place this report independently verified the draft's safety framing
rather than accepting it at face value.** A naive backward walk without a visited-set guard *would*
loop indefinitely on a genuine cycle — the draft's §9 explicitly requires a bounded/safe traversal
(a visited-set, or equivalent) and cites the repository's own `ADR-028`
`evidence_actor_attributions` cycle-rejection precedent as evidence this codebase already knows how
to build such a guard correctly. This report independently confirms that precedent is real (checked
directly, this session's own earlier work against `migrations/versions/0014_evidence_actor_attributions.py`)
and that citing it, rather than assuming "cycles can't structurally happen," is the correct level of
caution — `ADR-028`'s own migration found a cycle *was* achievable via an unexpected mechanism
(a multi-row `INSERT`) despite looking structurally impossible in advance, and this draft explicitly
declines to make the same optimistic assumption for `audit_log`.

## 7. Can dangling references be detected?

**Pass.** Directly follows from invariant 3 (referential validity) — a `prev_hash` with no matching
`hash` in the fetched entry set is, definitionally, detectable by a single map lookup. The draft's
§7 test requirement matches this exactly.

## 8. Can reachability be verified?

**Pass, and correctly distinguished from referential validity, not conflated with it.** The draft's
§8 test requires a graph where one hop resolves (referential validity passes) but the *full*
backward walk does not terminate at a recognised genesis/root — this is precisely the distinction
`ADR-030` §2 itself drew between invariants 3 and 4, and this report confirms it is a genuinely
separate check: a graph could satisfy "every prev_hash points somewhere real" while still containing
a component that never actually traces back to genesis (e.g., if that component's own root
incorrectly used a non-`GENESIS_HASH` value as its own `prev_hash` without any invariant-1 violation
being triggered in isolation — the draft's insistence on testing this as its own case, not assuming
it follows for free from invariant 3, is correct caution).

## 9. Is the completeness limitation honestly preserved, not overstated?

**Pass.** The draft's §10 restates `ADR-030`'s own disclosure verbatim in substance (terminal-leaf,
whole-branch, and tail-truncation deletion may remain undetected) and explicitly forbids the future
implementation's own documentation or test names from claiming otherwise. No anchor/checkpoint
mechanism is authorized. This report independently confirms this is the correct scope: nothing in
this Decision's charter (implement the verifier ADR-030 already decided) extends to solving the
completeness question ADR-030 itself explicitly left open.

## 10. Does the write path remain untouched?

**Pass, and the "extract, do not alter" precedent cited is real, not invented for this draft.** §13
explicitly forbids any change to `audit()`, `EagerPostgresAuditStore`, the suspended
`audit_staged()` design, hash generation, or transaction boundaries, and permits only a
behavior-preserving extraction if a genuinely shared helper needs factoring out — citing GD-009's
own `_build_entry` extraction (verified directly in this session's earlier work: `audit()`'s
observable behavior was proven unchanged by a full hermetic-suite run before and after that
refactor, 321 passed/3 skipped both times) as the established precedent for exactly this kind of
safe, non-behavior-changing extraction. The citation is accurate, not decorative.

## 11. Does GD-009 remain correctly suspended?

**Pass.** §20's four-step sequence (ADR-030 accepted → this Decision accepted → verifier
implemented/reviewed/merged/post-merge-verified → separate explicit resumption authorization)
matches `docs/adr/ADR-030-...md`'s own "GD-009 disposition" section exactly, re-checked directly
against that text in this review. The draft states plainly that ratifying and even implementing this
Decision satisfies only the second of four steps — it does not overclaim progress toward resumption.

## 12. Does the ADR-028 gate remain correctly blocked?

**Pass.** §22 grants no router, DTO, OpenAPI, generated-client, or frontend authority, and
explicitly states `ADR-028`'s existing five-condition gate (on GD-009 Batch 1, itself still
suspended) is unaffected and unshortened.

## Additional finding, not blocking, worth naming

The draft's §1 "verify_chain() consumers, re-derived fresh" claim was independently re-run for this
report (a second, separate `grep` against a fresh worktree at the same baseline) — it reproduces the
identical 11 call sites across the identical 9 files. Both the draft's own re-derivation and this
report's independent one agree exactly, and neither found any runtime, admin, or scheduled consumer
— confirming §16's "no consumer may silently receive broader authority" claim rests on a genuinely
re-verified fact, not an assumption carried forward from an earlier, possibly-stale document.

## Summary

| Question | Result |
|---|---|
| Six invariants implementable with current schema | Pass |
| No migration required | Pass |
| No new dependency required | Pass |
| Valid linear histories remain valid | Pass |
| Legitimate branches can be accepted | Pass |
| Cycles can be detected safely | Pass |
| Dangling references can be detected | Pass |
| Reachability can be verified (distinct from referential validity) | Pass |
| Completeness limitation not overstated | Pass |
| Write path remains untouched | Pass |
| GD-009 remains suspended | Pass |
| ADR-028 remains blocked | Pass |

This report's authority is limited to the twelve questions above, at this point in time, against the
draft GD's text as drafted. It does not ratify the draft, does not authorize any implementation, and
does not itself constitute the Governance Decision it reviews.
