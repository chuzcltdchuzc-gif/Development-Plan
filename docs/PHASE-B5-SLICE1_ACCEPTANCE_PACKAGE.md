# B5 Slice B5.1 — Acceptance Package: `StoragePort`

**Status:** Implemented, observed passing locally. **Not merged — held for Governance Authority
review**, per the Master Implementation Authorization's Merge Gate step. No commit has been created;
all files below are new, untracked, on the working tree only.

**Date:** 2026-08-01

**Slice:** B5.1 — `StoragePort` protocol + in-memory fake, per `docs/PHASE-B5_IMPLEMENTATION_PLAN.md`
§Phase 5 and `docs/adr/ADR-026-evidence-domain-model.md` ("Relationship to Slice B5.1" — this slice
is governed by the already-Accepted `docs/adr/ADR-024-delivery-platform-and-infrastructure-decisions.md`
D1 / `docs/adr/ADR-025-supabase-platform-baseline.md` E3, not by ADR-026, which gates only the
`EvidenceRecord` aggregate).

## Files changed

| File | Purpose |
|---|---|
| `backend/app/contexts/evidence/__init__.py` | Seeds the Evidence bounded-context package; docstring states explicitly what does and does not exist yet |
| `backend/app/contexts/evidence/ports.py` | `StoragePort` Protocol, `WormGrade` type alias, `StorageObjectNotFoundError`, `StorageImmutabilityViolationError` |
| `backend/tests/fakes/storage.py` | `InMemoryStoragePort` — hermetic fake, same convention as `tests/fakes/registry.py` |
| `backend/tests/test_storage_port.py` | 11 tests against the fake |
| `docs/adr/ADR-026-evidence-domain-model.md` | Proposed ADR — `EvidenceRecord` aggregate domain model (gates Slice B5.2 onward, not this slice) |

**No production wiring** (`main.py`, `dependencies.py`) was touched — there is no consumer yet
(`EvidenceService` does not exist; that's Slice B5.3+, gated on ADR-026's acceptance), so there is
nothing to wire `StoragePort` into in production at this point. This mirrors how `GeometryPort`
existed as a Registry-side port for a full slice before Spatial supplied any implementation.

## What was deliberately NOT built, and why

**No real adapter (Supabase Storage, Cloudflare R2) exists.** Building one would require:

1. A new external dependency (a Supabase client library, `boto3` for R2's S3-compatible API, or
   equivalent) — `docs/ENGINEERING_RULES.md` rule 5 requires explicit human approval, a
   justification, and a pinned version before any such dependency is added. Not sought or assumed
   here.
2. Real Supabase Storage / Cloudflare R2 credentials, to actually exercise `put`/`get`/
   `put_immutable`/`worm_grade` against live infrastructure — `docs/ENGINEERING_RULES.md` rule 7
   ("never mark something complete without observing it pass") means a real adapter cannot be
   claimed done without a live rehearsal, and no live rehearsal is possible without credentials this
   session does not have.

Shipping a "real" adapter that only *looks* real — an SDK call wrapped in code nobody has run
against actual storage — is exactly the failure pattern `docs/adr/ADR-007-audit-trail-evidence-model.md`
exists to prevent (its own founding motivation: a prior "WORM" implementation that was fake at the
storage layer, never wired beyond a stub). This package does not repeat that pattern. What is
delivered instead is the honest, currently-completable slice: the Protocol, proven correct against a
hermetic fake, with the real-adapter gap named explicitly rather than hidden.

## Test matrix — observed, not assumed

All 11 new tests, run against the real `pytest` invocation, not inferred from code inspection:

| # | Test | Proves |
|---|---|---|
| 1 | `test_put_then_get_returns_same_bytes` | Basic round-trip |
| 2 | `test_get_missing_key_raises_not_found` | `StorageObjectNotFoundError`, not a silent `None`/empty result |
| 3 | `test_list_keys_filters_by_prefix_and_sorts` | Prefix filtering, deterministic order |
| 4 | `test_list_keys_no_match_returns_empty_list` | Empty match is a legitimate result, distinct from `get`'s not-found case |
| 5 | `test_ordinary_put_can_overwrite_before_sealing` | Pre-seal mutability is intentional, not a bug |
| 6 | `test_put_immutable_seals_key_and_is_readable` | Sealing writes and is subsequently readable |
| 7 | `test_ordinary_put_after_seal_is_rejected` | **The core guarantee**: a plain `put` cannot silently overwrite sealed data |
| 8 | `test_second_put_immutable_after_seal_is_rejected` | Re-sealing (even with identical intent) is rejected — sealing is one-way |
| 9 | `test_worm_grade_defaults_to_governance` | Default grade matches Cloudflare R2's documented grade (ADR-024 D1) |
| 10 | `test_worm_grade_reflects_configured_grade` | Grade is adapter-instance-configurable, matching the "escalate without code change" design |
| 11 | `test_unsealed_key_reports_not_sealed` | The seal-state introspection helper itself behaves correctly |

**Observed:**

```
=== ruff ===
All checks passed!

=== mypy (evidence + new test files) ===
Success: no issues found in 4 source files

=== full ruff (matches CI's `ruff check .`) ===
All checks passed!

=== full mypy (matches CI's `mypy app tests`) ===
Success: no issues found in 105 source files

=== full pytest ===
181 passed, 1 skipped, 2 warnings in 27.99s
```

(170 passed before this slice + 11 new = 181; the 1 skip is the pre-existing live-only Postgres
rollback rehearsal, unrelated to this slice.) Zero regressions.

## Definition of Done — Tier 1 (Feature), per `docs/DOD.md`

- **Functional:** Protocol shape matches ADR-024 D1/ADR-025 E3 exactly (`put`/`get`/`list_keys`/
  `put_immutable`/`worm_grade`).
- **Code Quality:** ruff clean, mypy strict clean, no duplication, follows `docs/adr/` decisions.
- **Testing:** 11 unit tests, all observed passing; no integration/e2e tests exist for this slice
  because there is no HTTP surface or database involvement yet (both are later slices).
- **Security:** No new entity/table (no RLS question applies to this slice — it is pure Python, no
  persistence). No new authorization path. No new external dependency was added.
- **Performance:** N/A — no I/O beyond the in-memory fake.
- **Documentation:** This package; `docs/adr/ADR-026-evidence-domain-model.md`'s own "Relationship to
  Slice B5.1" section; module docstrings on every new file.
- **Deployment:** N/A — no production wiring exists yet for this slice to be deployed through.

## Risks carried forward (not resolved by this slice, not hidden)

- **R1** (from `docs/PHASE-B5_IMPLEMENTATION_PLAN.md`) — real adapters remain unbuilt pending Rule-5
  dependency approval and credentials. This slice narrows the gap (the Protocol now exists and is
  proven correct in isolation) but does not close it.
- **R3** — WORM grade / data-residency default is still undecided (`docs/EXECUTION_PLAN.md` §10);
  `InMemoryStoragePort` defaults to `"governance"` for test ergonomics only — this is not a claim
  about which grade the real, eventual default adapter should use.

## Merge Gate

**Not merged.** Per the Master Implementation Authorization's own Delivery Method (step 9, "Merge
Gate") and "Working Style" ("do not... merge phases"), this package is submitted for review. No
`git add`/`git commit` was run. Awaiting explicit direction to stage and commit, and separately,
Governance Authority review/acceptance of `docs/adr/ADR-026-evidence-domain-model.md` before Slice
B5.2 may begin.
