# LandVault Architecture Handbook

**Version 1.1**

**Type:** Operational engineering reference. **Not an ADR. Not the Constitution — LV-000
(`docs/LV-000-constitution.md`, adopted 2026-07-26) is superior to this Handbook in the platform's
documentation hierarchy (LV-000 Article II, Section 2) and this Handbook does not restate its
content. Not a PRD. Not a TRD.** This handbook consolidates, cross-references, and interprets the
architectural decisions this platform has already made — it decides nothing new, overrides
nothing, and duplicates no ADR's own text. Where this handbook and any ADR appear to differ, **the
ADR is authoritative** (LV-000 Article VI, Section 3 ratifies this); that would be a defect in
this handbook to fix, never a reason to treat the handbook as a second source of truth. Where this
handbook and LV-000 itself appear to differ, **LV-000 is authoritative** — that would likewise be
a defect in this handbook to fix.

**Date:** 2026-07-24 (v1.0); updated 2026-07-26 (v1.1, LV-000's adoption)

**Documentation programme only.** No production code, migration, API change, bounded context, or
ADR amendment is introduced by this document. This handbook does not authorize B4 Slice 3 or any
capability named in Part VIII.

**Audience:** every future developer, architect, reviewer, security assessor, government partner,
and technical auditor who needs to understand how LandVault is built and governed, without
reading all thirty-plus governance documents individually first.

---

## How to use this handbook

Each Part below states a principle or explains a structure, then points to the specific document
that is authoritative for its detail. Read this handbook first to orient; read the linked
document when you need the actual decision, its reasoning, its alternatives-considered, or its
exact technical content. This handbook is updated as new ADRs and programmes land (see the
Maintenance Recommendations at the end); it is never the place a new decision is first made.

---

# PART I — PLATFORM PHILOSOPHY

## Why LandVault exists

LandVault exists because two prior implementations of this same product were audited in full —
architecture, security, and correctness — before a single line of this rebuild was written
(`docs/audits/`). Base44 was feature-complete but insecure by default: client-side-only
authorization, missing or permissive row-level security on numerous entities (including a
self-service financial-fraud vector on organization wallets), and "trust validation" functions
that reported a passing score regardless of the data behind them. Emergent was a genuinely
well-architected authorization engine (its design is retained here, `docs/adr/
ADR-004-authentication-authorisation-model.md`) undermined by an entirely separate, undocumented
legacy auth system running alongside it and an unauthenticated admin-login bypass. Every rule in
`docs/ENGINEERING_RULES.md` (Part IV) and every non-negotiable in `docs/DOD.md` traces to a
specific, confirmed finding from one of those two audits — this platform's discipline is not
generic best practice; it is a direct, named response to how this exact product has failed twice
before.

## Platform versus application

LandVault is not being built as a single application with features bolted on as they're needed.
It is being built as a **platform**: a Platform Kernel (identity, authorization, audit, request
lifecycle — Part II) that every bounded context depends on identically, and a growing set of
bounded contexts (Registry, Spatial, and beyond) that each own one clear domain responsibility and
communicate only through explicit contracts (ports), never by reaching into one another's data.
This is why B4 (Spatial Intelligence) was treated as an entirely new programme with its own
discovery, threat model, and ADR sequence, even though it was already named as context #3 in the
original 13-context plan (`docs/REBUILD_PLAN.md`) — being *planned for* is not the same as being
*architected*, and this platform does not skip the difference.

## Digital trust infrastructure

LandVault's product purpose (per `docs/REBUILD_PLAN.md`'s own framing) is a land-registry and
verification platform for Nigeria — parcel registration, GIS-backed spatial validation, evidence
chain-of-custody, community/traditional-authority attestation, survey network management,
inheritance/customary-law resolution, and an economic/billing layer, all built around an
explainable, continuously-recalculated per-parcel trust score (the future Trust Engine, B7). The
architecture exists to make that trust score *earn* its explainability — every signal it will ever
consume (geometry validity, evidence integrity, survey completion, community attestation) must
itself be produced by a real, auditable, fail-safe mechanism, never a function that reports a
passing result because reporting failure was never wired up. This is the direct architectural
answer to Base44's "always passes" trust engine defect (`docs/ENGINEERING_RULES.md` rule 3).

## Evidence-first philosophy

Nothing in this platform is trusted merely because it was submitted. A parcel's geometry does not
exist until it passes real structural validation (`docs/adr/ADR-018-...md`'s
Validate-Then-Store doctrine); a mutation does not happen until the caller's specific authority
over that specific resource is checked, not merely their role (`docs/adr/
ADR-015-...md`/`ADR-022-...md`); every mutation, permitted or denied, is written to an
append-only, hash-chained audit log before the response is returned (`docs/adr/
ADR-007-audit-trail-evidence-model.md`). Evidence — of validity, of authority, of what happened —
is produced structurally, not asserted.

## Government-grade architecture

