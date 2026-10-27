# GD-012 — Evidence Actor Attribution HTTP Implementation Authorization

**Status:** **ACCEPTED — 2026-09-17, on explicit Governance Authority ratification. IN FORCE.** This
Decision authorizes exactly the minimum authenticated HTTP interface described below — the same
category of authorization `docs/GD-009-...md` gave its own Batch 1 implementation — and the narrowly
bounded `_verify_actor_reference` message-normalization exception identified during formal Governance
review. It does **not** authorize any `GET`/list/detail attribution endpoint, any frontend work, or
anything beyond this Decision's own bounded scope; see "Explicit exclusions" under "Approval Gate"
below.

**Date drafted:** 2026-09-17. **Ratified:** 2026-09-17.

**Operative authority:** **Article XVI §2** — this is a later numbered decision that explicitly names
`docs/adr/ADR-028-evidence-actor-and-commissioning-provenance.md` (to supply the API-contract and
authorization decisions ADR-028 itself explicitly deferred) and relies on `docs/GD-009-audit-
transaction-semantics-implementation-authorization-and-adr-007-regularisation.md` and `docs/
GD-011-gd009-batch1-resumption-authorization.md` (both satisfied) as jointly discharging the
prerequisite GD-009 §14 named for considering this authorization. It is not proposed under Article
XIV and does not amend this Constitution.

## Ratification Record

Ratified by Governance Authority for AquaSavannah LandVault, **2026-09-17**, following the formal
Governance review (`GD-012 GOVERNANCE REVIEW PASS WITH REQUIRED TEXTUAL REMEDIATION`) and the required
textual remediation that review identified — the `actor_principal_id` cross-tenant existence-disclosure
finding (§6.4), its narrowly bounded implementation exception (§9), and the corresponding required test
coverage (§10 items 8–12, 17, 19) — verified applied before ratification
(`GD-012 TEXTUAL REMEDIATION COMPLETE — READY FOR GOVERNANCE RATIFICATION`). This record does not alter
the draft; it identifies what ratification covers:

- **Exactly two authenticated HTTP endpoints authorized** (§4): `POST /v1/evidence/{evidence_id}/
  attributions` and `POST /v1/evidence/attributions/{attribution_id}/corrections`, calling the
  existing, unmodified `EvidenceActorAttributionService.record_attribution`/`correct_attribution`.
- **Authorization reuses the existing creator-or-governance-role gate** (§5) — no new role, permission,
  or authorization mechanism is created.
- **Response contract resolved narrowly** (§6): each endpoint discloses only the row it just wrote, to
  the caller who wrote it; no list/detail/third-party-disclosure endpoint is authorized, leaving
  `ADR-028`'s broader personal-data disclosure question to its own future, separate Governance act.
- **The cross-tenant `actor_principal_id` existence-oracle finding is remediated, not merely noted**
  (§6.4, §9): the two pre-existing failure messages must be normalized into one externally
  indistinguishable response before either endpoint is exposed, via a narrowly bounded, explicitly
  scoped exception to this Decision's general "reuse the service unchanged" posture — no broader
  authorization-, tenant-, or audit-logic change is authorized by that exception.
- **No schema migration, no new runtime dependency, no audit-kernel/verifier change, and no frontend
  work** is authorized (§8, §9, §11).

## 1. Governance baseline verified for this drafting

Read directly against the current repository, not assumed or carried over from any prior document:

