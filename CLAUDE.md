# CLAUDE.md

AquaSavannah LandVault — a Nigerian land-registry/verification platform, rebuilt from scratch on Claude Code after full security/architecture audits of two prior implementations (`docs/audits/`). **Current status: Phase 0/1 (Enterprise Planning / System Architecture) — planning package complete, Architecture v1.0 not yet frozen. No implementation sprint has started.**

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

## Repo layout (once code lands)

```
/frontend   — Next.js + TypeScript
/backend    — Python + FastAPI, one folder per bounded context
/infra      — Terraform, Docker
/docs       — this planning package
```

## Working model

Sprints are one per bounded context (13 total, dependency-ordered per `docs/REBUILD_PLAN.md` §1), each gated through the Claude Code Loop in `docs/PHASE_GATES.md` and signed off against `docs/DOD.md` before merge. Do not start a sprint whose dependencies (per the bounded-context ordering) aren't yet Sprint Done.

Build/test/run commands land here once Phase 2 (Development Environment) is complete.
