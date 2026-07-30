# ADR-025 — Supabase Platform Baseline (Identity, Storage & Compute)

**Status:** Proposed — 2026-07-30.

**Supersedes:** `docs/adr/ADR-004-authentication-authorisation-model.md` §1 only (the Keycloak/Auth0
identity-provider choice); `docs/adr/ADR-024-delivery-platform-and-infrastructure-decisions.md` D2
(Keycloak, confirmed) and D4 (AWS compute, interim) in full.

**Explicitly does not modify:** `ADR-002` (System Architecture — FastAPI/DDD-hexagonal application
architecture, 13 bounded contexts); `ADR-004` §2–§5 (the PDP/PEP/PIP policy engine, single
authorization path, role-hierarchy check, rate limiting — retained in full); `ADR-015` (registry
mutation authorization); `ADR-022` (spatial authorization model); `ADR-024` D3 (Paystack). `ADR-024`
D1 (`StoragePort`/R2) is **refined**, not superseded — see E3.

**Date:** 2026-07-30

**Scope:** Records the Governance Authority's decision to standardise forward-looking platform
selection on Supabase for identity, database hosting, storage and narrowly-scoped lightweight
backend execution, while leaving the existing FastAPI/DDD-hexagonal application architecture and
its authorization design completely intact. **This is an infrastructure and identity-substrate
decision, not an application-runtime rewrite** — confirmed explicitly this session before drafting,
given how large the alternative reading would be.

**Constitutional anchors:** Article VII §2–§4 (WORM grade declared; escalation without code
change); Article X §3 (the single authorisation path); Article X §5–§6 (ports; seams declared);
Article XI §2–§4 (observed not assumed; reversible; governed dependencies); Article XIV (amending
an accepted decision is a governed act — this ADR is that act, superseding named sections of
ADR-004 and ADR-024 rather than editing them in place).

## Context

`ADR-004` (2026-07-13) left Keycloak vs. Auth0 as an open sub-decision, recommending Keycloak.
`docs/EXECUTION_PLAN.md` §4.3 later confirmed Keycloak, and `ADR-024` (2026-07-30, this session)
recorded that confirmation as D2, alongside an AWS compute decision as D4. Separately, this session
received a governance directive ("Revision I") standardising the forward platform on Supabase —
Supabase Auth, Supabase-hosted PostgreSQL with Row-Level Security, Supabase Storage, and Supabase
Edge Functions for narrow backend needs — with Vercel as frontend hosting and Docker retained for
local development only.

Two things this ADR does **not** do, confirmed explicitly before drafting:

