# Phase 8 Acceptance Package — ADR-023 (Registry Ownership and Status History)

**Subject:** PR #2, `feat/adr-023-ownership-status-history` → `main`
**Status:** ACCEPT WITH CONDITIONS — both conditions now GREEN. Held at the merge gate for explicit
approval; not merged by this package.
**Date:** 2026-07-31
**Governance sequence applied:** Observe → Implement → Test → Verify → Document → Review → CI →
Acceptance → Explicit Merge

---

## 1. Original acceptance evidence (carried forward, unchanged)

From `docs/adr/ADR-023-registry-ownership-and-status-history.md` (Accepted — Implemented,
2026-07-31) and `docs/PHASE-1_IMPLEMENTATION_PLAN.md`:

- Migration `0011_registry_ownership_status_history.py`: two append-only history tables
  (`parcel_ownership_history`, `parcel_status_history`), RLS enabled + forced with the same
  predicate as `parcels`, append-only enforced at two independent layers (privilege grant —
  `SELECT, INSERT` only — and a `BEFORE UPDATE OR DELETE` trigger that fires regardless of role,
  including the schema-owning migration role).
- Domain value objects `OwnershipAssertion` / `StatusAssertion` (`app/contexts/registry/domain/history.py`)
  — pure, no I/O.
- `ParcelHistoryRepository` port with a Postgres adapter (`PostgresParcelHistoryRepository`) and an
  in-memory fake, wired through the same per-request `AsyncSession` as `ParcelRepository`
  (`app/contexts/registry/dependencies.py`).
- `ParcelService.create_parcel` / `update_parcel` / `archive_parcel` write history rows as a side
  effect of the existing mutation flows — no new endpoint, no new mutation command, no new
  authorization model.
