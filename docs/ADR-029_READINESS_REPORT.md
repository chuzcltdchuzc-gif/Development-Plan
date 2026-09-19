# ADR-029 Readiness Report — Audit Transaction Semantics and Outcome Integrity

**Type:** Point-in-time governance readiness review, produced against `main` at commit
`edbc4283005e86f5068de4014bedc8407ac5f61d`. Independently tests
`docs/adr/ADR-029-audit-transaction-semantics-and-outcome-integrity.md` ("the ADR") against the
questions Governance posed when authorizing its drafting. **The ADR's own text is authoritative for
its architecture; this report is authoritative only for the specific pass/fail questions below at
the time it was written**, per this repository's own established convention for a readiness
review's relationship to the decision it reviews.

**Date:** 2026-09-10

**Status of the reviewed ADR:** Proposed — architecture only. Not accepted. This report is not a
ratification.

## 1. Does the selected architecture actually resolve the ADR-007 contradiction?

**Pass, for the class it was contradicted on.** ADR-007 Decision 1 says every domain event is
written atomically with the state change it describes. That was proven false specifically for
successful-mutation events (the reality audit's Case B reproduction: an audit entry for
`registry.parcel.created` persisted while the parcel row it named did not). The ADR's selected
architecture stages successful-mutation audit rows into the same session, with no intermediate
commit, so they pass through the same single commit point as the business row. This was checked
against the actual mechanism (`get_db_session`'s one `await session.commit()` at the end of the
generator) rather than assumed: since the ADR introduces no new commit call anywhere in this path,
there is structurally nothing left to separate the two writes. The ADR does **not** claim to have
resolved the contradiction for denial/failure events, because — correctly, on inspection — ADR-007
Decision 1 was never a coherent requirement for that class in the first place (a denial's entire
point is surviving a rollback its own transaction requires).

## 2. Does denial/failure auditing remain durable?

**Pass.** The ADR leaves this path completely unchanged (`EagerPostgresAuditStore`, unmodified).
Verified independently against the ADR's own historical claim: `app/kernel/authorization/pep.py`'s
`require_role`/`enforce` deny-audit calls run during FastAPI dependency resolution, confirmed by
reading the dependency graph directly — neither depends on `get_db_session`, so no request-scoped
session is guaranteed to exist at that point regardless of any later architecture choice. An
independent store is not a stylistic preference for this caller; it is the only mechanism that can
work at all, and the ADR correctly leaves it alone.

## 3. Does RLS remain viable?

**Pass, and the ADR's account of *why* is more precise than the document that first flagged this
issue.** Read `migrations/versions/0001_identity_and_audit.py` directly: `audit_log`'s own RLS
policies are `USING (true)` / `WITH CHECK (true)` — no tenant predicate exists on this table at
all, and none is proposed. The actual historical risk was collateral: an intermediate commit on a
shared session would clear the `is_local`-scoped `app.tenant_id`/`app.is_super_admin` setting for
every *other* table's RLS for the rest of that request. The ADR's selected design avoids this by
never introducing an intermediate commit for the successful-mutation path — checked against the
literal code shape (`session.add()` + flush, no `commit()` call added anywhere), not merely
asserted. This closes the actual mechanism, not a restated version of the original, slightly
imprecise description of the risk.

## 4. Do successful-mutation events become transactionally truthful?

**Pass, for events migrated under this architecture.** The ADR is explicit that this becomes true
"by construction" for calls actually moved to the staged path — and equally explicit that this ADR
does not itself move any call site (§ "Minimum implementation consequence" is future work). This
report confirms that framing is honest: the ADR proposes an architecture, not a completed migration,
and does not overclaim that today's `evidence.actor_attribution.recorded` calls are already
truthful. They are not, today — the reality audit already proved the general mechanism applies to
this exact pair of calls by structural analogy (§6 of the ADR), even though it was not
independently live-reproduced for the attribution service specifically.

## 5. Is external Storage represented honestly?

**Pass.** The ADR explicitly refuses to claim distributed atomicity between Postgres and Supabase
Storage, names the existing ADR-026 orphaned-object risk as unsolved and unchanged, and correctly
scopes "database transactional atomicity" as covering only the DB-internal half of Evidence upload.
No sentence in the ADR could be read as promising cross-system atomicity that does not exist.

## 6. Is an outbox genuinely necessary?

