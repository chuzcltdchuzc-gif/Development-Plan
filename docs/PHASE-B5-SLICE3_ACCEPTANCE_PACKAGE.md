# B5 Slice B5.3 — Acceptance Package: Evidence Upload & Integrity Recording

**Status:** Implemented, observed passing locally and live against Docker Postgres, pushed to
`origin/feat/b5.3-evidence-upload-integrity`. **Not merged** — held for Governance Authority review
per the Merge Gate.

**Date:** 2026-08-04

**Governing ADR:** `docs/adr/ADR-026-evidence-domain-model.md` — Accepted; this slice implements its
"Transaction boundaries" and "Domain events" subsections, changing neither.

**Authorized scope:** the Evidence upload **application service** — hash, `StoragePort` write,
persist, independent read-back re-hash, `mark_hashed`, audit. Explicitly **not** an HTTP upload
endpoint; no `api/` router or `main.py` wiring was added.

---

## 1. Implementation summary

| Layer | File(s) | What it does |
|---|---|---|
| Application | `backend/app/contexts/evidence/application/evidence_service.py` | New `EvidenceIntegrityError`; `EvidenceService.upload_evidence()` — the real hash → store → persist → read-back-verify → mark_hashed → audit orchestration |
| DI | `backend/app/contexts/evidence/dependencies.py` | `get_storage_port()` (raises `NotImplementedError` if resolved in production — no real adapter exists, tests must override it); `get_evidence_service` now also depends on it |
| Test infra | `backend/tests/fakes/storage.py`, `backend/tests/fakes/evidence.py` | One-shot failure-injection attributes (`fail_next_put`/`fail_next_get`/`fail_next_add`/`fail_next_mark_hashed`) added to both fakes |
| Test harness | `backend/tests/app_factory.py` | `AppHarness.storage` field + `get_storage_port` override wiring |
| Tests | `backend/tests/test_evidence_upload.py` | 15 new hermetic tests |
| Tests (live) | `backend/tests/live/test_evidence_upload_rollback_live.py` | New live-Postgres rehearsal, mirrors `test_registry_history_rollback_live.py`'s structure exactly |
| Governance | `docs/adr/ADR-026-evidence-domain-model.md` | Implementation status note added |

**No changes to:** `EvidenceRecord` (domain), `EvidenceRepository`/`StoragePort` (port shapes),
migration `0012`, RLS, grants, `ParcelHistoryRepository`, `Parcel`, or any authorization mechanism.

## 2. Traceability matrix — authorization → implementation

| Authorized item | Implemented as |
|---|---|
| Accept upload requests | `upload_evidence(*, ctx, parcel_id, filename, mime_type, data, basis, evidence_type)` |
| Validate request invariants | Empty-tenant and empty-content checks (400); unknown `evidence_type`/non-positive size surfaced via `EvidenceRecord.new()`'s own existing validation (400) |
| Create `EvidenceRecord` | Via `EvidenceRecord.new()`, unchanged from B5.2 |
| Compute integrity metadata | `hashlib.sha256(data).hexdigest()`, `len(data)`, caller-supplied `mime_type`/`filename`, service-generated `storage_key`, `created_at` (aggregate default) |
| Persist through `EvidenceRepository` | `self.evidence.add(...)`, then `.mark_hashed(...)` |
| Invoke `StoragePort` | `self.storage.put(...)` then `self.storage.get(...)` for read-back |
| Create audit references | Pre-generated `entry_id`, set as the record's own `audit_ref` before persistence (mirrors ADR-023's pattern exactly) |
| Return application response | `_evidence_view(record)` dict, unchanged shape from B5.2 |
| ADR-026 transaction-order rules | Storage write precedes the DB row precisely as specified; live-verified (§7) |
| SHA-256, reuse kernel conventions | `hashlib.sha256`, the same algorithm `app.kernel.audit`'s hash chain already uses; no new dependency |
| Wire DI: dependencies.py, app factory, test harness | §1 above |

## 3. ADR compliance matrix

| ADR-026 provision | Compliance |
|---|---|
| "Transaction boundaries" — storage write before DB row | ✅ Implemented exactly as specified; live-verified |
| "Domain events" — `evidence.uploaded`/`evidence.hashed` action names | ✅ Both fired, in that order, verified in hermetic and live tests |
| No redesign of aggregate invariants | ✅ `EvidenceRecord` unmodified — confirmed by `git diff` touching no file under `domain/` |
| No redesign of legal hold, custody, ownership, parcel model | ✅ Untouched |
| No redesign of `EvidenceRepository`/`StoragePort` shapes | ✅ Unmodified — confirmed by `git diff` touching no method signature in `ports.py` |
| No new authorization model | ✅ Reuses `ExecutionContext`/tenant-scope check unchanged; no role-gating decision made |

