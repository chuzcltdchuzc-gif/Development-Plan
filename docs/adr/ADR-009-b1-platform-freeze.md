# ADR-009 — B1 Platform Freeze

**Status:** Accepted — B1 is frozen as of this date. Amend via a new ADR; do not edit this
document's description of "what B1 is" retroactively — a later ADR that changes B1 behavior
supersedes the relevant section here and must say so explicitly.

**Date:** 2026-07-15

**Verified against:** the real infrastructure described in
`docs/audits/B1_INFRASTRUCTURE_VERIFICATION.md` (Docker/Postgres/Keycloak, migrations `0001`
through `0003`, live end-to-end and adversarial testing) — this document is the architecture
description; that one is the evidence it's accurate.

## Context

B1 (Identity & Authorization) is complete and verified end-to-end against real infrastructure.
Bounded contexts B2–B13 are about to begin building on top of it. Per `docs/PHASE_GATES.md`
and `docs/ENGINEERING_RULES.md`, later contexts must treat B1 as a stable platform, not
something they casually reach into and modify. This ADR is the frozen description of B1
exactly as it exists at the moment of this writing — every claim below was read from the
actual source files or observed against the running system, not recalled from an earlier
design intent.

**Amendment procedure:** a bounded context that needs B1 to behave differently (a new role,
a changed token lifetime, an additional claim in the `ExecutionContext`, etc.) opens a new
ADR that references this one and states precisely what changes and why. It does not edit B1's
source directly as a side effect of B2+ work without that ADR existing first.

## Scope — what is frozen

Everything under `backend/app/kernel/` and `backend/app/contexts/identity/`, the migrations
`0001`–`0003`, the Keycloak realm configuration described in §5, and the Docker topology in
§16. Frontend Identity UI, and any bounded context other than Identity itself, are out of
scope for this freeze.

---

## 1. Authentication Flow

External identity provider: Keycloak (realm `landvault`). The application never verifies
passwords itself — `KeycloakIdentityProvider` (`backend/app/contexts/identity/adapters/
keycloak.py`) does two things against Keycloak, both server-to-server:

- **Registration** (`POST /v1/auth/register`, `AuthService.register_local`): validates
  email/password/full_name/country locally (password ≥ 8 chars; email/country parsed as
  value objects), rejects a pre-existing email, then calls Keycloak's Admin API
  (`POST {admin_api}/users`) to create the IdP-side user — `firstName`/`lastName` derived
  from `full_name.partition(" ")`, with the single-word-name fallback (§9 fix in the
  verification report) reusing the one word for both fields so Keycloak's declarative User
  Profile always sees a non-empty `lastName`. On success, a local `User` aggregate is created
  (`User.new(...)`, default role `general_user`, its own fresh `tenant_id`) and the flow
  immediately calls `login_local` to return real tokens — registration and login share one
  code path from that point on.
- **Login** (`POST /v1/auth/login`, `AuthService.login_local`): calls Keycloak's Direct
  Access Grant (`grant_type=password`) via `KeycloakIdentityProvider.authenticate`. On
  success, the returned access token's `sub` claim is used to look up the local `User` by
  `keycloak_subject`; a user that doesn't exist locally or fails `can_authenticate()`
  (`account_status != "active"`) is rejected with the same generic "Invalid email or
  password" as a genuine bad password — no oracle for account existence.

Registration and login are both rate-limited (§14) and every outcome — success and failure —
is audited (§8).

## 2. Authorization Flow

