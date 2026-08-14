# B1 Infrastructure Integration & Validation — Deployment Report

**Scope:** B1 (Identity & Authorization) re-verified end-to-end against real infrastructure
(Docker Desktop, PostgreSQL, Keycloak, FastAPI, Alembic) — no in-memory fakes, no mocked
adapters, no simulated results. Every claim below was produced by an actual command against
a running container, a real HTTP request, a real psql query, or a real server log line.

**Result: B1 — Infrastructure Verified.**

---

## 1. Infrastructure Status

All four services run as Docker containers and are healthy:

| Container | Status | Port |
|---|---|---|
| `aquasavannah-landvault-postgres-1` | Up, healthy | 5432 |
| `aquasavannah-landvault-keycloak-1` | Up | 8080 |
| `aquasavannah-landvault-backend-1` | Up | 8000 |
| `aquasavannah-landvault-frontend-1` | Up | 3000 |

The backend was additionally run outside Docker (`uvicorn ... --no-proxy-headers`, port
8123) against the same Postgres/Keycloak containers, specifically to iterate quickly on
fixes during this validation without a full image rebuild each time. The containerized
backend image was rebuilt and confirmed to carry the same fixes before sign-off (§10).

## 2. Docker Status

`docker compose --env-file .env -f infra/docker/docker-compose.yml up -d` brings up all
four services from a clean state. Two real build/config issues were found and fixed during
this work (not assumed away):

- `env_file:` in compose only injects vars into the container — it does **not** feed
  `${VAR}` substitution inside the compose YAML itself. Required `--env-file .env` on the
  `docker compose` invocation as well.
- The build failed on a missing `frontend/public/` directory; created with `.gitkeep`.

## 3. Database Status

PostgreSQL 16, reached directly via `psql` inside the container for every check in this
report (not through the application). Confirmed live:

- `identity_users`, `identity_sessions`, `audit_log` tables exist with the expected columns,
  indexes, and constraints.
- `FORCE ROW LEVEL SECURITY` is active on tenant-scoped tables.
- Two Postgres roles exist: an owning/migration role (full DDL) and `landvault_app`, a
  least-privilege role the application actually connects as. Verified live: `landvault_app`
  can `SELECT`/`INSERT`/`UPDATE` on `identity_users`/`identity_sessions`, can
  `SELECT`/`INSERT` (not `UPDATE`/`DELETE`) on `audit_log`, and a direct `UPDATE`/`DELETE`
  attempt against `audit_log` as this role fails with `permission denied for table
  audit_log`.
- RLS fail-closed behavior verified directly via `psql` as `landvault_app`: with
  `app.tenant_id` set to a tenant that doesn't exist, `SELECT count(*) FROM identity_users`
  returns `0`; with **no** session variable set at all, it also returns `0` (never an
  implicit full-table leak). As the owning role (RLS doesn't apply to a table owner), the
  same query returns the real row count — this asymmetry is exactly why the least-privilege
  role in migration 0002 exists; without it, `GRANT`/`REVOKE` alone is a no-op against the
  owner.

## 4. Migration Status

```
<base> -> 0001, identity and audit tables + RLS policies
0001 -> 0002, application role with least privilege (fixes ineffective audit_log REVOKE)
0002 -> 0003, timezone-aware timestamp columns (fixes naive/aware datetime mismatch)
```

`alembic current` on the live database reports `0003 (head)`. All three migrations were
authored, applied, and the schema they produced was independently inspected via `psql` —
not assumed correct from reading the migration source.

## 5. Keycloak Status

Realm `landvault` configured with a confidential client (`landvault-api`), Direct Access
Grants enabled, a service account with `manage-users` for admin-API user creation, and an
audience protocol mapper (without it, `aud` was `"account"`, not `landvault-api`, and the
verifier correctly rejected every token). Verified live end-to-end:

- JWKS discovery (`/protocol/openid-connect/certs`) reachable and used by the running app.
- Token issuance via Direct Access Grant (password grant) and via `client_credentials`
  (service account).
- Refresh token rotation — each `/v1/auth/refresh` call returns a new refresh token,
  confirmed to differ from the previous one.
- Logout — Keycloak-side session end plus local session revocation.
- Revocation on replay — see §8.

One real bug was found and fixed here (see §9): `full_name.partition(" ")` left `lastName`
empty for any single-word name, and Keycloak 26's declarative User Profile requires a
non-empty `lastName` for a "complete" profile — the affected user's *next* login (not
registration itself) failed with `resolve_required_actions` / "Account is not fully set
up". Confirmed fixed live: register + immediate login with a single-word name now succeeds.

## 6. JWT Status

RS256, verified against the real JWKS endpoint (no shared-secret shortcut). Adversarial
checks run live against the running server:

