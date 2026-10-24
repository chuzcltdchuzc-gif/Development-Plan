# ADR-030 Readiness Report — Audit Chain Concurrency, Ordering, and Linearization

**Type:** Point-in-time governance readiness review, produced against `origin/main` at commit
`cdda3c318fa6cbb22a0e5591769dfb38097112e4`. Independently tests
`docs/adr/ADR-030-audit-chain-concurrency-ordering-and-linearization.md` ("the ADR") against the
questions this architecture investigation was charged to answer. **The ADR's own text is
authoritative for its architecture; this report is authoritative only for the specific pass/fail
questions below, at the time it was written** — the same convention every prior readiness report in
this repository (`ADR-028`, `ADR-029`) has already established.

**Date:** 2026-09-12

**Status of the reviewed ADR:** Proposed — architecture only. Not accepted. This report is not a
ratification.

## 1. Does the ADR correctly separate the pre-existing defect from Batch 1's exposure?

**Pass, and independently re-derivable, not merely asserted.** The ADR's central claim — that the
fork is a pre-existing property of the unmodified eager-independent path, not something GD-009
introduced — rests on a reproduction against a detached worktree at the exact confirmed baseline SHA
with zero modified files. This report re-checked the mechanism claim directly: `EagerPostgresAuditStore.
last_hash()` and `.append()` (read from `origin/main`, unmodified) each open their own session via
`self._session_factory()` — confirmed by direct reading, not restated from the ADR's own account.
This structurally guarantees a two-round-trip gap between predecessor read and durable write for
*every* eager `audit()` call today, with nothing bridging it — the reproduction is a direct, expected
consequence of code already on `main`, not a contrived edge case.

## 2. Is the required topology conclusion (DAG, not strict linear chain) actually supported by the governing texts?

**Pass.** Checked directly against both texts the ADR cites: `docs/adr/ADR-007-...md`'s Decision 1
and Context use "atomically" and "tampering," never "linear," "total order," or "single successor";
LV-000 Article VIII §3's exact text ("every record... carries a resolvable reference to its audit
entry") is satisfied identically by a resolvable reference into a linear chain or into a DAG — the
sentence does not distinguish them. The ADR is correct that strict linearity was an unstated
implementation assumption, not a governance requirement — this report independently confirms it is
not merely a convenient reading invented to justify the cheapest fix.

## 3. Is the fork/tamper distinction accurate?