LandVault is being built to a bar suitable for government procurement, land-administration
partnership, and eventual multi-country deployment — not a bar of "works for a demo." This shows
up concretely: every new entity ships with its authorization policy in the same commit
(`docs/ENGINEERING_RULES.md` rule 1); every schema change is reversible and tested in staging
before production (rule 6); nothing is marked complete without being observed to pass, live,
against real infrastructure (rule 7). These are not aspirational — every programme from B1 through
B4 Slice 2 has been live-verified against real PostgreSQL, real Keycloak, and a real container
deployment before being considered done (see each programme's own verification checklist).

## Platform Kernel philosophy

The kernel is deliberately business-neutral. It knows about principals, tenants, roles,
delegation, sessions, audit entries, and HTTP request/response shape — it knows nothing about
parcels, geometry, evidence, or trust scores. Every bounded context depends on the kernel; the
kernel never depends on, imports from, or special-cases any bounded context. This is what makes
"one authorization path, no parallel auth system" (`docs/ENGINEERING_RULES.md` rule 1) actually
enforceable rather than aspirational — there is exactly one PDP/PEP/PIP engine, and every context's
authorization decision flows through it.

## Bounded Context philosophy

Each bounded context owns exactly one domain responsibility and is the only code permitted to
mutate its own aggregates. Registry owns parcel identity; Spatial owns geometry; neither imports
the other's domain models, repositories, or validation engines — they communicate only through
named ports (`docs/adr/ADR-016-...md`, `ADR-019-...md`), wired together exclusively at the
composition root (`app/main.py`/`tests/app_factory.py`), never inside either context's own code.
Part III explains this pattern in full, with the Registry↔Spatial seam as its worked example.

## Long-term ecosystem vision

The contexts built so far (Identity, Registry, Spatial) are the foundation a much larger ecosystem
is meant to stand on: evidence and chain-of-custody, survey-network management, a trust-scoring
engine, community/traditional-authority attestation, inheritance and customary-law resolution, an
economic/billing layer, and eventually a platform-intelligence layer that can reason *across*
these contexts under tight, audited, narrow authority (`docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md`,
Part II/VIII). None of this later ecosystem is permitted to compromise the tenant-isolation
default every context beneath it already established — new capability extends the platform's
trust model, it never quietly relaxes it.

## What LandVault is not

- **Not a monolithic application.** There is no single codebase-wide "do everything" service —
  each bounded context is its own vertical slice of domain, application, adapters, and API, wired
  together only through ports (`docs/adr/ADR-002-system-architecture.md`).
- **Not a single aggregate.** `Parcel` and `ParcelGeometry` are deliberately two separate
  aggregates in two separate bounded contexts, each with its own lifecycle, even though they
  describe "the same land" from a product perspective (`docs/adr/ADR-018-...md`'s own reasoning
  for why geometry is not a field on `Parcel`).
- **Not merely a registry.** Registry (B3) is one bounded context among (eventually) thirteen or
  more — it is foundational, not the whole platform.
- **Not merely a marketplace.** Economic/billing capability (`docs/REBUILD_PLAN.md` context #10,
  and the broader Marketplace scoping question recorded in `docs/
  MARKETPLACE_DISCOVERY_AND_PLANNING.md`) is one future programme among several, not this
  platform's organizing principle.

LandVault is, instead, a **trusted digital infrastructure platform**: a kernel of identity,
authorization, and audit; a growing set of independently-owned domain contexts; and, increasingly,
a layer of platform intelligence that can observe across those contexts under constitutional
constraint, never by default.

---

# PART II — PLATFORM ARCHITECTURE

## The complete architecture, top to bottom

```
Platform
│
└── Platform Kernel                    (ADR-002, ADR-009 — auth, audit, RLS, request lifecycle)
    │
    ├── Identity                        (B1 — ADR-004, ADR-009/010/011/012 — tenants, users,
    │                                     roles, delegation)
    ├── Registry                        (B3 — ADR-013/014/015/016/017 — Parcel aggregate,
    │                                     parcel identity, ownership, atomic numbering)
    ├── Spatial                         (B4 — ADR-018/019/021/022 — ParcelGeometry aggregate,
    │                                     geometry validation, per-tenant authorization,
    │                                     conflict detection [proposed])
    ├── Evidence                        (B5 — not yet built, `docs/REBUILD_PLAN.md` context #4)
    ├── Audit                           (cross-cutting — ADR-007, used by every context above)
    ├── Authorization                   (cross-cutting — the PDP/PEP/PIP engine, ADR-004, used
    │                                     by every context above)
    ├── Organizations                   (Identity's own Tenant aggregate, ADR-010 — the
    │                                     multi-tenancy boundary every context above is scoped to)
    │
    └── Platform Intelligence           (cross-cutting services, not a bounded context —
        │                                `docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md`)
        ├── Conflict Engine              (ADR-021/SCDS-001 — proposed, unimplemented)
        ├── Fraud Engine                 (not designed)
        ├── Risk Engine                  (not designed — the Trust Engine, B7, is this
        │                                 platform's first example of this shape)
        ├── AI Engine                    (not designed)
        ├── Analytics Engine             (not designed)
        └── Compliance Engine            (not designed)
    │
    └── Future Programmes                (Part VIII — Marketplace, Enterprise, Government, AI,
                                           Developer Platform, API Ecosystem, Compliance,
                                           Analytics — none authorized)
```

## How bounded contexts communicate

**Only through explicit, named ports — never by importing another context's domain model,
repository, or adapter, and never by direct cross-context database access
(`docs/ENGINEERING_RULES.md`'s "no direct database access across bounded contexts" principle,
Part IV).** The concrete, load-bearing example this platform has actually built: Registry depends
on `GeometryPort` (`docs/adr/ADR-016-...md`, amended `ADR-019-...md`) — a `Protocol` it defines
and owns. Spatial supplies the first real implementation of that protocol
(`RealGeometryAdapter`), but Registry's own code never imports anything from
`app.contexts.spatial`. The two are wired together exclusively in the **composition root**
(`app/main.py` in production, `tests/app_factory.py` in tests) via FastAPI's
`dependency_overrides` mechanism — the one place in the codebase permitted to know about both
contexts simultaneously. This pattern is not incidental; it is how every future cross-context
integration in this platform is expected to be built.

## Ownership boundaries

Every aggregate has exactly one owning bounded context, and only that context's application
services may construct or mutate it:

- **`Parcel`** (identity, tenant scope, ownership history, `geometry_reference`) — owned by
  Registry (`docs/adr/ADR-013-...md`).
- **`ParcelGeometry`** (boundary WKT, validation, ACTIVE/SUPERSEDED lifecycle) — owned by Spatial
  (`docs/adr/ADR-018-...md`).
- **`User`/`Tenant`/`Delegation`** — owned by Identity (`docs/adr/ADR-009/010/011-...md`).

No context ever reaches into another's table directly. Where a context genuinely needs
information another context owns, it depends on a narrow, purpose-built port that returns only
the minimum needed — never a raw session or a shared ORM model. `ParcelExistencePort` is the
concrete example: Spatial needs to know a parcel's `tenant_id`/`created_by`/`status` to enforce
ADR-022's authorization model, so it depends on that one, narrow, read-only port — never on
Registry's `Parcel` domain object or `ParcelRepository` directly.

## Contract-first integration

Every cross-context dependency is defined as a `Protocol` (a structural type) before any concrete
adapter is written, and the *interface* is what a consuming context depends on, never a concrete
implementation. When an interface needs to change (as `GeometryPort` did, `docs/adr/
ADR-019-...md`), that change is itself a governed act — a formal amendment ADR, not a silent
signature edit — even though the interface belongs to the *consuming* context (Registry) and the
change was driven by the *supplying* context's (Spatial's) needs.

## Why Registry never owns Spatial, and Spatial never owns Registry

Both contexts describe "the same land," but from genuinely different domain perspectives with
genuinely different lifecycles and genuinely different validation rules — Registry's concern is
*identity and ownership* (who registered this parcel, who currently owns it, what is its
registry number); Spatial's concern is *boundary correctness* (is this a well-formed polygon, does
it conflict with another). `docs/adr/ADR-018-...md` explicitly rejected storing geometry as a
field on `Parcel` for exactly this reason: doing so would force one aggregate's persistence and
validation lifecycle onto two conceptually independent concerns, and would make Registry's own
code dependent on GIS-aware types it has no business needing. The two-aggregate,
two-bounded-context split is a deliberate DDD decision (Part III), not an accident of build order.

## Platform Intelligence, in brief

A cross-cutting services layer — never a bounded context — that reads across bounded contexts (and,
narrowly, across tenants) to produce a finding, signal, or score *about* the domains beneath it,
without ever owning or mutating their aggregates. Every capability under this layer must satisfy
`docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md`'s four-part test (cross-context/cross-tenant read;
produces a finding, never a domain mutation; uses exactly one named Controlled Platform Authority
exception; downstream consumers see only a narrow, pre-scoped signal, never the raw cross-context
read). Spatial Conflict Detection (ADR-021/SCDS-001, proposed) is this layer's first designed
instance; the Trust Engine (B7, unbuilt) is retroactively recognized as its first example.

---

# PART III — DOMAIN-DRIVEN DESIGN

This platform's DDD vocabulary, illustrated exclusively with contexts already built — **this
section explains existing architecture; it invents nothing.**

## Bounded Contexts

