# ADR-001 — Repository Strategy

**Status:** Accepted
**Date:** 2026-07-13

## Context

Two prior implementations of this product exist: `landsecure-registry` (a Base44-platform build, fully audited and found to have severe security/correctness defects across its RLS configuration, client-side-only authorization, and backend function logic) and `landverify-nigeria-101-NEW` (an Emergent-platform build, more rigorously architected but undermined by a parallel legacy auth system and several critical findings of its own). Both audits are preserved in `docs/audits/`.

We need to decide where the rebuild lives, and how the frontend, backend, and infrastructure code are organized relative to each other.

## Decision

1. **A fresh repository** (`aquasavannah-landvault`) hosts the rebuild. `landsecure-registry` is left untouched as a historical archive — not merged, not migrated, not deleted. Its audit reports are copied (not moved) into `docs/audits/` here for continuity.
2. **Monorepo structure**, not separate repos per layer:
   ```
   /frontend   — Next.js + TypeScript
   /backend    — Python + FastAPI, DDD/hexagonal bounded contexts
   /infra      — Terraform, Docker
   /docs       — this planning package
   ```

## Consequences

- A small team (or a single Claude-Code-driven contributor) can reason across the full stack in one session and one PR when a change genuinely spans frontend/backend (e.g. a new API contract field).
- One CI pipeline, one issue tracker, one source of truth for the whole product.
- Trade-off: a monorepo requires discipline to keep bounded-context boundaries real inside `/backend` rather than letting them blur just because they're in the same repo — this is why `docs/ENGINEERING_RULES.md` §4 requires explicit approval to cross bounded-context boundaries regardless of physical repo layout.
- `landsecure-registry` remaining untouched means its GitHub remote, CI workflows (including the previously-confirmed-broken `npm test`/`npm publish` pipeline), and Base44 auto-sync behavior are irrelevant to this repo and require no cleanup here.
