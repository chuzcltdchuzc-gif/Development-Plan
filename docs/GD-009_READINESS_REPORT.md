# GD-009 Readiness Report — Audit Transaction Semantics Implementation Authorization and ADR-007 Regularisation

**Type:** Point-in-time governance readiness review, produced against `origin/main` at commit
`e4a8da9ab2d7c40f01a52eba0997a9001b76582d` (the `ADR-029` ratification squash commit, PR #29).
Independently tests `docs/GD-009-audit-transaction-semantics-implementation-authorization-and-adr-007-regularisation.md`
("the draft GD") against the nine questions this drafting task was asked to answer. **The draft GD's
own text is authoritative for its content; this report is authoritative only for the specific
pass/fail questions below, at the time it was written** — the same convention `docs/ADR-029_READINESS_REPORT.md`
and `docs/ADR-028_READINESS_REPORT.md` already established for a readiness review's relationship to
the decision it reviews.

**Date:** 2026-09-11

**Status of the reviewed draft:** Proposed — drafted for review. Not ratified. **This report is not
a ratification and does not itself authorize implementation.**

## 1. Does the draft regularize the ADR-007 divergence without rewriting history?

**Pass.** §3 of the draft states the divergence precisely (Decision 1's literal text vs. the actual
eager-independent-commit mechanism), cites the reality audit's live-reproduced Case B as the proof,
and attributes the resolution to `ADR-029`'s already-ratified two-invariant refinement rather than
re-deciding it here. Checked directly: the draft's §3 does not modify, quote-and-replace, or
"restate as corrected" any sentence of `ADR-007` itself — `ADR-007` is only ever cited, never edited
(confirmed: this task created no diff against `docs/adr/ADR-007-audit-trail-evidence-model.md`). The
draft explicitly states historical audit records remain untouched and that no historical row is
newly claimed to have possessed a guarantee it lacked at write time — this restates, rather than
weakens, `ADR-029`'s own "Historical audit records" section.

## 2. Does it authorize only Batch 1?

**Pass, verified against the draft's own arithmetic, not merely its prose.** §5 names exactly two
call sites (`evidence.actor_attribution.recorded`/`corrected`). §6 states the disposition of the
other 52 explicitly, with a per-file breakdown (`admin_service.py` 9, `auth_service.py` 5,
`evidence_service.py` 7, `parcel_service.py` 7, `spatial_service.py` 1 — summing to 29 unauthorized
successful-mutation sites) rather than a vague "everything else stays the same." §17 states
sequencing *principles* for later batches without authorizing any of them. §20 explicitly separates
architecture/implementation/HTTP authority into three named layers and states ratification grants
only the middle one, for Batch 1 only. No sentence in the draft grants a general or open-ended
migration authority.

## 3. Does denial/failure audit remain independently durable?

**Pass.** §4 states the independent path is preserved "unmodified, unless a future, separate
Governance act explicitly reclassifies a specific call site"; §9 requires regression tests
specifically guarding against recreating the original deny/failure-audit-loss bug; §18 additionally
freezes the two ambiguous sites on their current (independent) semantics rather than letting Batch 1
implicitly reclassify them by omission. Cross-checked against the actual code this session already
read directly (`app/kernel/audit_postgres.py`'s `EagerPostgresAuditStore`, `app/kernel/authorization/pep.py`'s
structurally session-less deny-audit calls): nothing in the draft's scope touches this mechanism, and
the draft does not ask it to.

## 4. Is the transaction-coupled success path implementable without an intermediate commit?

**Pass, on the evidence available at the architecture level; correctly flagged as unproven until
implementation.** §10 does not merely assert this — it re-derives the actual risk mechanism directly
from `app/kernel/uow.py`'s live code (re-confirmed by this report: `get_db_session` sets
`app.tenant_id`/`app.is_super_admin` via `set_config(..., is_local := true)`, transaction-scoped, and
`record_attribution`/`correct_attribution` (`app/contexts/evidence/application/attribution_service.py`,
read directly this session) currently call `self.attributions.record(...)` then the unmodified,
independently-committing `audit()` — meaning today's code path already holds an open session with no
intermediate commit up to that point). The draft correctly stops short of declaring the *eventual*
implementation safe by construction — §10's own last sentence requires live verification (§15 item 7)
rather than treating `ADR-029`'s text as sufficient proof. This is the right posture: architecturally
plausible, not yet demonstrated, and the draft says so.

## 5. Is a migration genuinely unnecessary?

