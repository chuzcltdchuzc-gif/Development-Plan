# Phase 1 Implementation Plan — Registry Ownership and Status History

**Status:** Draft, pending acceptance. No code is written under this plan until accepted.
**Date:** 2026-07-31
**Implements:** `docs/adr/ADR-023-registry-ownership-and-status-history.md` (Accepted, 2026-07-30) — exactly as written. This plan does not add, narrow, or reinterpret any decision ADR-023 already made; it sequences and operationalises it.

## Executive Summary

Registry (B3) gains two new append-only history tables — `parcel_ownership_history` and `parcel_status_history` — populated automatically inside the existing `create_parcel` / `update_parcel` / `archive_parcel` flows. No new endpoint, no new mutation command, no new authorization model. One additive migration (`0011`), two new domain value objects, one new repository port with a Postgres adapter and an in-memory fake, and history-writing calls added to three existing `ParcelService` methods. The Parcel aggregate's own contract — `current_owner_name`/`current_owner_contact` as a *current reference*, never a history — does not change (ADR-013 invariant #12, unchanged).

## Business Objective

Close the gap between "the audit chain proves a change happened" and "a structured, queryable table lets you ask what was asserted, who asserted it, on what basis, and when." This is the evidentiary backbone the Prime Directive requires before any future feature (verification requests, licensed assignment, due-diligence export) can honestly answer "what has been asserted about this parcel's ownership and status over time," without ever answering "who owns it."

## Architectural Objective

Extend Registry without adding a second authorization path, a second transaction boundary, or a second RLS model. Reuse: ADR-015's creator-or-governance check verbatim; the existing per-request Unit of Work (`app.kernel.uow.get_db_session`); `parcels`' RLS predicate text unchanged; the existing `audit()` mechanism (ADR-007) via new action names only. The two history tables are append-only by construction (privilege grant **and** a database trigger — two independent layers, ADR-023 "Append-only, enforced at the database").

## Scope

- Migration `0011`: `parcel_ownership_history`, `parcel_status_history` — schema, indexes, RLS (enabled + forced + policy, identical predicate to `parcels`), grants (`SELECT, INSERT` only), append-only triggers (`BEFORE UPDATE OR DELETE`, unconditional `RAISE EXCEPTION`).
- Domain: `OwnershipAssertion`, `StatusAssertion` value objects in `app.contexts.registry.domain`.
- Port: `ParcelHistoryRepository` protocol (`record_ownership`, `record_status`) mirroring `ParcelRepository`'s shape — a `Protocol`, a Postgres adapter, an in-memory fake.
- `ParcelService.create_parcel` writes the initial ownership assertion (if an owner reference was supplied) and the initial `ACTIVE` status assertion, in the same transaction as the parcel `INSERT`.
- `ParcelService.update_parcel` writes a new ownership-history row when, and only when, `current_owner_name` and/or `current_owner_contact` actually change (compared pre/post mutation).
- `ParcelService.archive_parcel` writes a status-history row for the `ACTIVE -> ARCHIVED` transition.
- New audit action names: `registry.parcel_ownership.recorded`, `registry.parcel_ownership.changed`, `registry.parcel_status.changed` — via the existing `audit()` function, no new mechanism.
- Full test matrix per ADR-023 (nine items, reproduced under "Testing Strategy" below).

## Out of Scope (per ADR-023, restated, not re-decided here)

- Ownership *transfer* as a distinct command — ADR-015 already left this open; this slice does not decide it.
- Any read endpoint over the history tables (e.g. `GET /v1/parcels/{id}/ownership-history`) — deferred to a future slice with an actual consumer.
- Evidence-backed `basis` values (B5+) — `basis` stays a fixed, honest string this slice (see "Basis" in ADR-023).
- Backfill of any kind for parcels existing before migration `0011` — explicitly, permanently out of scope, not merely deferred (see "Migration Strategy" below).
- The non-adjudication automated check (`ENGINEERING_RULES.md` §10) as a generic CI mechanism — this is cross-cutting infrastructure work, tracked separately; see "Dependencies" and "Definition of Done."
- Any Supabase, Keycloak, or identity-provider change of any kind — this slice has zero dependency on ADR-004/ADR-025 (see "Dependencies").
- Any storage, payment, or compute-platform work (ADR-024/ADR-025) — untouched by this slice.