## 4. Integrity verification evidence

- **Hash correctness** (`test_hash_matches_independently_computed_sha256`): `result["sha256"] ==
  hashlib.sha256(data).hexdigest()`, computed independently in the test.
- **Independent read-back re-hash is real, not decorative**: `test_integrity_mismatch_raises_and_leaves_record_at_received`
  uses a storage double that returns corrupted bytes on `get()` — the service detects the mismatch,
  raises `EvidenceIntegrityError`, fires `evidence.integrity_check_failed` (decision `DENY`,
  payload carrying both hashes for investigation), and the record is left at `RECEIVED`,
  `sha256=None` — never silently marked `HASHED` on a hash it could not confirm.
- **No client-supplied hash is ever trusted** — the service accepts no `sha256` parameter on
  `upload_evidence()` at all; it is always computed server-side.

## 5. Repository verification

- **Repository parity (real vs fake):** both `PostgresEvidenceRepository` and
  `InMemoryEvidenceRepository` are checked by mypy against the identical `EvidenceRepository`
  Protocol (`mypy app tests` passes with both wired through `dependencies.py`/`app_factory.py`/the
  live test). Behavioral parity for the same scenario (upload → hash → persist) is proven once
  against the fake (hermetic suite, §6) and once against the real adapter (live rehearsal, §7) — the
  identical split this codebase's own ADR-023/B5.2 test files already document, not a runtime
  side-by-side comparison test (no precedent for that pattern exists anywhere in this codebase).
- **StoragePort/repository failure paths**, both persist points:
  - `test_storage_put_failure_prevents_any_record_creation` — storage fails first; no repository
    call, no audit entry, nothing to roll back (ordering itself prevents it).
  - `test_repository_add_failure_after_storage_write_leaves_orphan_object` — storage succeeds,
    repository fails; the named, accepted residual risk (an orphaned stored object, no DB row) is
    directly observed, not merely asserted in prose.
  - `test_repository_mark_hashed_failure_leaves_record_at_received` — the RECEIVED row and its
    `evidence.uploaded` audit entry survive; the HASHED transition alone fails and does not corrupt
    the earlier state.
  - `test_storage_get_failure_during_readback_leaves_record_at_received` — a failure during the
    read-back itself (not the initial write) also leaves the record honestly at `RECEIVED`.

## 6. Test evidence — hermetic suite

```
ruff check .          → All checks passed!
mypy app tests         → Success: no issues found in 118 source files
pytest -q              → 230 passed, 2 skipped (both live-only Postgres rehearsals), 2 warnings
```

(215 passed before this slice + 15 new = 230.) Zero regressions. App-factory boot smoke test
(`from app.main import app`) unchanged: 9 routes — confirms no HTTP surface was added.

**Full test list** (`backend/tests/test_evidence_upload.py`): upload success (2), upload failure
(3), hash correctness (2), duplicate-upload behaviour documented as undefined-by-ADR-026 and
therefore unimplemented (1), storage/repository failure at every persist point (4), audit linkage
(1), integrity-mismatch handling (1), tenant scoping (1).

## 7. Live verification — observed, not assumed

Run against the existing local Docker Postgres (`aquasavannah-landvault-postgres-1`), via
`backend/tests/live/test_evidence_upload_rollback_live.py` (`LIVE_ROLLBACK_ADMIN_URL` set):

```
tests\live\test_evidence_upload_rollback_live.py .    [100%]
1 passed in 6.70s
```

What this one test observed, in a single run against a throwaway database (created, migrated,
torn down):

1. **Migration `0012` applies cleanly from scratch** on top of the full chain (`0001`–`0012`) — a
   from-genesis rehearsal, not only the incremental `0011→0012` step B5.2 already verified.
2. **A full, real `upload_evidence()` call** through `PostgresEvidenceRepository`, with a real
   `EagerPostgresAuditStore` (the exact class `app.main.create_app` wires in production) — not a
   fake audit store. Confirmed via a **fresh connection** afterward: the row persisted with
   `status=HASHED` and the correct `sha256`; both `evidence.uploaded` and `evidence.hashed` audit
   entries exist, durably, in the real `audit_log` table.
3. **Rollback**: a fault injected before the session's commit (matching the identical technique and
   documented boundary `test_registry_history_rollback_live.py` already established for Registry)
   — the `EvidenceRecord` row does **not** persist, and no orphan `audit_log` entry references it.
