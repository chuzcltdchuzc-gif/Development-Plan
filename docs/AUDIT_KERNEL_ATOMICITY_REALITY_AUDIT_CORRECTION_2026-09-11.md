# Correction Note — `AUDIT_KERNEL_ATOMICITY_REALITY_AUDIT.md` Call-Site Inventory

**Type:** Factual correction to a point-in-time evidence record. This note does **not** revise,
retract, or supersede `docs/AUDIT_KERNEL_ATOMICITY_REALITY_AUDIT.md`'s architecture or mechanism
findings, and that document is **not** edited by this note — it remains historically intact, exactly
as filed, per this repository's own discipline for point-in-time evidence records (the same
treatment `docs/ADR-029_READINESS_REPORT.md` itself already describes for its relationship to the
ADR it reviews).

**Date:** 2026-09-11

**Issued following:** a formal Governance review of ADR-029 (`ADR-029 GOVERNANCE REVIEW PASS WITH
REQUIRED TEXTUAL REMEDIATION`), which identified exactly one required remediation: the audit-call-site
inventory in the reality audit's §2 is arithmetically wrong.

## 1. Document identified

`docs/AUDIT_KERNEL_ATOMICITY_REALITY_AUDIT.md`, §2 ("Complete audit-call inventory"), produced
against `main` at `edbc4283005e86f5068de4014bedc8407ac5f61d`.

## 2. What remains valid — unchanged by this correction

Every architecture and mechanism finding in the reality audit is independently re-verified as
correct, against the live repository, as of this note:

- Audit writes resolve to `EagerPostgresAuditStore`, which opens a separate session and commits
  independently of the caller's own request transaction (`app/kernel/audit_postgres.py`,
  `app/kernel/audit.py`, `app/main.py` — re-read directly).
- `app/kernel/uow.py`'s `get_db_session` never binds the audit store to the request session, by its
  own docstring's explicit statement, and commits (not rolls back) on `HTTPException`.
- The Case B mechanism (a business mutation flushes, its audit entry commits independently, the
  surrounding transaction then rolls back, leaving an orphan audit entry) is a correct structural
  description of the live-reproduced defect.
- `audit_log`'s RLS (`FOR SELECT USING (true)` / `FOR INSERT WITH CHECK (true)`, no tenant predicate)
  is exactly as described.
- The ADR-007 Decision 1 contradiction, the GD-006/GD-007 regularisation precedent, and every
  qualitative finding in §§3–19 of the reality audit are unaffected by this correction.

**Nothing about the audit-atomicity finding, or ADR-029's architectural conclusion (split
transaction semantics: successful-mutation staged into the caller's transaction, denial/failure
audits remain independent, no outbox, no new dependency, no schema change), changes as a result of
this correction.** The call-site count is evidence supporting *how much work implementation would
touch*, not evidence for *whether* the atomicity defect exists or *which* architecture closes it.

## 3. The factual inventory error

The reality audit's §2 states "55 call sites" and gives a per-file table. Two independent problems
exist in that table, found under this correction:

1. **The table's own seven numbers do not sum to the total the text claims.** 8 + 2 + 13 + 12 + 7 +
   2 + 2 = **46**, not 55. This is an internal arithmetic error, independent of any comparison to the
   codebase.
2. **Neither number matches the actual repository.** A fresh, independent re-run of the same command
   the reality audit itself specifies (`grep -rn "await audit(" app/`, from `backend/`, against the
   confirmed, unchanged baseline `edbc4283005e86f5068de4014bedc8407ac5f61d`) returns **54** call
   sites, and a per-file breakdown that matches neither the reality audit's table nor its total.

`docs/ADR-029_READINESS_REPORT.md` §7 independently repeated the same "55" figure and characterized it
as independently re-derived and confirmed — that characterization was inaccurate; a genuinely
independent count would have caught both the total mismatch and the table's own internal
inconsistency. This is addressed directly in that report (see the corresponding update to
`docs/ADR-029_READINESS_REPORT.md`).

## 4. Verified current-baseline count

Re-run directly against the confirmed baseline for this correction (`backend/`, `grep -rn "await
audit(" app/`), with per-file counts cross-checked independently via `grep -c` on each file and via
a raw line-dump cross-tabulation — both methods agree exactly:

