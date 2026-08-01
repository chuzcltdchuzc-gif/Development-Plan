# Phase 9 Acceptance Package — Engineering Rules #10 (Non-Adjudication Automated Check)

**Subject:** PR #7, `feat/engineering-rules-10-non-adjudication-check` → `main`
**Status:** Implemented, tested, CI-verified. Held at the merge gate for explicit approval — not
merged by this package.
**Date:** 2026-08-01
**Governance sequence applied:** Observe → Implement → Test → Verify → Document → Review → CI →
Acceptance → Explicit Merge
**Authorizing plan:** `docs/PHASE-9_IMPLEMENTATION_PLAN.md` (approved; PR #6, merged `484a734`).
This package implements that plan exactly — no scope expansion, no new decision.

---

## 1. What was built

Two independent scanning layers, sharing a single reviewed phrase blocklist
(`backend/tests/support/non_adjudication.py`):

- **Static source scan** (`collect_static_sites` / `scan_static_sources`): AST-based extraction —
  not blanket grep — of exactly the constructs the plan named: `HTTPException(..., detail=...)`
  calls anywhere under `backend/app/`, any `description=` keyword argument anywhere under
  `backend/app/`, and module/class/function docstrings *only* within `api/`-directory files (the
  ones FastAPI actually exposes via OpenAPI). Internal application/domain-layer docstrings —
  which discuss "ownership," "determination," and "adjudication" as concepts extensively — are
  deliberately out of scope, since they are never returned to a caller.
- **Runtime response scan** (`scan_response_text`): flattens a real API response payload to text
  and scans it, catching wording assembled at request time that static scanning cannot see.
- **Blocklist:** 40+ multi-word phrases expressing a determination-of-right claim ("confirmed
  owner", "rightful owner", "title is valid", "ownership has been determined", etc.) — never bare
  single words ("owner", "confirmed", "verified", "conflict") in isolation, per the plan's
  false-positive analysis.

Both layers are exercised by `backend/tests/test_non_adjudication_check.py` (12 tests), which runs
inside the existing, already-required `pytest / ruff / mypy` CI job — no new workflow, no new
dependency (pure standard library — `ast`, `json`).

---

## 2. Test matrix — observed results (docs/PHASE-9_IMPLEMENTATION_PLAN.md §11)

| # | Scenario | Test | Result |
|---|---|---|---|
| 1 | Static scan of current real source | `test_static_source_scan_finds_no_adjudication_wording` | **PASS** — zero hits in `backend/app/` today |
| 2 | `GET /v1/parcels/{id}` response | `test_real_registry_endpoints_emit_no_adjudication_wording` | **PASS** |
| 3 | `POST` create / `PATCH` update / `POST archive` responses | `test_real_registry_endpoints_emit_no_adjudication_wording` | **PASS** |
| 4 | Adversarial probe — static scanner must actually detect | `test_static_scanner_detects_injected_adjudication_wording` | **PASS** — synthetic `HTTPException(detail="...confirmed owner...")` in a temp `api/` dir is caught; real source is never touched |
| 5 | Adversarial probe — response scanner must actually detect | `test_response_scan_detects_injected_adjudication_wording` | **PASS** — synthetic payload `{"note": "LandVault confirms ownership..."}` is caught |
| 6 | `current_owner_name`/`current_owner_contact` containing the word "Owner" as ordinary data | `test_real_registry_endpoints_emit_no_adjudication_wording` (uses "Ade Owens", "Owner's Court Estate Holdings") | **PASS** — no false positive |
| 7 | Existing legitimate `HTTPException detail=` messages | `test_existing_error_messages_are_not_misclassified` (6 parametrized cases) | **PASS** — no false positive |
| 8 | ADR-021 spatial classification vocabulary ("confirmed conflict", "no conflict", "boundary overlap", "suspicious pattern", etc.) | `test_blocklist_does_not_flag_spatial_conflict_classification_vocabulary` | **PASS** — no false positive |
| 9 | Full existing hermetic suite unaffected | `pytest -q` (whole suite) | **PASS** — 170 passed (158 pre-existing + 12 new), 1 skipped (unchanged live-rollback test) |

An additional test beyond the plan's numbered items, `test_internal_non_api_docstrings_are_not_scanned`,
directly proves the internal-vs-`api/`-directory docstring scope boundary described in the plan's
§6.2 — included because it is a design-correctness proof the plan called for but did not number
separately.

---

## 3. Exact verification results (this run)

| Check | Result |
|---|---|
| `ruff check .` | All checks passed! |
| `mypy app tests` | Success: no issues found in 101 source files |
| `pytest tests/test_non_adjudication_check.py -v` | 12 passed |
| `pytest -q` (full suite) | **170 passed, 1 skipped**, 2 warnings (pre-existing, unrelated) |
| GitHub CI — PR #7 (`6284d0a`) | `pytest / ruff / mypy`: **pass** (59s); `typecheck / lint / test / build`: **pass** (8s, skip path — frontend untouched) |
| `gh pr view 7` merge state | `mergeable: MERGEABLE`, `mergeStateStatus: CLEAN` |

---

## 4. Scope discipline — diff review

`git diff --stat` for this PR's single commit:

```
docs/ENGINEERING_RULES.md               |   4 +-
backend/tests/support/__init__.py       | new file
backend/tests/support/non_adjudication.py | new file
backend/tests/test_non_adjudication_check.py | new file
```

- **No** `.github/workflows/*.yml` change — the checks run inside the existing required `pytest`
  step, exactly as the plan specified (§14).
- **No** `backend/app/` change — no application, domain, port, or adapter code touched. The check
  is entirely test-time infrastructure.
- **No** ADR change of any kind. `docs/adr/ADR-023-*.md` and all other ADRs untouched.
- **No** `docs/LV-000-constitution.md` (Constitution) or Bible-volume change.
- **No** authorization-model change — `app/kernel/authorization/` untouched.
- **No** new dependency — the scanner uses only `ast` and `json` from the Python standard library.
- **One** documentation change: `docs/ENGINEERING_RULES.md` §10's "Why" note, updated from
  "not yet implemented" to "Implemented," with the evidence location cited — made only after the
  above results were observed (§7's own rule: never mark complete without having observed it
  pass), not in advance.

This matches the plan's §15 (Backward compatibility) and §9 (Non-scope) exactly. `CLAUDE.md` was
deliberately **not** modified — the plan listed this as "if warranted," and a minimal-scope PR was
judged not to warrant it; §10 was already absent from `CLAUDE.md`'s 6-rule summary before this
work and remains a documentation choice, not a governance gap.

---

## 5. Definition of Done (docs/PHASE-9_IMPLEMENTATION_PLAN.md §18)

- [x] Implementation complete
- [x] Tests complete
- [x] Negative cases (adversarial probes, items 4–5) tested and observed detecting
- [x] Positive/legitimate cases (items 6–8) tested and observed passing
- [x] `ruff` clean
- [x] `mypy` clean
- [x] Full `pytest` green (170 passed, 1 skipped)
- [x] CI green (both required PR checks pass)
- [x] Documentation updated (`ENGINEERING_RULES.md` §10)
- [x] Traceability complete — every test maps to a plan §7 traceability-matrix row or §11
      test-matrix item; no untraced control introduced
- [x] No constitutional drift — Article IV not reinterpreted or expanded beyond §4's own stated
      scope (API responses and user-facing text); frontend, reports/exports/marketing-copy
      scanning remain explicitly out of scope, as decided in the plan, not silently added
- [x] No architectural decision introduced without an ADR — none was required (plan §19); none
      was introduced here either

---

## 6. Outstanding governance items (unchanged by this work)

- Frontend/UI-layer non-adjudication scanning — deferred, as planned, until a parcel-facing
  frontend exists to scan.
- Reports, exports, notifications, marketing-copy scanning — outside Article IV §4/§10's stated
  automated-check scope; expanding it would be a new decision, not made here.
- B4 Slice 3 (spatial conflict detection) — remains unauthorized pending ADR-021's own acceptance,
  entirely unrelated to and not advanced by this work.
- The audit-store/main-session independent-commit limitation (from the ADR-023 acceptance
  package) — pre-existing, unrelated to §10.
- Residual risk inherent to any keyword/phrase-based check: a genuinely novel adjudicating
  phrasing not on the blocklist would not be caught mechanically. Recorded, per the plan, as a
  known limitation mitigated by ordinary PR review as a second layer — not claimed to be
  eliminated.

---

## 7. Merge gate

- [x] PR #7 required checks pass
- [x] Branch protection satisfied normally (`mergeStateStatus: CLEAN`)
- [x] No administrator bypass used or required
- [x] No new architectural decision introduced; no ADR touched
- [x] Constitution and Bible untouched
- [x] Implementation matches the approved plan exactly — no scope expansion

**PR #7 has not been merged.** Per the governing sequence, this package stops here for explicit
approval.