4. **The orphaned storage object is confirmed to exist** after the rollback — the exact, named,
   accepted residual risk ADR-026 "Transaction boundaries" describes, observed directly rather than
   only asserted in the ADR's prose.
5. **Connection pool health after rollback**: one more real write succeeds afterward, proving the
   session factory is not poisoned by the fault injection.

## 8. Known limitations (stated, not hidden)

- **Streamed/chunked hashing is not implemented.** `upload_evidence(data: bytes, ...)` hashes the
  complete, already-in-memory content in one pass. True chunked hashing of a live HTTP multipart
  body is a property of whichever future slice adds the actual upload endpoint — this method's own
  hashing logic is already correct and reusable once that endpoint exists; only its
  input-acquisition step would need to change.
- **No duplicate-upload detection.** ADR-026 does not define this behaviour (confirmed by re-reading
  its "Decision" and "Out of scope" sections); none is implemented. Uploading identical content
  twice produces two independent `EvidenceRecord` rows — observed directly in
  `test_uploading_identical_content_twice_creates_two_independent_records`, not merely assumed.
- **No real `StoragePort` adapter still exists.** `get_storage_port()` in `dependencies.py` raises
  `NotImplementedError` if ever resolved outside a test, by design — Supabase Storage/Cloudflare R2
  remain out of scope (Rule 5 dependency approval + live credentials, neither available). The live
  rehearsal (§7) used `InMemoryStoragePort`, proving the *ordering* discipline against a real
  database, not proving a real cloud adapter's own behaviour — that remains unverifiable until such
  an adapter exists.
- **The audit-store/main-session pairing is not itself transactional** — a pre-existing, documented
  gap from B1/ADR-007 (`app.kernel.audit_postgres.EagerPostgresAuditStore` commits independently and
  eagerly), not introduced or worsened by this slice. The live rollback test deliberately injects its
  fault before the first `audit()` call to isolate the row's own atomicity claim from this
  pre-existing, separately documented boundary — identical to how the Registry live-rollback test
  already handles it.

## 9. Deferred scope (explicitly out of this slice)

Everything the authorization's "Explicitly Out of Scope" list names: Supabase Storage adapter,
Cloudflare R2 adapter, WORM sealing (the physical act — the domain's `SEALED` status/`seal()` method
already existed from B5.2 and is unchanged), legal hold workflow, custody workflow, OCR, AI
processing, review workflow, notifications, payments, search, exports, evidence verification,
break-glass access, cross-tenant evidence access. Also deferred, noted but not authorized in this
slice: an actual HTTP upload endpoint/router.

## 10. Definition of Done assessment

| DoD criterion (Tier 1, `docs/DOD.md`) | Status |
|---|---|
| Requirements implemented per authorization, nothing beyond it | ✅ |
| Ruff/mypy clean | ✅ |
| Unit tests pass, observed | ✅ (230/230, 15 new) |
| Live verification, observed | ✅ (§7) |
| Authorization via PDP/PEP where applicable | ✅ — no new path; tenant-scope check reused unchanged |
| RLS ships with new entity | N/A — no new table |
| No permissive fallback default introduced | ✅ — `get_storage_port()` fails loudly (`NotImplementedError`), never silently degrades |
| No second/parallel authorization path | ✅ |
| Documentation updated in the same change | ✅ (ADR-026 status note, `PHASE-B5_IMPLEMENTATION_PLAN.md`, `CLAUDE.md`, this package) |
| No feature marked complete without an observed passing test run | ✅ |

## 11. Recommendation for acceptance

**Recommended for Governance Authority acceptance as delivered.** This slice implements exactly the
authorized application-layer orchestration — no HTTP endpoint, no real storage adapter, no workflow
beyond upload+hash+persist — and every claim above is backed by either a pasted command/test output
or a named, specific test. The one design judgment made without a direct line-item in the
authorization: choosing to leave real chunked-hashing/multipart-body handling for the future
endpoint slice rather than half-building it now against a `bytes` parameter — flagged in §8, not
hidden.

**Distinguishing status, as required:**

- **Implemented:** `upload_evidence()` orchestration, integrity-mismatch handling, DI wiring,
  failure-injection test infrastructure, hermetic and live test coverage.
- **Verified:** hash correctness, transaction ordering, rollback behaviour, audit linkage, all live
  against real Postgres (§7) in addition to hermetic coverage (§6).
- **Deferred:** real storage adapters, HTTP upload endpoint, streamed hashing, duplicate detection
  (undefined by ADR-026), everything in §9.
- **Out of scope:** everything the authorization explicitly excluded (§9).

**Per the Merge Gate: not merged. B5.4 not begun.** Awaiting Governance Authority review.