- Expired token (valid structure, `exp` in the past, signed with a throwaway key): `401`.
- Signature tampered mid-signature (flipping a character in the last base64 group is not a
  reliable test — base64 padding slack there can decode to the same bytes; a flip in the
  middle of the signature reliably corrupts it): `401`.
- Payload tampered: `401`.
- `alg: none` forged token, no signature: `401`.

## 7. RLS Status

Covered in §3 (direct psql) and §8 (live HTTP cross-tenant test). Fail-closed in both
directions: an absent tenant context and a bogus tenant context both yield zero visible
rows, never a fallback to "all rows."

## 8. Identity & Authorization Status

All `/v1/auth/*` and `/v1/admin/*` routes mounted via proper FastAPI DI
(`Depends(get_auth_service)` etc., not a shared singleton) and exercised over real HTTP
against the live server. Full acceptance suite, run twice (once before the Phase 9 fixes,
once after, to confirm no regression) — **12/12 passing** both times:

1. Anonymous access to a protected route → `401`.
2. Expired JWT rejected.
3. Refresh token rotates.
4. Logout invalidates the refresh token.
5. Stolen (replayed) refresh token rejected, **and** replay detection revokes the entire
   legitimate session chain too — not just the thief's request. This was a real bug found
   live: the generic "any exception → rollback" behavior in the Unit-of-Work was undoing
   `revoke_all_active_for_user()` immediately before the `401` was raised, since the raise
   itself was (wrongly) treated as a rollback signal. Fixed by distinguishing `HTTPException`
   (a deliberate, correctly-handled rejection — commit) from a genuine unexpected exception
   (rollback).
6. Role escalation impossible: a `compliance_officer` (seeded directly in Postgres, then
   authenticated through the real Keycloak Direct Access Grant) cannot grant `super_admin`
   to anyone, and cannot self-elevate to a higher role.
7. Self-registration cannot assign roles (`422` if attempted).
8. Policy engine denies by default — no governance role, no access to admin routes (`403`).
9. CORS rejects unknown origins (no `Access-Control-Allow-Origin` header at all for
   `https://evil.example`).
10. Rate limiting enabled (`429` after the configured threshold).
11. All auth events audited, and the hash chain verifies (`verify_chain()` returns `True`)
    over live-written entries.

**Cross-tenant adversarial test (beyond the 11 above, purpose-built for this phase):**
registered two users, each self-registration creating its own tenant boundary (this
platform's registration model — every self-registered user is the seed of a new tenant, not
grouped into a shared default). Seeded `compliance_officer` on one directly in Postgres,
authenticated them for real, then had them target the *other* tenant's user via
`POST /v1/admin/users/{id}/roles`:

- Cross-tenant target → `404 user not found` — RLS makes the row genuinely invisible, this
  is not a policy-layer `403`.
- Same-tenant self-target (as a control, proving the `404` above isn't just a broken
  endpoint) → `403` — the row **is** visible in-tenant, but the policy engine still denies
  the self-elevation attempt.

**Rate-limit bypass (the most involved finding this phase):** an attacker sending a
different spoofed `X-Forwarded-For` value on every request defeated the rate limiter
entirely — 15 requests, 15 different spoofed IPs, zero `429`s, where the same volume from
one real IP correctly tripped it at request 11. Two independent layers needed fixing, not
one:

1. **App layer** — `RateLimitMiddleware._client_ip()` and `auth_router._client_meta()` were
   reading `X-Forwarded-For` directly. Fixed to use only `request.client.host`; there is no
   configured trusted-reverse-proxy allowlist in this deployment (ADR-004), so the header is
   untrusted, full stop.
2. **ASGI layer — the actual root cause.** Even after fix #1, live retesting *still* showed
   the bypass. Traced to uvicorn's own defaults: `proxy_headers=True`,
   `forwarded_allow_ips="127.0.0.1"` — uvicorn rewrites `request.client` from
   `X-Forwarded-For` for any peer connecting from localhost, silently defeating fix #1 one
   layer below the application's own code, before our middleware ever runs. Fixed by adding
   `--no-proxy-headers` to both the Dockerfile `CMD` and the documented local dev command.

Verified live after both fixes: spoofed, *varying* `X-Forwarded-For` values across 12
requests now correctly hit `429` at request 11/12, matching the no-header baseline exactly.

**Wildcard CORS:** verified live (not just read from source) that setting
`CORS_ALLOWED_ORIGINS=*` raises a `pydantic.ValidationError` at settings-load time — the app
cannot even start with a wildcard origin. Fail-closed by construction, not by convention.

**Direct SQL / audit tamper attempts:** covered in §3 — `UPDATE`/`DELETE` on `audit_log` as
the application's own least-privilege role fails with a real Postgres permission error, not
an application-level check that could be bypassed by going around the app.

## 9. Bugs found and fixed this phase (chronological)

1. Least-privilege role: `REVOKE` on `audit_log` was a no-op against the owning role — added
   migration 0002 with a separate `landvault_app` role.
