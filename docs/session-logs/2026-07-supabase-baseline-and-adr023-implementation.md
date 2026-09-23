# Session Log — Keycloak Export, Supabase Platform Baseline, and ADR-023 Implementation

**Type: historical record only. This is not a governance document, not an ADR, not part of the
Constitution, and not part of the Bible volume numbering.** It is a plain narrative account of one
Claude Code conversation, kept so a future reader has context on *why* certain documents and code
changes were produced and in what order — never as evidence of what any document or the codebase
currently says. If anything below conflicts with the actual, current content of any governing
document, any ADR, or the code itself, **those are correct and this log is simply out of date.**
This log is not updated retroactively when things change after the fact; it records what happened
at the time, not what is current now.

**Date range covered:** 2026-07-30 through 2026-07-31.

---

## How this conversation started

The conversation opened mid-stream, continuing governance and infrastructure work already
in flight: GD-006 (regularising post-ratification observations) had been drafted and required
narrow-scope confirmation; a Keycloak realm export (`72dcc85`) was suspected of overstating what it
actually captured; and ADR-023 (Registry Ownership and Status History) already existed as Accepted
from an earlier session.

## 1. GD-006 scope confirmation and ADR-024 (Delivery Platform & Infrastructure Decisions)

GD-006 was confirmed, as drafted, to be narrowly scoped to factual post-ratification observations
only — no ADR approvals, no infrastructure work, no implementation activity folded in. Separately,
ADR-024 was drafted and committed: a decision record for storage (`StoragePort`/Cloudflare R2/WORM
grading), identity (Keycloak, confirmed at the time), payments (Paystack-only for pilot one,
narrowing ADR-006), and the AWS compute-provider decision that had previously lived only as an
inline `CLAUDE.md`/`EXECUTION_PLAN.md` note.

## 2. A repo mismatch, caught before any action

A large pasted "Prompt A" document named a different repository
(`C:\Users\chuky\Documents\GitHub\aquasavannah-landvault`) than the one this conversation's shell
session was rooted in (`landsecure-registry`). Rather than proceed on the assumption they were the
same project, the mismatch was verified directly: `landsecure-registry` had none of the governance
instruments the prompt referenced (no `docs/LV-000-constitution.md`, no `docs/adr/`, no
`infra/keycloak/`), while `aquasavannah-landvault` — confirmed as a sibling directory — had all of
them, and its `git remote` pointed at `Development-Plan`, matching the prompt's own `gh api`
commands exactly. The rest of this conversation operated in `aquasavannah-landvault`, invoked via
absolute paths from a shell whose default working directory stayed pinned to `landsecure-registry`.

## 3. Keycloak realm export: the overstated-completeness defect, confirmed

`infra/keycloak/realm-landvault.json`'s `clientId`/`groups`/`roles` counts were checked directly:
zero clients, zero groups, zero roles — despite commit `72dcc85`'s message claiming a "real export"
with `exportClients=true, exportGroupsAndRoles=true`. The root cause: those two flags were sent as
JSON request-body fields to `kcadm.sh create realms/.../partial-export`, but the endpoint reads them
as query parameters, so both silently defaulted to `false`. This was confirmed by direct inspection
before any correction was proposed. The actual re-export was paused, pending the user completing an
interactive `kcadm.sh config credentials` authentication step themselves (never handled in chat,
per the standing credentials rule) — and, notably, was still not completed by the end of this
conversation; it remains open work.

## 4. A "Revision I" master prompt: Supabase as the platform baseline

A second large pasted prompt directed a platform pivot: Supabase Auth as the production identity
provider (retiring Keycloak), Supabase-hosted Postgres/RLS, Supabase Storage, and narrowly-scoped
Supabase Edge Functions, with Vercel for frontend hosting. Given the scale of what "Supabase Edge
Functions are the backend execution environment" could mean if read literally — up to and including
superseding ADR-002's FastAPI/DDD-hexagonal architecture across all 13 bounded contexts — three
clarifying questions were asked before any document was touched:

1. Whether ADR-004's PDP/PEP/PIP policy engine was being retired in favour of bare RLS, or retained
   with RLS as the last-mile layer underneath it (**answer: retained**).
2. Whether the existing FastAPI backend was being superseded by Edge Functions, or whether Edge
   Functions were additive for narrow new needs only (**answer: FastAPI stays; Edge Functions are
   additive**).
3. (In a follow-up round) what ADR number the new Supabase decision should take, given the standing
   rule against auto-allocating ADR numbers (**answer: 025**, with the previously-earmarked "Pilot
   Non-Functional Targets" ADR renumbered to 026).

`ADR-025-supabase-platform-baseline.md` was drafted on that basis: superseding ADR-004 §1 (identity
provider only) and ADR-024 D2/D4 (identity, compute) in full, refining ADR-024 D1 (storage — R2
becomes the WORM-grade escalation adapter behind Supabase Storage, not superseded), and leaving
ADR-002, ADR-004 §2–§5, ADR-015, and ADR-022 explicitly untouched. It was first left at Proposed
(pending a superseding-ADR precondition the user had set), then moved to Accepted once the user
confirmed, in a later message, that Supabase Auth was the production target and Keycloak a "retired
evaluation" outright. `ADR-024`'s D2/D4 sections were annotated as superseded (historical text
preserved, not rewritten), and a "Technology Replacement Principle" section was added to `ADR-024`
per the governing prompt's own instruction.