1. It does not retire the PDP/PEP/PIP policy-evaluation engine `ADR-004` §2–§5 established. The
   source directive's phrase "PostgreSQL RLS is the authoritative authorization model" is read, per
   this session's clarification, as *RLS is the authoritative last-mile database enforcement layer*
   — exactly the role `ADR-004` §2 already gave it ("two independent layers... so a caller who
   forgets to populate one still cannot bypass the other") — not as "the PDP is retired." `ADR-015`
   and `ADR-022`'s authorization semantics are PDP-layer decisions and are unaffected.
2. It does not supersede `ADR-002`. The source directive's "Supabase Edge Functions are the backend
   execution environment" is read, per this session's clarification, as **additive**: the existing
   FastAPI backend (13 bounded contexts, 148 passing tests) continues as the API layer, now pointed
   at Supabase-hosted Postgres/Auth/Storage; Edge Functions are reserved for new, narrow pieces
   (webhook receivers, lightweight triggers) that do not belong in the main application. Reading it
   as a full backend-language rewrite would be a materially larger claim than the directive's own
   framing ("Backend: Supabase" sits beside "Application: Next.js/React," not in place of an
   existing, tested, frozen application layer) and was not what was confirmed this session.

## Decision

### E1 — Identity: Supabase Auth supersedes Keycloak as the forward target

Supabase Auth is now the authoritative identity provider for future work, superseding `ADR-004` §1
and `ADR-024` D2. Keycloak was not a wrong decision when made — it was recommended in good faith on
2026-07-13, confirmed on 2026-07-30, and implemented and verified (Docker Compose service, realm
exported as code, live-infrastructure validation per `docs/audits/B1_INFRASTRUCTURE_VERIFICATION.md`).
That work is **preserved as historical record, not erased.**

Existing Keycloak artifacts — the `docker-compose` service, `infra/keycloak/realm-landvault.json`,
the `KEYCLOAK_*` environment variables, and any backend code wired to Keycloak's JWKS endpoint —
are preserved until governance decides to archive or remove them. This ADR does not delete or
archive any of them; it only stops treating Keycloak as the target for *new* identity work.

**What this ADR does not decide:** the migration mechanics — when existing sessions move, whether
there is a dual-running period, how first-login provisioning changes under Supabase Auth. That is
implementation work for whichever phase undertakes it, gated by its own test matrix. This ADR
records the target, not the cutover plan.

### E2 — Authorization: PDP/PEP/PIP retained in full; RLS is the last-mile layer, unchanged in kind

`ADR-004` §2–§5 — the fail-closed policy engine, the single authorization path, the role-hierarchy
check, rate limiting — is retained in full and untouched by this ADR. Postgres RLS continues
exactly the role `ADR-004` §2 already gave it: one of two independent enforcement layers, not a
replacement for the PDP. The only change under this ADR: the PEP's JWT verification target moves
from Keycloak's JWKS endpoint to Supabase Auth's, and RLS's session-scoping variables continue to
be set by the same request-scoped mechanism, now against Supabase-hosted Postgres rather than the
current Docker Postgres instance. `ADR-015`'s creator-or-governance mutation check and `ADR-022`'s
spatial authorization model are PDP-layer decisions; neither is touched.

### E3 — Storage: Supabase Storage becomes the primary adapter; Cloudflare R2 remains the WORM-grade escalation adapter

`ADR-024` D1's `StoragePort` abstraction is unchanged in shape and is **refined, not superseded**:
Supabase Storage is now the primary/default adapter behind `StoragePort` for ordinary
document/evidence storage, and Cloudflare R2 (Bucket Locks, `governance` WORM grade) remains the
adapter for sealed evidence needing immutable retention — exactly the "future immutable archive"
role `EXECUTION_PLAN.md` §4.2 and `ADR-024` D1 already reserved for a WORM-grade backend. No
bounded context calls a storage SDK directly (Article X §5, restated, unchanged); escalating
between adapters remains a swap behind `StoragePort`, without a code change to any calling context
(Article VII §3). Current implementation status, verified in `ADR-024`: no `StoragePort` code or
adapter of any kind exists yet — this refinement applies before any implementation.

### E4 — Compute: Supabase (Postgres + Edge Functions) and Vercel supersede the AWS interim decision; Docker becomes local-only

`ADR-024` D4's AWS compute decision is **superseded**. The forward platform baseline is: Vercel for
frontend hosting, Supabase for backend database hosting and narrowly-scoped backend execution
(Edge Functions), and Docker retained exclusively for local development, testing, and service
orchestration — not as a production target.

**Confirmed explicitly this session: this does not supersede `ADR-002`.** The existing FastAPI
backend (all 13 bounded contexts, 148 passing tests) continues as the API layer, now pointed at
Supabase-hosted Postgres/Auth/Storage instead of self-hosted equivalents. Supabase Edge Functions
are additive — reserved for new, narrow needs that do not belong in the main FastAPI application —
not a replacement runtime for the existing bounded contexts. Where the existing FastAPI backend is
itself deployed once a production compute target is chosen for *it* is future infrastructure work
this ADR does not decide.

`infra/terraform/versions.tf`'s AWS provider block is preserved as a historical artifact of the
superseded D4 decision, per the Technology Replacement Principle this ADR restates in E6 — it is
not deleted by this ADR. Its removal or replacement is separate follow-up work.

### E5 — Payments and secrets manager: unaffected, restated for completeness

Paystack-only-for-pilot-one (`ADR-024` D3) is unaffected. The secrets manager (`ADR-024` D5) remains
**undecided**. The prior implicit candidate (AWS Secrets Manager, contingent on AWS remaining the
compute provider) no longer applies now that AWS is superseded as the compute provider (E4);
Supabase's own secrets/vault primitives become a candidate to evaluate, but this ADR does not
decide it and does not manufacture a rationale to make this section look more finished than it is.

### E6 — Technology Replacement Principle (restated, not duplicated)

This ADR is itself an instance of the Technology Replacement Principle recorded in `ADR-024`:
named technologies are implementation choices, not constitutional requirements; they may be
replaced provided stable contracts and architectural intent survive the replacement; and a
migration is governed by a superseding ADR, never a silent edit. This ADR is that superseding ADR
for the sections it names above. Its text is not duplicated a second time here.

## Alternatives considered

- **Silently editing `ADR-004`/`ADR-024`'s Keycloak/AWS text in place to read "Supabase"** —
  rejected: overwrites the historical record of what was actually decided and implemented (realm
  export, live-infrastructure verification), which the standing rule against overwriting history
  exists to prevent.
- **Deferring this decision until a full backend-runtime migration ADR is also ready** — rejected:
  identity/storage/compute substrate and application-runtime language are independent decisions
  (confirmed this session — `ADR-002` is untouched), so there is no reason to block the substrate
  decision on a runtime decision nobody has proposed making.

## Relationship to the frozen baseline

- **ADR-002** — untouched. FastAPI/DDD-hexagonal architecture, 13 bounded contexts, unchanged.
- **ADR-003** — untouched in substance (Postgres remains the database engine); its hosting
  substrate becomes Supabase-managed Postgres once implemented, a hosting detail, not an
  engine change.
- **ADR-004** — §1 (Keycloak/Auth0 choice) superseded by E1. §2–§5 (PDP/PEP/PIP, single auth path,
  hierarchy check, rate limiting) unchanged, per explicit confirmation this session.
- **ADR-006** — untouched.
- **ADR-009 / ADR-012 / ADR-017** (B1/B2/B3 platform freezes) — the frozen descriptions of what was
  built and verified (Keycloak-based JWT, Docker Postgres) are preserved unchanged as historical
  fact. Re-verifying the same guarantees against Supabase Auth/Postgres is future implementation
  work, not performed by this ADR and not assumed complete.
- **ADR-013 through ADR-023** — untouched; none depend on the identity provider or compute
  substrate in a way this ADR touches.
- **ADR-024** — D1 (`StoragePort`/R2) refined by E3, not superseded. D2 (Keycloak) superseded by
  E1. D3 (Paystack) unaffected. D4 (AWS compute) superseded by E4. D5 (secrets manager) restated,
  still undecided.

## Consequences

- Keycloak, the AWS compute decision, and their related infrastructure remain in the repository as
  preserved historical artifacts pending a future archival decision — nothing is deleted by this
  ADR.
- Whichever phase implements this decision must **re-verify, not assume**, every guarantee
  `ADR-009`/`ADR-012`/`ADR-017` recorded against Keycloak/Docker-Postgres once the same guarantee is
  asserted against Supabase Auth/Postgres (Article XI §2).
- `ADR-024` remains at status Proposed, held pending this ADR, per this session's explicit
  direction; `ADR-024` D2/D4 are cross-referenced to this ADR (see that document). `ADR-024` may now
  be considered for acceptance.
- No code is authorised or implied by this ADR. It is a target-state decision record, not an
  implementation instruction.