**Pass, and this is the ADR's single most load-bearing technical claim, so it was checked most
carefully.** `app.kernel.audit._compute_hash` (read directly) hashes only
`entry_id, action, resource_type, resource_id, decision, principal_id, payload, created_at,
prev_hash` — no other row's data ever enters this computation. Therefore `entry.recompute_hash() ==
entry.hash` genuinely cannot be affected by any other row existing, forking, or not. The ADR's claim
that a fork degrades only `verify_chain()`'s linear-walk assumption, and not any individual entry's
own tamper-evidence, is confirmed correct by this independent re-derivation from the actual hash
function's inputs — not merely plausible-sounding prose.

## 4. Does the selected architecture (D/F) genuinely require zero write-path change?

**Pass.** `audit()`, `audit_staged()`, `PostgresAuditStore`, and `EagerPostgresAuditStore` are none
of them referenced anywhere in the ADR's "Decision" §1–§3 as needing modification — only
`verify_chain()` (a read-time function, called nowhere in any write path, confirmed by `grep`-level
reasoning: it exists solely for offline/scheduled integrity checking, per `docs/adr/ADR-007-...md`
Decision 1's own description of it as "run on a schedule, not left as a theoretical guarantee").
This is a real, checkable structural property of the selection, not an aspiration.

## 5. Is the rejection of Alternative E (unique constraint + retry) fair, or does the ADR stack the deck against the runner-up?

**Pass, with the reasoning independently re-examined rather than accepted at face value.** E's real
cost is specific and correctly identified: a `UNIQUE(prev_hash)` violation raised mid-transaction in
Postgres poisons that transaction for further statements until an explicit `ROLLBACK TO SAVEPOINT` —
this is standard, well-documented Postgres transaction-error behavior, not an invented obstacle. The
ADR's comparison table gives E full credit for preserving strict linearity and needing no lock, and
only downgrades it on the transaction-coupled retry-complexity point and the schema-change point —
both real, both smaller than the ADR could have overstated them as. This report finds E fairly, not
strategically, characterized as "the closest runner-up," not dismissed.

## 6. Is Alternative A/B's lock-duration concern for the transaction-coupled path quantified honestly?

**Pass.** The ADR's "Deadlock, retry, and failure analysis" section names the specific, concrete
mechanism (a chain-head lock held from `audit_staged()`'s call until the caller's own final commit,
so any slow downstream call in that same transaction extends the lock's hold time) rather than a
generic "locking is slow" hand-wave. This report independently confirms the mechanism is real: any
lock acquired inside a transaction-coupled audit call and held until that session's own
`get_db_session` commit would, by construction, be held for however long the rest of that request's
business logic takes — this is not a hypothetical, it follows directly from how `audit_staged()`
(already designed, on the blocked branch) is meant to work.

## 7. Does the ADR overstate or understate the fork's security/evidentiary severity?

**Pass — the calibration is correct in both directions.** It does not claim the fork is harmless
(explicitly names it a false-positive corruption alarm and a governance/trust risk), and does not
overclaim a security vulnerability where none exists (explicitly and correctly states no deletion,
substitution, or forgery becomes newly possible). This report checked this against the actual
attacker-capability question directly: nothing in the fork mechanism grants write access to any
existing row, bypasses `REVOKE UPDATE, DELETE`, or lets an attacker choose an arbitrary `prev_hash`
without also needing a real, already-committed hash to reference — the severity calibration holds.

## 8. Is the global-vs-tenant analysis honest about what a per-tenant chain would and would not fix?

**Pass.** The ADR does not claim per-tenant chaining eliminates the race — it explicitly states
same-tenant concurrent writers would still fork under a per-tenant chain-head lock, only with a
smaller blast radius. This is the correct, non-oversold framing; a reviewer expecting "per-tenant
chains would have solved this" would be independently corrected by the ADR's own text, not misled by
it.

## 9. Does the ADR avoid smuggling implementation scope into an "architecture only" document?

**Pass.** The "Future, separately-decidable enhancement" (the optional monotonic sequence column) is
explicitly named as not authorized and requiring its own future proposal — checked against the
"Implementation consequences" section, which lists only a future verifier rewrite and explicitly
states no migration, no write-path change. No schema, code, or test file is created by this ADR
(confirmed: only three files exist in this drafting task's diff, all documentation).

## 10. Is the GD-009 disposition coherent, or does it quietly relitigate GD-009?

**Pass.** The ADR states GD-009 remains Accepted/In Force and does not require re-ratification; it
states Batch 1's write-path design needs no change under the selected topology; and it states Batch
1 implementation remains suspended pending this ADR's acceptance and a conforming verifier's
existence — three distinct, individually checkable claims, none of which contradicts GD-009's own
text (re-read directly: GD-009 §11 itself already anticipated exactly this outcome — "If Batch 1
proves that transaction-coupled successful audit writes can create... implementation must stop and
return to Governance" — this ADR is that return, not a reversal of GD-009's own authority).

## 11. Does the ADR correctly leave the ADR-028 HTTP gate untouched?

**Pass.** No sentence in the ADR loosens, restates more permissively, or otherwise touches
`docs/adr/ADR-028-...md`'s Approval Gate; the gate's dependency chain is extended (now also
depending on this ADR's acceptance and a conforming verifier), never shortened.

## Additional finding, not blocking, worth naming

The ADR's "Historical audit records" section correctly declines to inspect any live/staging
Supabase environment (outside this investigation's authorization) but names its existence. This
report agrees that is the right boundary — checking a live environment's actual data would exceed
"architecture investigation and drafting only" — but flags, as the ADR itself already does, that
this leaves a genuine open question (does any persistent environment already contain a fork?) that
this document correctly does not resolve and correctly does not pretend to.

## Summary

| Question | Result |
|---|---|
| Pre-existing-defect vs. Batch-1-introduced separation | Pass |
| Topology conclusion matches governing texts | Pass |
| Fork/tamper distinction accurate | Pass |
| Selected architecture requires zero write-path change | Pass |
| Alternative E rejection fair | Pass |
| Alternative A/B lock-duration concern quantified honestly | Pass |
| Severity calibration (neither overstated nor understated) | Pass |
| Global-vs-tenant analysis honest | Pass |
| No implementation scope smuggled in | Pass |
| GD-009 disposition coherent | Pass |
| ADR-028 gate untouched | Pass |

This report's authority is limited to the eleven questions above, at this point in time, against the
ADR text as drafted. It does not accept the ADR, does not authorize any implementation, and does not
itself constitute the Governance Decision the ADR names as a future requirement.