**Fail-to-need, correctly concluded.** The ADR evaluates Alternative D and rejects it, on grounds
independently checked here: a transactional outbox would require a new background-worker
component this codebase has never had (a new runtime dependency, squarely Engineering Rule #5
territory — human approval, justification, pinned version), and would only produce *eventual*
consistency for the materialized `audit_log` row, which is a *weaker* guarantee than what
Alternative C achieves immediately by reusing an already-open transaction. Rejecting the more
architecturally fashionable option here is the correct call, not merely the simpler one — checked
against the actual invariant required (§2 of the ADR: successful-mutation must be exactly
simultaneous with its state change), which an outbox does not provide any more precisely than
Alternative C does, while costing materially more to build and operate.

## 7. Can implementation remain bounded?

**Pass, and this section's original evidence was wrong — corrected below rather than concealed.**
The ADR's minimum-implementation-consequence section requires: no schema change, no new dependency,
and a call-site-by-call-site classification of every existing call before any code changes —
explicitly declining to pre-classify the ambiguous cases and instead requiring an implementing
engineer to default to the independent (unchanged) path on any uncertainty. This shape — a genuinely
bounded, incremental change, not a rewrite — is unaffected by what follows.

This report originally stated it had "re-derived independently... confirming 55 total call sites and
the ADR's rough classification buckets are plausible groupings, not fabricated." **That claim was
false.** A subsequent formal Governance review re-ran the same `grep -rn "await audit(" app/` query
against the confirmed baseline and found 54 call sites, not 55 — and separately found that the
reality audit's own per-file table summed to 46, not 55, an internal arithmetic error independent of
any comparison to the codebase. This report's "independent" re-derivation did not actually catch
either problem; it repeated the first document's number rather than genuinely re-deriving it.

Following that review, a fresh, individually-verified count was performed for this correction (not
reused from either prior document): **54** call sites total —
`evidence_service.py` 9, `attribution_service.py` 2, `admin_service.py` 17, `auth_service.py` 14,
`parcel_service.py` 8, `spatial_service.py` 2, `pep.py` 2 — with every site individually classified
against the ADR's four-class taxonomy: 31 successful-mutation, 20 denial, 1 failure, 2 ambiguous
(named individually, not estimated, in
`docs/AUDIT_KERNEL_ATOMICITY_REALITY_AUDIT_CORRECTION_2026-09-11.md`), reconciling exactly to 54 on
both the per-file and per-class axes. **This correction changes the evidentiary record only — it
does not change this section's Pass verdict, and it does not change the architecture**: the ADR's
own instruction (classify every site; default the ambiguous ones to the unchanged independent path)
already absorbed a miscount of this kind without consequence. The governance process is recorded
here as having caught and corrected its own error, not as having been right the first time.

## 8. Is a separate Governance Decision required?

**Answered by the ADR, and independently checked here against the cited precedent.** The ADR
points to ADR-026 as the precedent for "architecture acceptance ≠ implementation authorization" —
verified directly: `docs/adr/ADR-026-evidence-domain-model.md`'s own Status line reads "Accepted —
Governance Authority authorization, 'B5.2 — Evidence Domain Model Implementation'" — i.e. ADR-026's
acceptance and its implementation authorization are named as two distinct governance acts, exactly
as the readiness-reviewed ADR claims. This confirms the ADR's answer ("acceptance authorizes the
decision; a later, explicit Governance act authorizes implementation") is not an invented parallel
but a real, checkable repository convention.

## Additional finding not raised as a blocking question, worth naming

The ADR's Context section states that `get_db_session`'s `HTTPException`-commits fix, on inspection,
already independently closes part of the original deny-audit-loss problem for denials raised from
*inside* an existing session (as opposed to PEP's structurally session-less denials). This is a
genuine, independently-checkable finding (re-read `AuthService.redeem_invitation`'s
`identity.invitation.redemption_denied` call directly: it raises `_unauthenticated(...)`, an
`HTTPException`, from inside a session-bearing method) — the ADR could, in principle, have proposed
migrating *these specific* denial calls to the shared path too, since they would now survive. It
deliberately does not, reasoning that the independent path already works correctly for them and
migrating them adds classification risk for no gain. This report agrees with that restraint: adding
scope here would not improve outcome integrity and would only add call sites to reclassify.

## Summary

| Check | Result |
|---|---|
| Resolves the ADR-007 contradiction (successful-mutation class) | Pass |
| Denial/failure durability preserved | Pass |
| RLS remains viable, mechanism correctly identified | Pass |
| Successful-mutation events become truthful once migrated | Pass (architecture only — no migration performed by the ADR itself) |
| External Storage represented honestly | Pass |
| Outbox correctly found unnecessary | Pass |
| Implementation boundable | Pass |
| Governance Decision requirement correctly identified | Pass, checked against the cited ADR-026 precedent |

This report's authority is limited to the eight questions above, at this point in time, against the
ADR text as drafted. It does not accept the ADR, does not authorize any implementation, and does
not itself constitute the Governance Decision the ADR names as a future requirement.