2. `CREATE ROLE ... PASSWORD $1` — DDL doesn't accept bind parameters; used an escaped SQL
   literal with a defensive check against quote/backslash injection in the password.
3. `KEYCLOAK_ADMIN_TOKEN_URL` pointed at the `master` realm; `client_credentials` must
   target the client's own realm.
4. Token `aud` was `"account"`; added an audience protocol mapper.
5. `UserRecord.updated_at`'s `onupdate=func.now()` caused `MissingGreenlet` — SQLAlchemy
   marks the column expired after an UPDATE flush, and accessing it without an explicit
   `refresh()` trips the async bridge. Removed `onupdate`; set explicitly in repository code.
6. `PostgresAuditStore.append()` never passed `created_at` explicitly, so the DB-generated
   timestamp never matched what was hashed — broke `verify_chain()` on every entry.
7. `entry_id=str(record.id)` vs `record.id.hex` — the canonical hyphenated UUID string
   differs from the original `uuid.uuid4().hex` that was hashed; same hash-chain-breaking
   effect as #6.
8. Naive vs aware datetime mismatch (`asyncpg.exceptions.DataError`) — added migration 0003
   to make all datetime columns `TIMESTAMPTZ`.
9. `User.new()`/`Session.new()` used `"usr_"+hex`/`"ses_"+hex`, which doesn't match a
   Postgres UUID column and was silently replaced by a random UUID on persist. Fixed to
   generate a bare `str(uuid.uuid4())`.
10. `require_role()`'s deny path 500'd instead of 403 — `audit()` ran during dependency
    resolution, before any per-request DB session existed. Fixed with an eager,
    independently-committing fallback audit store bound at startup.
11. Making that eager store commit independently exposed a second bug: the main request
    session was *also* bound as the audit store, so `audit()`'s commit ended the
    transaction the RLS `set_config(..., is_local=true)` was scoped to, silently clearing
    tenant scoping/RLS-bypass for the rest of the request. Fixed by never binding the main
    session as the audit store.
12. Deny/failure audit entries were rolled back along with the request that triggered them
    — `PostgresAuditStore.append()` only `flush()`'d. Fixed to `commit()` immediately.
13. Replay-detection revocation undone by rollback (§8, item 5) — fixed by distinguishing
    `HTTPException` (commit) from a genuine unexpected exception (rollback) in the
    Unit-of-Work.
14. Rate-limit bypass via `X-Forwarded-For`, at both the app and ASGI layers (§8).
15. Single-word `full_name` broke Keycloak's declarative User Profile (§5, §9 above).

## 10. Remaining Risks

- **Orphaned Keycloak user on partial failure.** Registration creates the Keycloak user
  first, then the Postgres row. If the Postgres write fails after the Keycloak user was
  successfully created, there is no distributed transaction/saga to undo the Keycloak side
  — the user exists in Keycloak but not in the application's own `identity_users` table.
  Not fixed in this phase; needs either a compensating-action saga or a reconciliation job
  before production traffic.
- **Rate limiter is in-process, not distributed.** By design (documented in
  `http_hardening.py` as the "inner layer" of defence in depth) — a real deployment needs an
  edge/ingress-level limiter as the outer layer, since this one resets on every process
  restart and doesn't coordinate across replicas.
- **No automated test currently pins the uvicorn `--no-proxy-headers` requirement.** It's
  enforced by the Dockerfile/CLAUDE.md, but nothing fails CI if that flag is accidentally
  dropped from either. Worth a smoke test in CI that boots the real ASGI stack and asserts
  the bypass stays closed, rather than relying on the flag being remembered.

## 11. Technical Debt

- The containerized backend and the local (`--reload`-free) dev-server path both need
  manual restarts to pick up code or infrastructure changes; no `--reload` is used against
  the containers, which is correct for production-likeness but slows iteration.
- `docker compose up backend` was observed to recreate the `postgres` container as a side
  effect in this session (compose detected a dependency change) — data survived because the
  volume is named and persists independently, but this is worth being aware of before
  running compose commands against a database anyone cares about.

## 12. Production Readiness

B1 (Identity & Authorization) is verified against real infrastructure end-to-end: migrations
apply cleanly, RLS is proven fail-closed at the database level (not just in application
code), Keycloak issues/refreshes/revokes real tokens, the Unit-of-Work correctly
distinguishes deliberate rejections from genuine failures, audit logging is tamper-evident
and durable independent of the surrounding transaction, and every adversarial check in the
Phase 9 list (JWT tampering, expired tokens, role escalation, cross-tenant access, direct
SQL/RLS bypass, refresh replay, unknown-origin and wildcard CORS, rate-limit bypass) was
rejected live, not merely by unit test.

**B1: Infrastructure Verified.**

Per the governing instruction for this work: stopping here to wait for approval before
beginning B2 — Identity Management.
