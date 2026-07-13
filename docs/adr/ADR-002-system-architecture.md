# ADR-002 — System Architecture

**Status:** Accepted
**Date:** 2026-07-13

## Context

`landverify-nigeria-101-NEW`'s audit found its Domain-Driven Design / hexagonal architecture (domain → ports → adapters → application → api layering, bounded contexts, event-sourced transactional outbox) to be genuinely well-built where it wasn't undermined by a parallel legacy system. `landsecure-registry`'s audit found the opposite problem in a different form: no architectural boundaries at all — a flat collection of ~60 serverless functions and a React SPA calling entities directly, with business logic, authorization, and data access all intermixed.

## Decision

Adopt DDD/hexagonal architecture with **13 bounded contexts** (full detail and dependency ordering in `docs/REBUILD_PLAN.md` §1):

Identity · Registry · Spatial Intelligence · Evidence · Survey · Trust Engine · Workflow · Community Trust · Inheritance & Customary Law · Economic/Billing · Knowledge Graph · Security · Operations

Each context follows the same internal layering:
- **domain/** — pure aggregates, invariants, value objects, events. No I/O.
- **ports/** — repository and specification interfaces.
- **adapters/** — concrete Postgres/S3/external-API implementations of those ports.
- **application/** — orchestrating services: open a transaction, drive aggregate commands, persist, publish events.
- **api/** — FastAPI routers + strictly-typed request/response DTOs (no mass-assignment — extra fields rejected).

Cross-context communication happens **only** through the transactional event outbox (see ADR-007) — no context reaches into another's tables directly. Knowledge Graph (ADR-005/REBUILD_PLAN §1) and Trust Engine are both built as event-subscribing read-projections of this outbox, not as contexts with their own authoritative writes into other contexts' data.

## Consequences

- Aggregate invariants (immutable fields, monotonic versions, append-only history) are enforced once, in the domain layer, not re-implemented per caller.
- New signal sources (a new bounded context) can feed the Trust Engine or Knowledge Graph by adding an event subscriber, without modifying either engine's core — this is the direct fix for Base44's "trust score bolted on top of 8 already-built silos" failure mode.
- Trade-off: this is more upfront structure than either prior build had (Base44 had none; Emergent had it for 4 of what are now 13 contexts). The 13-context scope is deliberately larger than either prior attempt — see `docs/REBUILD_PLAN.md` §4 for the resulting ~38–40 week timeline, and `docs/DOD.md` §3 for which contexts are in vs. out of MVP scope.
