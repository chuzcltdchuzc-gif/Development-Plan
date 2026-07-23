# B4 Final Verification Checklist

Cumulative, append-only register of verification work. Slice 1 followed the deferred-verification
policy (`CLAUDE.md`'s "B3 status" section, adopted mid-B3-Slice-3 and continued into early B4) —
each slice's completion report appended its own section here rather than running full live
verification immediately. **Slice 2's own authorization explicitly required live verification be
performed then, not deferred** — its section below is direct evidence, not a deferred-item list.
**No item still marked deferred below may be skipped** — it is executed exhaustively, once, during
the eventual B4 Quality Gate (mirroring B3's own End-of-B3 Quality Gate,
`docs/B3_FINAL_VERIFICATION_CHECKLIST.md`), before B4 may be proposed for freeze.

## Slice 1 — Spatial Domain Foundation (docs/adr/ADR-018, docs/adr/ADR-019)

**Already done (targeted, not deferred, per policy):**
- Full `ruff check .` and full `mypy .`: clean across the whole backend (104 source files).
- Full `pytest` suite: **132/132 passed** (119 prior + 13 new Spatial tests), zero regressions
  in B1/B2/B3.
- Migration `0010` applied to the live dev Postgres with no failure; schema independently
  inspected via `psql`:
  - `boundary geometry(Polygon,4326)` — SRID and geometry subtype enforced at the column level,
    confirmed via `\d parcel_geometries`.
  - FKs confirmed: `parcel_id -> parcels.id`, `tenant_id -> tenants.id`,
    `created_by -> identity_users.id`.
  - RLS confirmed `FORCE`d and enabled (`relrowsecurity`/`relforcerowsecurity` both `t`); policy
    text matches every other tenant-scoped table's shape exactly.
  - Grants confirmed `SELECT, INSERT, UPDATE` only for `landvault_app` — no `DELETE`.
  - Fail-closed confirmed live: no session context → `0` rows; `DELETE` denied at the grant
    level (`permission denied for table parcel_geometries`).
  - Partial unique index `ix_parcel_geometries_one_active_per_parcel` confirmed present
    (`UNIQUE (parcel_id) WHERE status = 'ACTIVE'`) — not yet exercised under real concurrent
    submission (see deferred items).
- One real design gap found and fixed via test failure, not assumed correct: the first draft of
  `SpatialService` relied solely on `ParcelExistencePort`'s real-adapter RLS behavior for tenant
  scoping, with no explicit application-layer check — correct for the real Postgres adapter, but
  silently over-permissive against the in-memory fake (which has no RLS equivalent), caught by
  `test_cross_tenant_parcel_404s` returning `201` instead of `404`. Fixed by adding the identical
  `_in_scope(ctx, resource_tenant_id)` two-independent-layers pattern
  `app.contexts.registry.application.parcel_service` already uses — RLS is one layer for the
  real adapter, `_in_scope` is the layer this slice's own test suite actually exercises. This is
  exactly the kind of gap live/test verification exists to catch before it ships, not evidence
  the architecture was wrong, evidence the discipline works.

**Deferred at the time Slice 1 shipped — resolved in Slice 2 (see that section below) unless
otherwise noted:**

- [x] Full `pytest` suite re-run alongside Slice 2's additions — 148/148, see Slice 2 section.
- [x] Live Postgres: `PUT`/`GET /v1/spatial/parcels/{id}/geometry` persisting/reading `boundary`
      through the real `Geometry` `TypeEngine` against a live request — exercised as part of
      Slice 2's full live HTTP verification sequence (every scenario below round-trips through it).
- [x] Live RLS — see Slice 2 section (now run as the actual `landvault_app` role, not just
      schema-inspected).
- [ ] Live concurrency: confirm the partial unique index
      (`ix_parcel_geometries_one_active_per_parcel`) actually rejects a second concurrent
      `INSERT` racing to become `ACTIVE` for the same parcel — still not exercised under genuine
      concurrent load; carried forward, see Slice 2 section's own deferred list.
- [x] Live Keycloak, real authenticated flow — see Slice 2 section (all scenarios, plus the
      ADR-022 tiers Slice 1 didn't yet have).
- [x] Live audit chain — see Slice 2 section.
- [x] Containerized backend — see Slice 2 section.
- [ ] Security validation: confirm `SubmitGeometryRequest`'s `extra="forbid"` rejects an attempt
      to set `tenant_id`, `parcel_id`, `status`, or `geometry_id` directly through the API body —
      still not exercised; carried forward, see Slice 2 section's own deferred list.

**Known limitations at the time Slice 1 shipped — resolved in Slice 2 unless marked otherwise:**

- ~~`PlaceholderGeometryAdapter` remains Registry's registered `GeometryPort` implementation~~ —
  **resolved in Slice 2**: `RealGeometryAdapter` now wired via `app/main.py`'s
  `dependency_overrides`, live-verified end to end (see Slice 2 section).
- **No `geoalchemy2` dependency was added** — unchanged, still true in Slice 2 (the real
  structural validator is also pure Python, no new dependency).
- ~~Validation is structural only via a regex~~ — **resolved in Slice 2**: real structural
  validation (ring closure, point count, coordinate bounds, OGC winding order, SRID), still no
  self-intersection/administrative-boundary containment (deliberately deferred further, per
  ADR-022's own scope boundary, not this slice's job either).
- ~~Spatial's own authorization is coarse~~ — **resolved in Slice 2**: ADR-022's full
  creator-or-governance model is now implemented and live-verified, closing the ADR-005-shaped gap
  this section originally flagged.
- Carried from B3, **partially resolved**: the containerized backend's Keycloak networking gap
  is fixed (see Slice 2 section) — SQLAlchemy's default connection-pool ceiling under heavy
  concurrent load is still carried forward, unchanged.

**Performance observations:** none yet specific to this slice — no spatial queries exist to
evaluate (that's ADR-020/021's job); the append-only supersede pattern is a single-row update per
submission, structurally similar to Registry's own mutation pattern.

**Infrastructure observations:** none new.

## Slice 2 — Geometry Validation & Real Geometry Adapter (docs/adr/ADR-022)

Unlike Slice 1, this slice's own authorization explicitly required **live verification now, not
deferred**. Every item below was executed against real infrastructure during this slice, not
carried forward.

**Automated verification:**
- Full `ruff check .` and full `mypy app`: clean across the whole backend (76 source files).
- Full `pytest` suite: **148/148 passed** (119 prior + 29 Spatial tests, up from Slice 1's 13 —
  16 new: validator edge cases, ADR-022 authorization tiers, Registry↔Spatial `GeometryPort`
  integration), zero regressions in B1/B2/B3.
- Two Slice-1 test fixtures (`VALID_POLYGON`/`OTHER_POLYGON`) were discovered to be wound
  *clockwise* once real winding-order validation existed to check them — a legitimate consequence
  of Slice 2 building real validation where Slice 1 had none, not a defect in either slice. Fixed
  by re-winding both fixtures counter-clockwise (OGC Simple Features convention).

**Live verification (real Postgres/PostGIS/Keycloak, not fakes):**
- [x] Migration state: still at head `0010` — Slice 2 required no schema change (no speculative
  schema was added), confirmed via `psql`.
- [x] Container rebuild: `docker compose build backend` succeeded; recreated container passes
  `/health/live` (`{"status":"ok"}`) and `/health/ready` (`{"status":"ready"}`, real DB
  connectivity); `/openapi.json` lists both `/v1/spatial/parcels/{parcel_id}/geometry` and
  `/v1/parcels/{parcel_id}/geometry`.
- [x] Live RLS, run as the actual least-privilege `landvault_app` role (not the schema-owning
  superuser, which has `BYPASSRLS` and would silently pass regardless of policy correctness):
  wrong `app.tenant_id` → `0` rows from `parcel_geometries`; correct tenant → all rows visible;
  `DELETE` → `permission denied for table parcel_geometries`. Matches Slice 1's `psql`-schema-only
  check with an actual query-level confirmation this time.
- [x] Creator authority: a `field_agent` submits geometry for their own parcel → `201`.
- [x] Supersession: a second submission by the same creator → `201`, new `geometry_id`, prior row
  confirmed superseded.
- [x] ADR-005-shaped regression: a same-tenant, non-creator `field_agent` submits for a
  colleague's parcel → `403`; `spatial.parcel_geometry.mutation_denied` audit row confirmed in the
  live `audit_log` table with `reason = "not_creator_and_not_governance"`.
- [x] Governance authority: a `compliance_officer` (non-creator, same tenant) submits for a
  colleague's parcel → `201`; audit payload `effective_authority = "governance:compliance_officer"`.
- [x] Delegated governance: a `compliance_officer` delegates to a `general_user` via the real
  `POST /v1/admin/delegations` endpoint; the delegate then submits geometry for the same
  colleague's parcel → `201`.
- [x] Cross-tenant `super_admin` override: submits for a parcel outside their own tenant → `201`;
  audit payload `effective_authority = "governance:super_admin"`.
- [x] Cross-tenant, non-`super_admin`: a `field_agent` in a different tenant → `404` for both
  `PUT` (submit) and `GET` (read) — existence not revealed cross-tenant.
- [x] Malformed geometry: a non-WKT string → `400`; a structurally well-formed but
  clockwise-wound exterior ring → `400` (OGC winding-order check proven live, not only in-process).
- [x] Archived-parcel block: parcel archived via Registry's own `POST /v1/parcels/{id}/archive`;
  subsequent geometry submission attempts by the **creator**, a **governance role**, and
  **`super_admin`** each independently return `409` — no override for any tier, confirmed live.
- [x] Real Registry↔Spatial `GeometryPort` seam, in the actual production wiring (no test
  override): geometry submitted via Spatial, then its `geometry_id` set as Registry's
  `geometry_reference` via `PUT /v1/parcels/{id}/geometry` → `200`, `geometry_reference` echoed
  back; an unknown UUID → `400`; a real `geometry_id` belonging to a *different* parcel → `400`
  (`RealGeometryAdapter`'s `parcel_id` cross-check, not just an existence check).
- [x] Audit chain integrity: `verify_chain()` invoked directly against the live `audit_log` table
  → `True`, over the platform's entire recorded history (B1 through this session), confirming no
  hash-chain break was introduced by any Slice 2 write path.

**Pre-existing infrastructure defect found and fixed as a live-verification blocker (not a Slice 2
architectural change):** `infra/docker/docker-compose.yml`'s `backend` service overrode
`DATABASE_URL`/`MIGRATIONS_DATABASE_URL` for container-to-container networking but not
`KEYCLOAK_REALM_URL`/`KEYCLOAK_ADMIN_TOKEN_URL`/`KEYCLOAK_ADMIN_API_URL` — those leaked `.env`'s
host-oriented `localhost` values straight through, which are unreachable from inside the
container's own network (Keycloak is only addressable there via its compose service name). This
is the exact gap Slice 1's own checklist had already flagged as "carried unchanged from B3: the
containerized backend's `KEYCLOAK_REALM_URL` host-relative networking gap" — it blocked this
slice's mandated live-Keycloak verification, so it was fixed now (three environment overrides
added, mirroring `DATABASE_URL`'s existing pattern) rather than deferred again.

**Deferred to the eventual B4 Quality Gate (unchanged from Slice 1, still not this slice's job):**
- [ ] Live concurrency: the partial unique index (`ix_parcel_geometries_one_active_per_parcel`)
  actually rejecting a second concurrent `INSERT` racing to become `ACTIVE` for the same parcel —
  not exercised under genuine concurrent load in either slice yet.
- [ ] Security validation: `SubmitGeometryRequest`'s `extra="forbid"` rejecting an attempt to set
  `tenant_id`/`parcel_id`/`status`/`geometry_id` directly through the API body.
- [ ] SQLAlchemy's default connection-pool ceiling under heavy concurrent load (carried from B3).

**Known limitations (documented, not defects):**
- Validation remains structural only (ADR-022's own explicit scope boundary) — no
  self-intersection check, no coordinate-topology check, no administrative-boundary containment.
  Deferred to ADR-021/later, per this slice's approved scope.
- `RealGeometryAdapter` treats any `SUPERSEDED` geometry as an invalid reference (only `ACTIVE`
  geometries are valid references) — a deliberate design choice (ADR-018's lifecycle model), not
  a limitation to revisit.
- No overlap/duplicate-geometry detection, fraud detection, or GIS analysis exists anywhere in
  this codebase — explicitly out of scope for this slice, reserved for ADR-021/B4 Slice 3, not
  authorized to begin.

**Performance observations:** none new — the ADR-022 authorization check is a single additional
`ParcelExistencePort` field read (no extra round-trip; `get_parcel_authority` replaced
`get_tenant_id` in place), and the real structural validator is pure in-process arithmetic with no
measurable overhead versus Slice 1's placeholder regex.

**Infrastructure observations:** the container-networking Keycloak-URL gap above; otherwise none
new.
