# B3 Release Notes (draft — pending Platform Freeze approval)

**Proposed release tag:** `b3-freeze` (not yet created — pending explicit authorization)
**Date:** 2026-07-20
**Governing ADRs:** `docs/adr/ADR-013-parcel-aggregate-registry-domain-model.md`,
`docs/adr/ADR-014-postgresql-atomic-parcel-number-allocation.md`,
`docs/adr/ADR-015-registry-mutation-authorization-model.md`,
`docs/adr/ADR-016-geometry-port-boundary-spatial-integration.md`

B3 builds the Registry bounded context from nothing to feature-complete per
`docs/B3_DISCOVERY_AND_PLANNING.md`'s Phase-0 scope: a canonical Parcel aggregate, PostgreSQL-
native atomic parcel numbering, creator-aware mutation authorization that closes a confirmed
historical vulnerability (ADR-005), and a clean architectural boundary for future spatial
capability. No frozen B1/B2 decision (ADR-009 through ADR-012) was modified — every extension
point used already existed in that baseline.

---

## Completed slices

| Slice | Delivered | ADR |
|---|---|---|
| 1 | Parcel aggregate — canonical identity, tenant isolation, registry metadata, current-ownership reference, archived-immutability guard | ADR-013 |
| 2 | PostgreSQL-native atomic parcel numbering — per-`country_code` upsert-counter, corrected mid-slice from an initial per-tenant design after live concurrency testing exposed a cross-tenant collision | ADR-014 |
| 3 | Mutation commands & authorization hardening — `PATCH`/`archive`, creator-or-governance authorization closing the ADR-005 defect | ADR-015 |
| 4 | Geometry port boundary & spatial integration foundation — `GeometryPort` contract, `geometry_reference` association, zero GIS logic | ADR-016 |

## Migrations (0007–0009)