| File | Verified count |
|---|---|
| `app/contexts/evidence/application/evidence_service.py` | 9 |
| `app/contexts/evidence/application/attribution_service.py` | 2 |
| `app/contexts/identity/application/admin_service.py` | 17 |
| `app/contexts/identity/application/auth_service.py` | 14 |
| `app/contexts/registry/application/parcel_service.py` | 8 |
| `app/contexts/spatial/application/spatial_service.py` | 2 |
| `app/kernel/authorization/pep.py` | 2 |
| **Total** | **54** |

No compiled bytecode (`.pyc`) contamination was found in the grep results (checked directly); the
count reflects source files only, exactly as the original methodology intended.

## 5. Corrected classification, reconciled to the total

Beyond the count itself, ADR-029's own migration matrix (§"Audit-call-site migration matrix") gave
only *approximate* per-class groupings ("~34" successful-mutation, "~11" denial, "~6" failure, "~4"
ambiguous — summing to 55, the same uncorrected total). Per the Governance review's instruction that
category totals must reconcile mechanically to the verified inventory, every one of the 54 call
sites was read individually (not sampled) and classified against ADR-029's own four-class taxonomy:

| Class | Count | admin_service.py | auth_service.py | evidence_service.py | attribution_service.py | parcel_service.py | spatial_service.py | pep.py |
|---|---|---|---|---|---|---|---|---|
| Successful mutation | 31 | 9 | 5 | 7 | 2 | 7 | 1 | 0 |
| Denial | 20 | 7 | 8 | 1 | 0 | 1 | 1 | 2 |
| Failure | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| Ambiguous (requires implementation-time governance) | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| **Column total** | **54** | **17** | **14** | **9** | **2** | **8** | **2** | **2** |

Row sum: 31 + 20 + 1 + 2 = 54. Column sum for each file matches §4's verified per-file count exactly
(e.g. `admin_service.py`: 9 + 7 + 0 + 1 = 17; `auth_service.py`: 5 + 8 + 0 + 1 = 14). Both axes
reconcile.

**The two ambiguous sites, named explicitly rather than folded into a rough bucket:**

- `admin_service.py`, `AdminService.get_delegation` (`identity.delegation.invalidated`, fired during
  a read when a delegation is found to be currently ineffective — no mutation is attempted or
  performed by this call path, and the method does not raise afterward). This does not cleanly fit
  successful-mutation (nothing commits), denial (nothing was attempted and rejected), or failure (no
  operation failed) — it is a detected-fact audit surfaced during a successful read. Left
  unclassified pending implementation-time governance review, defaulting to the existing,
  independent, unchanged path per ADR-029's own instruction for ambiguous cases.
- `auth_service.py`, `AuthService._authorize_invitation_redemption` (the `authority_lost_reason`
  branch: `identity.invitation.redemption_denied`, fired *after* a real mutation — the stale
  invitation is revoked and persisted — but describing, by its action name, only the caller's denied
  redemption attempt, not the revoke itself). This single call site carries two different facts (a
  successful side-effect mutation, and a denied caller request) under one denial-shaped action name.
  It works correctly today (per `HTTPException`-commits, both facts survive together), but it is
  the same "audits a state change and a permission check in the same call" pattern ADR-029 §16
  already named for a small number of `admin_service.py` sites — found here in `auth_service.py` as
  well, and not previously named as such. Left unclassified pending implementation-time governance
  review, defaulting to the existing, independent, unchanged path — exactly as ADR-029's own rule for
  an unresolved ambiguous case requires.

No ambiguous site was forced into the successful-mutation category to make totals balance; both are
left classified as "ambiguous" and default to the independent, unchanged path, consistent with
ADR-029's own stated default.

## 6. Disposition

- This correction note is filed alongside, not instead of, the original reality audit.
- `docs/adr/ADR-029-audit-transaction-semantics-and-outcome-integrity.md` is updated to cite the
  corrected total and matrix, referencing this note.
- `docs/ADR-029_READINESS_REPORT.md` is updated to disclose, rather than repeat, the original miscount.
- No architectural conclusion in either document changes.