A bounded context is a self-contained vertical slice — domain, application, adapters, API — that
owns one coherent set of business rules and their own ubiquitous language. This platform's built
contexts: **Identity** (`app/contexts/identity/`), **Registry** (`app/contexts/registry/`),
**Spatial** (`app/contexts/spatial/`). Each has an identical internal shape (below), and none
imports another's `domain/` or `adapters/` package directly.

## Aggregates

The one true root of consistency for a cluster of related data, with its own constructor-enforced
invariants and its own guarded mutation methods. **`Parcel`** (Registry): tenant-scoped identity,
atomic parcel numbering, append-only ownership/status history, a guarded `_ensure_mutable` check
every mutator calls first (`docs/adr/ADR-013-...md`). **`ParcelGeometry`** (Spatial):
tenant-scoped boundary, validate-then-store construction (`ParcelGeometry.new()` is the *only*
constructor and performs full structural validation before an instance can exist at all — there is
no `PENDING`/`REJECTED` stored state), append-only ACTIVE→SUPERSEDED lifecycle (`docs/adr/
ADR-018-...md`).

## Repositories

The persistence abstraction an application service depends on — never a raw database session.
`ParcelRepository`/`ParcelGeometryRepository` are `Protocol`s; `PostgresParcelRepository`/
`PostgresParcelGeometryRepository` are their real adapters; `InMemoryParcelRepository`/
`InMemoryParcelGeometryRepository` are their test fakes. An application service is written once
and runs, unmodified, against either.

## Application Services

The use-case layer — `ParcelService`, `SpatialService` — depends only on ports (repositories and
other protocol-typed dependencies), never on adapters or raw sessions directly. A real defect this
platform caught and fixed during B4 Slice 1 illustrates why this discipline matters: `SpatialService`'s
first draft took a raw `AsyncSession` directly, a violation of this exact rule, caught during
design review before a single test ran.

## Ports

Named `Protocol` interfaces an application service depends on: `GeometryPort` (Registry depends on
it, Spatial supplies its real implementation), `ParcelExistencePort` (Spatial depends on it,
Registry's data satisfies it through a narrow read), `ParcelGeometryRepository` (Spatial's own
persistence port). A port is defined by, and belongs to, the context that *consumes* it — never
the context that happens to supply data for it.

## Adapters

