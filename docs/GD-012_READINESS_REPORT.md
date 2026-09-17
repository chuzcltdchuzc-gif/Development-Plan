# GD-012 EVIDENCE ACTOR ATTRIBUTION HTTP GOVERNANCE READINESS REPORT

**Type:** Point-in-time governance readiness review, produced against `origin/main` at commit
`76ea17f323e3f1b3a3fbc27980e86ffb48a3eb76`, preserved as the pre-ratification readiness record
alongside the draft `docs/GD-012-evidence-actor-attribution-http-implementation-authorization.md`.

## 1. Baseline SHA and numbering verification

- `origin/main`: `76ea17f323e3f1b3a3fbc27980e86ffb48a3eb76` — fetched fresh for this drafting; matches
  the SHA at which the prior GD-009 Batch 1 closure assessment concluded, no intervening commits.
- GD-012 availability: confirmed by direct search of every `docs/GD-0*.md` file (highest existing:
  GD-011), the Article XVI Log in `docs/LV-000-constitution.md` (entries GD-001–GD-011 only), all six
  open pull requests (#28, #25, #12, #10, #9, #1 — none related), and the full remote branch listing
  (no `gd012`/`gd-012`-named branch). **GD-012 is the next available number, unused and uncontested.**

## 2. Sources inspected

Read in full, directly from `origin/main` at the baseline SHA above (not from conversational summary
or prior-session memory):

- `docs/LV-000-constitution.md`, Article XVI (full Governance Decision Log, GD-001 through GD-011).
- `docs/adr/ADR-026-evidence-domain-model.md` (full).
- `docs/adr/ADR-027-supabase-storage-authorization-and-tenant-isolation.md` (retrieved; consulted for
  tenant-isolation convention — this Decision's scope does not touch Storage).
- `docs/adr/ADR-028-evidence-actor-and-commissioning-provenance.md` (full, 678 lines).
- `docs/adr/ADR-029-audit-transaction-semantics-and-outcome-integrity.md` (full, previously read this
  session).
- `docs/adr/ADR-030-audit-chain-concurrency-ordering-and-linearization.md` (relevant sections read this
  session and in the prior closure assessment).
- `docs/GD-009-audit-transaction-semantics-implementation-authorization-and-adr-007-regularisation.md`
  (full).
- `docs/GD-010-audit-dag-verifier-implementation-authorization.md` (relevant sections; full document
  previously reviewed in this session's earlier closure assessment).
- `docs/GD-011-gd009-batch1-resumption-authorization.md` (full).
- Current implementation on `main`: `backend/app/contexts/evidence/application/attribution_service.py`
  (full, 359 lines), `backend/app/contexts/evidence/api/evidence_router.py` (full),
  `backend/app/contexts/evidence/api/dtos.py` (full), `backend/app/contexts/evidence/dependencies.py`
  (relevant section), `backend/app/contexts/evidence/domain/attribution.py` (constants),
  `backend/app/main.py` (router registration), `backend/migrations/versions/0014_evidence_actor_
  attributions.py` (trigger/constraint confirmation), and a repository-wide search for OpenAPI/
  generated-client tooling (`backend/scripts/export_openapi.py`, `lib/api-spec/openapi.yaml`,
  `lib/api-spec/orval.config.ts`).

No assumption was substituted for a direct read where the repository could answer the question.

## 3. Authority-chain findings

Verified directly, not assumed:

1. `ADR-028` (Accepted 2026-09-10) establishes the `EvidenceActorAttribution` architecture — domain
   model, migration shape, repository port — and explicitly defers two decisions: (a) who may record
   which attribution role, and (b) the API/disclosure contract, including whether `actor_name`/
   `actor_organization_name` need separate disclosure authorization.
2. `GD-009` (Accepted 2026-09-11) authorized transactional audit migration for exactly
   `evidence.actor_attribution.recorded`/`corrected`, with a §14 sequence (implement, test, review,
   merge, post-merge verify) as the condition for Governance to **consider** ADR-028 HTTP exposure —
   not an automatic grant.
3. `GD-011` (Accepted 2026-09-15) lifted `GD-009`'s concurrency-related suspension, restating at its
   own §19 that ADR-028 HTTP exposure "requires its own, further, separate Governance authorization"
   after the resumed Batch 1's own full sequence completes.
4. PR #35 completed that sequence: squash `76ea17f...`, single parent `2df3640...`
   (pre-Batch-1 baseline), tree-identical to the approved, human-reviewed head `d4e827b7...`, all
   required CI green, independently post-merge re-verified this session (337 hermetic tests, ruff,
   mypy, `git diff --check` all clean against an isolated checkout of the squash commit itself; the
   pre-merge live-PostgreSQL proof carries forward by the proven tree-identity, not independently
   re-run post-merge).
5. **Prerequisite satisfaction is not implementation authorization** — restated directly from
   `GD-009` §14 and `GD-011` §19's own text, both of which use materially identical language ("a
   separate, future, explicit Governance act, not an automatic consequence of Batch 1's merge"). GD-012
   is drafted to be that act; it grants nothing by existing in draft form.

## 4. Exact proposed HTTP scope

Two authenticated, mutating endpoints only:

- `POST /v1/evidence/{evidence_id}/attributions` → `EvidenceActorAttributionService.record_attribution`
- `POST /v1/evidence/attributions/{attribution_id}/corrections` →
  `EvidenceActorAttributionService.correct_attribution`

No `GET`/list/detail endpoint is proposed (§12 below explains why this is a deliberate scope choice,
not an oversight, notwithstanding that a `list_attributions_for_evidence` service method already
exists).

## 5. Existing services and router conventions

**Central finding: the domain/application/persistence/DI foundation this HTTP work would call into
already exists on `main`, independent of GD-012.** Direct inspection of
`attribution_service.py`'s own docstring and content shows:

- `EvidenceActorAttributionService` (with all three methods — `record_attribution`,
  `correct_attribution`, `list_attributions_for_evidence`) was implemented, tested, and merged under
  `ADR-028`'s own "Implementation consequences" authorization **before** GD-009 Batch 1 began. GD-009
  Batch 1's own PR #35 modified only two things in this file: the audit call in each of
  `record_attribution`/`correct_attribution`, swapped from `audit()` to `audit_staged()`, plus the
  `session` constructor parameter needed to support that. Everything else in the file — domain
  construction, authorization checks, tenant-scope checks, lineage resolution, the read method — was
  already on `main` beforehand.
- The FastAPI dependency `get_evidence_actor_attribution_service` (`dependencies.py`) is already fully
  wired, already resolving every constructor argument the service needs, including the request-scoped
  `AsyncSession`.
- **This means GD-012's actual implementation footprint is narrow**: a router module, two request
  DTOs, one response DTO, router registration in `main.py`, and tests — not a new domain, application,
  or persistence slice. This materially reduces this Decision's risk profile relative to what a cold
  read of "authorize the ADR-028 HTTP API" might suggest.

Router convention derived from `evidence_router.py` (the only existing precedent in this bounded
context):

- `APIRouter(prefix=..., tags=["evidence"])`, resource-scoped prefix.
- Two-tier authorization: a coarse `Depends(require_role(*PARCEL_REGISTRANT_ROLES))` (or
  `require_auth` for a read-open case, not applicable here) at the router layer, with the
  fine-grained, resource-aware check performed inside the application service.
- `operation_id` in `verbNoun` camelCase (`uploadParcelEvidence`, `listParcelEvidence`) —
  `recordEvidenceAttribution`/`correctEvidenceAttribution` would follow the same convention.
- `response_model` as a Pydantic DTO mirroring the service's own return shape field-for-field, per
  `dtos.py`'s own documented convention, deliberately omitting internal-only fields (`tenant_id` as
  implicit-in-session, `audit_ref` as audit-internal).

## 6. Authentication and authorization model

`ADR-028`'s deferred "who may record which attribution role" question is resolved by **reuse, not
invention**: `_can_mutate` in `attribution_service.py` (already on `main`, unmodified by this Decision)
is explicitly documented as "a deliberate, small duplication of `EvidenceService._can_mutate`,"
applying the identical creator-or-governance-role gate IMVP-5 already established for Evidence upload,
evaluated against the same `ParcelAuthorityInfo` and the same `GOVERNANCE_ROLES` constant. The proposed
HTTP-layer coarse gate — `require_role(*PARCEL_REGISTRANT_ROLES)` — mirrors `upload_parcel_evidence`'s
own coarse gate exactly, preserving the same two-tier split already proven at this router's only
existing sibling endpoint. **No new role, permission, or authorization mechanism is proposed**; this is
presented in the draft as a resolution by direct precedent-application, not a fresh policy decision —
Governance review should confirm this characterization is fair rather than accept it uncritically.

## 7. Tenant-isolation assessment

No new tenant-isolation surface is introduced. `_load_evidence_in_scope`/`_in_scope` (tenant match or
`super_admin`) and `_verify_actor_reference` (same-tenant-only live `actor_principal_id`, per `ADR-028`
"Tenant isolation" §2) are already implemented, already tested hermetically
(`test_evidence_actor_attribution_service.py`), and unchanged by anything this Decision proposes. The
HTTP router adds no independent tenant-scoping logic — it is a pure pass-through to already-governed
checks.

## 8. Actor-reference and snapshot rules

`ADR-028`'s four `actor_reference_kind` states (`INTERNAL_PRINCIPAL`, `EXTERNAL_NAMED`,
`HISTORICAL_ASSERTED`, `UNKNOWN`) and the immutable-snapshot requirement (`actor_name` captured at
write time regardless of `actor_principal_id`) are enforced today at the domain-construction layer
(`EvidenceActorAttribution.new`, raising `ValueError` → the service's existing `_bad_request` mapping to
HTTP 400). The proposed request DTOs mirror these constants as `StrEnum`s (matching `EvidenceType`'s own
mirror-plus-assertion pattern in `dtos.py`) purely for OpenAPI-visible validation and documentation —
they introduce no new business rule.

## 9. Correction and concurrency semantics

Append-only correction (new row, `supersedes_id` → current lineage head, superseded row never touched)
is enforced today at two layers: application (`_resolve_active_head`'s lineage walk) and database
(migration `0014`'s `evidence_actor_attributions_reject_cycle` trigger — confirmed present by direct
inspection, plus the supersession-uniqueness and no-self-supersession constraints `ADR-028` §"Supersession
integrity" requires). The draft requires one new proof this stack does not yet have: an HTTP-level,
real-Postgres test of two concurrent corrections racing against the same lineage head, confirming the
losing request surfaces a coherent 4xx rather than a 500 or a silently-accepted fork — this is a router-
level integration property, not something the existing service-level hermetic tests exercise.

## 10. Audit transaction integration

No new audit design. The router is required to call the existing, unmodified
`EvidenceActorAttributionService` methods, which already stage `evidence.actor_attribution.recorded`/
`corrected` via `audit_staged()` inside the same request-scoped session, per GD-009 Batch 1
(unaffected, unmodified by this Decision). The draft's only new test obligation here is a router-level
re-confirmation that the property survives HTTP-triggered invocation — not a re-proof of GD-009 Batch
1's own transaction/concurrency guarantees, which stand as already established.

## 11. Required HTTP/DTO/OpenAPI changes

- One new router module (`attribution_router.py`), registered in `main.py` alongside the existing five.
- Two request DTOs, one response DTO, in a new or extended `dtos.py`-equivalent module for this
  sub-surface.
- Mechanical OpenAPI regeneration via the already-existing `backend/scripts/export_openapi.py` (already
  covers all five existing routers) extended to include the two new routes, and the already-existing
  `lib/api-spec/orval.config.ts`-driven TypeScript client regeneration — both confirmed present in the
  repository as standing tooling, not new infrastructure. The draft is explicit that running this
  existing mechanism is authorized as a mechanical consequence of adding routes, and is explicitly not,
  by itself, authorization to write or modify anything that *consumes* the regenerated client.

## 12. Frontend exclusion

No frontend page, component, or Surveyor Dashboard work is authorized. This is stated three times in
the draft (§9, §11, §13) deliberately, given that a mechanical generated-client regeneration is
authorized as a build step — the draft is explicit that regeneration and consumption are two different
things, and only the former is in scope.

**The read/list exclusion is the single most consequential scope decision in this draft**, and is
recorded here for Governance's direct attention rather than buried in the operative text alone:
`list_attributions_for_evidence` already exists, already works, and would be the obvious "complete the
set" addition. The draft deliberately excludes it because `ADR-028`'s own "API contract" section left
the disclosure-authorization question for `actor_name`/`actor_organization_name` — plausibly personal
data about a third party who may never have interacted with LandVault at all (e.g. a `HISTORICAL_
ASSERTED` actor named off a fifty-year-old document, or an `EXTERNAL_NAMED` actor with no account) —
explicitly unresolved. Authorizing a list/read endpoint under GD-012 would answer that question by
implication rather than by the explicit decision `ADR-028` called for. The draft instead grants each
mutating endpoint permission to return only the row it just wrote, to the caller who wrote it — which
requires no new disclosure decision because that caller already possesses everything in the response
(they just supplied it). **This is presented to Governance as a recommendation, not a foregone
conclusion** — an alternative (authorize list/read now, with an explicit disclosure ruling) is available
if Governance judges the deferred question already answerable, but the draft as written does not make
that judgment on Governance's behalf.

## 13. Proposed test matrix

See draft §10 in full. Summary: 11 hermetic cases (auth failure, coarse-gate failure, fine-grained
authorization failure, invalid actor-reference, invalid enum value, not-found, self-supersession,
cyclic-attempt-rejected-at-router-level, non-adjudication wording, plus the two happy-path cases) and 3
real-PostgreSQL cases (concurrent-correction race, HTTP-triggered commit/rollback-together
re-confirmation, real-trigger cycle rejection). Existing GD-009 Batch 1 tests (hermetic and live) are
explicitly stated as insufficient substitutes, since they do not exercise the HTTP layer at all.

## 14. Migration and dependency findings

**None required.** `evidence_actor_attributions` and all its constraints (self-supersession check,
ordering/cycle trigger, single-successor uniqueness) already exist on `main` as migration `0014` —
confirmed present by direct inspection of `backend/migrations/versions/0014_evidence_actor_
attributions.py`, including the `{TABLE}_reject_cycle` trigger function and its `BEFORE INSERT`
attachment. No new runtime dependency is required for a JSON-body FastAPI router using existing
Pydantic/SQLAlchemy machinery already in `pyproject.toml`.

## 15. Non-adjudication compliance

The draft requires (§12) that both endpoints' OpenAPI descriptions restate, in substance, `ADR-028`'s
own non-implication rules for `ORIGINATED_BY`/`REVIEWED_BY`/`COMMISSIONED_BY` — no runtime disclaimer
field is introduced (none exists on any comparable existing DTO, e.g. `EvidenceResponse`), consistent
with this repository's practice of carrying that discipline in documentation/description text and
governance review rather than a wire-visible field.

## 16. ADR-028 architectural compatibility

Full compatibility confirmed by direct reading: this draft introduces no domain-model change, no new
field, no new invariant, and no reinterpretation of any of `ADR-028`'s four actor-reference states, its
three attribution roles, or its supersession-integrity rules. It exercises the already-accepted
architecture through a thin HTTP layer only.

## 17. Remaining-52 audit exclusion

Entirely unaffected. This draft touches none of the 52 eager `audit()` call sites GD-009 §6/GD-011
§6/§20 already exclude from any transaction-coupled migration; it calls the already-migrated two
(`evidence.actor_attribution.recorded`/`corrected`) via the existing, unmodified service methods only.

## 18. Pre-mortem findings

| Failure | Governance control (draft §) | Implementation acceptance test |
|---|---|---|
| Cross-tenant attribution creation | §5, §7 — reuses existing `_load_evidence_in_scope`/`_authorize_mutation`, unchanged | Existing hermetic tenant-isolation tests, extended to the HTTP layer (item 8, §10) |
| Identity spoofing via actor references | §5 — `_verify_actor_reference`'s existing same-tenant-only rule, unchanged | Existing hermetic test, extended (item 6, §10) |
| Corrections overwriting rather than appending | §7 — restates existing append-only mechanism; introduces no new write path | Item 2, and item 14 (real-trigger cycle rejection) |
| Concurrent correction forks | §7, §10 — requires a new HTTP-level real-Postgres race test | Item 12, §10 |
| HTTP success while audit staging fails | §8 — router must not bypass the existing shared-transaction path | Item 13, §10 (re-confirmation, not re-proof) |
| Bypassing the approved application service | §8 — explicit prohibition on any direct-to-database mutation path | Code review against the draft's own explicit requirement |
| API scope creeping beyond two mutating operations | §4, §9, §11 — explicit exclusion list, explicit stop-and-return phrase | Governance review of the merged PR's file scope, mirroring GD-009's own PR-boundary discipline |
| Personal information exposed through error messages | Not separately addressed in the draft — a gap, noted here | Recommend adding an explicit test that 404/400 responses for out-of-scope or nonexistent resources do not leak another tenant's attribution content (the existing `_not_found`/`_not_found_attribution` helpers return generic messages today, which appears sufficient, but this was not exhaustively verified against every error path during this drafting) |
| Attribution presented as legal ownership | §12 — non-adjudication language requirement | Manual/documentation review of OpenAPI description text |
| Generated-client regeneration becoming unintended frontend authority | §9, §11 — explicit "mechanical only" carve-out | Governance review of the merged PR's file scope (no frontend files) |

## 19. Unresolved architecture or authorization questions

1. **Personal-data disclosure for list/read** (`ADR-028`'s own open question) — the draft deliberately
   does not resolve this; it narrows GD-012's own scope to avoid answering it by implication. This
   remains open for a future, separate Governance act if a list/read endpoint is ever wanted.
2. **Error-message information-leakage across tenants** — flagged in §18 above as a gap this drafting
   did not fully verify; the existing generic 404 messages appear sufficient by inspection but were not
   exhaustively tested against every code path during this readiness review.
3. **Route path for correction** (`/v1/evidence/attributions/{attribution_id}/corrections`, not nested
   under an `evidence_id` segment) is a derived design choice, not a pre-existing convention this
   codebase has used before (no other correction/supersession endpoint currently exists in this bounded
   context to compare against) — Governance should confirm this path shape is acceptable rather than
   treat it as settled by precedent, since it is reasoned from the service signature, not copied from
   an existing route.

None of these three rises to a blocking defect in the draft as written; each is disclosed so Governance
reviews them deliberately rather than discovering them later.

## 20. Article XVI draft

Included in the operative document at `docs/GD-012-evidence-actor-attribution-http-implementation-
authorization.md` §14. Not inserted into `docs/LV-000-constitution.md` by this drafting — that edit is
explicitly reserved for ratification, per this repository's own established convention (identical to
how GD-009's and GD-011's own §21/§23 log text was drafted alongside, not before, ratification).

## 21. Exact files created

Exactly two, both uncommitted, both new (no existing file modified):

- `docs/GD-012-evidence-actor-attribution-http-implementation-authorization.md`
- `docs/GD-012_READINESS_REPORT.md`

Created in a fresh, detached worktree (`Development-Plan-gd012-draft`, checked out at
`origin/main`'s `76ea17f...`) to avoid placing uncommitted drafting material inside either the
already-merged `feat/gd009-batch1-resumption` worktree or the governance-protected
`feat/gd009-batch1-transactional-audit` preserved-prototype worktree (GD-011 §17's standing
retention/non-alteration instruction for the latter was not touched by this drafting).

## 22. Working-tree state

The drafting worktree contains only the two new files above, untracked, unstaged, uncommitted. No
existing governance document, ADR, LV-000, backend code, frontend code, or migration was modified,
staged, or committed. No branch was created; the worktree is in a detached-HEAD state at `origin/main`.
No push, commit, or PR was made.

## 23. Recommendation for Governance review

The draft is internally consistent with the full authority chain (`ADR-028` → `GD-009` → `GD-011` → PR
#35), reuses existing, already-accepted authorization and tenant-isolation mechanisms rather than
inventing new ones, narrows its own scope specifically to avoid silently answering `ADR-028`'s deferred
disclosure question, and derives its API surface from actual repository convention rather than
assumption. The three items in §19 are disclosed, non-blocking design notes for Governance's attention,
not defects requiring textual remediation before review. On that basis:

**GD-012 READY FOR FORMAL GOVERNANCE REVIEW**
