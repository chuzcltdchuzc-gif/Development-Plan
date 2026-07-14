# CLAUDE.md

AquaSavannah LandVault — a Nigerian land-registry/verification platform, rebuilt from scratch on Claude Code after full security/architecture audits of two prior implementations (`docs/audits/`). **Current status: B0.0 (dev environment scaffold) done; B1 (Identity & Authorization) application/domain logic done and fully tested — see "B1 status" below for exactly what that does and doesn't cover.**

Docker Compose has never been booted end-to-end in any session this was built in — no Docker daemon has been available in the environment. The backend/frontend were instead verified directly (real `uvicorn`/`npm` processes, not just TestClient), and the compose YAML was schema-checked, but neither substitutes for an observed `docker compose up`. Cloud (staging/production) environments do not exist yet — Terraform has real version pins but no provider/resources (AWS vs. Azure is still open, see `docs/REBUILD_PLAN.md` §6).

## B1 status (Identity & Authorization)

**Done and verified (27/27 tests pass, including all 11 acceptance criteria the Operator specified — anonymous-blocked, expired-JWT-rejected, refresh-rotates, logout-invalidates, stolen-refresh-rejected, role-escalation-impossible, self-registration-cannot-assign-roles, policy-engine-default-deny, CORS-rejects-unknown-origins, rate-limiting-enabled, all-events-audited; ruff + mypy clean):**
- Kernel PDP/PEP/PIP authorization engine, ported closely from `landverify-nigeria-101-NEW`'s audited-sound design (real reference code read, not just the audit's prose)
- JWT verification against a JWKS provider (Keycloak-shaped, real RS256/kid flow)
- Hash-chained append-only audit log with a real `verify_chain()`
- Security headers + sliding-window rate-limit middleware
- Identity domain (User/Session aggregates), role hierarchy with a real assignment-time check (fixes the exact `assign_role` self-escalation defect the Emergent audit found — no hierarchy check existed there at all)
- AuthService/AdminService, `/v1/auth/*` + `/v1/admin/*` routes

**Scope of that verification:** Keycloak and Postgres are swapped for in-memory fakes at the port boundary (`tests/fakes/`, `tests/app_factory.py`) — this is real business logic under test, not mocked-out logic, but the *adapters* to the actual external systems are separately real code (below) that hasn't been run against live infra.

**Written but NOT yet run against live infrastructure** (no Docker/Postgres/Keycloak available in this environment):
- `app/contexts/identity/adapters/postgres_repositories.py` + `orm.py` — Postgres repositories/ORM models
- `migrations/versions/0001_identity_and_audit.py` — Alembic migration, RLS policies for tenant isolation + an append-only guarantee on `audit_log` (UPDATE/DELETE revoked at the grant level)
- `app/contexts/identity/adapters/keycloak.py` — Direct Access Grant + JWKS + admin user-creation calls

**Not wired into `app/main.py` yet, and deliberately so:** the Identity routes aren't mounted on the production app. Doing that correctly requires a per-request database session (fresh `AsyncSession` per request, with `SET LOCAL app.tenant_id` set from the `ExecutionContext` for the RLS policies above to do anything) — a Unit-of-Work pattern that doesn't exist yet and is a cross-cutting kernel concern every future bounded context will also need, not something to bolt on as a one-off for B1. Wiring it in without that pattern would mean sharing one `AsyncSession` across concurrent requests, which is a correctness bug, not just an untested path. This is the concrete next step before B1 is deployable.

This file is the always-loaded operational summary. It is a pointer, not the source of truth — if anything here ever conflicts with the documents it points to, **those documents win.**

## The 5 non-negotiable rules (full detail: `docs/ENGINEERING_RULES.md`)

1. **No new entity/table without an RLS/authorization policy in the same commit.** (Base44 shipped wallet/invoice entities with unconditional public update access — this is the exact bug class that rule prevents.)
2. **No permissive fallback default on any security-relevant env var.** Missing config must fail startup, never silently degrade to an insecure default. (Emergent's CORS wildcard-with-credentials and hardcoded signing-secret fallback.)
3. **Exactly one authorization path: the PDP/PEP/PIP engine.** No parallel/legacy auth system, no unguarded dev-login, ever — not even temporarily. (Emergent's dual auth system + unauthenticated admin bypass.)
4. **Every scoring/validation function fails safe:** zero/missing data → low or neutral result, never a passing score. (Base44's trust engine reported 100/A+ with zero real evidence.)
5. **Never mark something complete without having actually observed it pass.** Static code inspection is not evidence — run the test, see it pass.

## Where to look for more

| Need | Go to |
|---|---|
| The technical build plan (stack, 13 bounded contexts, stages, milestones) | `docs/REBUILD_PLAN.md` |
| Process/quality gates per phase, the Claude Code Loop, standing review questions | `docs/PHASE_GATES.md` |
| Definition of Done (Feature / Sprint / Product tiers) | `docs/DOD.md` |
| Full engineering rules, incl. when to stop and ask a human | `docs/ENGINEERING_RULES.md` |
| Why a specific architectural decision was made | `docs/adr/` |
| The audit findings everything above is derived from | `docs/audits/` |

## Repo layout

```
/frontend   — Next.js + TypeScript (F0 shell landed; bounded-context UI stages land per docs/REBUILD_PLAN.md §3)
/backend    — Python + FastAPI (B0 kernel landed in app/kernel/; one folder per bounded context as B1+ land)
/infra      — Terraform (version-pinned baseline, no provider yet), Docker (infra/docker/docker-compose.yml)
/docs       — this planning package
```

## Working model

Sprints are one per bounded context (13 total, dependency-ordered per `docs/REBUILD_PLAN.md` §1), each gated through the Claude Code Loop in `docs/PHASE_GATES.md` and signed off against `docs/DOD.md` before merge. Do not start a sprint whose dependencies (per the bounded-context ordering) aren't yet Sprint Done.

## Build/test/run commands

**Backend** (from `/backend`):
```
python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"
.venv/Scripts/pytest                 # unit tests
.venv/Scripts/ruff check .           # lint
.venv/Scripts/mypy app tests         # type check
.venv/Scripts/uvicorn app.main:app --reload   # run locally; needs env vars, see .env.example
```

**Frontend** (from `/frontend`):
```
npm install
npm run typecheck
npm run lint
npm run build && npm run start       # or `npm run dev` for local development
```

**Full stack** (from repo root, requires Docker):
```
cp .env.example .env   # then fill in real values
docker compose -f infra/docker/docker-compose.yml up --build
```
Not yet verified in any session — see the status note above.