- `origin/main` SHA: **`76ea17f323e3f1b3a3fbc27980e86ffb48a3eb76`** — the GD-009 Batch 1 squash-merge
  commit (PR #35), confirmed the current tip of `main`, confirmed tree-identical to the formally
  human-approved PR #35 head (`d4e827b7090cf74a6236245a7c9716b1a9e67fa6`), confirmed all required CI
  checks green on the squash commit itself, confirmed via independent post-merge hermetic
  re-verification (337 hermetic tests, ruff, mypy, `git diff --check`, all passing against an isolated
  checkout of the squash commit).
- `docs/adr/ADR-026-evidence-domain-model.md`: **Accepted.**
- `docs/adr/ADR-027-supabase-storage-authorization-and-tenant-isolation.md`: **Accepted** — read for
  its tenant-isolation conventions; this Decision's scope does not touch Storage and finds no
  conflict.
- `docs/adr/ADR-028-evidence-actor-and-commissioning-provenance.md`: **ACCEPTED — 2026-09-10, on
  explicit Governance Authority ratification. IN FORCE.** Authorizes the `EvidenceActorAttribution`
  domain model, migration shape, and repository port only; explicitly defers (a) who may record which
  attribution role, and (b) whether and how attribution rows are exposed in any API response,
  including personal-data disclosure authorization for `actor_name`/`actor_organization_name` — both
  addressed by this Decision, below.
- `docs/adr/ADR-029-audit-transaction-semantics-and-outcome-integrity.md`: **ACCEPTED — 2026-09-11,
  IN FORCE.** Unaffected, unmodified by anything in this drafting.
- `docs/adr/ADR-030-audit-chain-concurrency-ordering-and-linearization.md`: **ACCEPTED — 2026-09-13,
  IN FORCE.** Unaffected, unmodified.
- `docs/GD-009-...md`: **ACCEPTED — 2026-09-11, IN FORCE.** Batch 1 (§5) implemented, tested, formally
  reviewed, squash merged (PR #35, `76ea17f...`), and post-merge verified — all five §14 steps
  independently confirmed complete for both `evidence.actor_attribution.recorded` and `.corrected`.
- `docs/GD-010-...md`: **ACCEPTED — 2026-09-14, IN FORCE.** DAG-aware `verify_chain()` merged and
  post-merge verified (PR #33). Unaffected by this Decision.
- `docs/GD-011-...md`: **ACCEPTED — 2026-09-15, IN FORCE.** Lifted GD-009 §11's suspension; its own
  §19 restates that this Decision — a further, separate, explicit Governance act — is exactly what
  remains outstanding before ADR-028 HTTP exposure.
- Article XVI Governance Decision Log (`docs/LV-000-constitution.md`): entries **GD-001 through
  GD-011** exist. No `GD-012` or higher entry exists anywhere in the repository (checked by direct
  search of every `docs/GD-0*.md` file, the Log itself, all open pull requests, and all remote
  branches — none competing).
- **Next available Governance Decision number, confirmed by repository reality: GD-012.**
- **Prerequisite satisfaction is not implementation authorization.** GD-009 §14 and GD-011 §19 both
  state, in identical substance, that satisfying the five-step sequence only makes ADR-028 HTTP
  exposure something Governance **may consider** authorizing — "a separate, future, explicit
  Governance act, not an automatic consequence of Batch 1's merge." This Decision, if ratified, is
  that act. Nothing before ratification authorizes any of the work below.
- **The application-service foundation already exists on `main`, independent of this Decision.**
  `backend/app/contexts/evidence/application/attribution_service.py`'s `EvidenceActorAttributionService`
  — `record_attribution`, `correct_attribution`, and `list_attributions_for_evidence` — together with
  its domain model (`domain/attribution.py`), repository port and Postgres adapter, and FastAPI
  dependency wiring (`dependencies.py:get_evidence_actor_attribution_service`), were already
  implemented, tested, and merged under ADR-028's own "Implementation consequences" authorization
  before GD-009 Batch 1 began (GD-009 Batch 1 added only the two methods' `audit_staged()` migration
  — confirmed directly by reading the file's own docstring and the diff GD-009 Batch 1 actually
  introduced). **This Decision therefore authorizes an HTTP router and its DTOs/tests calling an
  already-existing, already-reviewed application service — not a new domain/application/persistence
  slice.**

## 2. Purpose

This Decision does exactly one thing: **authorizes the minimum authenticated HTTP interface** needed
to record and correct Evidence actor attribution against an already-authorized `EvidenceRecord`, per
`ADR-028`'s accepted domain model, now that `GD-009` Batch 1 (as resumed by `GD-011`) has satisfied the
prerequisite `GD-009` §14 named. It supplies the two decisions `ADR-028` explicitly deferred to a
future, separate act — **who may record which attribution role** (§5 below) and **what, if anything, an
HTTP response may disclose** (§6 below) — and authorizes nothing else.

## 3. Governance chain verified

1. `ADR-028` establishes the actor-attribution architecture (Accepted, 2026-09-10).
2. `GD-009` authorized transactional audit migration for exactly
   `evidence.actor_attribution.recorded`/`corrected` (Accepted, 2026-09-11).
3. `GD-011` lifted `GD-009`'s Batch 1 concurrency-related execution suspension (Accepted, 2026-09-15).
4. PR #35 completed the authorized migration: squash commit `76ea17f...`, single parent
   `2df3640...`, tree-identical to the formally human-approved head `d4e827b7...`, all required CI
   green, independently post-merge verified (337 hermetic tests, ruff, mypy, `git diff --check`; the
   pre-merge live-PostgreSQL 6/6 concurrency/atomicity proof carries forward by proven tree identity).
5. `GD-009` §14's prerequisite for **considering** `ADR-028` HTTP exposure is therefore satisfied for
   both named events.

**Prerequisite satisfaction is not implementation authorization.** This Decision, once and only once
ratified, is what supplies that authorization — nothing before ratification does.

## 4. Scope authorized — two mutating operations, nothing else

Subject to §5 (authorization), §6 (response contract), §9 (boundaries), and §11 (explicit exclusions)
below, this Decision authorizes implementation of exactly:

**A. Record Evidence Actor Attribution** — `POST /v1/evidence/{evidence_id}/attributions`

Creates a new attribution row against an existing, in-scope `EvidenceRecord`, calling
`EvidenceActorAttributionService.record_attribution` unchanged.

**B. Correct Evidence Actor Attribution** — `POST /v1/evidence/attributions/{attribution_id}/corrections`

Appends a correction superseding an existing, in-scope attribution's current lineage head, calling
`EvidenceActorAttributionService.correct_attribution` unchanged. The route is attribution-scoped, not
nested under an `evidence_id` path segment: `correct_attribution`'s own signature takes only
`attribution_id` and resolves the governing `EvidenceRecord` from the attribution's own lineage
(`_resolve_active_head` → `head.evidence_id`) — requiring a caller-supplied `evidence_id` on this route
would be redundant with what the service already resolves, and would introduce a consistency-check
the service itself does not perform today. This mirrors the route/service-signature correspondence the
existing `evidence_router.py` already establishes (`upload_parcel_evidence`/`list_parcel_evidence` take
exactly the path/query parameters their service methods take, no more).

Route naming and path shape are derived directly from the two service methods' actual signatures and
from `backend/app/contexts/evidence/api/evidence_router.py`'s existing conventions (`APIRouter` with a
resource-scoped prefix, `operation_id` in the existing `verbNoun` camelCase style, `response_model`
Pydantic DTOs) — not invented independently of repository precedent.

**No other HTTP operation is authorized.** In particular, **no `GET`/list/detail endpoint is
authorized by this Decision** — see §6 below for why this is a deliberate scope boundary, not an
oversight, notwithstanding that `list_attributions_for_evidence` already exists at the service layer.

## 5. Authorization — reuses the existing, already-accepted gate; decides nothing new

`ADR-028`'s own text explicitly deferred "who may record which attribution role" as a role-gating
decision. **This Decision resolves it by reuse, not by invention**, because the deferred question has
already been answered once, at the application-service layer, by direct, deliberate extension of an
existing, already-governed pattern:

- `EvidenceActorAttributionService._can_mutate` (already on `main`, unmodified by this Decision)
  applies **exactly** the same creator-or-governance-role gate `EvidenceService._can_mutate` already
  applies to Evidence upload — "a deliberate, small duplication... mirroring the same 'a third
  occurrence is the trigger to promote this into the kernel' reasoning `ADR-013`/`ADR-026` already
  established," per that method's own docstring. It is evaluated against the same `ParcelAuthorityInfo`
  (the attributed Evidence's own parcel authority), the same `GOVERNANCE_ROLES` constant, and the same
  "creator or governance role" logic — not a new rule invented for attribution.
- **Coarse HTTP-level gate**: this Decision authorizes `require_role(*PARCEL_REGISTRANT_ROLES)` on
  both routes, exactly mirroring `upload_parcel_evidence`'s own coarse gate in
  `evidence_router.py` — a registrant role is necessary to reach either endpoint at all, with the
  service's own `_authorize_mutation`/`_can_mutate` remaining the fine-grained, resource-aware
  decision, exactly as the existing two-tier split already works for upload.
- **`ADR-028` "Tenant isolation" §3 is restated, not altered**: attribution never grants authorization,
  in either direction — being named as an actor confers no right, and being authorized to *record* an
  attribution is decided entirely by the caller's relationship to the Evidence's parcel, never by
  anything internal to the attribution claim itself.

**No new role, no new permission, and no broadening of `GOVERNANCE_ROLES`/`PARCEL_REGISTRANT_ROLES` is
authorized or required.** This Decision supplies the missing HTTP-layer wiring to an authorization
decision the application service already made, under precedent this Governance Authority already
accepted (`ADR-013`, `ADR-026`) — it does not make a new authorization decision.

## 6. Response contract — the genuinely unresolved question, decided narrowly

`ADR-028`'s own "API contract" section left open "whether personal data (`actor_name`,
`actor_organization_name`) requires its own disclosure authorization separate from Evidence's own read
authorization." This Decision resolves it as narrowly as the authorized scope (§4) allows, rather than
deciding the broader question by implication:

1. **Each mutating endpoint returns only the single row it just wrote**, to the same authenticated,
   already-authorized caller who just wrote it (mirroring `record_attribution`/`correct_attribution`'s
   existing return shape — each already returns exactly the created/corrected row as a `dict`, via the
   existing `_attribution_view` helper). A caller who is authorized to create an attribution row is
   self-evidently authorized to see the row they just created — this requires no new disclosure
   decision.
2. **No endpoint authorized by this Decision discloses any attribution row to a caller other than the
   one who just wrote it.** This is why §4 above authorizes no `GET`/list/detail route: `ADR-028`
   explicitly flagged third-party disclosure of `actor_name`/`actor_organization_name` (potentially
   personal data about someone who may never have consented to being named, per `ADR-028`'s own
   "Impersonation" red-team entry) as an open question, and this Decision does not resolve it by
   silent extension merely because `list_attributions_for_evidence` already exists at the service
   layer. **Exposing that method via HTTP — to any caller broader than "the row's own author,
   immediately after writing it" — requires its own, future, separate Governance act** that squarely
   decides the disclosure-authorization question `ADR-028` deferred, rather than inheriting an answer
   from this Decision's narrower mutating-endpoint scope.
3. The response DTO must, consistent with `evidence/api/dtos.py`'s existing convention (omitting
   `tenant_id` because it is implicit in the authenticated session; omitting fields that are always
   empty at this phase rather than always-null), omit `tenant_id` and include every other field
   `_attribution_view` already returns (`attribution_id`, `evidence_id`, `attribution_role`,
   `actor_reference_kind`, `actor_principal_id`, `actor_name`, `actor_organization_name`, `actor_type`,
   `basis`, `review_method`, `recorded_by`, `recorded_at`, `supersedes_id`, `is_active`) — omitting
   `audit_ref` as internal, exactly as `EvidenceResponse` already omits it for the same reason.
4. **Cross-tenant `actor_principal_id` existence disclosure — identified during formal Governance
   review, remediated here.** `EvidenceActorAttributionService._verify_actor_reference` (already on
   `main`, pre-dating this Decision) currently raises two HTTP 400s with different message text for
   `actor_principal_id`: one when the id matches no `identity_users` row at all ("...does not exist"),
   and a different one when it matches a real principal in a *different* tenant ("...must reference a
   principal in the same tenant..."). Both are already HTTP 400 today, but the distinguishable message
   text lets any authenticated caller use this field as a cross-tenant principal-existence oracle —
   submitting a guessed or enumerated UUID reveals whether it belongs to *some* real account on the
   platform, even though the caller can never reach that account's tenant, name, or role. This is
   pre-existing behavior, introduced before this Decision and unconnected to GD-009 Batch 1 — but it
   has never been reachable through a public HTTP surface before, and this Decision would be the first
   governance act to make it so. **This Decision therefore requires, as part of the implementation it
   authorizes** (see §9's explicit exception below), that the two failure paths be normalized into one
   externally indistinguishable response before either endpoint is exposed:
   - identical HTTP status code (400) for both a nonexistent and an out-of-tenant `actor_principal_id`;
   - identical error category/detail shape;
   - a single message that does not reveal which of the two conditions occurred, e.g.
     `actor_principal_id must reference an existing principal in the caller's own tenant`;
   - no actor name, organization, tenant identity, or other protected metadata in either response.
   Successful same-tenant principal resolution, and the prohibition on live cross-tenant references
   (`ADR-028` "Tenant isolation" §2), are unaffected — only the two *failure* messages are unified.

## 7. Append-only correction semantics — restated, not altered

The HTTP layer introduces no new correction semantics. `correct_attribution`'s existing behavior —
create a new row, `supersedes_id` pointing at the current lineage head, never update or delete the
superseded row — is called unchanged. The existing, already-migrated database-level invariants remain
the actual enforcement mechanism: no self-supersession, no cycles (enforced by
`evidence_actor_attributions_reject_cycle`, confirmed present in migration `0014`), and one direct
successor per superseded row. **Simultaneous correction attempts** are resolved by the same mechanism
`correct_attribution`'s existing `_resolve_active_head` and the database's own supersession-uniqueness
constraint already provide — the second of two racing corrections against the same lineage will either
resolve against an already-superseded head (a normal, already-handled case the existing hermetic test
suite covers) or fail the database's uniqueness guard; this Decision requires an HTTP-level acceptance
test proving the caller receives a coherent 4xx response in that race, not a 500, but authorizes no new
concurrency-control mechanism to produce it.

## 8. Audit transaction integrity — restated, not altered

The two relevant successful-mutation events remain exactly `evidence.actor_attribution.recorded` and
`evidence.actor_attribution.corrected`, staged via `audit_staged()` inside the same request-scoped
session `EvidenceActorAttributionService` already uses (GD-009 Batch 1, unmodified). **The HTTP router
must invoke `EvidenceActorAttributionService` exactly as it exists — it must not introduce any
alternative, direct-to-database mutation path**, and must not modify `audit_staged()`, eager `audit()`
behavior, `_compute_hash`, `GENESIS_HASH`, or `verify_chain()`. A successful HTTP-triggered mutation and
its audit record continue to commit or roll back together, exactly as GD-009 Batch 1 already proved;
this Decision requires no new transaction-level proof of that property, only that the router not
bypass it.

## 9. Exact API surface authorized

Derived directly from repository convention (`backend/app/contexts/evidence/api/evidence_router.py`,
`dtos.py`), not invented independently:

- **Router**: a new module, `backend/app/contexts/evidence/api/attribution_router.py`, an `APIRouter`
  registered in `backend/app/main.py` alongside the existing five (`app.include_router(...)`), exposing
  exactly the two routes in §4.
- **Request DTOs**: two new Pydantic request models (record, correct) mirroring
  `EvidenceActorAttribution.new`'s actual parameters — `attribution_role`, `actor_reference_kind`,
  `actor_type`, `basis`, `actor_principal_id` (optional), `actor_name` (optional),
  `actor_organization_name` (optional), `review_method` (optional) — with `attribution_role`,
  `actor_reference_kind`, and `actor_type` as `StrEnum`s mirroring the domain module's own constants
  (`ORIGINATED_BY`/`REVIEWED_BY`/`COMMISSIONED_BY`;
  `INTERNAL_PRINCIPAL`/`EXTERNAL_NAMED`/`HISTORICAL_ASSERTED`/`UNKNOWN`;
  `INDIVIDUAL`/`ORGANIZATION`/`UNKNOWN`), exactly as `EvidenceType` already mirrors
  `EVIDENCE_TYPES` with a same-file assertion keeping them in sync. Unlike the upload endpoint, these
  are ordinary JSON request bodies (no raw-bytes/multipart constraint applies here), so standard
  Pydantic request models are the correct and only sensible shape — no Engineering Rule 5 preflight
  question arises.
- **Response DTO**: one new Pydantic response model per §6.3 above, `AttributionResponse`.
- **Authorization dependency**: `require_role(*PARCEL_REGISTRANT_ROLES)` on both routes, per §5.
- **Application-service invocation**: `Depends(get_evidence_actor_attribution_service)` — the existing,
  already-wired dependency — unchanged.
- **API tests**: a new `backend/tests/test_attribution_api.py`, mirroring `test_evidence_api.py`'s
  existing structure and hermetic-fake conventions.

**OpenAPI/generated-client synchronization**: this repository already maintains
`backend/scripts/export_openapi.py` and `lib/api-spec/openapi.yaml`/`orval.config.ts` as a standing,
mechanical build step for every existing backend route (confirmed present and already covering the five
existing routers). This Decision authorizes running that same existing, unmodified export/generation
step against the two new routes — regenerating `lib/api-spec/openapi.yaml` and its generated TypeScript
client — as a mechanical consequence of adding the routes, not as a new capability. **This mechanical
synchronization is not, and must not be treated as, authorization to write or modify any frontend page,
component, or feature that consumes the regenerated client** — no frontend work of any kind is
authorized by this Decision (§11).

**Explicit, narrowly bounded exception — `_verify_actor_reference` message normalization.** This
Decision additionally authorizes exactly one, minimal change to existing application-service code
beyond the general "call the service unchanged" rule elsewhere in this Decision:
`EvidenceActorAttributionService._verify_actor_reference` (`attribution_service.py`) may be edited to
merge its two `actor_principal_id` failure branches (nonexistent; cross-tenant) into a single code
path raising one shared, non-distinguishing `_bad_request` message, per §6.4 above. This exception is
stated explicitly so implementation does not need to infer permission to touch this file, and so it is
not mistaken for the general "reuse unchanged" posture this Decision otherwise requires. Authorization
under this exception is **strictly limited** to that one message-normalization change, plus updating
the existing hermetic test(s) whose assertions depend on the old, distinguishable message text
(`test_cross_tenant_actor_cannot_be_linked_via_live_internal_reference`,
`test_nonexistent_internal_principal_rejected` — both in
`tests/test_evidence_actor_attribution_service.py`) and adding the new regression tests §10 requires.
**This exception does not authorize, and no implementation under it may introduce:**

- any change to `_can_mutate`, `_authorize_mutation`, or any other authorization rule;
- any change to tenant-membership resolution, `_in_scope`, or `PrincipalTenantPort`'s own logic —
  only the *message* raised after that logic already produced its answer may change;
- any new `actor_reference_kind` or `attribution_role`;
- any change to audit transaction semantics, `audit_staged()`, or any frozen audit-kernel region
  (§8, §11 remain fully in force);
- any broader refactoring of `attribution_service.py` beyond this one method's two `raise`
  statements;
- any schema migration.

**Explicitly excluded from this API surface** — none of the following may appear in the implementation
this Decision authorizes, individually or in combination:

- any `GET`, list, or detail endpoint for attribution (§6.2);
- frontend pages, components, or Surveyor Dashboard functionality of any kind;
- public or anonymous attribution submission;
- bulk/batch attribution;
- attribution deletion or any direct edit/replace operation (append-only correction, §7, is the only
  mutation shape);
- any new Evidence download or Storage endpoint;
- any endpoint not named in §4.

## 10. Required validation

The implementation this Decision authorizes must include tests proving, at minimum:

**Hermetic (in-memory fakes, mirroring `test_evidence_actor_attribution_service.py`'s existing
pattern, extended to the HTTP layer):**

1. Successful attribution recording via `POST /v1/evidence/{evidence_id}/attributions`.
2. Successful append-only correction via `POST /v1/evidence/attributions/{attribution_id}/corrections`.
3. Authentication failure (no/invalid credentials) → 401, before any service code runs.
4. Coarse-gate failure (caller lacks a `PARCEL_REGISTRANT_ROLES` role) → 403, before any service code
   runs.
5. Fine-grained authorization failure (authenticated registrant, not the Evidence's parcel creator, no
   governance role) → 403, from `_authorize_mutation` unchanged.
6. Invalid actor-reference combination (e.g. `INTERNAL_PRINCIPAL` with no `actor_principal_id`) → 400,
   from existing domain validation unchanged.
7. Invalid `attribution_role`/`actor_reference_kind`/`actor_type` value → 422, from FastAPI/Pydantic
   enum validation at the DTO boundary — the router's own contribution, not previously tested at the
   HTTP layer.
8. **Recording against a genuinely nonexistent `EvidenceRecord`** → 404, from
   `_load_evidence_in_scope` unchanged. **No existing test exercises this at the service layer for the
   attribution methods specifically** — this must be added, not merely "extended to HTTP" from an
   existing precedent.
9. **Recording against another tenant's `EvidenceRecord`** → 404, response body/status
   indistinguishable from item 8. **No existing test — hermetic or HTTP — exercises a genuinely
   cross-tenant `record_attribution` attempt today**; the existing suite covers cross-tenant *read*
   (`list_attributions_for_evidence`) and cross-tenant *actor-reference* validation only, not this
   mutation path. This is a net-new test obligation, not a lift of an existing one.
10. **Correcting a genuinely nonexistent `attribution_id`** → 404, from `_resolve_active_head`
    unchanged.
11. **Correcting an attribution belonging to another tenant** → 404, response body/status
    indistinguishable from item 10. **Likewise net-new** — the existing
    `test_unauthorized_caller_cannot_correct_attribution` test covers a same-tenant unauthorized
    principal (403), not a genuinely different-tenant caller (404); no existing test covers the
    cross-tenant case for correction.
12. **`actor_principal_id` existence-oracle regression (§6.4)** — submitting (a) an `actor_principal_id`
    matching no principal at all, and (b) an `actor_principal_id` matching a real principal in a
    different tenant, in otherwise-identical requests, must produce byte-identical response status,
    error category, and body — proving the §6.4/§9 normalization was actually applied, not merely
    described. A valid same-tenant `actor_principal_id` must remain accepted when every other
    requirement is met. May be established hermetically; a hermetic fake `PrincipalTenantPort` is
    sufficient for this property, since it turns entirely on message construction, not on database or
    transaction behavior.
13. Self-supersession attempt → 400/422, from existing domain validation unchanged.
14. Cyclic correction attempt → rejected, from the existing database trigger (requires a real-Postgres
    test, see below — a hermetic fake cannot exercise a database trigger).
15. Non-adjudication response wording: the two endpoints' OpenAPI descriptions/response examples must
    not imply ownership, legal validity, or certification (§12).

**Real PostgreSQL (mirroring `tests/live/test_attribution_transactional_audit_live.py`'s existing
pattern — mocks cannot prove these properties):**

16. Competing corrections against the same lineage head, executed concurrently: the losing request
    must receive a coherent 4xx response, not a 500 or a silently-accepted fork (§7).
17. Successful HTTP-triggered mutation and its audit record commit together; a forced failure after
    staging rolls both back together (re-confirming GD-009 Batch 1's existing property is not broken by
    the new call path, not re-proving GD-009 Batch 1 itself). No attribution row and no
    successful-mutation audit event may be committed following any of the items-8-through-11
    unauthorized/inaccessible attempts above — this must be verified as an actual persistence check
    against real PostgreSQL, not inferred from the HTTP status code alone.
18. Cyclic correction attempt rejected by the actual database trigger (item 14, against real
    PostgreSQL).
19. The router itself must not reintroduce the §6.4 distinction through exception translation or
    response serialization — i.e., the HTTP-level integration test for item 12 must confirm the
    router's own error-handling middleware/handler does not append additional detail (e.g. a debug
    traceback, a validation-library default message) that re-distinguishes the two cases the service
    layer already normalized.

Existing GD-009 Batch 1 hermetic and live tests are not substitutes for the above — they prove the
application service and audit-transaction properties in isolation from any HTTP surface; the tests
above prove the router's own contribution (authentication, coarse authorization, request validation,
response shape, and the two endpoints' composition of already-proven service behavior). **Items 8, 9,
10, 11, and 12 are, specifically, net-new test coverage this Decision requires — none of them exists
in the current suite today, at any layer**, confirmed by direct inspection during formal Governance
review; they are not a re-labeling of existing precedent.

## 11. No unauthorized architecture expansion

This Decision does not authorize, and no implementation under it may introduce:

- any new evidence domain entity, value object, or invariant beyond what `ADR-028`/the existing
  `domain/attribution.py` already define;
- any schema migration (`evidence_actor_attributions` and its constraints, per `ADR-028`
  "Implementation consequences," already exist on `main` as migration `0014` — confirmed present);
- any new runtime dependency;
- any change to authentication mechanism, RLS policy, or tenant-isolation architecture;
- any new tenant type;
- any redesign of `audit_staged()`, eager `audit()`, `verify_chain()`, `_compute_hash`, or
  `GENESIS_HASH`;
- migration of any of the remaining 52 audit call sites (`GD-009` §6, `GD-011` §6/§20 — entirely
  unaffected and unrelated to this Decision);
- any background-worker infrastructure;
- any external audit anchor, checkpoint, or completeness mechanism (`ADR-030` §6's limitation stands
  unaffected).

**Stop-and-return condition.** If implementation reality is found to require a migration, a new
dependency, a change to any of the frozen audit-kernel regions above, or an authorization mechanism
broader than §5's reuse of the existing creator-or-governance-role gate, the implementing engineer must
stop and return exactly:

**`GD-012 BLOCKED — [MIGRATION | DEPENDENCY | AUDIT-KERNEL | AUTHORIZATION] AUTHORITY REQUIRED`**

rather than improvise a workaround inside this Decision's own authority.

## 12. Non-adjudication language preserved

Every response and OpenAPI description this Decision authorizes must preserve, in substance, the
governing disclaimer already established by `ADR-028`/`ADR-026`'s non-adjudication doctrine (LV-000
Article IV): recording or correcting an attribution is an evidentiary assertion, never a determination
of legal ownership, copyright, professional licensure, or title validity. Consistent with this
repository's existing convention of carrying this discipline in code comments, docstrings, and
`ENGINEERING_RULES.md`-anchored review practice rather than a runtime string field (no such field exists
on `EvidenceResponse` today, and this Decision introduces none for the same reason), the two new
endpoints' OpenAPI `description` fields must state plainly that an attribution row records who is
asserted to be involved in creating, reviewing, or commissioning evidence, and nothing about ownership,
legal validity, or professional certification follows from it — mirroring `ADR-028`'s own "Origination
provenance"/"Professional review"/"Commissioning provenance" non-implication rules verbatim in
substance.

## 13. Explicit programme exclusions

For consistency with `GD-008`, `ADR-026`, and `ADR-028`'s own out-of-scope conventions: this Decision
does not authorize Marketplace; the Partner programme; Job; Assignment; Customer; accreditation;
payments; the Surveyor Dashboard; SECI; EQF; the Professional Performance Index; Rights or licensing;
Legacy Vault; `ADR-021` functionality; or general Background Jobs infrastructure. None of these is
touched, implied, or brought closer to authorization by this Decision's subject matter.

## 14. Article XVI entry

The following text is inserted into `docs/LV-000-constitution.md`'s Article XVI Log as part of this
ratification (a separate edit to that file, not by this document itself, and not performed by this
draft):

> **GD-012 — Evidence Actor Attribution HTTP Implementation Authorization.** *(Ratified 17 September
> 2026.)*
> Operative authority: **Article XVI §2** — GD-012 is a later numbered decision that explicitly names
> `docs/adr/ADR-028-evidence-actor-and-commissioning-provenance.md` (to supply the API-contract and
> authorization decisions it explicitly deferred) and relies on `docs/GD-009-...md` and `docs/
> GD-011-...md` (both satisfied, per PR #35's squash merge and post-merge verification) as jointly
> discharging `GD-009` §14's prerequisite; it is not proposed under Article XIV and does not amend this
> Constitution.
>
> **Decision.** Implementation of exactly two authenticated HTTP endpoints —
> `POST /v1/evidence/{evidence_id}/attributions` and
> `POST /v1/evidence/attributions/{attribution_id}/corrections` — calling the existing, unmodified
> `EvidenceActorAttributionService.record_attribution`/`correct_attribution` is authorized. Authorization
> reuses the application service's existing creator-or-governance-role gate (`ADR-013`/`ADR-026`
> precedent) unchanged; no new role or permission is created. Each endpoint discloses only the single
> row it just wrote, to the caller who wrote it — no list, detail, or third-party-disclosure endpoint is
> authorized, leaving `ADR-028`'s personal-data disclosure question to its own future, separate
> Governance act. As a narrowly bounded exception identified during formal Governance review,
> `_verify_actor_reference`'s two `actor_principal_id` failure messages (nonexistent vs. cross-tenant)
> must be normalized into one externally indistinguishable response before either endpoint is exposed,
> closing a pre-existing cross-tenant principal-existence oracle this Decision would otherwise make
> newly reachable via a public HTTP surface; no other application-service logic, and no authorization,
> tenant-membership, or audit-transaction rule, may change under this exception. No schema migration,
> no new runtime dependency, and no other change to the audit kernel, `verify_chain()`,
> tenant-isolation architecture, or any frontend surface is authorized or required.
>
> **Scope excluded — no retroactive expansion.** This decision does not authorise any `GET`/list/detail
> attribution endpoint; any frontend page, component, or Surveyor Dashboard work; bulk or anonymous
> attribution; attribution deletion or direct editing; migration of any of the 52 audit call sites
> `GD-009`/`GD-011` already exclude; or any of the programmes `GD-008`/`ADR-026`/`ADR-028` already
> exclude.

## Approval Gate

This Governance Decision is **ACCEPTED**, per the Ratification Record above. Acceptance authorizes
only the minimum authenticated HTTP interface described in §4, reusing the existing application
service and authorization gate unchanged (§5), plus the narrowly bounded `_verify_actor_reference`
message-normalization exception (§9) — never anything broader.

**Explicit exclusions.** Ratification does not authorize: any `GET`, list, or detail attribution
endpoint (§6, §9); any frontend page, component, generated-client consumption, or Surveyor Dashboard
work (§9, §11); bulk or anonymous attribution; attribution deletion or direct editing; any schema
migration, new runtime dependency, or audit-kernel/verifier change absent a further stop-and-return to
Governance (§11); any authorization-, tenant-membership-, or audit-logic change beyond §9's narrow
message-normalization exception; migration of any of the 52 call sites `GD-009`/`GD-011` exclude; or
any of the programmes named in §13.

**Implementation process, restated.** Ratification of this Decision authorizes drafting the
implementation; it does not itself constitute implementation, testing, review, or merge. The eventual
implementation must still follow this repository's standing feature-branch, testing, human-review,
squash-merge, and post-merge-verification discipline (the same five-step sequence `GD-009` §14 and
`GD-011` §19 already established for Batch 1) before either endpoint may be considered complete.

See the companion readiness report, `docs/GD-012_READINESS_REPORT.md`, for the independent challenge of
this draft that should precede any ratification decision.
