# B3 Final Verification Checklist

Cumulative, append-only register of verification work deferred under the B3 Development
Workflow Update (deferred-verification policy, adopted mid-Slice-3). Each slice's completion
report appends its own section here rather than running the full verification suite
immediately. **No item on this list may be skipped** — it is executed exhaustively, once, during
the End-of-B3 Quality Gate (full `ruff`/`mypy`/`pytest`, live Postgres/Keycloak/RLS/audit/
delegation/cross-tenant/ownership-attack/container verification, full B1+B2+B3 regression),
before B3 may be proposed for freeze.

Slices 1 and 2 predate this policy — they already received full live verification at the time
they were built (see their own completion reports and `CLAUDE.md`'s B3 status section for what
was already proven). They are listed here only where Slice 3 touches shared mechanisms they
depend on, so nothing already proven silently goes unchecked a second time.

## Slice 3 — Mutation Commands & Authorization Hardening (docs/adr/ADR-015)

**Already done (targeted, not deferred):** `ruff`/`mypy` on every changed file (clean); the full
`tests/test_b3_registry.py` file, including all 19 new Slice 3 tests (37/37 passed). Immediate
coding defects found and fixed during implementation (not deferred, per policy — these are
"obvious implementation defects," not verification): two new tests initially seeded two users
without a shared `tenant_id`, so they landed in different tenants and got 404 instead of the
403/200 the test intended — fixed by passing `tenant_id=<first user>.tenant_id` explicitly; the
suspended-tenant test initially expected 401, corrected to 403 to match the PEP's existing,
documented behavior (roleless-after-failed-hydration still isn't the literal "anonymous"
sentinel, so `require_role` denies with 403, not `require_auth` with 401).

**Deferred to the End-of-B3 Quality Gate:**

- [ ] Full `pytest` suite (all of B1 + B2 + B3 slices 1–3 together) — the last full run (90/90)
      predates Slice 3's changes to `app/kernel/authorization/pep.py` and
      `app/contexts/identity/context_hydration.py` (both touched to thread
      `ExecutionContext.attributes["delegated_roles"]` through). Those two files are shared by
      every B1/B2 authenticated endpoint, not Registry-specific — a full run is the only way to
      confirm zero regression there, not just in `test_b3_registry.py`.
- [ ] Full `ruff`/`mypy` across the whole repo (only the changed-file subset has been checked so far).
- [ ] Live Postgres: confirm `PATCH /v1/parcels/{id}` and `POST /v1/parcels/{id}/archive` actually
      persist `updated_by`/`archived_at`/changed fields against the real `parcels` table (no new
      migration this slice — reuses columns reserved since `0007` — but the write path itself is
      new and untested against a real UPDATE grant/RLS combination).
- [ ] Live RLS: confirm `UPDATE` under a bogus/absent `app.tenant_id` session var still fails
      closed (0 rows affected) for the new mutation paths specifically, not only for `INSERT`
      (Slice 1) and the counter table (Slice 2).
- [ ] Live Keycloak, real authenticated flow: creator update/archive, non-creator same-tenant
      denial (the ADR-005 regression, reproduced for real — not only against the in-memory fake),
      governance-role override, `super_admin` cross-tenant override, cross-tenant 404.
- [ ] Live delegation: a real delegation created via `POST /v1/admin/delegations`, exercised
      against a real parcel mutation, then revoked/expired/delegator-demoted/tenant-suspended,
      each re-checked against the running server (not only the in-memory fake) — proving
      ADR-011's fail-closed re-resolution actually reaches Registry mutation end-to-end, live.
- [ ] Live audit chain: confirm `registry.parcel.updated`/`.archived`/`.mutation_denied` entries
      exist in the real `audit_log` table with the documented payload shape
      (`effective_authority`, `delegated_roles`, `tenant_id`, `fields_changed`), and
      `verify_chain()` still returns `True` afterward.
- [ ] Containerized backend: rebuild, confirm it boots healthy and exposes the two new routes
      (`PATCH /v1/parcels/{id}`, `POST /v1/parcels/{id}/archive`) in `/openapi.json`. Full
      authenticated-flow verification through the container itself is expected to hit the same
      pre-existing, out-of-scope `KEYCLOAK_REALM_URL` host-relative networking gap Slice 2's
      completion report already documented (unrelated to this slice, not yet fixed, still an
      open infrastructure item — see "Known limitations" below).
- [ ] Security validation: attempt to `PATCH` an immutable field (`parcel_id`, `tenant_id`,
      `created_by`, `status`, `parcel_number`) via a crafted raw HTTP request bypassing the
      DTO's `extra="forbid"` — confirm the domain-level `UPDATABLE_FIELDS` allow-list in
      `Parcel.update_details` is a real second layer, not merely redundant with Pydantic
      validation (currently proven only via a direct unit test against the domain object,
      `test_domain_update_details_rejects_unknown_fields`, not via HTTP).

**Known limitations (documented, not defects):**

- No "restore" command exists — `ARCHIVED` remains one-way, per ADR-013's original "terminal"
  designation. ADR-015 records this as deliberate, not an oversight.
- Ownership-transfer authorization (who may initiate a future transfer of
  `current_owner_name`/`current_owner_contact`) is explicitly left for whichever future slice
  builds that command — ADR-015 states only that `created_by` must remain untouched by it.
- The containerized backend's `KEYCLOAK_REALM_URL` is host-relative (`localhost:8080`), carried
  over unchanged from Slice 2 — full authenticated live verification continues to go through the
  host dev server, not the container directly, until that infrastructure item is addressed (out
  of Registry's scope).
- SQLAlchemy's default connection-pool ceiling (`pool_size=5` + `max_overflow=10` = 15),
  documented in Slice 2, is a platform-wide operational constraint that still applies; Slice 3
  introduces no new concurrency-sensitive path (mutation is a single-row update per parcel, not
  a shared-counter contention point like allocation was).

**Performance observations:** none specific to this slice — `update_parcel`/`archive_parcel` are
single-row operations with no shared-lock contention analogous to Slice 2's counter table.

**Infrastructure observations:** none new — see "Known limitations" above (carried over from
Slice 2, not introduced by Slice 3).