| # | File | Adds |
|---|---|---|
| 0007 | `0007_parcels.py` | `parcels` table; `CREATE EXTENSION IF NOT EXISTS postgis`; database-wide partial unique index on `parcel_number`; RLS; least-privilege grants (`SELECT/INSERT/UPDATE`, no `DELETE`) |
| 0008 | `0008_registry_parcel_counters.py` | `registry_parcel_counters` table, keyed by `country_code` (not `tenant_id` — corrected mid-slice, see ADR-014's revision note); RLS policy admitting any authenticated session (this table holds no tenant-owned data); grants |
| 0009 | `0009_parcels_geometry_reference.py` | `parcels.geometry_reference`, nullable `VARCHAR` — an opaque pointer, never a PostGIS type; purely additive |

No destructive migration in the set. Every migration was applied to the live Postgres instance
and independently inspected via `psql` before being marked done.

## API surface added

```
POST   /v1/parcels
GET    /v1/parcels
GET    /v1/parcels/{id}
PATCH  /v1/parcels/{id}
POST   /v1/parcels/{id}/archive
PUT    /v1/parcels/{id}/geometry
```

## Test totals

**119/119 tests passing** across the whole platform at the B3 Final Quality Gate (0 failures,
0 skips) — `ruff` clean, `mypy` clean across the entire backend (one pre-existing type-annotation
gap in `migrations/env.py`, unrelated to B3, found by the whole-repo gate run and fixed).

| Suite | Count | Covers |
|---|---|---|
| B1 acceptance + unit | 27 | Unmodified from B1 — regression-checked after every B3 slice |
| B2 (invitations/tenants/delegations) | 45 | Unmodified from B2 — regression-checked, including after Slice 3's shared-code touch to `context_hydration.py`/`pep.py` |
| Registry (`test_b3_registry.py`, all 4 slices) | 47 | Creation, allocation, tenant isolation, ownership/governance mutation authorization, the ADR-005 regression test, delegation lifecycle interaction, archive immutability, geometry association, audit integrity |

## Accepted ADRs

- **ADR-013** — Parcel Aggregate & Registry Domain Model. Accepted; establishes the canonical
  aggregate, its 12 domain invariants, and the `_ensure_mutable`/guarded-mutation-point pattern
  every later slice inherited.
- **ADR-014** — PostgreSQL-Native Atomic Parcel Number Allocation. Accepted; documents the
  per-`country_code` upsert-counter design and the mid-slice correction from an initially-chosen
  per-tenant scope, found via live concurrency testing before review.
- **ADR-015** — Registry Mutation Authorization Model. Accepted; documents the creator-or-
  governance authorization rule that closes the confirmed ADR-005 defect, and how delegated
  authority participates without any Registry-specific delegation logic.
- **ADR-016** — Geometry Port Boundary & Spatial Integration Architecture. Accepted; documents
  the `GeometryPort` contract, the `geometry_reference` association-not-geometry aggregate
  boundary, and what B4 inherits without needing to renegotiate Registry's design.

## Known limitations (tracked, not hidden)

- **No restore command.** `ARCHIVED` is a one-way terminal state (ADR-013, reaffirmed ADR-015).
  Revisiting this requires its own ADR, not an assumption inside a mutation-commands slice.
- **Ownership-transfer authorization is undecided.** `created_by` must survive any future
  transfer command unchanged (ADR-015/ADR-016); who may *initiate* a transfer is left for
  whichever slice builds it.
- **`GeometryPort` has exactly one adapter, which validates nothing about a reference's
  content** (`PlaceholderGeometryAdapter`, always permits) — deliberate, pending B4's own real
  implementation (ADR-016).
- **The containerized backend's `KEYCLOAK_REALM_URL` is host-relative** (`localhost:8080`),
  inherited from the platform's original Docker Compose configuration — full authenticated live
  verification goes through the host dev server, not the container directly, throughout B3. Out
  of Registry's scope; not introduced or worsened by B3.
- **SQLAlchemy's default connection-pool ceiling** (`pool_size=5` + `max_overflow=10` = 15) was
  found under heavy same-tenant concurrent load during Slice 2's live testing — a genuine,
  documented operational constraint for future capacity planning, not a Registry defect.

## Production verification summary

Every slice's live-infrastructure verification was performed against the actual running stack
(Docker Compose: Postgres, Keycloak, backend), not simulated. The B3 Final Quality Gate
(2026-07-20) additionally re-ran the full cycle end-to-end after Slice 4:

- **Migrations**: all three (`0007`–`0009`) applied cleanly; schema, indexes, RLS policy text,
  and grants independently inspected via `psql`.
- **RLS**: fail-closed confirmed for `parcels` and `registry_parcel_counters` — no session
  context or a bogus tenant returns zero rows on both `SELECT` and `UPDATE` (0 rows affected,
  not an error); `DELETE` denied at the grant level.
- **End-to-end flows, real Keycloak + real Postgres**: parcel creation → cross-tenant `GET`
  denied → tenant-scoped listing; 12 concurrent HTTP requests across two tenants sharing one
  gapless, duplicate-free `country_code` sequence; the **ADR-005 ownership-attack reproduction**
  — a same-tenant, non-creator, non-governance registrant denied `PATCH`/`archive` (403) on a
  colleague's real parcel, confirming the historical defect is closed; governance-role and
  `super_admin` override permitted; a full delegation lifecycle (create → mutate → revoke) with
  the very next request on an unchanged access token immediately denied; archive immutability
  enforced across every mutation type, including geometry; geometry attach/detach live, with
  cross-tenant and archived-parcel denial; a live attempt to smuggle immutable fields
  (`parcel_id`, `created_by`, `status`, `parcel_number`, `tenant_id`, `geometry_reference`)
  through the update endpoint rejected at 422 before the domain layer was ever reached.
- **Audit chain**: `verify_chain()` confirmed `True` after all of the above, with every expected
  action name (`registry.parcel.created`/`.updated`/`.archived`/`.mutation_denied`/
  `.geometry_attached`/`.geometry_detached`) present in the real, Postgres-persisted audit log.
- **Containerized backend**: rebuilt from current `main` at the Quality Gate; boots clean,
  `/openapi.json` lists every Registry route including the three added across Slices 3–4;
  Postgres data confirmed intact across the container recreation.

Full detail, including every individual check and its result, is in
`docs/B3_FINAL_VERIFICATION_CHECKLIST.md`.

## Recommended freeze declaration (pending approval — not yet in effect)

B3 is feature-complete per its Phase-0 scope and has passed the B3 Final Quality Gate in full.
**This document recommends but does not declare** B3 frozen — per this engagement's governance
model, that requires the same explicit authorization B2's freeze received (a dedicated
authorization step, an ADR of its own recording the freeze, an annotated tag, and a verified
push), not an implicit consequence of the Quality Gate passing. Pending that authorization, this
release remains local-only (no tag, no push) and B4 (Spatial Intelligence) remains unauthorized.
