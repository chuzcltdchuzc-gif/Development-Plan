# B3 Final Verification Checklist

Cumulative register of verification work deferred under the B3 Development Workflow Update
(deferred-verification policy, adopted mid-Slice-3), now resolved in full by the **B3 Final
Quality Gate** (2026-07-20). Each slice's completion report appended its own section here rather
than running the full verification suite immediately; this document now records that every
deferred item was subsequently executed, with evidence, and passed.

Slices 1 and 2 predate the deferred-verification policy — they already received full live
verification at the time they were built (see their own completion reports and `CLAUDE.md`'s B3
status section for what was already proven).

## Slice 3 — Mutation Commands & Authorization Hardening (docs/adr/ADR-015)

**Already done (targeted, at implementation time):** `ruff`/`mypy` on every changed file (clean);
the full `tests/test_b3_registry.py` file at the time (37/37 passed). Two test-authoring bugs
found and fixed immediately (users seeded without a shared `tenant_id` landed in different
tenants; the suspended-tenant test's expected status corrected from 401 to 403 to match the PEP's
existing, documented behavior) — not deferred, per policy, since these are "obvious
implementation defects," not verification gaps.

**Resolved at the B3 Final Quality Gate (see gate section below for full evidence):** full
`pytest` suite, full `ruff`/`mypy`, live Postgres write-path, live RLS fail-closed check, live
Keycloak-authenticated ownership-attack reproduction (ADR-005 regression), governance override,
`super_admin` cross-tenant override, cross-tenant 404, live delegation lifecycle (create/mutate/
revoke, live), live audit-chain verification, containerized rebuild + route check, and the
immutable-field-smuggling security check (crafted `PATCH` body including `parcel_id`/
`created_by`/`status`/`parcel_number`/`tenant_id` rejected at 422 by the DTO's `extra="forbid"`,
before ever reaching the domain layer — confirmed live, parcel provably unchanged afterward).

**Known limitations (documented, not defects):**

- No "restore" command exists — `ARCHIVED` remains one-way, per ADR-013's original "terminal"
  designation. ADR-015 records this as deliberate, not an oversight.
- Ownership-transfer authorization (who may initiate a future transfer of
  `current_owner_name`/`current_owner_contact`) is explicitly left for whichever future slice
  builds that command — ADR-015 states only that `created_by` must remain untouched by it.
- The containerized backend's `KEYCLOAK_REALM_URL` is host-relative (`localhost:8080`) — full
  authenticated live verification goes through the host dev server, not the container directly,
  until that infrastructure item is addressed (out of Registry's scope; unchanged since Slice 2).
- SQLAlchemy's default connection-pool ceiling (`pool_size=5` + `max_overflow=10` = 15),
  documented in Slice 2, is a platform-wide operational constraint; Slice 3 introduces no new
  concurrency-sensitive path (single-row updates, not a shared-counter contention point).

## Slice 4 — Geometry Port Boundary & Spatial Integration Foundation (docs/adr/ADR-016)

**Already done (targeted, at implementation time):** `ruff`/`mypy` on every changed file (clean);
the full `tests/test_b3_registry.py` file (47/47 passed, 10 new); migration `0009` applied to the
live dev Postgres with no failure.

**Resolved at the B3 Final Quality Gate:** live Postgres write-path for `geometry_reference`
(set and cleared, confirmed via real HTTP against the running server); live RLS (existing
row-level policy applies to the new column automatically — confirmed by the same fail-closed
checks run for the whole table); live Keycloak-authenticated attach/detach, cross-tenant 404,
governance override, archived-parcel 409; live audit chain
(`registry.parcel.geometry_attached`/`.geometry_detached` present with correct payload,
`verify_chain()` → `True`); containerized rebuild exposing `PUT /v1/parcels/{id}/geometry` in
`/openapi.json`; security check confirming `geometry_reference` cannot be smuggled through the
`PATCH` (ADR-015) endpoint — rejected at 422, same mechanism as the Slice 3 immutable-field check.

**Known limitations (documented, not defects):**

- `GeometryPort.reference_is_valid` has exactly one production implementation,
  `PlaceholderGeometryAdapter`, which validates nothing about the reference's content (always
  `True`) — deliberate, not an oversight (ADR-016). Any real validation is B4's responsibility.
- No geometry data model, persistence, or computation of any kind exists anywhere in this
  codebase yet — `geometry_reference` is an opaque string with no format enforced beyond "is a
  string." B4's own ADR will define what a real reference looks like.
- The containerized backend's `KEYCLOAK_REALM_URL` host-relative networking gap (Slices 2–3)
  still applies and is still out of Registry's scope.
- SQLAlchemy's default connection-pool ceiling (Slice 2) is unaffected — geometry mutation is a
  single-row update, not a shared-counter contention point.

## B3 Final Quality Gate — Result: **PASSED** (2026-07-20)

**Static analysis:**
- Full `ruff check .` (backend, whole repo): **clean.**
- Full `mypy .` (backend, whole repo): **1 issue found and fixed** —
  `migrations/env.py:58`, `do_run_migrations(connection)` was missing a type annotation
  (pre-existing, not introduced by Slices 3–4; never caught before because prior `mypy` runs were
  scoped to `app/`/`tests/`, not the whole repo including `migrations/`). Fixed by annotating
  `connection: Connection` (`sqlalchemy.engine.Connection`) — a type-only change, no behavior
  change. Re-run: **clean, 88 source files.**