Single path, enforced by one FastAPI dependency chain — there is no second, ad hoc auth
check anywhere in the codebase (`docs/ENGINEERING_RULES.md` #1):

1. **PEP** (`app.kernel.authorization.pep`) — `current_context_dep` runs on every request
   that declares it as a dependency (directly or via `require_auth`/`require_role`). It
   extracts the bearer token (`Authorization: Bearer ...` header, or the `lv_access` cookie
   as a fallback), verifies it via `JwtVerifier` (§3), and — critically — **never trusts the
   token's own claims for authorization attributes beyond `sub`**. It calls the configured
   `ContextHydrator` to look up roles/tenant/country/organization from Postgres (§3 of
   `context_hydration.py`'s docstring: "Keycloak's token only proves `sub`; our own Postgres
   is the single source of truth for authorization attributes"). The result is an
   `ExecutionContext` (`app.kernel.context`), bound to a `ContextVar` for the lifetime of the
   request.
2. **`require_auth`** — 401s if the resulting context is anonymous.
3. **`require_role(*roles)`** — 403s (and audits the denial as `authz.deny`) if the
   authenticated principal holds none of the required roles. Used by `/v1/admin/*` routes
   with `GOVERNANCE_ROLES` (`super_admin`, `surveyor_general`, `compliance_officer`).
4. **`enforce(action, resource, env)`** — the programmatic PDP entry point for
   finer-grained, resource-level decisions (not yet called by any B1 route directly, but
   available to B2+): calls `app.kernel.authorization.pdp.authorize`, audits the decision
   either way, and raises 403 on DENY.

The **PDP** (`app.kernel.authorization.pdp.authorize`) is a pure function: it evaluates
registered policies (`app.kernel.authorization.policies`) in ascending priority order and
returns the first non-`None` `Decision`; if every policy abstains (returns `None`), the PDP
itself returns `Decision.deny("no policy granted access (default deny)")`. A policy that
raises is treated as a DENY, logged, never silently swallowed. This is fail-closed by
construction, not by convention — there is no code path that defaults to PERMIT.

Default policies, in priority order: `platform.tenant_isolation` (10) → deny cross-tenant
resource access unless `super_admin`; `platform.country_isolation` (11) → same for
cross-country; `platform.super_admin` (20) → `super_admin` permits everything;
`platform.anonymous_public` (30) → anonymous callers may only reach
`identity.register`/`identity.login`/`identity.refresh` or an action explicitly prefixed
`platform.public.`; `identity.self` (40) → an authenticated principal may always read/log
out their own record.

**Role hierarchy** (`ROLE_RANK` in `value_objects.py`) governs role *assignment* only, not
general authorization: `general_user`(0) < `{field_agent, community_validator,
government_observer}`(10) < `{surveyor, surveyor_partner}`(20) < `licensed_surveyor`(30) <
`{compliance_officer, surveyor_general}`(40) < `super_admin`(100). `AdminService.assign_role`
hard-denies (a) a caller targeting their own `user_id` and (b) granting a role ranked higher
than the caller's own highest rank — both checked before the target row is even touched.

## 3. JWT Lifecycle

Access tokens are **RS256**, issued and signed by Keycloak — this application never holds a
signing key or issues its own access tokens. `JwtVerifier` (`app.kernel.security.jwt`)
verifies every presented token against the realm's live JWKS endpoint
(`{realm_url}/protocol/openid-connect/certs`), matched by the token header's `kid`; an
unparseable header, missing/unknown `kid`, or signature/claim failure all raise
`InvalidTokenError`, surfaced by the PEP as `401`. Required claims (enforced via
`options={"require": [...]}`, not merely "if present"): `exp`, `iat`, `iss`, `aud`, `sub`.
`iss` must equal the configured realm URL; `aud` must equal `JWT_AUDIENCE`
(`landvault-api`) — this requires the audience protocol mapper described in §5, without which
`aud` defaults to `"account"` and every token is correctly rejected.

`KeycloakJWKSProvider` caches fetched keys for `cache_ttl_seconds` (default 300s) and
re-fetches on a cache miss or expiry — a key rotated at the IdP is picked up within one
verification cycle at worst.

No token refresh happens silently inside verification: an expired access token is simply
rejected (`401`); the client is expected to call `/v1/auth/refresh` (§4) to obtain a new one.

## 4. Refresh-Token Lifecycle

Refresh tokens presented to *our* API are **opaque**, not the Keycloak-issued refresh token
directly (`app.kernel.security.tokens`): 32 bytes of `secrets.token_urlsafe` randomness, sent
to the client exactly once as an httpOnly, `SameSite=Lax` cookie
(`lv_refresh`, path `/v1/auth`, `Secure` outside `development` — `Settings.cookie_secure`).
Only the token's SHA-256 hash is persisted (`identity_sessions.refresh_token_hash`); a
database read alone never yields a usable token. The corresponding **Keycloak-issued**
refresh token (`idp_refresh_token`) is also stored server-side, never sent to the client, and
is what's actually presented back to Keycloak to mint a new access token on `/v1/auth/refresh`.

Lifecycle, modeled by `Session` (`app.contexts.identity.domain.session`):

- **Issued** on register/login/refresh (`AuthService._issue_tokens`) — `ACTIVE`, TTL 30 days
  (`REFRESH_TOKEN_TTL_SECONDS`).
- **Rotated** on every `/v1/auth/refresh` call: the presented session is looked up by hash,
  validated (`ACTIVE`, not expired, owning user still `can_authenticate()`), then Keycloak is
  asked to refresh the *IdP* token; only on that success is the old session marked `REVOKED`
  (reason `"rotated"`) and a brand-new session/opaque-token pair issued
  (`rotated_from` linking the two for lineage).
- **Revoked** on logout (reason `"user_logout"`), on expiry (`"expired"`), on the owning
  user going inactive (`"user_inactive"`), on the IdP rejecting the refresh
  (`"idp_refresh_rejected"`) — or, most importantly:
- **Replay detected**: presenting a session hash whose `status != "ACTIVE"` (i.e. an already
  rotated-away or revoked token) is treated as token theft, not a normal error. It triggers
  `revoke_all_active_for_user()` — every other active session for that user is killed too —
  before rejecting the replaying request with `401`. This is deliberately more aggressive
  than rejecting just the replayed token: the entire session chain is presumed compromised.

The revocation-on-replay commit is only real because of the Unit-of-Work's
`HTTPException`-commits distinction (§10) — this was a genuine bug found and fixed during B1
verification (`docs/audits/B1_INFRASTRUCTURE_VERIFICATION.md` §8 item 5).

## 5. Keycloak Configuration

Realm: `landvault`. Client: `landvault-api`, confidential (has a client secret), with:

- **Direct Access Grants enabled** — required for the Resource Owner Password Credentials
  flow this app uses for `/v1/auth/login` and `/v1/auth/refresh` (`grant_type=password` /
  `grant_type=refresh_token` against `{realm_url}/protocol/openid-connect/token`).
  There is no browser redirect/authorization-code flow in B1 — the SPA/API talks to our
  backend, and our backend talks to Keycloak directly.
- **Service account enabled**, with the `manage-users` realm-management role — used for
  `client_credentials`-grant admin operations (creating IdP users on registration). Verified
  live that this service account has no broader permission (§ "Remaining Risks" in the
  verification report — attempting to list clients with it returns `403`), consistent with
  least privilege.
- **An audience protocol mapper** on this client so issued tokens carry `aud: "landvault-api"`
  rather than the default `"account"` — without it, `JwtVerifier`'s required-audience check
  correctly rejects every token.
- **Declarative User Profile** (Keycloak 26 default) requires non-empty `firstName` and
  `lastName` for a "complete" profile; an incomplete profile fails the user's *next* login
  with `resolve_required_actions` even though user creation itself still returns `201`. This
  is why `create_user()` never sends an empty `lastName` (§1, §9).

`KEYCLOAK_ADMIN_TOKEN_URL` for the service account's `client_credentials` grant must target
this client's **own realm** (`landvault`), not `master` — an early configuration bug, fixed
during B1 verification.

**Known gap:** no realm export (JSON) is committed to this repository, and the service
account currently configured lacks permission to produce one via the Admin API (confirmed
live, §above). The configuration above is enforced by the application code's requirements and
was verified working end-to-end, but is not yet a versioned, reproducible artifact. Recommend
a follow-up ADR or ops task to export the realm and commit it (or manage it via Keycloak's
declarative config / Terraform provider) before this becomes a multi-environment concern.

## 6. Database Schema

PostgreSQL, three tables (migration `0001`, columns as currently typed after `0003`'s
timezone fix — see full DDL in `backend/migrations/versions/0001_identity_and_audit.py`):

**`identity_users`** — `id` (UUID, PK), `keycloak_subject` (unique), `email` (unique),
`full_name`, `country` (2 chars), `tenant_id` (indexed), `organization_id` (nullable),
`roles` (JSONB array, default `[]`), `account_status` (default `"active"`),
`suspension_reason` (nullable), `last_login_at` (nullable, `TIMESTAMPTZ`), `version`
(optimistic-lock counter, default `1`), `created_at`/`updated_at` (`TIMESTAMPTZ`,
server-defaulted; `updated_at` has no `onupdate` trigger — see §10's ORM note on why),
`created_by`/`updated_by` (nullable, unused by B1 itself), `deleted_at` (nullable, unused —
no soft-delete logic implemented yet).

**`identity_sessions`** — `id` (UUID, PK), `user_id` (FK → `identity_users.id`, indexed),
`refresh_token_hash` (unique), `idp_refresh_token`, `status` (`ACTIVE`/`REVOKED`,
default `ACTIVE`), `expires_at` (`TIMESTAMPTZ`), `rotated_from` (nullable UUID, self-referential
lineage, not an FK constraint), `user_agent`/`ip_address` (nullable), `revoked_at`/
`revoked_reason` (nullable), `created_at` (`TIMESTAMPTZ`).

**`audit_log`** — `id` (UUID, PK), `action`, `resource_type`, `resource_id` (nullable),
`decision` (nullable), `principal_id`, `payload` (JSONB, default `{}`), `prev_hash`/`hash`
(64-char hex, `hash` unique), `created_at` (`TIMESTAMPTZ`, indexed). No `updated_at` — this
table is genuinely append-only (§8).

Two Postgres roles exist: the schema-owning role (`POSTGRES_USER`, runs migrations, created
by the `postgis` image bootstrap) and `landvault_app` (migration `0002`), the role the
running application actually connects as, with exactly: `SELECT/INSERT/UPDATE` on
`identity_users`/`identity_sessions`, `SELECT/INSERT` only on `audit_log`. The owning role is
never used at runtime — only for migrations — because table ownership bypasses `GRANT`/
`REVOKE` and RLS entirely, confirmed live (§7).

## 7. RLS Policy Model

All three tables have `ROW LEVEL SECURITY` **and** `FORCE ROW LEVEL SECURITY` enabled
(the `FORCE` variant applies RLS even to the table owner — though for `landvault_app`
specifically, ownership isn't the issue since it doesn't own the tables; `FORCE` matters if
anyone ever runs the app as the owning role by mistake).

- **`identity_users_tenant_isolation`** — `USING (tenant_id = current_setting('app.tenant_id',
  true) OR current_setting('app.is_super_admin', true) = 'true')`.
- **`identity_sessions_tenant_isolation`** — same condition, checked via an `EXISTS` join
  back to the owning `identity_users` row (sessions have no `tenant_id` column of their own).
- **`audit_log_read_all`** (`FOR SELECT USING (true)`) and **`audit_log_insert_only`**
  (`FOR INSERT WITH CHECK (true)`) — audit rows are globally readable and insertable by
  design (audit trail visibility isn't tenant-scoped in B1); the real protection for this
  table is the `UPDATE`/`DELETE` grant revocation (§6/§8), not RLS.

Fail-closed by construction: `current_setting(..., true)` returns `NULL`/empty rather than
erroring when unset, and an empty string never equals a real `tenant_id`, so a request that
somehow reaches a query without its session variables set sees **zero rows**, never all
rows. Verified live directly via `psql` as `landvault_app`: a bogus tenant and a *completely
unset* session variable both return `0` visible rows on `identity_users`, while the owning
role (RLS bypass via ownership, not policy) sees the real count.

Who sets these session variables, and when, is entirely the Unit-of-Work's job (§10) — RLS
policies themselves have no knowledge of HTTP requests, only of whatever
`current_setting()` returns for the current Postgres transaction.

## 8. Audit-Chain Architecture

Append-only, hash-chained log (`app.kernel.audit`, ADR-007). Every entry's SHA-256 hash
covers a canonical JSON serialization (`sort_keys=True`, no extraneous whitespace) of its own
`entry_id`, `action`, `resource_type`, `resource_id`, `decision`, `principal_id`, `payload`,
`created_at`, and the *previous* entry's hash (`prev_hash`) — chaining every entry to the one
before it back to a fixed genesis hash (64 zero characters). `verify_chain()` recomputes every
hash from stored content and confirms both the linkage and the recomputed value match what
was stored; tampering with any single field of any single historical entry breaks every
subsequent hash's recomputation, not just a status flag that could itself be forged.

Storage: `PostgresAuditStore` (`app.kernel.audit_postgres`) — lives in the kernel, not
Identity, since audit logging is cross-cutting. `append()` commits **immediately** (not just
flushes) — durability independent of whatever the rest of the request's transaction does. Two
binding mechanisms:

- **Per-request**: the normal path is for `audit()` calls made during route handling to go
  through whatever store is bound to the request's own transaction context... except this
  codebase deliberately does **not** bind the main request session as the audit store (see
  §10's Unit-of-Work note on why — binding it caused a second bug on top of the one it fixed).
- **Eager fallback** (`EagerPostgresAuditStore`, configured once at startup via
  `configure_eager_fallback`): opens, uses, and closes its own fresh session per call. This is
  what every `audit()` call in this codebase actually goes through today, including ones that
  happen *before* any per-request DB session exists at all (e.g. the PEP's `require_role`
  deny, which runs during dependency resolution).

`entry_id` is stored as `record.id.hex` on read (32-char, no hyphens) — not
`str(uuid.UUID(...))`'s canonical 36-char hyphenated form — because the *original* hash was
computed over the `.hex` representation at write time; the two are different strings for the
identical UUID value, and using the wrong one silently breaks every hash recomputation
without an exception (a real bug found and fixed during B1 verification).

At the database level, `landvault_app` has no `UPDATE`/`DELETE` grant on `audit_log` at all
(§6) — defense in depth on top of there being no application code path that would ever
attempt either.

## 9. Request Lifecycle

For a typical authenticated request (e.g. `POST /v1/admin/users/{id}/roles`), in order:

1. **CORS** (`CORSMiddleware`, outermost) — origin checked against
   `settings.cors_allowed_origins` (never a wildcard — §12 config validation).
2. **`SecurityHeadersMiddleware`** — wraps `call_next`, appends headers on the way out (§15).
3. **`RateLimitMiddleware`** — checked before the route even resolves dependencies, for any
   path prefix in `RATE_LIMITS` (§14); returns `429` immediately on overflow, never reaching
   FastAPI's routing/dependency layer.
4. **FastAPI dependency resolution**, in dependency order:
   a. `current_context_dep` (PEP) — verifies the JWT, hydrates the `ExecutionContext` from
      Postgres, binds it to the context var.
   b. `require_role(...)` (if the route needs it) — 403s and audits on failure.
   c. `get_db_session` (Unit-of-Work) — opens a fresh `AsyncSession`, sets the RLS session
      variable(s) from the now-resolved `ExecutionContext`.
   d. Service dependencies (`get_admin_service` etc.) — built fresh from that session.
5. **Route handler** — pure composition: parse the validated Pydantic body, call the
   application service, shape the response. No business logic lives in a router.
6. **Unit-of-Work commit/rollback** (§10) — on the way back out through `get_db_session`'s
   generator.
7. Response passes back out through the security-headers and CORS middleware.

## 10. Unit-of-Work Pattern

`app.kernel.uow.get_db_session` — one fresh `AsyncSession` per request, never reused or
shared across requests (a shared session across concurrent requests would corrupt RLS session
state and transaction boundaries). Before yielding the session to route/service code, it sets
exactly one of two Postgres session variables via `set_config(name, value, is_local=true)`
(transaction-scoped — a connection-scoped `SET` would leak into whatever unrelated request
later reuses the same pooled physical connection):

- `app.is_super_admin = 'true'` — for anonymous requests (registration/login, which are
  *creating* a tenant boundary, so there's nothing pre-existing to scope to) and for
  authenticated `super_admin` principals (explicitly cross-tenant by RLS policy design).
- `app.tenant_id = <ctx.tenant_id>` — every other authenticated request, strictly scoped to
  its own tenant.

On the way out: `HTTPException` propagating from the route/service is **committed**, not
rolled back — it represents a deliberate, correctly-handled application decision (401, 403,
409, ...), and side effects that led up to it (e.g. replay-detection's
`revoke_all_active_for_user()` immediately before raising 401) must survive. Any other,
genuinely unexpected exception still triggers a full rollback. This distinction was a real
bug fix during B1 verification — treating every raise as "roll back everything" silently
undid legitimate revocations.

`SET LOCAL var = $1` does **not** accept a bind parameter (confirmed live — `syntax error at
or near "$1"`, since `SET` isn't a regular parameterized statement); `set_config(name, value,
is_local)` is the parameterizable equivalent and is what's actually used everywhere in this
codebase, including the one-off super-admin bypass in `build_production_context_hydrator`
(which uses a literal `SET LOCAL app.is_super_admin = 'true'`, safe because it's a fixed
string with no interpolated value, not a counterexample to the bind-parameter rule).

## 11. Dependency Injection

FastAPI's native `Depends()` graph, no other DI framework or service locator. Two categories
of provider, both in `app.contexts.identity.dependencies`:

- **Per-request** (`get_user_repository`, `get_session_repository`, `get_auth_service`,
  `get_admin_service`) — each builds a fresh instance from the request-scoped `AsyncSession`
  (itself `Depends(get_db_session)`), specifically so nothing holds a stale session across
  requests or shares one across concurrent requests.
- **Singleton, configured once at startup** (`get_identity_provider`) — the Keycloak adapter
  is pure stateless HTTP calls per invocation, so a single shared instance is safe and
  avoids re-constructing an `httpx` client story per request. Bound via
  `configure_identity_provider()` in `create_app()`.

Tests override the per-request providers directly via `app.dependency_overrides` with
in-memory fakes (`tests/app_factory.py`) — `get_db_session` is consequently never invoked at
all in the unit-test suite, since nothing downstream of an override needs it.

## 12. Error Model

RFC 7807 (`application/problem+json`) for every error response, including truly unhandled
exceptions — there is no ad hoc `{"error": "..."}` shape anywhere (`app.kernel.errors`).
Three handlers registered on the `FastAPI` app: Starlette `HTTPException` (the common case —
401/403/404/409/422/429 etc., `detail` reflected as both `title` and `detail`),
`RequestValidationError` (422, Pydantic validation errors serialized into `detail`), and a
catch-all `Exception` handler (500, logs the full exception server-side via
`logger.exception`, returns a fixed, non-leaking `"An unexpected error occurred."` detail to
the client — no stack trace or internal detail ever reaches the response body).

## 13. Logging Model

Structured JSON to stdout (`app.kernel.logging.configure_logging`), one `JsonFormatter`
installed on the root logger: `timestamp` (UTC ISO-8601), `level`, `logger` (dotted module
name), `message`, plus `exception` (formatted traceback) when `exc_info` is present. Log
level is a required, fail-closed setting (`Settings.log_level`, one of `DEBUG`/`INFO`/
`WARNING`/`ERROR`, no implicit default beyond the declared `"INFO"`). No secrets are
deliberately logged anywhere in the current code (passwords/tokens are never passed to a
logger call) — this has not been exhaustively grepped as part of this freeze and is worth a
dedicated audit pass before production traffic.

## 14. Rate Limiting

In-process sliding-window limiter (`RateLimitMiddleware`, `app.kernel.security.
http_hardening`), explicitly documented as the *inner* layer of defense-in-depth — a real
deployment needs an edge/ingress limiter as the outer layer, since this one resets on process
restart and doesn't coordinate across replicas. Configured limits, keyed by path prefix:
`/v1/auth/login` → 10/60s, `/v1/auth/register` → 5/60s, `/v1/auth/refresh` → 30/60s. Overflow
returns `429` with a `Retry-After` header, before FastAPI routing/dependency resolution ever
runs.

**Client identification is `request.client.host` only — never `X-Forwarded-For`, at two
independent layers**, both required (found and fixed during B1 verification, §14 of the
verification report):

1. **Application layer** — `RateLimitMiddleware._client_ip()` and `auth_router._client_meta()`
   (used for session IP metadata, not just rate limiting) read only `request.client.host`.
   There is no configured trusted-reverse-proxy allowlist in this deployment, so the header
   is untrusted, full stop — not partially trusted, not trusted-if-it-looks-plausible.
2. **ASGI-server layer** — uvicorn is run with **`--no-proxy-headers`** in both
   `backend/Dockerfile`'s `CMD` and the documented local dev command (`CLAUDE.md`). Without
   this flag, uvicorn's own default (`proxy_headers=True`, `forwarded_allow_ips="127.0.0.1"`)
   rewrites `request.client` from a client-supplied `X-Forwarded-For` for any peer connecting
   from localhost — silently defeating layer 1 from *below* the application's own code. This
   was confirmed live: layer-1-only initially still showed a full bypass under adversarial
   testing until `--no-proxy-headers` was also applied.

If this deployment ever sits behind a real, trusted reverse proxy, re-enabling proxy-header
trust requires **both** an explicit `forwarded_allow_ips` naming that proxy specifically (not
re-enabling the default) **and** an ADR updating this section — it must not be re-enabled as
an incidental side effect of an unrelated infrastructure change.

## 15. Security Headers

`SecurityHeadersMiddleware` appends, without overriding a value a handler already set:
`Content-Security-Policy` (default: self-only for scripts/styles/connect, `object-src 'none'`,
`frame-ancestors 'none'`, `upgrade-insecure-requests`; overridable via `CSP_OVERRIDE` env var),
`Strict-Transport-Security` (`max-age=63072000; includeSubDomains; preload`),
`Cross-Origin-Opener-Policy: same-origin`, `Cross-Origin-Resource-Policy: same-origin`,
`Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
`Permissions-Policy` (denies camera/microphone/geolocation/payment/usb/etc. by default).

## 16. Docker Topology

Four services, `infra/docker/docker-compose.yml`, one shared `.env` (via `--env-file .env` on
the `docker compose` invocation — plain `env_file:` inside the compose file only injects
variables into containers, it does **not** feed `${VAR}` substitution within the compose YAML
itself):

- **`postgres`** — `postgis/postgis:16-3.4`, named volume `postgres_data`, healthcheck
  `pg_isready`, port `5432`.
- **`keycloak`** — `quay.io/keycloak/keycloak:26.0`, `start-dev` command (development mode —
  a production deployment needs a proper `start` configuration, not covered by this freeze),
  named volume `keycloak_data`, port `8080`.
- **`backend`** — built from `backend/Dockerfile` (`python:3.12-slim`, `pip install .`,
  `uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-proxy-headers`), depends on
  `postgres` being `service_healthy`, connects as `landvault_app` (`DATABASE_URL`) — never
  the owning `POSTGRES_USER` (`MIGRATIONS_DATABASE_URL`, used only for
  `alembic upgrade head`, run manually via `docker compose exec backend alembic upgrade
  head`, not automatically on container start), port `8000`.
- **`frontend`** — built from `frontend/`, depends on `backend`, port `3000`. Out of scope
  for this freeze (B1 is a backend/infrastructure freeze).

## 17. Environment Variables

Every variable in `.env.example` is **required** — `Settings` (`app.kernel.config`) has no
defaults for any security-relevant field, and Pydantic raises at startup (not at first use)
if one is missing, per the fail-closed rule (`docs/ENGINEERING_RULES.md` #2):

`ENVIRONMENT` (`development`/`staging`/`production` — gates `cookie_secure`),
`POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB` (owning role, migrations only),
`POSTGRES_APP_PASSWORD` (the `landvault_app` role's password), `MIGRATIONS_DATABASE_URL`,
`DATABASE_URL` (app role — what the running server actually uses), `CORS_ALLOWED_ORIGINS`
(comma-separated, wildcard rejected by a `field_validator` — verified live that
`CORS_ALLOWED_ORIGINS=*` raises a `ValidationError` at settings-load time, the app cannot
even start), `LOG_LEVEL`, `KEYCLOAK_ADMIN`/`KEYCLOAK_ADMIN_PASSWORD` (the Keycloak container's
own bootstrap admin, unrelated to the application client), `KEYCLOAK_REALM_URL`,
`KEYCLOAK_CLIENT_ID`/`KEYCLOAK_CLIENT_SECRET`, `KEYCLOAK_ADMIN_TOKEN_URL` (must target the
`landvault` realm, not `master`), `KEYCLOAK_ADMIN_API_URL`, `JWT_AUDIENCE`.

## 18. Startup Sequence

`create_app()` (`backend/app/main.py`), in order: load settings (fail-closed — a missing/
invalid value raises here, before anything else happens) → configure structured logging →
construct the `FastAPI` app → register `CORSMiddleware` → `configure_security()` (rate
limiter + security headers) → register RFC-7807 error handlers → build the async engine and
mount the health router → build the session factory, `configure_uow()`, and
`configure_eager_fallback(EagerPostgresAuditStore(...))` → build the JWKS provider and
`JwtVerifier`, `configure_pep()` with the production context hydrator → build and
`configure_identity_provider()` the Keycloak adapter → mount `auth_router` and
`admin_router`. Nothing in this sequence lazily initializes on first request — every
kernel/Identity dependency is bound before the app starts accepting traffic.

## 19. Health Checks

`GET /health/live` — always `200 {"status": "ok"}`, no dependency checks (process-alive
only). `GET /health/ready` — executes `SELECT 1` against the real database engine; any
exception (connection refused, auth failure, etc.) is caught and reported as `503
{"status": "not_ready", "reason": "database_unreachable"}` rather than propagating or being
swallowed into a false `200` — fail-closed readiness, per `docs/DOD.md`.

---

## Consequences

- B2 and later contexts get a stable, verified authentication/authorization/audit/RLS
  foundation to build on without re-litigating any of the above.
- Any change to the items in §1–19 — a new role, a different token TTL, an added
  `ExecutionContext` field, a changed RLS policy shape, a new rate limit, etc. — requires a
  new ADR that references this one, not a silent edit during B2+ feature work.
- The two known gaps called out above (no committed Keycloak realm export, §5; no dedicated
  secret-leak-in-logs audit, §13) are inherited as open items for whichever future ADR/task
  addresses them — they are not blocking this freeze, but they are not "done" either.
