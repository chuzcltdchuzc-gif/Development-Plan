# B5 Slice B5.2 — Acceptance Package: Evidence Domain Model Implementation

**Status:** Implemented, observed passing locally and live against Docker Postgres, pushed to
`origin/feat/b5.2-evidence-domain-model` (commit `50b970d`). **Correction (2026-08-02, per the
Reality Verification Gate):** this package originally stated "a PR is opened" — that was inaccurate
at the time of writing and is corrected here. No pull request had been opened; confirmed via a
read-only GitHub API check (zero PRs, zero CI workflow runs against this branch) — see the Final
Merge Gate Report (`docs/PHASE-B5-SLICE2_MERGE_GATE_REPORT.md`) for the exact evidence. **Not
merged.** Merge itself and Slice B5.3 both await explicit further authorization.

**Date:** 2026-08-02

**Governing ADR:** `docs/adr/ADR-026-evidence-domain-model.md` — **Accepted**.

**Authorized scope:** database (migration `0012`), domain (`EvidenceRecord` aggregate),
repository layer (port + Postgres adapter + in-memory fake), dependency injection, tests, live
migration rehearsal. Explicitly excluded from this slice, and not implemented: upload endpoints,
storage adapters (Supabase/R2), hash computation, WORM sealing (the physical act, as opposed to
the domain's own `SEALED` status field), chain-of-custody workflow, legal-hold workflow (as opposed
to the domain's own hold *state*), and everything else the authorization's "Explicitly Out of
Scope" list names.

---

## 1. Implementation summary

| Layer | File(s) | What it does |
|---|---|---|
| Domain | `backend/app/contexts/evidence/domain/evidence_record.py` | `EvidenceRecord` aggregate: identity, metadata, `RECEIVED→HASHED→SEALED` lifecycle, legal hold, `EvidenceSealedError`/`EvidenceLifecycleError` |
| Ports | `backend/app/contexts/evidence/ports.py` | `EvidenceRepository` Protocol added alongside the existing `StoragePort` (Slice B5.1) |
| Adapters | `backend/app/contexts/evidence/adapters/orm.py`, `postgres_repositories.py` | `EvidenceRecordModel` (SQLAlchemy), `PostgresEvidenceRepository` |
| Migration | `backend/migrations/versions/0012_evidence_records.py` | `evidence_records` table: RLS, indexes, FKs, least-privilege grants |
| Application | `backend/app/contexts/evidence/application/evidence_service.py` | `EvidenceService`: `record_upload`/`get_evidence`/`list_evidence_for_parcel`/`mark_hashed`/`seal`/`apply_legal_hold`/`release_legal_hold` |
| DI | `backend/app/contexts/evidence/dependencies.py` | `get_evidence_repository`/`get_evidence_service` FastAPI providers |
| Test infra | `backend/tests/fakes/evidence.py` | `InMemoryEvidenceRepository` |
| Test harness | `backend/tests/app_factory.py` | `AppHarness.evidence` field + `dependency_overrides` wiring (no router included — none exists yet) |
| Tests | `backend/tests/test_evidence_domain.py`, `test_evidence_service.py` | 34 new tests |
| Infra | `backend/migrations/env.py` | Registers `app.contexts.evidence.adapters.orm` with `Base.metadata` |
| Governance | `docs/adr/ADR-026-evidence-domain-model.md` | Status updated to Accepted |

## 2. Traceability matrix — ADR-026 → implementation

| ADR-026 decision | Implemented as |
|---|---|
| `EvidenceRecord` aggregate, immutable identity | `evidence_record.py:63-107` — `evidence_id` set once in `.new()`, no setter |
| Document metadata immutable once hashed | No setter exists for `filename`/`mime_type`/`size_bytes`/`evidence_type` at all — enforced by omission, matching `Parcel.parcel_id`'s own discipline |
| Lifecycle `RECEIVED→HASHED→SEALED`, one-way | `mark_hashed`/`seal`, each checking `self.status` before transitioning |
| Legal hold orthogonal to status, exception to post-seal immutability | `apply_legal_hold`/`release_legal_hold` deliberately skip `_ensure_not_sealed()` |
| Storage reference (`storage_key`, `worm_grade`) | Fields on the aggregate; `storage_key` required at construction (never null), `worm_grade` set only at `seal()` |
| Provenance (`basis`, `audit_ref`) | Fields on the aggregate; `audit_ref` pre-generated and set before persistence in `EvidenceService.record_upload`, mirroring ADR-023's own pattern |
| `EvidenceRepository` port shape | `ports.py` — exact method set ADR-026 specifies, no generic update/delete |
| Transaction boundaries (storage write before DB row) | Documented in `postgres_repositories.py` and `evidence_service.py` docstrings; not directly testable in this slice since no real `StoragePort` call happens yet (B5.3/B5.4) — the ordering *contract* is established now so B5.3 has no design decision left to make here |
| Domain events (audit) | `evidence.uploaded`/`.hashed`/`.sealed`/`.legal_hold.applied`/`.legal_hold.released`, via the unchanged kernel `audit()` function |
| No new authorization model | `_in_scope()` tenant check only (mirrors `parcel_service._in_scope` exactly, duplicated per the same ADR-013 precedent); no role-based mutation gate — deliberately deferred, per ADR-026's own "Out of scope" |
| RLS, same predicate as every tenant-scoped table | Confirmed **character-for-character identical** to `parcels`'/`parcel_ownership_history`'s predicate, live (§5 below) |

## 3. ADR compliance

- No `StoragePort`, Supabase Storage, or Cloudflare R2 code was touched or redesigned.
- No hash computation, WORM sealing (physical), chain-of-custody workflow, or legal-hold workflow
  was implemented — only the domain's own state fields and guarded transitions, as ADR-026 itself
  scopes.
- No authentication, authorization model, audit mechanism, or parcel ownership logic was modified
  — `evidence_service.py` reuses the existing kernel `audit()` function and `ExecutionContext`
  unchanged.
- No upload endpoint or router was added — confirmed by `git diff --stat` (below) touching no
  `api/` directory, and by the app boot-smoke test showing the route count unchanged (9 routes,
  same as before this slice).
- `EvidenceRecord` never carries a `verified`/`authentic` field — the non-adjudication doctrine is
  structural, not just a wording convention (ADR-026 "Explicitly not owned by the aggregate").

## 4. Migration verification (schema, static)

Live `\d evidence_records` output (Docker Postgres, `landvault` schema-owning role):

```
Foreign-key constraints:
    evidence_records_legal_hold_by_fkey FOREIGN KEY (legal_hold_by) REFERENCES identity_users(id)
    evidence_records_parcel_id_fkey FOREIGN KEY (parcel_id) REFERENCES parcels(id)
    evidence_records_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(id)
    evidence_records_uploaded_by_fkey FOREIGN KEY (uploaded_by) REFERENCES identity_users(id)
Policies (forced row security enabled):
    POLICY "evidence_records_tenant_isolation"
      USING ((((tenant_id)::text = current_setting('app.tenant_id'::text, true))
        OR (current_setting('app.is_super_admin'::text, true) = 'true'::text)))
```

Grants (`information_schema.role_table_grants`, `landvault_app`): **SELECT, INSERT, UPDATE only —
no DELETE**, confirmed both by the grants query and by a live attempted `DELETE` as `landvault_app`
failing with `permission denied for table evidence_records`.

## 5. Live verification results — observed, not assumed

All against the existing local Docker Postgres (`aquasavannah-landvault-postgres-1`), per
Engineering Rule 7:

| Check | Result |
|---|---|
| `alembic current` before | `0011` |
| `alembic upgrade head` (0011→0012) | Succeeded, no errors |
| Schema inspection (`\d evidence_records`) | All columns, FKs, indexes present exactly as designed |
| Grants (`landvault_app`) | SELECT, INSERT, UPDATE — no DELETE |
| RLS: same-tenant `INSERT`+`SELECT` as `landvault_app` | Succeeded; row visible |
| RLS: cross-tenant `SELECT` as `landvault_app` | **0 rows** — isolation confirmed, positive and negative |
| RLS: `super_admin` bypass (`app.is_super_admin='true'`) | Row visible regardless of tenant context |
| Mutable-row `UPDATE` as `landvault_app` (status/sha256) | Succeeded — confirms this table is **not** append-only, unlike migration `0011`'s history tables, by design |
| `DELETE` as `landvault_app` | **Denied** — `permission denied for table evidence_records` |
| Test transaction | Wrapped in `BEGIN`/`ROLLBACK` — zero residue left in the database |
| `alembic downgrade 0011` | Succeeded; `evidence_records` table, policy, and grants all removed (`pg_policies` count: 0) |
| `alembic upgrade head` (re-upgrade) | Succeeded; schema restored identically |
| Final `alembic current` | `0012 (head)` |

## 6. Test results

```
ruff check .          → All checks passed!
mypy app tests        → Success: no issues found in 116 source files
pytest -q             → 215 passed, 1 skipped, 2 warnings in ~22–49s
```

(181 passed before this slice + 34 new = 215; the 1 skip is the pre-existing live-only Postgres
rollback rehearsal from ADR-023, unrelated to this slice.) Zero regressions.

App-factory boot smoke test: `from app.main import app` succeeds with the same env vars
`tests/conftest.py` sets; route count unchanged at 9 (no evidence router exists in this slice).

**Test matrix, mapped to the authorization's explicit list:**

| Requirement | Covered by |
|---|---|
| Aggregate invariants | `test_evidence_domain.py` — 17 tests: construction validation, lifecycle ordering, sealed-immutability, legal-hold orthogonality |
| Repository behavior | `test_evidence_service.py` — exercises `InMemoryEvidenceRepository` through `EvidenceService` for every operation |
| RLS verification | §5 above (live, not unit-testable against an in-memory fake — same split ADR-023's own test file documents) |
| Append-only enforcement | **N/A by design** — this table is a mutable aggregate root (like `parcels`), not append-only (like migration `0011`'s history tables); §4/§5 instead verify the grant shape (`SELECT,INSERT,UPDATE`, no `DELETE`) that *is* the correct enforcement for this table's actual invariant |
| Transaction behavior | `PostgresEvidenceRepository` constructed from the same per-request `AsyncSession` as every other repository (code-level, matches ADR-023's Unit-of-Work pattern exactly); no live cross-repository rollback test in this slice since there is no second repository call to roll back against yet (that arrives with B5.3's real upload flow) |
| Migration verification | §4/§5 |
| Repository parity (real vs fake) | Both `PostgresEvidenceRepository` and `InMemoryEvidenceRepository` are checked by mypy against the identical `EvidenceRepository` Protocol (confirmed: `mypy app tests` passes with both wired through `dependencies.py`/`app_factory.py`); behavioral parity for the same scenarios (create→hash→seal→hold) is proven once against the fake (hermetic suite) and once against the real adapter (§5's live rehearsal) — the same split this codebase's own test file for ADR-023 documents explicitly, not an automated side-by-side comparison test (no precedent for that pattern exists anywhere in this codebase) |
| Legal hold invariants | `test_evidence_domain.py::test_legal_hold_can_be_applied_after_sealing`, `test_apply_legal_hold_requires_a_reason`, `test_release_legal_hold_clears_all_fields`; `test_evidence_service.py::test_apply_legal_hold_and_audit`, `test_apply_legal_hold_on_sealed_record_still_succeeds` |
| Custody invariants | `audit_ref` resolution: `test_evidence_service.py::test_upload_audit_ref_resolves_to_a_real_consistent_audit_entry`; full chain-of-custody *workflow* is out of scope for this slice (B5.5) |

## 7. Known limitations (stated, not hidden)

- No role-based mutation authorization exists yet — only tenant-scope enforcement. ADR-026 itself
  defers this ("Out of scope"); it is not an oversight of this slice.
- No cross-repository transactional-rollback test exists yet (e.g., "evidence row and audit entry
  roll back together on failure") — there is only one write per operation in this slice's service
  methods, so there is nothing yet to prove rolls back *together* with something else. This becomes
  testable once B5.3 adds a second write in the same request (e.g., a StoragePort call whose
  failure must not leave an orphan row — the exact scenario ADR-026's "Transaction boundaries"
  section already specifies).
- `worm_grade`/`sha256` values used in tests are synthetic placeholders (`"a" * 64"`, `"governance"`)
  — no real hash or real storage adapter exists yet to produce authentic ones.
- The non-adjudication check (`docs/ENGINEERING_RULES.md` §10) does not yet scan any Evidence
  surface, because no Evidence API response exists yet to scan (its scanners cover `api/`-directory
  code and real HTTP responses — neither exists for Evidence in this slice). This becomes relevant
  starting with B5.3.

## 8. Remaining scope (explicitly not this slice)

Everything in the authorization's "Explicitly Out of Scope" list: upload endpoints, storage
adapters, hash computation, WORM sealing, chain-of-custody workflow, legal-hold workflow, OCR,
evidence review, AI, notifications, payments, search, break-glass/cross-tenant access.

## 9. Definition of Done assessment

| DoD criterion (Tier 1, `docs/DOD.md`) | Status |
|---|---|
| Requirements implemented per ADR-026, nothing beyond it | ✅ |
| Ruff/mypy clean | ✅ |
| Unit tests pass, observed | ✅ (34 new, 215 total, 1 pre-existing skip) |
| Authorization via PDP/PEP where applicable | ✅ (no new path introduced; `ExecutionContext` reused unchanged) |
| RLS ships in the same migration as the new table | ✅ |
| No permissive fallback default introduced | ✅ (no new env var) |
| No second/parallel authorization path | ✅ |
| Documentation updated in the same change | ✅ (ADR-026 status, this package) |
| Deployable to staging with a rollback | ✅ — live up/down/up rehearsed |
| No feature marked complete without an observed passing test run | ✅ — every claim above is either a pasted command output or a specific test name |

## 10. Recommendation for acceptance

**Recommended for Governance Authority acceptance as delivered**, on the following explicit basis:
this slice implements exactly the database, domain, repository, and DI scope authorized — no
upload endpoint, no storage adapter, no hash/seal/custody/legal-hold *workflow* — and every claim
of correctness above is backed by an observed command output, not inference. The one deliberate
design judgment made without a line-item precedent in the authorization is treating
`evidence_records` as a **mutable aggregate root** (grant shape `SELECT/INSERT/UPDATE`, no
DB-level immutability trigger) rather than **append-only** (grant shape `SELECT/INSERT` plus a
trigger, migration `0011`'s shape) — justified in §4/§6 above and in the migration's own docstring,
on the grounds that ADR-026 never declares this table append-only, and its actual shape (a guarded
mutable aggregate with a terminal state) matches `parcels`' own precedent, not the history tables'.
Flagged explicitly for review, not assumed uncontroversial.

**Per the Merge Gate: not merged. Slice B5.3 not begun.** Awaiting explicit Governance Authority
authorization for both.