- 158/158 tests passing hermetically (via `tests/app_factory.py`'s in-memory fakes), `ruff`/`mypy`
  clean.
- Live rehearsal already performed at implementation time: migration up/down/up repeatability, RLS
  cross-tenant isolation, both append-only layers, FK parent-relationship enforcement, end-to-end
  HTTP create/update/archive flows with `audit_ref` resolving to payload-consistent audit entries.
- Self-flagged gap at acceptance: *"no orphan row on failure" is backed by a unit test plus the
  kernel's existing rollback-on-exception behavior, not a live fault-injection demonstration.* This
  package closes that gap (§3).

This package does not revisit or reopen any of the above. It addresses only the two conditions
raised at the PR-merge gate.

---

## 2. Condition 1 — CI / branch-protection correction

**Observed defect:** `main`'s branch protection required two status contexts —
`pytest / ruff / mypy` and `typecheck / lint / test / build` — but both `backend-ci.yml` and
`frontend-ci.yml` gated their *trigger* on `paths:` (`backend/**` / `frontend/**` respectively).
PR #2 is backend-only, so `frontend-ci.yml` never ran, `typecheck / lint / test / build` never
received any status, and branch protection held it permanently pending — confirmed via
`gh pr checks 2` (context absent, not failing) and `gh api repos/.../branches/main/protection`.

**Root cause:** a required status check cannot be satisfied by a PR that structurally cannot
trigger the workflow that reports it.

**Correction implemented ([PR #3](https://github.com/chuzcltdchuzc-gif/Development-Plan/pull/3),
merged to `main` as `4a16bb6`):** both workflows now always trigger; `dorny/paths-filter` gates the
actual install/lint/test/build steps *inside* the job. An unaffected path means the job completes
quickly with its steps skipped and still reports **success** — the required check is now always
satisfiable. Applied symmetrically to both workflows (the identical defect existed in
`backend-ci.yml` for a hypothetical frontend-only PR).

No branch-protection rule was weakened. No administrator bypass was used. ADR-023 was not modified
to accommodate this.

**Verification:**

| Check | Evidence |
|---|---|
| PR #3 required checks | Both pass |
| Empirical skip-path proof | Throwaway PR #4 (backend-only diff): `typecheck / lint / test / build` completed in 7s (steps skipped) → **pass**; `pytest / ruff / mypy` ran for real (61s) → **pass**. Closed without merging after observation. |
| PR #2 after rebase onto fixed `main` (commit `5c2e45b`) | `pytest / ruff / mypy` pass; `typecheck / lint / test / build` pass (skip path, confirmed by 8s runtime) |
| `gh pr view 2 --json mergeable,mergeStateStatus` | `{"mergeable":"MERGEABLE","mergeStateStatus":"CLEAN"}` |

---

## 3. Condition 2 — live PostgreSQL transaction failure-path evidence

**Observed gap:** every test in `backend/tests/` runs through `tests/app_factory.py`, which
overrides every Registry repository with an in-memory fake and never calls
`app.kernel.uow.get_db_session`. The "same Unit of Work" rollback claim in ADR-023 had therefore
only been demonstrated by (a) a unit test against the fakes, and (b) trusting `uow.py`'s own
`except Exception: await session.rollback(); raise` logic by reading it — never by observing a real
Postgres transaction actually roll back.

**Rehearsal added:** `backend/tests/live/test_registry_history_rollback_live.py` (committed to
`feat/adr-023-ownership-status-history` as `b1ed977`). Deliberately **not** part of the hermetic
suite CI runs (skipped unless `LIVE_ROLLBACK_ADMIN_URL` is set — CI has no Postgres service, and
every other test in this repo is intentionally hermetic). What it does:

1. Creates a throwaway database on the local Postgres instance.
2. Runs the real Alembic migration chain against it via `alembic upgrade head` as a subprocess
   (through revision `0011`) — this is also a live-migration rehearsal.
3. Drives `app.kernel.uow.get_db_session` **directly** — the real generator FastAPI calls
   per-request, not a substitute — with the real `PostgresParcelRepository` and
   `PostgresParcelHistoryRepository`, mirroring `create_parcel`'s exact sequence: insert a parcel,
   write an ownership-history row, write a status-history row.
4. Injects a genuine (non-`HTTPException`) fault into the generator via `athrow`, *before* any
   `audit()` call and before `session.commit()` — forcing the real
   `except Exception: await session.rollback(); raise` branch.
5. On a fresh connection, asserts: the parcel row is absent, both history rows are absent, and
   `audit_log` has zero entries referencing the attempted `audit_ref`s.
6. Proves the connection pool/session factory is not poisoned: performs one more real write through
   the same factory afterward and confirms it persists.
7. Drops the throwaway database.

**Observed result (actual run, not predicted):**

```
tests/live/test_registry_history_rollback_live.py::test_parcel_and_history_roll_back_together_on_live_postgres PASSED
======================== 1 passed in 4.70s ========================
```

Confirmed by direct query during development of this test (before the assertions were finalized)
that the parcel/history rows and audit_log entries were genuinely absent post-rollback, and that
the post-rollback write genuinely persisted — this is what the test's own assertions now enforce on
every run.

**Known limitation this rehearsal does NOT close (by design, not oversight):**
`app.kernel.uow`'s own docstring documents that `audit()` commits eagerly and independently of the
main request session — a deliberate, pre-existing choice, made to keep the RLS `is_local=true`
session-variable scoping correct (see the reasoning in `uow.py`, notably the replay-detection
example). A fault injected *after* an `audit()` call but *before* the main session's commit could
still leave an `audit_log` entry referencing a parcel/history row that never persisted. This
rehearsal injects its fault *before* the first `audit()` call specifically to isolate and prove the
parcel+history atomicity guarantee ADR-023 actually claims ("Same Unit of Work" — the parcel and its
history, not the parcel and its audit trail). It does not claim, and ADR-023 never claimed, that the
audit store and the main session are jointly transactional — they are not, by design, for reasons
independent of ADR-023. Recorded here as a known, pre-existing, out-of-scope limitation rather than
silently ignored.

---

## 4. Re-run verification suite — exact results

Run in `pr2-worktree` (backend deps installed via `pip install -e ".[dev]"`, matching CI):

| Check | Result |
|---|---|
| `ruff check .` | All checks passed! |
| `mypy app tests` | Success: no issues found in 98 source files |
| `pytest -q` (hermetic) | **158 passed, 1 skipped**, 2 warnings (pre-existing, unrelated: `httpx`/starlette deprecation notices) |
| Live migration verification | `alembic upgrade head` against a fresh database, clean through revision `0011` |
| Live transaction failure-path verification | `pytest tests/live/test_registry_history_rollback_live.py` → **1 passed** (see §3) |
| GitHub CI — PR #2 (`5c2e45b`, pre-test-commit) | `pytest / ruff / mypy` pass; `typecheck / lint / test / build` pass |
| GitHub CI — PR #2 (`b1ed977`, current head) | `pytest / ruff / mypy` pass; `typecheck / lint / test / build` pass |
| `gh pr view 2` merge state | `mergeable: MERGEABLE`, `mergeStateStatus: CLEAN` |

---

## 5. ADR-023 traceability

No architectural decision was added, narrowed, or reinterpreted by this package. Both conditions
were CI-governance and verification-evidence gaps, external to ADR-023's own content:

- Condition 1 (CI path-filter defect) is a property of `.github/workflows/*.yml`, unrelated to
  Registry, ADR-023, or branch-protection *rules* themselves.
- Condition 2 (live rollback rehearsal) *demonstrates* ADR-023's existing "Same Unit of Work" claim
  against a real database; it does not change the transaction model, the schema, the authorization
  model, or any of ADR-023's stated invariants.

`docs/adr/ADR-023-registry-ownership-and-status-history.md`'s status note has been updated with one
sentence recording that the previously self-flagged live-fault-injection gap is now closed, pointing
to this package — no other change to that ADR.

---

## 6. Remaining known limitations (honest inventory, not newly introduced by this package)

- **`docs/ENGINEERING_RULES.md` §10 (non-adjudication automated check) remains NOT implemented.**
  §10's own text already states this explicitly: *"This is not yet implemented as an automated
  check anywhere in this codebase; it is recorded here as a required rule, not yet as a satisfied
  one."* `docs/PHASE-1_IMPLEMENTATION_PLAN.md` lists it as out of scope for ADR-023/this PR,
  tracked separately. **This package does not claim §10 is implemented. It is a separate,
  pre-existing gap, unchanged by this work.**
- The audit-store/main-session independent-commit limitation described in §3 (pre-existing,
  deliberate, cross-cutting — not introduced by ADR-023 or this package).
- No read endpoint exists over the history tables (explicitly out of scope per ADR-023).
- No backfill of history for parcels created before migration `0011` (explicitly, permanently out
  of scope per ADR-023's "Migration and backfill strategy").
- Ownership *transfer* as a distinct command remains undecided (left open by ADR-015, restated as
  out of scope by ADR-023).

---

## 7. Merge gate

All required evidence is GREEN:

- [x] PR #2 required checks pass (`pytest / ruff / mypy`, `typecheck / lint / test / build`)
- [x] Branch protection satisfied normally (`mergeStateStatus: CLEAN`)
- [x] No administrator bypass used or required, at any point in this package
- [x] No new architectural decision introduced; ADR-023 unchanged in substance
- [x] `docs/ENGINEERING_RULES.md` §10 correctly left marked as NOT implemented — not falsely closed

**PR #2 has not been merged.** Per governance rule, this package stops here for explicit approval.
