# B4 Final Verification Checklist

Cumulative, append-only register of verification work deferred under the same B3 Development
Workflow Update (deferred-verification policy — `CLAUDE.md`'s "B3 status" section, adopted
mid-B3-Slice-3 and continued into B4). Each slice's completion report appends its own section
here rather than running full live verification immediately. **No item on this list may be
skipped** — it is executed exhaustively, once, during the eventual B4 Quality Gate (mirroring
B3's own End-of-B3 Quality Gate, `docs/B3_FINAL_VERIFICATION_CHECKLIST.md`), before B4 may be
proposed for freeze.

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

**Deferred to the eventual B4 Quality Gate:**

- [ ] Full `pytest` suite re-run alongside whatever Slice 2+ adds (this slice's 132/132 is the
      baseline the gate re-confirms, not a substitute for it).
- [ ] Live Postgres: confirm `PUT /v1/spatial/parcels/{id}/geometry` and
      `GET /v1/spatial/parcels/{id}/geometry` actually persist/read `boundary` as WKT through the
      custom `Geometry` `TypeEngine` (`ST_GeomFromText`/`ST_AsText`) against a live request — the
      migration's column type was confirmed via `psql` directly, but the ORM round-trip through
      the ORM/ `Geometry` type has not yet been exercised via a real HTTP request.
- [ ] Live RLS: confirm cross-tenant `PUT`/`GET` on `parcel_geometries` fails closed against the
      real database (0 rows / 404), not only against the in-memory fake's `_in_scope` check —
      the two layers need to each be independently proven, per this platform's own standing
      "RLS is one layer, application check is the other, both independently verified" practice.
- [ ] Live concurrency: confirm the partial unique index
      (`ix_parcel_geometries_one_active_per_parcel`) actually rejects a second concurrent
      `INSERT` racing to become `ACTIVE` for the same parcel — the domain-level
      `get_active_for_parcel` → `supersede()` → `add()` sequence assumes no other request
      concurrently inserts a competing `ACTIVE` row inside the same window; the database
      constraint is the real backstop, not yet proven under genuine concurrent load (mirroring
      B3 Slice 2's own live-concurrency-testing discipline, not yet applied here).
- [ ] Live Keycloak, real authenticated flow: submit geometry as creator, non-registrant denied
      (403), cross-tenant denied (404), `super_admin` cross-tenant permitted (201), malformed
      boundary rejected (400), a second submission superseding the first — all currently proven
      only against in-memory fakes + Keycloak-free `TestClient`, not the real running server.
- [ ] Live audit chain: confirm `spatial.parcel_geometry.created` entries exist in the real
      `audit_log` table with the documented payload shape, and `verify_chain()` still returns
      `True` afterward.
- [ ] Containerized backend: rebuild, confirm it boots healthy and exposes
      `PUT`/`GET /v1/spatial/parcels/{id}/geometry` in `/openapi.json`.
- [ ] Security validation: confirm `SubmitGeometryRequest`'s `extra="forbid"` rejects an attempt
      to set `tenant_id`, `parcel_id`, `status`, or `geometry_id` directly through the API body —
      analogous to the immutable-field-smuggling check already performed for Registry's own
      `PATCH` endpoint in the B3 Quality Gate.

**Known limitations (documented, not defects):**

- **`PlaceholderGeometryAdapter` remains Registry's registered `GeometryPort` implementation,
  unconnected to this slice's real `ParcelGeometry` data**, per explicit instruction — Registry's
  `parcels.geometry_reference` and Spatial's own `parcel_geometries` table are not yet wired
  together. That connection is ADR-020's job (the real `GeometryPort` adapter).
- **No `geoalchemy2` dependency was added.** `boundary` is treated as an opaque WKT string at the
  application layer; the custom `Geometry` `TypeEngine`
  (`app/contexts/spatial/adapters/orm.py`) handles `ST_GeomFromText`/`ST_AsText` wrapping at the
  SQL boundary with zero external dependencies, sufficient for this slice's needs (no real
  spatial query capability required yet). Revisit if ADR-020/021 genuinely need richer
  Python-side spatial operations.
- **Validation is structural only** (non-empty, well-formed `POLYGON(...)` WKT syntax via a
  regex) — no self-intersection check, no coordinate-bounds sanity check, no administrative-
  boundary containment. Explicitly deferred to ADR-020, per this slice's approved scope.
- **Spatial's own authorization is coarse**: the same `PARCEL_REGISTRANT_ROLES` role gate
  Registry's mutation endpoints use, plus the tenant-scope `_in_scope` check — but *not* a
  creator-or-governance check on the specific parcel (mirroring ADR-015's model for Registry).
  Any `PARCEL_REGISTRANT_ROLES` holder in the correct tenant can submit geometry for *any* parcel
  in that tenant, not only ones they created. This is a deliberate, documented scope boundary,
  not an oversight — a full Spatial Authorization Model is explicitly ADR-022's job. **This
  should be weighed carefully before Slice 1 is considered production-ready**, since it is
  structurally similar in shape to the original ADR-005 defect Registry's own ADR-015 closed —
  the difference is that this is disclosed and scoped deliberately, with a named ADR already
  reserved to close it, not an unnoticed gap.
- Carried unchanged from B3: the containerized backend's `KEYCLOAK_REALM_URL` host-relative
  networking gap; SQLAlchemy's default connection-pool ceiling under heavy concurrent load.

**Performance observations:** none yet specific to this slice — no spatial queries exist to
evaluate (that's ADR-020/021's job); the append-only supersede pattern is a single-row update per
submission, structurally similar to Registry's own mutation pattern.

**Infrastructure observations:** none new.