**Automated testing:**
- Full `pytest` suite (all of B1 + B2 + B3 slices 1–4): **119/119 passed.** No regressions in
  Identity, authorization, delegation, or audit tests from Slice 3's changes to
  `app/kernel/authorization/pep.py`/`app/contexts/identity/context_hydration.py`.
- Registry regression: 47/47 (`test_b3_registry.py`, all slices 1–4).

**Live verification** (real Postgres, real Keycloak, real running server — not the containerized
backend for authenticated flows, see the `KEYCLOAK_REALM_URL` limitation above; the container was
separately verified for boot health and route exposure):

- **Real PostgreSQL / RLS:** `parcels.geometry_reference` column confirmed present;
  `parcels` RLS still `FORCE`d and enabled; no session context → 0 rows; bogus tenant → 0 rows on
  both `SELECT` and `UPDATE` (0 rows affected, not an error) — fail-closed confirmed for the
  mutation paths specifically, not only `INSERT`.
- **Real tenant isolation / cross-tenant attack scenarios:** cross-tenant `GET` → 404;
  cross-tenant `PATCH`/`archive`/`geometry` → 404 (existence not revealed, evaluated before the
  ownership check).
- **Ownership attack reproduction (ADR-005 regression):** a same-tenant, non-creator, non-
  governance `field_agent` was denied `PATCH` (403) and `archive` (403) on a colleague's real,
  Keycloak-authenticated, Postgres-persisted parcel — the exact historical defect, reproduced and
  confirmed closed.
- **Creator authorization:** the actual creator succeeded on `PATCH`/`archive`/`geometry` (200).
- **Governance override:** a `compliance_officer` in the same tenant, not the creator, succeeded
  on `PATCH`/`geometry` (200).
- **`super_admin` cross-tenant override:** succeeded on `PATCH` across tenants (200).
- **Delegation lifecycle, live:** a real delegation created via `POST /v1/admin/delegations`,
  exercised successfully by the delegate against a real parcel mutation (200), then revoked via
  `POST /v1/admin/delegations/{id}/revoke` (200) — the very next request from the same,
  unchanged access token was denied (403), confirming ADR-011's fail-closed re-resolution reaches
  Registry mutation end-to-end with no caching or grace period.
- **Archive behaviour:** creator archive succeeded (200, `status: ARCHIVED`); subsequent
  `PATCH`/`geometry` on the archived parcel both denied (409), for the creator — no privileged
  bypass exists for any role.
- **Atomic parcel numbering:** unaffected by Slices 3–4; re-confirmed passing as part of the full
  regression run (Slice 2's own live concurrency proof stands unchanged).
- **Mutation commands:** `PATCH`/`archive` exercised live end-to-end (create → update → archive →
  further-mutation-denied), all persisted and re-readable via `GET`.
- **Geometry boundary integration:** attach (200, reference stored), detach (200, reference
  cleared to `null`), cross-tenant denial (404), archived-parcel denial (409) — all live.
- **Real audit chain:** `registry.parcel.updated`/`.archived`/`.mutation_denied`/
  `.geometry_attached`/`.geometry_detached` all present in the real `audit_log` table with the
  documented payload shape (`effective_authority`, `delegated_roles`, `tenant_id`,
  `fields_changed` where applicable, `reason` on denials); `verify_chain()` → **`True`** after all
  of the above.
- **Security validation:** crafted `PATCH` bodies attempting to smuggle `parcel_id`,
  `created_by`, `status`, `parcel_number`, `tenant_id`, and `geometry_reference` through the
  update endpoint all rejected at **422** by the DTO's `extra="forbid"`, before the domain-level
  `UPDATABLE_FIELDS` allow-list is ever consulted — confirmed live, and the target parcel was
  re-fetched afterward and confirmed provably unchanged on every one of those fields.
- **Containerized deployment:** backend rebuilt from current `main`; container boots clean
  (`Application startup complete`); `/docs` → 200; `/openapi.json` lists
  `PATCH /v1/parcels/{id}`, `POST /v1/parcels/{id}/archive`, and
  `PUT /v1/parcels/{id}/geometry`; Postgres data (15 parcels, unrelated to the rebuild) confirmed
  intact across the container recreation.

**Issues found and resolved during this gate:** one (`migrations/env.py`'s missing type
annotation, above) — a static-analysis-only finding, zero behavioral impact, fixed and re-verified
clean. No test failures, no live-verification failures, no security findings requiring a fix in
this cycle — the verification cycle needed to run only once.

**Outstanding known limitations carried into freeze (not defects, all previously documented):**
`KEYCLOAK_REALM_URL` host-relative container-networking gap (Slice 2); SQLAlchemy default
connection-pool ceiling under heavy same-tenant concurrency (Slice 2); no restore/ownership-
transfer commands (Slices 3/4, explicitly deferred); `GeometryPort`'s sole adapter validates
nothing about reference content (Slice 4, deliberate placeholder pending B4).

**Conclusion: all quality gates pass. B3 is ready for the Platform Freeze decision.**