## 5. A real, pre-existing defect found while re-verifying the test baseline

Before trusting the historical "148 passing" figure, the suite was actually run. It failed at
*collection* — `Settings` (`extra="forbid"`) rejected several keys present in the root `.env` that
belong to `docker-compose`/Alembic (`POSTGRES_USER`, `KEYCLOAK_ADMIN`, etc.) but that `Settings`
itself never declared. Fixed by relaxing to `extra="ignore"` (every actually-required, declared
field still fails closed on its own). Two further, independent defects surfaced once collection
succeeded: `test_jwt_verifier.py`'s async tests were silently depending on `asyncio_mode = "auto"`,
a setting only discovered when pytest's rootdir resolves to `backend/` — not from the repo root,
which is how the suite is actually invoked — so an explicit `pytestmark = pytest.mark.asyncio` was
added; and `test_missing_database_url_fails_closed` assumed no `.env` file would supply
`DATABASE_URL`, which is false for a real local checkout, fixed with `_env_file=None` to isolate the
assertion under test. Result: 148 passed, 0 failed, `ruff`/`mypy` clean — matching the historical
figure exactly once the environment mismatch was corrected, not coincidentally.

## 6. Branch protection, on a solo-maintainer profile

Once `gh` was confirmed genuinely installed (not merely a stale PATH — `where gh` found nothing
until it was invoked by absolute path, since the install predated this shell session), classic
branch protection was applied to `main`: required status checks (`pytest / ruff / mypy`,
`typecheck / lint / test / build`, names discovered from real CI runs via the public GitHub API, not
guessed), required conversation resolution, linear history, no force pushes, no deletions,
`enforce_admins: false`, and a satisfiable `required_approving_review_count: 0` — deliberately
excluding admin enforcement, code-owner review, and signed commits, per explicit instruction. A test
push was not flatly rejected as the original template anticipated — it succeeded, tagged "Bypassed
rule violations," because the authenticated account is the repo's own admin/owner and
`enforce_admins: false` grants exactly that bypass. This was reported as the correct, intended
behaviour for a solo maintainer, not a protection failure, with the caveat that a true rejection
could not be demonstrated without a non-admin collaborator account.

## 7. Implementing ADR-023: Registry Ownership and Status History

A `docs/PHASE-1_IMPLEMENTATION_PLAN.md` was written first (migration sequencing, affected
components, risk register, test matrix — all reproducing ADR-023's own decisions, not adding new
ones), accepted, and only then implemented: migration `0011` (two append-only history tables,
RLS identical to `parcels`, `GRANT SELECT, INSERT` only, a `BEFORE UPDATE OR DELETE` trigger as a
second, independent enforcement layer); `OwnershipAssertion`/`StatusAssertion` domain value objects;
a `ParcelHistoryRepository` port with a Postgres adapter and an in-memory fake; and history-writing
calls added to `create_parcel`/`update_parcel`/`archive_parcel`, with a small, backward-compatible
addition to the kernel's `audit()` function (an optional `entry_id` parameter) so a history row's
`audit_ref` could be set before the corresponding, independently-and-eagerly-committing audit write.

A live rehearsal against the actual Docker Postgres container — not merely the in-memory-fake test
suite — caught a real defect the design and the unit tests could not have revealed: the migration's
first draft built both history tables from one shared tuple of SQLAlchemy `Column`/`ForeignKey`
objects, which silently dropped every foreign key except the self-referencing `supersedes_id` on
the second table created. This was found by inspecting `\d parcel_status_history` directly against
the live database, not assumed correct from reading the migration source. Fixed by generating fresh
`Column` objects per table, then re-verified: 8 foreign keys total (4 per table), RLS enabled and
forced on both, both append-only layers independently rejecting `UPDATE`/`DELETE` (including from
the schema-owning role, which bypasses privilege grants entirely), a real end-to-end HTTP
create/update/archive flow via the live backend and real Keycloak-issued JWTs, and a full
upgrade→downgrade→upgrade repeatability cycle. Final state: 158/158 tests passing (148 + 10 new),
`ruff`/`mypy` clean, PR #2 opened, with the one applicable CI check (`pytest / ruff / mypy`)
green.

One defect in the branch-protection configuration itself surfaced at this point: the PR reported
`mergeStateStatus: BLOCKED` despite its one applicable check passing, because
`typecheck / lint / test / build` is path-filtered to `frontend/**` and therefore never ran at all
for a backend-only change — yet branch protection still requires it by name. This affects every
future path-filtered PR, not just this one, and was left unresolved and explicitly flagged rather
than silently worked around.

## What remained open at the end of this conversation

- The Keycloak realm export correction (§3) — paused on the user's interactive `kcadm.sh`
  authentication step, never completed in this conversation.
- PR #2 (ADR-023 implementation) — open, not merged; blocked by the path-filtered required-check
  interaction described in §7, awaiting the user's decision on how to resolve it.
- The non-adjudication automated check (`docs/ENGINEERING_RULES.md` §10) — still unimplemented,
  a pre-existing gap this work did not close and did not claim to close.
- The secrets manager decision (`ADR-024` D5 / `ADR-025` E5) — still undecided.
- "No orphan history row on a failed mutation" — verified only via a unit test plus the kernel's
  existing rollback-on-exception behaviour, not a live fault-injection test against real Postgres.