## Dependencies

| Dependency | Status | Relevance |
|---|---|---|
| ADR-023 (Registry Ownership and Status History) | Accepted | The governing decision this plan implements |
| ADR-013 (Parcel Aggregate & Registry Domain Model) | Accepted, frozen (B3) | `current_owner_name`/`current_owner_contact` semantics unchanged (invariant #12) |
| ADR-014 (Atomic Parcel Number Allocation) | Accepted, frozen (B3) | No relationship — `parcel_number` untouched |
| ADR-015 (Registry Mutation Authorization Model) | Accepted, frozen (B3) | Creator-or-governance check reused verbatim — no new authorization branch |
| ADR-016 (Geometry Port Boundary) | Accepted, frozen (B3) | No relationship — geometry untouched |
| ADR-007 (Audit Trail & Evidence Model) | Accepted | New action names only, via the existing `audit()` function |
| ADR-009 (B1 Platform Freeze) | Accepted, frozen | PDP/PEP, Unit-of-Work, RLS pattern, audit chain — consumed unchanged |
| ADR-004 / ADR-025 (Identity) | Accepted | **Zero dependency.** No new authorization mechanism is introduced; whichever identity provider issues the JWT is irrelevant to this slice |
| ADR-024 (Delivery Platform) | Accepted | **Zero dependency.** No storage, payment, or compute surface is touched |
| `ENGINEERING_RULES.md` §10 (non-adjudication check) | Not yet implemented | Tracked separately (see "Definition of Done") — this plan's test matrix does not claim to satisfy it |
| Migration `0010` (`parcel_geometries`) | Merged | Confirms `0011` is the correct next migration number (verified: `backend/migrations/versions/` highest file is `0010_parcel_geometries.py`) |
| Test baseline | Verified green, 2026-07-31: 148 passed, 0 failed; `ruff check`: clean; `mypy`: clean, 106 files | The baseline this plan's own gate (148 + N green) is measured against |

## Affected Components

- `backend/migrations/versions/0011_registry_ownership_status_history.py` — new.
- `backend/app/contexts/registry/domain/` — two new value objects (`OwnershipAssertion`, `StatusAssertion`); no change to the existing `Parcel` dataclass's fields or invariants.
- `backend/app/contexts/registry/ports/` (or wherever `ParcelRepository`'s protocol lives) — new `ParcelHistoryRepository` protocol.
- `backend/app/contexts/registry/adapters/` — new Postgres adapter for `ParcelHistoryRepository`; new in-memory fake for tests.
- `backend/app/contexts/registry/application/parcel_service.py` (or equivalent) — `create_parcel`, `update_parcel`, `archive_parcel` gain history-writing calls; no signature change to any public method, no new endpoint.
- `backend/app/contexts/registry/dependencies.py` (or equivalent DI wiring) — one new provider for `ParcelHistoryRepository`, mirroring the existing `ParcelRepository` provider wiring.
- `backend/tests/` — new test module(s) for the history tables, append-only enforcement, cross-tenant isolation, and Unit-of-Work atomicity; existing Registry tests extended, not replaced.

No change to any API router, request/response DTO, or existing endpoint's contract.

## Database Changes

One migration, `0011`, additive only:

- `CREATE TABLE parcel_ownership_history` and `CREATE TABLE parcel_status_history`, shared shape per ADR-023 "Schema": `id` (UUID PK), `tenant_id` (FK -> `tenants.id`, NOT NULL), `parcel_id` (FK -> `parcels.id`, NOT NULL), `asserted_holder_ref` (nullable), `asserted_status` (nullable), `basis` (NOT NULL), `recorded_by` (FK -> `identity_users.id`, NOT NULL), `recorded_at` (TIMESTAMPTZ, server default `now()`), `audit_ref` (nullable), `supersedes_id` (nullable, self-FK).
- Indexes: `(tenant_id)` on both (matching `ix_parcels_tenant`'s shape), `(parcel_id)` on both, `(supersedes_id)` on both.
- RLS: `ENABLE ROW LEVEL SECURITY` **and** `FORCE ROW LEVEL SECURITY` on both tables; policy text copy-pasted verbatim from `parcels` (migration `0007`):
  ```sql
  tenant_id = current_setting('app.tenant_id', true)
    OR current_setting('app.is_super_admin', true) = 'true'
  ```
- Grants: `GRANT SELECT, INSERT ON parcel_ownership_history, parcel_status_history TO landvault_app` — **no UPDATE, no DELETE**, following the precedent in `backend/migrations/versions/0002_app_role_least_privilege.py`.
- Append-only triggers: a trigger function per table, `BEFORE UPDATE OR DELETE`, unconditionally `RAISE EXCEPTION`, created in this same migration (not a follow-up).
- `downgrade()`: drops both triggers, both trigger functions, both policies, both tables — a real, tested downgrade, not a stub. No data migration needed downward (nothing was backfilled).

## Migration Strategy

**History begins at the migration epoch. No backfill, ever — not deferred, declined.** Per ADR-023 "Migration and backfill strategy": Registry has no reliable record of who asserted an existing parcel's current owner reference, on what basis, or when — only that it is the value now on the row. A parcel created before `0011` shows no history until its next `update_parcel`/`archive_parcel`, at which point the first row is written honestly, describing the assertion being made *then*. Rollback is rehearsed on a staging-like database (Docker Postgres locally) before merge, per Article XI §3 — not assumed safe from reading the migration alone.

## Security Review

- **Authorization:** No new mechanism. History writes happen only as a side effect of mutations already gated by `_authorize_mutation`/`_can_mutate` (ADR-015). There is no "who may write history" question distinct from "who may mutate this parcel."
- **Tenant isolation:** RLS enabled and forced on both new tables, identical predicate and mechanism to `parcels`. Positive and negative cross-tenant tests are mandatory (see "Testing Strategy").
- **Append-only integrity:** Two independent layers — privilege grant (no UPDATE/DELETE to `landvault_app`) and a trigger that fires regardless of role, including the schema-owning migration role. Both must be observed failing independently in tests; passing only one does not prove the other exists.
- **Non-adjudication:** `asserted_holder_ref`/`asserted_status` are named and will be documented as *assertions*, never as "owner" or "title" bare, in any future surface that exposes them. The automated CI check for adjudication wording (`ENGINEERING_RULES.md` §10) is not implemented by this slice — flagged explicitly under "Definition of Done," not silently assumed satisfied.
- **PII:** No new PII surface — `asserted_holder_ref` sources from fields (`current_owner_name`/`current_owner_contact`) that already exist and are already governed by ADR-013's decision not to add anything resembling a national ID field.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| History row written without the mutation that produced it (or vice versa) | Low | High (data integrity, evidentiary trust) | Same `AsyncSession`/Unit of Work as the parcel mutation and the audit entry — one transaction, one commit point. Tested: a forced failure mid-transaction must leave zero orphan rows. |
| Append-only silently defeated by a future migration | Low | High (defeats the ADR's core guarantee) | Trigger layer is independent of role/privilege; dropping it would itself be a reviewable migration diff, not a silent runtime change. |
| Cross-tenant read/write leak on the new tables | Low | High (tenant isolation breach) | RLS forced (binds even the table-owning role), identical predicate to `parcels`, both positive and negative tests required before merge. |
| `basis` field misread as an evidence citation it isn't yet | Medium | Medium (could look more authoritative than it is) | Fixed, honest strings only this slice (`"registrant declaration via update_parcel"` etc.); no fabricated `document_reference`. |
| Non-adjudication check remains unimplemented after this slice ships | High (known, pre-existing) | Medium | Explicitly flagged as outstanding in Definition of Done and the final acceptance report — not silently deferred without a mention. |
| Rollback (`downgrade()`) untested before merge | Low if disciplined | High if it ever needs to run for real | Rehearsed against a staging-like Docker Postgres before merge, per Article XI §3; result reported with evidence, not assumed. |

## Rollback Plan

`alembic downgrade -1` from `0011` drops both triggers, both trigger functions, both RLS policies, and both tables, in that order (dependency-safe). No data-migration step is needed in either direction, since nothing is backfilled on the way up. Rollback is rehearsed against the local Docker Postgres instance before merge; the exact commands run and their output are recorded in the acceptance report, not assumed to work from reading the migration file.

## Acceptance Criteria

Reproduced from ADR-023's own governing text, not restated differently:

1. One migration creates both tables, their indexes, their RLS policies, and the `REVOKE`-equivalent (here, a `GRANT SELECT, INSERT`-only, no `UPDATE`/`DELETE` ever granted) — all in the same migration. Downgrade is real, not a stub.
2. Backfill behaviour matches "no backfill, ever," exactly.
3. History rows are written inside the existing `create_parcel`/`update_parcel`/`archive_parcel` flows, in the same Unit of Work. No new endpoint. No new mutation command. No new authorization model — ADR-015's check reused verbatim.
4. `PARCEL_REGISTRANT_ROLES` (or equivalent) continues to derive from Identity's `Role` enum. No duplicated string literals.
5. Test suite goes from **148 passing to 148 + N passing**, all green — exact counts reported, not rounded up.
6. A test proves the append-only guarantee bites at both layers independently (privilege AND trigger).
7. A test proves a failed mutation leaves no orphan history row.
8. `ruff`, `mypy`, and the full `pytest` suite are run and their exact exit codes reported.
9. The non-adjudication check is run and its result reported honestly — if it does not exist yet, that is stated plainly, not glossed over.

## Definition of Done

- All nine acceptance criteria above satisfied or explicitly, honestly reported as not satisfied with a reason.
- `ADR-023` status updated from Accepted to **Accepted — Implemented** (or equivalent marker) only in the commit that lands this work, once merged and green — never marked done in advance of that evidence.
- The non-adjudication check (`ENGINEERING_RULES.md` §10) either (a) implemented as part of this slice's own CI work, or (b) explicitly logged as outstanding technical debt in the acceptance report with a named owner/next-step — not silently absent from the report.
- Documentation: this plan, `ADR-023`, and `CLAUDE.md`'s B3/current-status paragraph updated to reflect the new tables exist and are populated, once merged.

## Testing Strategy

Full matrix per ADR-023 §"Test matrix" — all *observed*, none assumed:

1. Creating a parcel with an owner reference writes exactly one ownership row and one status row (initial `ACTIVE`); no owner reference writes zero ownership rows.
2. `update_parcel` changing owner fields writes exactly one new ownership row (`supersedes_id` set); changing unrelated fields (`address`, `title`, etc.) writes zero ownership rows.
3. `archive_parcel` writes exactly one status row, `supersedes_id` pointing at the initial `ACTIVE` row.
4. Append-only enforced at **both** independent layers, observed failing separately: (a) `UPDATE`/`DELETE` as `landvault_app` — permission denied; (b) `UPDATE`/`DELETE` as the schema-owning migration role — trigger exception.
5. Cross-tenant isolation, positive and negative: tenant A cannot read tenant B's history; `super_admin` can, across tenants.
6. Every history row's `audit_ref` resolves to a real `AuditEntry`, payload-consistent.
7. Migration `0011` up and down; rollback rehearsed on a staging-like database before merge.
8. Parcel aggregate regression: `current_owner_name`/`current_owner_contact` behaviour completely unchanged.
9. Non-adjudication wording check — tracked separately; this test matrix does not claim to close it.

## Performance Expectations

No new query path is added to any hot endpoint's read side (no history read-endpoint exists yet). Write-side impact: one or two additional `INSERT`s per mutating call, inside the same transaction already performing the parcel `UPDATE`/`INSERT` and the audit-chain `INSERT` — expected to be negligible relative to existing per-request latency, and not separately benchmarked in this slice absent evidence of a real cost.

## Success Metrics

- 148 + N tests green (N = the number of new tests this slice adds), `ruff`/`mypy` clean, reported with exact counts.
- Zero orphan history rows demonstrable under a forced-failure test.
- Zero cross-tenant history leakage demonstrable under both positive and negative tests.
- Rollback rehearsed and its output captured in the acceptance report.

## Open Questions

- Whether the non-adjudication automated check is built as part of this slice or logged as separate follow-up — a decision for whoever accepts this plan, not decided here.
- Exact naming for the `Parcel*History` domain module/file locations — resolved during implementation by mirroring `ParcelRepository`'s existing file layout, not a design decision this plan needs to pre-empt.
- Whether `docs/adr/ADR-023-registry-ownership-and-status-history.md`'s status marker should read "Accepted — Implemented" or simply stay "Accepted" with a dated addendum — a formatting convention, not a governance question; recommend following whatever pattern `ADR-009`/`ADR-012`/`ADR-017` (the B1/B2/B3 freeze ADRs) already use for "this is now built," for consistency.

## Governance References

`docs/adr/ADR-023-registry-ownership-and-status-history.md` (governing decision) · `docs/adr/ADR-013-parcel-aggregate-registry-domain-model.md` · `docs/adr/ADR-014-postgresql-atomic-parcel-number-allocation.md` · `docs/adr/ADR-015-registry-mutation-authorization-model.md` · `docs/adr/ADR-016-geometry-port-boundary-spatial-integration.md` · `docs/adr/ADR-007-audit-trail-evidence-model.md` · `docs/adr/ADR-009-b1-platform-freeze.md` · `docs/adr/ADR-004-authentication-authorisation-model.md` and `docs/adr/ADR-025-supabase-platform-baseline.md` (cited only to confirm zero dependency) · `docs/ENGINEERING_RULES.md` §10 · LV-000 v1.8 Articles IV, VII §6, VIII §2–§3, X §3, XI §2–§3.

## Implementation Sequence

1. Migration `0011` — tables, indexes, RLS, grants, triggers, tested `up`/`down`.
2. Domain value objects (`OwnershipAssertion`, `StatusAssertion`) — pure, no I/O.
3. `ParcelHistoryRepository` protocol, Postgres adapter, in-memory fake, DI wiring.
4. `ParcelService.create_parcel` — initial assertions.
5. `ParcelService.update_parcel` — conditional ownership-history write.
6. `ParcelService.archive_parcel` — status-history write.
7. New `audit()` action names wired at each of the three call sites.
8. Full test matrix (nine items above).
9. `ruff` / `mypy` / `pytest` run, exact results captured.
10. Non-adjudication check — implement or explicitly log as outstanding.
11. Acceptance report (Phase 7 of the governing execution prompt).

## Deliverables

- `backend/migrations/versions/0011_registry_ownership_status_history.py`
- New domain/port/adapter/fake files (exact paths determined by mirroring `ParcelRepository`'s existing layout)
- Updated `ParcelService` methods (no signature changes)
- New and extended test modules under `backend/tests/`
- This plan, `ADR-023`, and `CLAUDE.md` updated to reflect implementation status
- Implementation Report / Architecture Compliance Report / Risk Summary / Acceptance Checklist (Phase 7 deliverables, produced after implementation)