**Pass.** §12 restates `ADR-029`'s own finding (no schema migration required — `audit_log`'s existing
shape supports being written from either session) and adds a governance-level stop-and-return
requirement if implementation reality later contradicts this. This report additionally re-checked the
claim directly: `audit_orm.py`'s `AuditLogRecord` mapping and migration `0001_identity_and_audit.py`'s
`audit_log` schema (both read earlier in this session) impose no session-origin constraint on any
column — nothing about *which* session performs the `INSERT` requires a schema change. Confirmed, not
merely repeated.

## 6. Is no new dependency required?

**Pass.** §4 explicitly excludes a transactional outbox, Kafka, CQRS, event sourcing, and any new
background-worker infrastructure or runtime dependency — the same exclusions `ADR-029` itself already
established (Alternative D rejected). Batch 1's own scope (§5) requires only an internal
abstraction change reusing the existing `AuditStore`/`audit()`/session machinery already present in
the codebase.

## 7. Does the ADR-028 API gate remain intact?

**Pass, and stated more precisely than a bare restatement.** §14 does not merely say "the gate still
applies" — it enumerates five sequential conditions (implemented → tested → formally reviewed →
squash merged → post-merge verified) before Governance may even *consider* authorizing the API, and
explicitly states that satisfying all five is not itself an automatic authorization — a further,
separate Governance act is still required. This is a stricter reading than the minimum `ADR-029`
itself demanded, which this report finds appropriate given `ADR-028`'s API is the specific,
newly-shipping surface `ADR-029`'s own "API exposure gate" section singled out as warranting caution
beyond the 52 already-tolerated pre-existing call sites.

## 8. Do later call-site batches remain unauthorized?

**Pass.** §6's closing sentence and §17 both state, in direct terms, that no call site beyond the two
named in §5 may be migrated under this Decision, and that each later batch requires its own separate
governance act. §19's PR-boundary requirement (one bounded branch/PR, containing only the items
listed) is a structural control reinforcing this — an implementation that stayed within §19's stated
boundary could not, as a side effect, sweep in additional call sites.

## 9. Do historical audit records remain untouched?

**Pass.** §3 states no destructive rewriting, deletion, retroactive fabrication, metadata migration,
or "legacy" flag column is authorized. §16 additionally scopes request-replay/idempotency and Storage
compensation as explicitly separate, unaddressed concerns, preventing scope creep into "fixing"
historical ambiguity through a different mechanism than the one already accepted (a documentation
qualification, per `ADR-029` §9).

## Additional findings, not blocking, worth naming

- **Call-site inventory re-verified fresh for this report**, not reused from memory: a repeat
  `grep -rn "await audit(" app/` against `origin/main` at the exact baseline SHA above confirms 54
  total, matching the draft's §6 table exactly (`evidence_service.py` 9, `attribution_service.py` 2,
  `admin_service.py` 17, `auth_service.py` 14, `parcel_service.py` 8, `spatial_service.py` 2, `pep.py`
  2). The draft's arithmetic (31 successful-mutation − 2 authorized = 29 remaining, by file: 9+5+7+7+1
  = 29) reconciles correctly against this.
- **Governance-decision numbering.** GD-009 was independently confirmed, not assumed: `docs/LV-000-constitution.md`'s
  Article XVI Log contains GD-001 through GD-008 (GD-008 as a full standalone instrument with a
  condensed Log entry, matching the pattern this draft's own §21 follows); no `GD-009` or higher
  exists anywhere in the repository prior to this drafting.
- **§7's deliberate non-prescription of method names** is consistent with this repository's own
  stated preference (`ADR-029` itself: "rather than fixing names now, this ADR describes the shape a
  future implementation phase would need") — not a gap, a considered choice this report agrees with.
- **One residual risk not fully closeable at the drafting stage**: §10's RLS/session-context claim is
  architecturally sound and grounded in direct code reading, but — as the draft itself acknowledges —
  remains unproven until Batch 1's live tests (§15 item 7) actually run against real PostgreSQL. This
  report does not treat that as a blocker (the draft already requires exactly this proof before
  merge), but flags it so a future reader does not mistake "architecturally plausible" for
  "demonstrated."

## Summary

| Question | Result |
|---|---|
| Regularises ADR-007 divergence without rewriting history | Pass |
| Authorizes only Batch 1 | Pass |
| Denial/failure audit remains independently durable | Pass |
| Transaction-coupled success path implementable without intermediate commit | Pass (architecture-level; correctly left unproven pending Batch 1's own live tests) |
| Migration genuinely unnecessary | Pass |
| No new dependency required | Pass |
| ADR-028 API gate remains intact | Pass |
| Later call-site batches remain unauthorized | Pass |
| Historical audit records remain untouched | Pass |

This report's authority is limited to the nine questions above, at this point in time, against the
draft GD's text as drafted. It does not ratify the draft, does not authorize any implementation, and
does not itself constitute the Governance Decision it reviews.
