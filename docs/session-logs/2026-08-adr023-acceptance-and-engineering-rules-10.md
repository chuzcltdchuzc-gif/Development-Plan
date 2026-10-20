# Session Log — ADR-023 Acceptance/Merge and Engineering Rules #10 (Non-Adjudication Check)

**Type: historical record only. This is not a governance document, not an ADR, not part of the
Constitution, and not part of the Bible volume numbering.** It is a plain narrative account of one
Claude Code conversation, kept so a future reader has context on *why* certain documents and code
changes were produced and in what order — never as evidence of what any document or the codebase
currently says. If anything below conflicts with the actual, current content of any governing
document, any ADR, or the code itself, **those are correct and this log is simply out of date.**
This log is not updated retroactively when things change after the fact; it records what happened
at the time, not what is current now.

**Date range covered:** 2026-07-31 through 2026-08-01.

---

## How this conversation started

The conversation opened with a large pasted governance directive — a "Phase 8 Acceptance Package"
review for ADR-023 — addressed to a Claude Code session, but the session's actual shell was rooted
in `landsecure-registry`, a separate frontend-only repository with no ADR-023, no PR #2, no
`ENGINEERING_RULES.md`, and no relation to the backend migration file the IDE happened to have open
(`aquasavannah-landvault/backend/migrations/versions/0011_registry_ownership_status_history.py`).
Rather than proceed on the assumption the directive applied to the current working directory, the
mismatch was surfaced directly to the user, who confirmed the correct target repository was
`Development-Plan` (cloned locally at
`C:\Users\chuky\Downloads\LandVaultBibleLibrary\Development-Plan`) — found by searching local
directories for a remote matching a repo name the user supplied. All subsequent work in this
session happened there, via isolated `git worktree` checkouts per task rather than the single local
`main` checkout, which was found to already carry unrelated pre-existing uncommitted changes
(`CLAUDE.md`, `frontend/package.json`, `frontend/package-lock.json` modified;
`.claude/`, `AGENTS.md`, `docs/bible/`, `frontend/lib/utils.test.ts` untracked) that were
deliberately left untouched throughout.

GitHub CLI (`gh`) was not on `PATH` at the start of the session but was found already installed and
already authenticated (`chuzcltdchuzc-gif`, `repo`/`workflow` scopes) once located — no OAuth flow
was needed.

## 1. Phase 8 Acceptance Package — two conditions on PR #2 (ADR-023)

PR #2 (`feat/adr-023-ownership-status-history` → `main`, implementing ADR-023 — Registry Ownership
and Status History) had been reviewed in an earlier session and held at "ACCEPT WITH CONDITIONS."
Two conditions remained:

**Condition 1 — CI/branch-protection defect.** `main`'s branch protection required two status
contexts (`pytest / ruff / mypy`, `typecheck / lint / test / build`), but both `backend-ci.yml` and
`frontend-ci.yml` gated their *trigger* on `paths:` filters. Because PR #2 was backend-only,
`frontend-ci.yml` never ran and its required context stayed permanently pending — confirmed via
`gh pr checks` and `gh api .../branches/main/protection` before any fix was proposed. The fix
(proposed, confirmed with the user, then implemented as **PR #3**, merged `4a16bb6`): both
workflows always trigger now, with `dorny/paths-filter` gating the actual work steps *inside* the
job, so an unaffected path still reports a passing (skipped-work) status. The fix was verified
empirically with a throwaway backend-only test PR (#4, closed without merging) before being applied
for real, then PR #2 was rebased onto the fixed `main` and both required checks were confirmed
passing.

**Condition 2 — live PostgreSQL rollback evidence.** ADR-023's own acceptance note had flagged that
its "same Unit of Work" rollback claim was backed only by unit tests against in-memory fakes and by
reading (not observing) the kernel's rollback logic. A new test,
`backend/tests/live/test_registry_history_rollback_live.py`, was designed (confirmed with the user
first), then implemented and run against an ephemeral database on the user's already-running local
Docker Postgres: it drives the real `app.kernel.uow.get_db_session` generator with the real
Postgres-backed repositories, injects a genuine fault before commit, and confirms on a fresh
connection that neither the parcel row, the history rows, nor any `audit_log` entry persisted, then
proves the connection pool isn't poisoned by completing one more real write. Also functioned as a
live-migration rehearsal (Alembic clean through revision `0011`). The test is skipped by default
(no live database configured) so it never affects the hermetic CI suite.

`docs/PHASE-8_ACCEPTANCE_PACKAGE.md` was written recording both conditions' evidence. With both
GREEN, the user gave explicit merge authorization and **PR #2 was merged** (squash commit
`1601564`). A follow-up correction (**PR #5**, merged `6278206`) fixed one stale
pre-merge statement in that acceptance package ("PR #2 has not been merged") once the merge had
actually happened.

## 2. Phase 9 — Engineering Rules #10 (non-adjudication automated check)

With ADR-023 closed, the user authorized the next governed slice: implementing `ENGINEERING_RULES.md`
§10 (LV-000 v1.8 Article IV §4 — an automated check that fails the build on ownership-adjudication
wording in API responses and user-facing text), split deliberately into an investigation-and-plan
stage followed by a separate, explicitly-authorized implementation stage.

**Investigation** read the Constitution (Article IV §§1–4), `GOVERNANCE_BASELINE.md` Part C.3,
`EXECUTION_PLAN.md` §7.5–7.6, ADR-013/015/021/022/023, `PLATFORM_INTELLIGENCE_ARCHITECTURE.md`,
`CLAUDE.md`, and the actual Registry/spatial code — finding zero existing implementation of the
check anywhere, but also finding the domain model (ADR-013/ADR-023's "assertion, never a
determination") already constitutionally aligned by construction. The primary false-positive risk
identified was ADR-021's six-category spatial classification vocabulary ("confirmed conflict" — a
geometric finding, not an ownership determination; no such code exists yet, since B4 Slice 3
remains unauthorized pending ADR-021's own acceptance).

`docs/PHASE-9_IMPLEMENTATION_PLAN.md` (**PR #6**, merged `484a734`) proposed two pytest-based
scanning layers — AST-based static-source scan and real-API-response-content scan, sharing one
reviewed multi-word phrase blocklist — running inside the existing required `backend-ci.yml`
`pytest` step, with a full test matrix including adversarial detection probes and false-positive
proofs. It concluded no new ADR was required (the requirement's existence, scope, and enforcement
standard were already fully decided across the Constitution, Governance Baseline, and Engineering
Rules themselves). The user reviewed and explicitly approved this plan before any code was written.

**Implementation** (**PR #7**, merged `88448e4`) built exactly that: `backend/tests/support/non_adjudication.py`
(the blocklist and both scanners) and `backend/tests/test_non_adjudication_check.py` (12 tests
covering every plan test-matrix item, including synthetic adversarial probes proving actual
detection capability and false-positive proofs against ADR-021 vocabulary, caller-submitted data
containing the word "Owner," and existing legitimate error messages). `ENGINEERING_RULES.md` §10
was updated from "not yet implemented" to "Implemented" only after 170/1-skipped tests, clean
`ruff`, and clean `mypy` were actually observed. `docs/PHASE-9_ACCEPTANCE_PACKAGE.md` recorded the
evidence; the user reviewed and explicitly authorized the merge.

**Documentation synchronization** (**PR #8**, merged `000a770`) updated `CLAUDE.md`'s operational
summary to record both completions and the current test count, and added
`docs/REPOSITORY_STATUS_REPORT.md` — a consolidated snapshot of Constitution/Bible/ADR/Governance
Decision/Engineering Rules status, completed vs. remaining implementation slices, outstanding
governance items, and current platform maturity (noting, among other things, that ADR-020 is
deliberately vacant and that ADR-021 remains the one open ADR decision in the repository).

## State at the end of this conversation

`main` is at `000a770`. ADR-023 is Accepted — Implemented, merged, with live-rollback evidence.
`ENGINEERING_RULES.md` §10 is Implemented. 170 backend tests pass, 1 skipped (the live-only
rollback rehearsal), `ruff`/`mypy` clean, Alembic head `0011`. No ADR, the Constitution, or any
Bible volume was modified by any of this work. The one open governance item flagged as a possible
next decision point is whether to bring ADR-021 (Spatial Conflict Detection) back for explicit
acceptance — not decided in this conversation, and no next implementation slice was begun or
selected.
