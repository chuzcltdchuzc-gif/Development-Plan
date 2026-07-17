# CLAUDE.md

AquaSavannah LandVault — a Nigerian land-registry/verification platform, rebuilt from scratch on Claude Code after full security/architecture audits of two prior implementations (`docs/audits/`). **Current status: B1 (Identity & Authorization) is complete, verified against real infrastructure, and frozen — see `docs/adr/ADR-009-b1-platform-freeze.md` and `docs/audits/B1_INFRASTRUCTURE_VERIFICATION.md`. B2 (tenant provisioning / role assignment / delegation) is in progress — see "B2 status" below.**

Docker Compose (Postgres + Keycloak + backend + frontend) has been booted end-to-end and is the normal way this repo is verified now — see `docs/audits/B1_INFRASTRUCTURE_VERIFICATION.md` for the full live-infrastructure validation this passed (migrations, RLS, JWT, rate limiting, audit chain, adversarial security checks). Cloud (staging/production) environments do not exist yet — Terraform has real version pins but no provider/resources (AWS vs. Azure is still open, see `docs/REBUILD_PLAN.md` §6).

## B1 status (Identity & Authorization) — frozen

Complete and verified against live infrastructure (real Docker/Postgres/Keycloak, not in-memory fakes) — see `docs/adr/ADR-009-b1-platform-freeze.md` for the full frozen architecture description (auth flow, JWT/refresh lifecycle, RLS model, audit-chain architecture, Unit-of-Work, rate limiting, etc.) and `docs/audits/B1_INFRASTRUCTURE_VERIFICATION.md` for the evidence. **Any change to what ADR-009 describes requires a new ADR referencing it — do not silently modify frozen B1 behavior while building B2+.**

## B2 status (tenant provisioning / role assignment / delegation) — in progress

**Slice 1 — tenant membership invitations (done, verified against live infrastructure):** a governance-role principal (`super_admin`/`surveyor_general`/`compliance_officer`) invites an email into their own tenant at a role no higher than their own rank (reuses `assign_role`'s hierarchy check exactly), via `POST /v1/admin/invitations`. The invitee redeems an opaque, hashed, expiring (7-day) token via `POST /v1/auth/invitations/accept` to complete registration directly into the inviter's tenant with the invited role. New table `identity_invitations` (migration `0004`), same RLS/grant shape as `identity_users`. No email-delivery integration exists yet — the plaintext token is returned once to the inviter to relay out-of-band; this is a known, documented limitation, not a bug.

**Not yet built:** invitation revocation/listing endpoints (natural next slice), delegation wired into the PDP (no existing spec — will need its own design pass before implementation).

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
/backend    — Python + FastAPI (B0 kernel in app/kernel/; app/contexts/identity/ has B1 + B2 slice 1)
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
.venv/Scripts/uvicorn app.main:app --reload --no-proxy-headers   # run locally; needs env vars, see .env.example
# --no-proxy-headers: no trusted reverse proxy is configured (ADR-004) — without
# this flag uvicorn trusts X-Forwarded-For from 127.0.0.1 by default and rewrites
# request.client, defeating the app's own anti-spoofing rate-limiter logic.
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
docker compose --env-file .env -f infra/docker/docker-compose.yml up --build
# --env-file is required: plain env_file: in the compose YAML only injects
# vars into containers, it does not feed ${VAR} substitution in the YAML itself.
```
Migrations against the live database (owning role, not the app's least-privilege role):
```
docker compose --env-file .env -f infra/docker/docker-compose.yml exec backend alembic upgrade head
```
