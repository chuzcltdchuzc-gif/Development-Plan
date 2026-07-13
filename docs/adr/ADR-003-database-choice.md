# ADR-003 — Database Choice

**Status:** Accepted
**Date:** 2026-07-13

## Context

Nearly every critical bug found across both audits traced back to the same root cause: no real ACID transactions and no native row-level security.

- Base44 (a document-store-backed low-code platform): `CreditWallet`'s update policy allowed the record owner to edit their own `credit_balance` field directly (record-level RLS, not field-level) — a direct self-service financial-fraud vector. `OrganizationWallet`, `ServiceRequest`, and `Invoice` had `update: {}` — unconditionally public. 15 entities had no RLS block at all.
- Emergent (MongoDB via Motor): a standalone (non-replica-set) MongoDB deployment silently falls back to no-transaction mode, so a crash between a wallet `$inc` and its corresponding transaction-log insert leaves no idempotency record — a webhook retry can re-credit the same purchase. `lvServiceBilling`'s credit-reservation flow crashed on an undefined variable *after* committing a partial write, leaving reserved credits permanently locked with no compensating transaction.

## Decision

**PostgreSQL, self-managed** (not a managed document store, not Supabase-managed) for Identity role/tenant mapping, Registry, Spatial Intelligence (with **PostGIS**), Survey, and Economic/Billing.

- Real multi-statement ACID transactions for every money-moving or state-transition operation (see ADR-006).
- **Native row-level security policies**, enforced at the database engine — not an application-layer convention that's easy to forget or bypass by using a different code path (both audits found exactly this "opt-in and forgettable" pattern repeated across dozens of call sites).
- PostGIS for genuine polygon overlap, adjacency, and spatial-index queries (see `docs/REBUILD_PLAN.md` B4) — the audits found both prior builds' "duplicate detection" was GPS-proximity-distance-only, never real geometry containment/overlap.
- Alembic for migrations, with the rule (see `docs/ENGINEERING_RULES.md` §6) that every migration ships reversible and with its RLS policy update in the same commit.

Evidence binaries remain in S3-compatible object storage (never in Postgres) — see ADR-007. Knowledge Graph (ADR-002) uses a dedicated graph store, fed by projection off the event outbox, never Postgres directly for its traversal queries.

## Consequences

- Structurally closes the entire "non-atomic financial operation" and "forgot the RLS policy" bug classes rather than relying on developer discipline per call site.
- Requires an actual migration/ops discipline (Alembic, connection pooling, PostGIS extension management) that a managed platform would otherwise absorb — accepted as the cost of the control this rebuild needs, particularly for money and land-title data.
- Self-managed (not Supabase) per the Operator's explicit instruction that Supabase not become the entire architecture; Supabase Auth remains a documented fallback option for identity only (ADR-004), not for the database.