Concrete implementations of a port: `PostgresParcelRepository`, `RealGeometryAdapter`,
`PlaceholderGeometryAdapter` (the deliberately-inert placeholder `GeometryPort` implementation
that let Registry ship, tested and deployed, before Spatial existed at all — swapping it for
`RealGeometryAdapter` in B4 Slice 2 changed zero lines of Registry code, which is this whole
pattern's point).

## Dependency Injection

FastAPI's `Depends()`/`dependency_overrides` is this platform's DI mechanism, used identically in
production (`app/main.py`) and tests (`tests/app_factory.py`): a per-request-scoped `AsyncSession`
is resolved once and shared by every port that needs it within that request (the mechanism
`docs/adr/ADR-014-...md`'s atomic-numbering transaction model relies on); a stateless adapter
(like `PlaceholderGeometryAdapter`) is a single module-level instance reused across requests.

## Contracts

A port's method signature, including every parameter, *is* the contract — changing it is a
governed act. `GeometryPort.reference_is_valid`'s signature amendment (`docs/adr/
ADR-019-...md`) is this platform's only executed example: a formal ADR, reviewed and accepted,
before the placeholder adapter's signature was touched, even though the change added parameters
neither the interface's original caller nor its original single implementation strictly needed
yet — the amendment was made because a *future* real adapter would need them, decided explicitly
rather than guessed at.

## Anti-corruption boundaries

The composition root (`app/main.py`/`tests/app_factory.py`) is this platform's only anti-corruption
layer location — the one place permitted to import from more than one bounded context, precisely
so that neither context's own code ever needs to. This is what makes Registry "completely
infrastructure-agnostic" toward Spatial (and every future context) a structural guarantee, not a
code-review convention.

---

# PART IV — ENGINEERING RULES

Every rule below is fully specified, with its originating defect, in `docs/ENGINEERING_RULES.md`
— this section is a consolidated index, not a restatement of the reasoning.

| # | Rule (short form) | Full detail |
|---|---|---|
| 1 | No new entity/table ships without an RLS/PDP-PEP policy in the same commit; exactly one authorization path (PDP/PEP/PIP), never a parallel auth system. | `docs/ENGINEERING_RULES.md` §1 |
| 2 | No permissive fallback default on any security-relevant environment variable — missing config fails startup, never silently degrades. | §2 |
| 3 | Every scoring/validation function fails safe — missing/zero data yields a low or `INSUFFICIENT_DATA` result, never a passing score. | §3 |
| 4 | Explicit stop/ask conditions — cross-context changes, schema changes, new dependencies, auth/payments/evidence-integrity changes, any deletion, legal/compliance-adjacent logic. | §4 |
| 5 | No new dependency without explicit approval, justification, and a pinned version. | §5 |
| 6 | Migrations must be reversible; schema change ships with its RLS/policy update in the same commit; rollback tested in staging first. | §6 |
| 7 | Never mark something complete without having actually run the check and observed it pass. | §7 |
| 8 | One bounded context per PR where feasible; DoD checklist required; hooks never skipped without explicit authorization; commit messages explain *why*. | §8 |
| 9 | **Controlled Platform Authority** — any platform-wide/cross-tenant read or write must be a named, narrow, fixed-at-call-site, read-only-wherever-possible, audited exception; never an implicit or general-purpose bypass. | §9 |

**Additional principles this programme has established through practice, consolidated here for
the first time (each traceable to a specific ADR or verification record, not a new rule):**

- **ADR before implementation.** Every ADR in `docs/adr/` was drafted and, where required,
  accepted before its corresponding code was written — no exception across B1 through B4 Slice 2.
- **Threat model before cross-tenant capability.** `docs/B4_THREAT_MODEL.md` was produced and
  accepted before ADR-018 was drafted, specifically because Spatial Intelligence was the first
  context anticipated to need cross-tenant reasoning at all.
- **Discovery before coding.** Every programme (B2, B3, B4) began with an explicit
  Discovery-and-Planning document, reviewed and approved before any ADR was drafted from it.
- **Validate-then-store.** No aggregate's invalid state can ever exist, let alone persist —
  validation happens inside the sole constructor, never as a separate post-hoc check
  (`docs/adr/ADR-018-...md`).
- **Append-only where legally significant.** Ownership history (`Parcel`), geometry history
  (`ParcelGeometry`), and the audit log itself are all append-only — a correction adds a new row
  and marks the prior one terminal, it never edits history in place.
- **No speculative abstractions.** No interface, table, or generalization exists for a capability
  not yet authorized — e.g., `ParcelGeometry` has no `MultiPolygon` support and no administrative-
  boundary reference table, both explicitly declined as open questions in ADR-018 until a real
  need is scoped.
- **No hidden coupling.** Every cross-context dependency is an explicit, named port — never an
  implicit shared table, shared session, or convention-based coupling.
- **No direct database access across bounded contexts.** Spatial reads Registry's `parcels` table
  only through `ParcelExistencePort`, never a direct join or raw query against a table it does not
  own.
- **Controlled Platform Authority only for approved platform intelligence.** Restates rule 9 for
  the specific case of the Platform Intelligence layer (Part II/VIII) — no capability under that
  layer inherits another's exception; each needs its own.
- **No bypass of RLS except through approved mechanisms.** The `super_admin` session-variable
  bypass and the context-hydration service-account's fixed lookup are this platform's only two
  precedents; any new one requires the same explicit reasoning rule 9 demands.
- **Kernel remains business-neutral.** No bounded-context-specific concept (a parcel, a geometry, a
  trust score) is ever added to `app/kernel/`.
- **Platform services never become business domains.** Platform Intelligence capabilities produce
  findings/signals about domains; they do not acquire their own domain aggregates or product
  requirements independent of the contexts they observe, unless a future ADR explicitly promotes
  one to a genuine bounded context (`docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md`).
- **Business domains never bypass contracts.** Registry never imports Spatial's domain model to
  "save a round-trip"; the port is the contract, even when the two contexts happen to be in the
  same codebase and the same deploy.

---

# PART V — SECURITY MODEL

Each subsection names the governing document(s) — this handbook does not reproduce their content.

## Authentication

Keycloak-issued JWTs, verified against the realm's JWKS on every request (`docs/adr/
ADR-004-...md`, `docs/adr/ADR-009-b1-platform-freeze.md` §1/§3 for the frozen flow detail).

## Authorization

Exactly one path: the PDP/PEP/PIP engine (`docs/adr/ADR-004-...md`, ADR-009 §2). Every mutation's
authorization decision is made fresh, per request, never cached, and every context's own
mutation-authorization model (Registry's creator-or-governance model, `docs/adr/
ADR-015-...md`; Spatial's identical model, `docs/adr/ADR-022-...md`) is built as an explicit
extension of this one engine, never a second mechanism.

## Delegation

A delegate exercises exactly their currently-effective delegated role's own reach, re-resolved
fresh on every request with no caching — a revoked or expired delegation loses effect on the very
next request, not merely at its own expiry check (`docs/adr/ADR-011-delegated-administration.md`).

## Tenant isolation

The platform's default, absolute boundary: every tenant-scoped table's RLS policy denies any row
outside the caller's own `tenant_id`, with `super_admin` as the sole, named, audited-elsewhere
exception (`docs/adr/ADR-010-...md`; every migration since `0001`).

## Row-Level Security

`FORCE ROW LEVEL SECURITY` plus the canonical policy shape
(`tenant_id = current_setting('app.tenant_id', true) OR current_setting('app.is_super_admin', true)
= 'true'`) on every tenant-scoped table, paired with a second, independent application-layer
`_in_scope` check in every context's own service — RLS cannot be exercised against an in-memory
test fake, so the explicit check is what the hermetic test suite actually verifies (a real gap
this exact reasoning caught and fixed during B4 Slice 1).

## Controlled Platform Authority

`docs/ENGINEERING_RULES.md` §9 (Part IV, above) — the doctrine governing any cross-tenant or
platform-wide read/write. Its first genuinely new application beyond the two existing precedents
(`super_admin`, the hydration service-account) is Spatial Conflict Detection's proposed
cross-tenant read (`docs/adr/ADR-021-...md` §1, refined `docs/
SCDS-001-spatial-conflict-detection-specification.md` §5) — not yet implemented.

## Audit chain

Append-only, hash-chained (`docs/adr/ADR-007-audit-trail-evidence-model.md`) — each entry's hash
covers its own content plus the prior entry's hash, so `verify_chain()` detects tampering by
recomputation rather than trusting a stored status flag (the exact "security theater" pattern the
Emergent audit found). Live-verified as unbroken across this platform's entire history as of the
most recent B4 Slice 2 verification (`docs/B4_VERIFICATION_CHECKLIST.md`).

## Least privilege

The database's own least-privilege application role (`landvault_app`, `SELECT/INSERT/UPDATE`
only, no `DELETE`, migration `0002`) and Controlled Platform Authority's own "as narrow as the
task allows" requirement are the same principle applied at two different layers — the database
grant model, and the application-level exception-scoping model.

## Threat modelling

Performed before any cross-tenant-capable ADR is drafted — `docs/B4_THREAT_MODEL.md` preceded
ADR-018 and named the requirements ADR-021/SCDS-001 later resolved (TB5). This is now this
platform's standing practice for any future context anticipated to need similar reach (Part VI).

## Cross-tenant intelligence

Exactly one exception exists in this codebase's design as of this handbook's writing: Spatial
Conflict Detection (ADR-021 §1, proposed, unimplemented). Every future platform-intelligence
capability needs its own separate exception and its own ADR — none inherits another's
(`docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md`).

## Minimal disclosure

An ordinary registrant learns, at most, that a conflict exists and should be escalated to
governance — never another tenant's geometry, identity, or Registry-owned metadata
(`docs/adr/ADR-021-...md` §3, `docs/SCDS-001-...md` §4's full disclosure matrix).

## Platform Intelligence

`docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md` in full — the four-part test for what belongs under
this layer, and why it is a services layer, never a bounded context.

---

# PART VI — PROGRAMME GOVERNANCE

## The LandVault lifecycle

```
Discovery
   ↓
Threat Model            (only when the programme plausibly touches cross-tenant/platform-wide
   ↓                     reach — not every programme needs one, but every one that might must
   ↓                     have it before its first ADR, per B4's own precedent)
ADR
   ↓
Review
   ↓
Approval
   ↓
Implementation
   ↓
Verification            (live, against real infrastructure — not simulated, not deferred by
   ↓                     default once a programme's own authorization requires it live, as
   ↓                     B4 Slice 2's did)
Platform Freeze          (a dedicated Freeze ADR — ADR-009/012/017's pattern — declaring the
   ↓                     programme's shape locked, extensible only via a new ADR referencing it)
Programme Complete
```

**Every future programme follows this lifecycle.** No step is skipped by default; a step may be
explicitly, narrowly waived only by the same explicit human authorization
`docs/ENGINEERING_RULES.md` §4 already requires for any ambiguous or cross-boundary decision.

## How this maps to the Definition of Done and Phase Gates

`docs/DOD.md`'s three tiers (Feature, Sprint/Bounded-Context, Product/MVP) and
`docs/PHASE_GATES.md`'s Phase 0–12 model are this lifecycle's operational instantiation — the
lifecycle above is the *sequence of governance artefacts* a programme produces; the DoD/Phase
Gates are the *quality bar* each step must clear before the next begins. Neither document is
superseded by this handbook; this handbook only names how they compose.

## Freeze as a first-class governance act

A "Platform Freeze" is not merely "done" — it is its own ADR (ADR-009 for B1, ADR-012 for B2,
ADR-017 for B3), git-tagged (`b2-freeze`, `b3-freeze`), and it declares explicitly what is now
immutable without a new ADR referencing it. B4 has not yet reached this point — Slices 1–2 are
individually accepted and their own scope frozen under ADR-022 (`docs/
B4_VERIFICATION_CHECKLIST.md`'s governance-decision entry), but B4 as a whole programme awaits
Slice 3's resolution (ADR-021) before any B4-wide freeze ADR would be appropriate.

## Slices within a programme

A programme (e.g., B4) is delivered as a sequence of individually-reviewed, individually-approved
slices — never as one large, unreviewable implementation. Each slice's own completion report
follows the same shape: executive summary, ADR compliance review, files changed, test results,
live verification (where required), risks, deferred responsibilities, and an explicit stop
condition naming what is *not* authorized next. This handbook does not introduce a new completion-
report template — every slice from B2 onward has already used this shape consistently; it is
recorded here because consistency is itself a governance property worth naming.

---

# PART VII — DOCUMENTATION HIERARCHY

```
LV-000 Constitution           (docs/LV-000-constitution.md, adopted 2026-07-26 — the platform's
   ↓                          supreme governing document, per its own Article II)
Architecture Handbook         (this document — navigation and interpretation, not decision)
   ↓
Platform Strategy             (docs/PLATFORM_STRATEGY.md — vision, positioning, five-layer
   ↓                          model; docs/REBUILD_PLAN.md remains the underlying 13-context
   ↓                          technical plan/stack-choice/milestone document the strategy
   ↓                          layer explains the commercial significance of)
PRD                           (product requirements — not a distinct document type in this
   ↓                          codebase today; product intent is currently expressed through
   ↓                          docs/REBUILD_PLAN.md, each programme's own Discovery document, and
   ↓                          — for future programmes — their own Business Strategy document,
   ↓                          e.g. docs/PARTNER_PROGRAMME_STRATEGY.md)
TRD                           (technical requirements — likewise expressed today through each
   ↓                          programme's own Discovery-and-Planning document, e.g.
   ↓                          docs/B4_DISCOVERY_AND_PLANNING.md, rather than a separate TRD file)
ADRs                          (docs/adr/ — the actual, binding architectural decisions; every
   ↓                          layer above this line explains or plans, every layer at or below
   ↓                          this line decides or specifies)
Engineering Specifications     (docs/SCDS-001-...md — implementation guidance beneath an ADR,
   ↓                          never itself an architectural decision)
Threat Models                 (docs/B4_THREAT_MODEL.md — binding constraints on the ADRs it
   ↓                          precedes)
Verification Checklists        (docs/B3_FINAL_VERIFICATION_CHECKLIST.md,
   ↓                          docs/B4_VERIFICATION_CHECKLIST.md — the evidence record)
Release Notes                  (docs/audits/B2_RELEASE_NOTES.md, B3_RELEASE_NOTES.md — the
   ↓                          shipped-and-frozen summary)
Implementation                 (the actual code, migrations, and tests)
```

**No document overrides the Constitution or any accepted ADR.** This handbook sits directly
beneath LV-000 and above the platform-strategy/discovery layer, precisely because its role is to
explain how the layers below it relate to one another — it does not itself belong in the
decision-making chain. Where this codebase does not yet have a distinct PRD/TRD artifact type, the
programme-level Discovery-and-Planning and Business Strategy documents currently serve that role;
introducing genuinely separate PRD/TRD documents is a future documentation-process decision, not
one this handbook makes.

**Reconciliation with LV-000's own strategic-layer hierarchy:** LV-000 Article II, Section 2
states a five-level precedence (LV-000 → Handbook → Accepted ADRs → Programme Documents →
Engineering Documentation) that governs *conflicts of principle*. The document-artifact-type
hierarchy immediately above governs *what kind of document to consult for what level of detail* —
the two compose exactly as `docs/PLATFORM_STRATEGY.md`'s own earlier reconciliation note already
described for the strategic-layer hierarchy it introduced, which LV-000's Article II now
subsumes as the platform's single, authoritative precedence statement.

**Update (2026-07-25) — the Platform Strategy layer is now populated.** `docs/
PLATFORM_STRATEGY.md` occupies this hierarchy's "Platform Strategy" position, with a set of
per-programme "Business Strategy" documents beneath it: `docs/PARTNER_PROGRAMME_STRATEGY.md`,
`docs/ENTERPRISE_PROGRAMME_STRATEGY.md`, `docs/GOVERNMENT_PROGRAMME_STRATEGY.md`, `docs/
DEVELOPER_PLATFORM_STRATEGY.md`, `docs/COMMERCIAL_ARCHITECTURE.md`, `docs/OPERATING_MODEL.md`,
`docs/TRUST_FRAMEWORK.md`, and `docs/NETWORK_GROWTH_STRATEGY.md`, alongside the already-existing
`docs/MARKETPLACE_DISCOVERY_AND_PLANNING.md`. `docs/PLATFORM_STRATEGY.md` itself reconciles a
second, strategic-layer hierarchy (LV-000 → Handbook → Platform Strategy → Business Strategy →
Marketplace Strategy → Government Strategy → Engineering Roadmap → Programme Implementation)
against this section's own document-artifact-type hierarchy — see that document's own
"Reconciliation" note for how the two compose rather than conflict. None of these documents
authorizes any implementation; each ends in its own Approval Gate, mirroring `docs/
B4_DISCOVERY_AND_PLANNING.md`'s own pattern.

---

# PART VIII — FUTURE PROGRAMMES

**Summarized without implementation.** Each entry names purpose, expected bounded contexts, a
likely ADR roadmap, integration points, and dependencies — none of this authorizes any code,
migration, or API.

**Update (2026-07-25) — dedicated planning documents now exist for most entries below**, produced
under the Enterprise Programme Transition planning exercise: Marketplace →
`docs/MARKETPLACE_DISCOVERY_AND_PLANNING.md`; Enterprise → `docs/
ENTERPRISE_PROGRAMME_STRATEGY.md`; Government → `docs/GOVERNMENT_PROGRAMME_STRATEGY.md`;
Developer Platform/API Ecosystem → `docs/DEVELOPER_PLATFORM_STRATEGY.md` (treated as one planning
exercise, per that document's own opening note); Platform Intelligence →
`docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md` (already existed, referenced in Part II above);
Compliance/Analytics remain named only below and in `docs/
PLATFORM_INTELLIGENCE_ARCHITECTURE.md`'s Compliance/Analytics Engine entries, with no dedicated
document of their own yet — `docs/OPERATING_MODEL.md` names Compliance as an organizational
function, distinct from (but related to) a future Compliance Engine. A new Partner Programme entry
also now exists (`docs/PARTNER_PROGRAMME_STRATEGY.md`), not originally named in this Part's first
version, since the Enterprise Programme Transition's own review distinguished Partner from
Marketplace explicitly (see that document's own "Why a distinct programme" section). The entries
below are preserved as this Handbook's own summary; the dedicated documents are authoritative for
anything beyond that summary.

### Marketplace

- **Purpose:** transactional capability — payments, wallet, escrow, ratings, and (least-specified)
  enterprise dispatch — building on `docs/REBUILD_PLAN.md` context #10 (Economic/Billing).
- **Expected bounded contexts:** undetermined — the scoping question (one expanded context vs.
  several new ones) is explicitly left open for this programme's own Phase 0
  (`docs/MARKETPLACE_DISCOVERY_AND_PLANNING.md`).
- **Likely ADR roadmap:** a domain-model ADR for whichever entities scoping produces; a
  Marketplace-specific authorization ADR planned from the start (avoiding the coarse-gate-then-
  escalate pattern Registry and Spatial each went through once); a Controlled Platform Authority-
  governed ADR for Escrow if it needs cross-tenant/governance-conditional release logic.
- **Integration points:** Registry (parcel identity a transaction may reference), Identity
  (tenant/role scope for who may transact).
- **Dependencies:** likely depends on Evidence (B5, unbuilt) for dispute-resolution evidence, and
  possibly Workflow (`docs/REBUILD_PLAN.md` context #7, unbuilt) for escrow-release state
  machinery.

### Enterprise

- **Purpose:** named in `docs/MARKETPLACE_DISCOVERY_AND_PLANNING.md`'s disclosure matrix as a
  distinguished tenant tier with no current definition anywhere in this platform.
- **Expected bounded contexts:** none scoped — no Enterprise-specific context exists in
  `docs/REBUILD_PLAN.md`'s 13-context plan.
- **Likely ADR roadmap:** would need its own domain-model ADR defining what "Enterprise" means as
  a tenant classification before any capability is gated on it.
- **Integration points:** Identity (tenant classification), Marketplace (differentiated
  commercial terms, if any).
- **Dependencies:** depends on Marketplace's own scoping being resolved first, if Enterprise's
  primary differentiation is commercial.

### Government

- **Purpose:** external-integration consumer and/or partner-facing capability — named in
  `docs/SCDS-001-...md` §4/§8 as a future disclosure tier and extension point with no current
  access to anything this platform has built.
- **Expected bounded contexts:** none scoped.
- **Likely ADR roadmap:** any government-facing read or write requires its own Controlled Platform
  Authority justification and its own ADR (`docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md`'s "no
  exception inherits another's" rule applies with full force here).
- **Integration points:** Registry (parcel-of-record data a government partner may need), Spatial
  (geometry, if ever disclosed externally), Platform Intelligence (any aggregate/analytics view).
- **Dependencies:** depends on Compliance (below) for whatever regulatory posture such an
  integration must satisfy.

### AI

- **Purpose:** `docs/adr/ADR-008-ai-integration-strategy.md` already exists as this platform's AI
  integration ADR (Accepted, scope subject to narrowing at Phase 6 kickoff per
  `docs/PHASE_GATES.md`) — this entry names the *future programme* of actually building against
  that strategy, not a new decision.
- **Expected bounded contexts:** none new — AI capability is expected to manifest as Platform
  Intelligence services (AI Engine, Part II) consuming existing contexts' data through the same
  narrow, audited exceptions every other Platform Intelligence capability must use.
- **Likely ADR roadmap:** each AI capability (e.g., a future ML-based "Suspicious pattern"
  classifier, `docs/SCDS-001-...md` §1 item 11) needs its own ADR before implementation, per
  ADR-021 §6's intelligence-boundary doctrine.
- **Integration points:** every context whose data might inform a model — gated, per capability,
  by Controlled Platform Authority.
- **Dependencies:** depends on ADR-008's own strategy remaining current, and on whichever
  Platform Intelligence capability an AI feature is meant to enhance already existing.

### Platform Intelligence

- **Purpose:** already named and architected (not implemented) — `docs/
  PLATFORM_INTELLIGENCE_ARCHITECTURE.md`. Listed here for completeness of Part VIII's survey, not
  as a new item.
- **Expected bounded contexts:** explicitly none — a services layer, not a context.
- **Likely ADR roadmap:** ADR-021 (Conflict Engine, proposed) is its first instance; each future
  engine (Fraud, Risk, AI, Analytics, Compliance) needs its own ADR.
- **Integration points:** every existing and future bounded context, narrowly, per capability.
- **Dependencies:** depends on each consumed context's own data being stable and validated first
  (e.g., Conflict Engine depends on Spatial's real geometry validation, already shipped in Slice 2).

### Developer Platform

- **Purpose:** not named anywhere in `docs/REBUILD_PLAN.md`'s existing plan — a plausible future
  capability (public API access, third-party integration, developer credentials) with no current
  scoping.
- **Expected bounded contexts:** undetermined — likely intersects with Identity (API credential/
  key management as a new principal type) and a new API-gateway-adjacent concern.
- **Likely ADR roadmap:** an authentication-model ADR for non-human/API-key principals, extending
  ADR-004/ADR-009 rather than replacing them.
- **Integration points:** every context a public API would expose, each requiring its own
  authorization review — a public surface is a materially different threat model than this
  platform's current authenticated-tenant-user model.
- **Dependencies:** depends on API Ecosystem (below) being scoped first, since the two are likely
  the same underlying capability viewed from two angles.

### API Ecosystem

- **Purpose:** as above — not currently scoped. Likely the same underlying need as Developer
  Platform.
- **Expected bounded contexts:** undetermined.
- **Likely ADR roadmap:** shared with Developer Platform, above.
- **Integration points:** every context with any external-facing data.
- **Dependencies:** Developer Platform.

### Compliance

- **Purpose:** named in Part II's Platform Intelligence diagram (Compliance Engine) — regulatory/
  audit-reporting capability, not designed.
- **Expected bounded contexts:** explicitly none — a Platform Intelligence service, per the
  four-part test.
- **Likely ADR roadmap:** its own ADR before any cross-context compliance report is built,
  per Platform Intelligence's standing rule.
- **Integration points:** every context whose data a compliance report might need to summarize.
- **Dependencies:** depends on Audit (already built, ADR-007) as its primary data source — a
  compliance report is expected to be substantially an audit-log aggregation/reporting capability,
  not a new data-collection mechanism.

### Analytics

- **Purpose:** named in Part II's diagram (Analytics Engine) — cross-context reporting, not
  designed.
- **Expected bounded contexts:** explicitly none — a Platform Intelligence service.
- **Likely ADR roadmap:** its own ADR, per Platform Intelligence's standing rule, with particular
  attention to whether any analytics view could re-identify cross-tenant data through aggregation
  (a distinct threat-model question SCDS-001 does not itself resolve for this future capability).
- **Integration points:** every context, read-only, in aggregate.
- **Dependencies:** depends on enough live contexts existing to make aggregate analytics
  meaningful — premature before Registry/Spatial/Evidence/Trust Engine all have real production
  data.

---

# PART IX — ARCHITECTURAL EVOLUTION

## How LandVault evolved

```
Digital Registry              (the original Base44/Emergent product concept — parcel records,
   ↓                           minimal verification)
Evidence Platform              (the audits identified chain-of-custody and evidence integrity as
   ↓                           load-bearing, not optional — Evidence, B5, and the audit-chain
   ↓                           mechanism, ADR-007, both trace to this recognition)
Verification Platform          (Spatial Intelligence, B4 — the recognition that "a parcel exists"
   ↓                           is insufficient without "this parcel's boundary is real,
   ↓                           structurally valid, and non-conflicting")
Multi-Tenant Platform          (B2's Tenant/Organization aggregate and delegation model — the
   ↓                           recognition that this platform serves many independent
   ↓                           registries/organizations, not one)
Trusted Digital Infrastructure  (the current framing — a platform whose Trust Engine (B7) can make
                                an explainable claim about any parcel's reliability, built from
                                real signals every context beneath it actually produces)
```

## Why each transition occurred

- **Digital Registry → Evidence Platform:** the original audits (`docs/audits/`) found that
  neither prior implementation could actually prove anything it claimed — data existed, but
  nothing about its provenance or integrity was verifiable. Evidence-first philosophy (Part I) is
  this platform's answer.
- **Evidence Platform → Verification Platform:** recording evidence is necessary but not
  sufficient if the underlying spatial claim (a parcel's boundary) is never actually validated —
  Base44's own spatial validation used a hardcoded bounding-box check that could not catch real
  boundary conflicts. B4 exists to replace that with real, structural, eventually cross-tenant-
  aware validation.
- **Verification Platform → Multi-Tenant Platform:** as soon as more than one organization's
  registrants would use this platform concurrently, tenant isolation had to be the platform's
  absolute default, not an assumed side effect of "each customer gets their own deployment" — B2's
  entire program exists because that assumption does not hold at the scale this platform targets.
- **Multi-Tenant Platform → Trusted Digital Infrastructure:** once identity, tenancy, registry
  identity, and real geometry validation all exist, the platform can begin making an *explainable*
  trust claim about any given parcel — but only once every signal that claim depends on is itself
  produced by a real, fail-safe mechanism (Part I), which is precisely the discipline every
  programme from B1 through B4 has enforced before B7 (Trust Engine) is ever built.

## How the architecture evolved while preserving backward compatibility

Every extension in this platform's history has been additive, never a silent rewrite of frozen
behavior: `Tenant`/`Delegation` (B2) extended B1's `User`/`Role` model without changing a single
frozen B1 decision (ADR-009's own freeze scope was never touched by ADR-010/011). `Parcel` (B3)
introduced a new aggregate without modifying Identity. `ParcelGeometry` (B4) introduced a second
new aggregate, and even its one required change to frozen B3 code — `GeometryPort`'s signature —
was executed as a formal, reviewed amendment (ADR-019) that changed zero test files and broke zero
existing behavior, not a rewrite. This pattern — extend via new ADR referencing the frozen one,
never silently edit a frozen ADR's own text — is this platform's mechanism for evolving without
ever accumulating undocumented architectural drift.

---

# PART X — ENGINEERING CULTURE

The philosophy every contributor to this platform is expected to internalize, not merely follow
as an external checklist:

- **Architecture before implementation.** Every ADR precedes its code, without exception, across
  every programme this platform has completed.
- **Governance before coding.** Discovery, then threat model (where relevant), then ADR, then
  review, then approval — implementation is the *seventh* step of this platform's lifecycle
  (Part VI), never the first.
- **Security before convenience.** A placeholder adapter that always returns `True`
  (`PlaceholderGeometryAdapter`) shipped for an entire programme rather than a real adapter built
  before its authorization model was designed — the inconvenience of waiting was preferred to the
  risk of shipping a real capability without its governing authorization model in place
  (ADR-022's own genesis).
- **Clarity over cleverness.** This platform's custom `Geometry` SQLAlchemy type
  (`app/contexts/spatial/adapters/orm.py`) is a small, explicit `UserDefinedType` wrapping two SQL
  functions — chosen specifically to avoid a new GIS dependency (`docs/ENGINEERING_RULES.md` §5),
  not because it is the cleverest possible solution, but because it is the clearest one that
  satisfies the constraint.
- **Explicit decisions over implicit assumptions.** ADR-018 explicitly declined `MultiPolygon`
  support and administrative-boundary reference data as open questions, rather than silently
  assuming either answer — an explicit "not decided yet" is preferred to an implicit default that
  later has to be discovered and reversed.
- **Review before implementation.** Every slice in this platform's history has had an explicit
  human review-and-approval step before the next slice began — B4 Slice 2's own authorization
  required a governance review before Slice 3 could even be discussed.
- **Documentation as production artefacts.** ADRs, threat models, and verification checklists are
  treated with the same rigor as code — reviewed, dated, versioned by git commit, never informal
  notes. This handbook itself is one such artefact.
- **Long-term maintainability over short-term speed.** The Registry↔Spatial composition-root
  wiring pattern (Part II/III) takes more files and more indirection than a direct import would —
  chosen because it guarantees bounded-context independence for the platform's entire remaining
  life, not merely for this one integration.
- **Platform thinking over feature thinking.** Controlled Platform Authority (`docs/
  ENGINEERING_RULES.md` §9) was generalized from two existing precedents into an explicit,
  reusable doctrine specifically so that every *future* context needing similar reach inherits a
  reviewed rule, rather than re-deriving its own justification for elevated access from nothing.

---

# APPENDIX A — CROSS-REFERENCE MAP

Every governance document that exists as of this handbook's version, and which Part(s) above
reference it.

| Document | Referenced in | Status as of this handbook |
|---|---|---|
| `docs/adr/ADR-001-repository-strategy.md` | Part VII | Accepted |
| `docs/adr/ADR-002-system-architecture.md` | Part II, III | Accepted |
| `docs/adr/ADR-003-database-choice.md` | — | Accepted |
| `docs/adr/ADR-004-authentication-authorisation-model.md` | Part I, V | Accepted |
| `docs/adr/ADR-005-property-registry-data-model.md` | — | Accepted |
| `docs/adr/ADR-006-payment-architecture.md` | Part VIII (Marketplace) | Accepted |
| `docs/adr/ADR-007-audit-trail-evidence-model.md` | Part I, IV, V | Accepted |
| `docs/adr/ADR-008-ai-integration-strategy.md` | Part VIII (AI) | Accepted |
| `docs/adr/ADR-009-b1-platform-freeze.md` | Part I, II, V, VI, IX | Accepted — B1 frozen |
| `docs/adr/ADR-010-tenant-organization-aggregate.md` | Part II, V, IX | Accepted — extends ADR-009 |
| `docs/adr/ADR-011-delegated-administration.md` | Part V | Accepted — extends ADR-009/010 |
| `docs/adr/ADR-012-b2-platform-freeze.md` | Part VI, IX | Accepted — B2 frozen |
| `docs/adr/ADR-013-parcel-aggregate-registry-domain-model.md` | Part II, III | Accepted — extends ADR-009/010/011/012 |
| `docs/adr/ADR-014-postgresql-atomic-parcel-number-allocation.md` | Part III | Accepted — extends ADR-013 |
| `docs/adr/ADR-015-registry-mutation-authorization-model.md` | Part I, V | Accepted — extends ADR-009/010/011/012 |
| `docs/adr/ADR-016-geometry-port-boundary-spatial-integration.md` | Part II, III | Accepted — extends ADR-009/013; preserved as historical record, current contract is ADR-019 |
| `docs/adr/ADR-017-b3-platform-freeze.md` | Part VI, IX | Accepted — B3 frozen |
| `docs/adr/ADR-018-spatial-domain-model.md` | Part I, II, III, IV, IX | Accepted |
| `docs/adr/ADR-019-geometry-port-interface-amendment.md` | Part II, III, IX | Accepted, implemented |
| `docs/adr/ADR-021-spatial-conflict-detection-and-controlled-cross-tenant-intelligence.md` | Part II, IV, V | **Proposed — not yet accepted** |
| `docs/adr/ADR-022-spatial-authorization-model.md` | Part I, V | Accepted, frozen |
| `docs/REBUILD_PLAN.md` | Part I, II, VII, VIII | Living plan document |
| `docs/PHASE_GATES.md` | Part VI | Living process document |
| `docs/DOD.md` | Part VI | Living process document |
| `docs/ENGINEERING_RULES.md` | Part IV, throughout | Authoritative if this handbook ever diverges from it |
| `docs/B3_DISCOVERY_AND_PLANNING.md` | Part VI, VII | Historical (B3 accepted baseline) |
| `docs/B3_FINAL_VERIFICATION_CHECKLIST.md` | Part I, VI, VII | Historical (B3 gate passed) |
| `docs/B4_DISCOVERY_AND_PLANNING.md` | Part VI, VII | Accepted baseline, amended as B4 progressed |
| `docs/B4_THREAT_MODEL.md` | Part I, IV, V, VII | Accepted baseline |
| `docs/B4_VERIFICATION_CHECKLIST.md` | Part I, VI, VII | Live register — Slice 1/2 resolved, Slice 3 pending |
| `docs/SCDS-001-spatial-conflict-detection-specification.md` | Part V, VII, VIII | Draft, pending review alongside ADR-021 |
| `docs/B4_SLICE3_PREIMPLEMENTATION_REVIEW.md` | Part VI (implicitly, as the review-step record) | Complete — no amendment to ADR-021 required |
| `docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md` | Part I, II, IV, V, VIII | Named, not implemented |
| `docs/MARKETPLACE_DISCOVERY_AND_PLANNING.md` | Part I, VIII | Planning recommendation only |
| `docs/CONSTITUTIONAL_RECOMMENDATIONS.md` | Part VII | Recorded, not adopted; LV-000 does not exist — now 2 entries |
| `docs/LV-000-constitution.md` | Handbook header, Part VII | **Adopted 2026-07-26 — the platform's supreme governing document** |
| `docs/PLATFORM_STRATEGY.md` | Handbook header note, Part VII/VIII | Planning only — vision, positioning, five-layer model, strategic-layer hierarchy (its own precedence diagram now subsumed by LV-000 Article II) |
| `docs/PARTNER_PROGRAMME_STRATEGY.md` | Part VIII | Planning recommendation only |
| `docs/ENTERPRISE_PROGRAMME_STRATEGY.md` | Part VIII | Planning recommendation only |
| `docs/GOVERNMENT_PROGRAMME_STRATEGY.md` | Part VIII | Planning recommendation only |
| `docs/DEVELOPER_PLATFORM_STRATEGY.md` | Part VIII | Planning recommendation only (Developer Platform + API Ecosystem, treated as one) |
| `docs/COMMERCIAL_ARCHITECTURE.md` | Part VIII | Planning only — revenue lines named, no pricing decided |
| `docs/OPERATING_MODEL.md` | Part VIII | Planning only — organizational functions named, none staffed |
| `docs/TRUST_FRAMEWORK.md` | Part V (business-facing companion) | Planning only — ties engineering mechanisms to ecosystem trust claims |
| `docs/NETWORK_GROWTH_STRATEGY.md` | Part VIII | Planning only — no growth target or infrastructure change committed |
| `docs/LANDVAULT_BIBLE_VOLUME_I_EXECUTIVE_OVERVIEW.md` | — (non-normative) | Executive narrative synthesizing this Handbook, LV-000, and Platform Strategy for external audiences; explanatory only, decides nothing, cited by nothing above it |
| `docs/audits/` (Base44/Emergent forensic audits) | Part I, IV | Historical — every engineering rule traces here |
| `docs/audits/B2_RELEASE_NOTES.md` | Part VII | Historical |
| `docs/audits/B3_RELEASE_NOTES.md` | Part VII | Historical |

---

# APPENDIX B — RECOMMENDATIONS FOR FUTURE HANDBOOK UPDATES

This handbook is a snapshot as of 2026-07-24. It should be revised, not left to drift, at each of
the following triggers:

1. **On any new ADR's acceptance.** Add it to Appendix A immediately; update whichever Part(s) it
   materially affects (most commonly Part II if it changes a context relationship, Part IV if it
   establishes a new rule, Part V if it touches security posture).
2. **On any Platform Freeze.** When B4 as a whole eventually freezes (after Slice 3, if ADR-021 is
   accepted and implemented), Part VI's "Freeze as a first-class governance act" section should be
   updated to reflect B4's own freeze ADR, the same way this version already reflects ADR-009/012/017
   for B1/B2/B3.
3. **On B5 (Evidence) or any subsequent programme's own Discovery-and-Planning acceptance.** Part
   II's architecture diagram currently lists Evidence as "not yet built" — this should be corrected
   the moment that programme's own discovery is accepted, not only once it ships.
4. **On any Platform Intelligence capability's first ADR beyond ADR-021.** Part II/V/VIII's
   Platform Intelligence sections should be updated to move that capability from "not designed" to
   its actual status, mirroring how this version already distinguishes ADR-021 (proposed) from the
   other five named engines (not designed).
5. **~~On LV-000's eventual drafting.~~ Fired 2026-07-26.** LV-000 v1.0 was adopted
   (`docs/LV-000-constitution.md`); this handbook's header, Part VII diagram, and Appendix A were
   updated accordingly (v1.0 → v1.1, this trigger's own action). Both entries in `docs/
   CONSTITUTIONAL_RECOMMENDATIONS.md` were reconciled into LV-000 (Article IX, Sections 1 and 4)
   and that file's own entries updated to record where. This trigger will not fire again unless
   LV-000 itself is amended (LV-000 Article XX) — a future LV-000 amendment is a new, distinct
   trigger, not a repeat of this one.
6. **On any Marketplace/Enterprise/Government/Developer-Platform/API-Ecosystem/Compliance/
   Analytics programme's own Phase 0 acceptance.** Move that programme's Part VIII entry from
   "summarized without implementation" to a real cross-reference against its own Discovery
   document and ADR roadmap, mirroring how Spatial Intelligence's Part VIII-shaped content
   (had it existed at the time) would have been superseded by B4's actual discovery and ADR
   sequence once B4 began.
7. **Version numbering:** this document is v1.0. Increment the minor version (v1.1, v1.2, ...) for
   additive updates triggered by the events above; reserve a major version increment (v2.0) for a
   restructuring of the Parts themselves, not for routine content updates.
8. **This trigger list already fired once, 2026-07-25.** The Enterprise Programme Transition
   planning exercise populated the Platform Strategy layer (`docs/PLATFORM_STRATEGY.md`) and eight
   further planning-only documents in a single pass — this handbook's own header note and Part
   VIII were updated accordingly (see both sections' "Update (2026-07-25)" notes), without a minor
   version bump, since the updates were additive cross-references, not a restructuring of any
   Part. Future updates of similar shape (several related documents landing together) should
   follow this same pattern: update the affected Parts' own text with a dated note, update
   Appendix A, and reserve an actual version increment for when the *Handbook's own Parts* change.

**This handbook does not update itself automatically.** Each trigger above should be treated as
its own small documentation task at the point the triggering event occurs — bundled into that
event's own completion report where practical (mirroring how this version was itself produced as
its own dedicated documentation task, not smuggled into a slice's implementation work).
