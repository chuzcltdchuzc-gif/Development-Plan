# ADR-014 — PostgreSQL Atomic Parcel Number Allocation

**Status:** Accepted — extends ADR-013 (Parcel Aggregate & Registry Domain Model). Does not
modify ADR-009 through ADR-013; see §"Relationship to the frozen baseline."

**Date:** 2026-07-19

**Scope:** B3 Slice 2 only — migration `0008_registry_parcel_counters.py`, the
`ParcelNumberAllocator` port/adapter, and `ParcelService.create_parcel`'s integration with it.
No mutation commands, ownership transfer, geometry, evidence, or survey capability — those
remain out of scope per this slice's authorization.

## Revision note

This ADR's first draft chose a **per-tenant** counter, scoped by `tenant_id`. Live concurrency
verification (two tenants concurrently registering parcels in the same country) exposed that
this contradicts ADR-013 / migration `0007_parcels.py`'s own `ix_parcels_number_unique`
constraint, which makes `parcel_number` unique **database-wide**, not per tenant: two tenants
each starting their own sequence at `1` produce the identical string `LV-NG-000001`, and the
second tenant's insert is rejected outright by that constraint. This was found and fixed before
this slice's initial review, not after — no per-tenant design was ever shipped or reviewed as
final. The document below describes the corrected, **per-country_code** design; the rejected
per-tenant alternative is kept in §"Alternatives considered and rejected" for the record,
including why it seemed reasonable at first and exactly what live testing exposed.

## Context

ADR-013 reserved `parcels.parcel_number` as a nullable column with a database-level partial
unique index already in place — global, not tenant-scoped, because a land registry number is
meant to identify one parcel unambiguously across the whole jurisdiction, not merely within one
surveying firm's private ledger. ADR-013 explicitly deferred the allocation *mechanism* to this
ADR. ADR-005 documented Emergent's MongoDB allocator as a `find_one_and_update` with
`$inc`/upsert — in practice, a single mutable counter document, locked and incremented per
allocation. This platform is PostgreSQL (ADR-003), and a literal port of that mechanism is
neither idiomatic nor architecturally sound here: it would mean a bare, non-transactional
`SEQUENCE`, which silently produces gaps on any rollback since `nextval()` is never undone.

## Decision

### The allocation mechanism: a per-country_code upsert-counter table

```sql
INSERT INTO registry_parcel_counters (country_code, last_allocated)
VALUES (:country_code, 1)
ON CONFLICT (country_code) DO UPDATE
SET last_allocated = registry_parcel_counters.last_allocated + 1
RETURNING last_allocated
```

One row per country, created lazily on that country's first-ever allocation. A single atomic
SQL statement handles both "this country has never allocated before" (the `INSERT` branch,
starting at `1`) and "increment the existing counter" (the `ON CONFLICT DO UPDATE` branch) — no
separate existence-check, no race window between checking and creating. `parcel_number` is
formatted as `LV-{country_code}-{last_allocated:06d}` (e.g. `LV-NG-000001`).

**Why per-country_code, not per-tenant:** `parcel_number` carries a database-wide unique
constraint (`ix_parcels_number_unique`, migration `0007`), because it is meant to be read as a
national registry identifier — any tenant, regulator, or member of the public referencing
`LV-NG-000001` must mean exactly one parcel, not "tenant X's parcel #1, which happens to share a
string with tenant Y's parcel #1." A per-tenant counter cannot satisfy that constraint the
moment two tenants operate in the same country, which is the normal case for a multi-tenant
registry, not an edge case — confirmed to fail immediately under live concurrency testing
(§"Revision note" above). Scoping the counter by `country_code` instead keeps every tenant
registering parcels in the same country drawing from one shared, gapless sequence, which is
exactly what a database-wide unique constraint requires.

**Why not a single fully-global counter (no partition at all):** would still satisfy
uniqueness, but would serialize *every* tenant across *every* country on one row, and would
mean each country's numbering starts from an arbitrary point instead of `1` — worse on both
contention and readability than per-country_code, for no compensating benefit, since `NG` and
`GH` parcels already need different formatted prefixes and therefore naturally partition by
country regardless.

**Why not a bare `SEQUENCE`:** Postgres sequences are deliberately non-transactional —
`nextval()` advances immediately and is never rolled back, even if the surrounding transaction
aborts. That means a failed registration attempt would permanently burn a parcel number,
producing a gap for no domain reason (an implementation artifact, not a legitimate skip). The
upsert-counter table, by contrast, is an ordinary row mutation like any other — governed by the
same transaction as everything else in the request, so a rollback undoes it exactly like it
undoes the parcel insert itself.

**Why not a literal Mongo port:** Mongo's `$inc`/upsert is, in effect, a single mutable document
with atomic-increment semantics. The natural Postgres translation is a *row* locked and
incremented per allocation — which is what this design does, just partitioned by the key that
actually matches `parcel_number`'s real uniqueness scope (country), not an app-convenient one
(tenant) that turned out to be the wrong scope entirely.

### Concurrency model

Two concurrent allocation attempts for the **same country_code** (regardless of which tenant
each request belongs to): the second transaction's `INSERT ... ON CONFLICT DO UPDATE` blocks on
the row-level lock the first transaction holds, until the first commits or rolls back.
- **First commits:** the second proceeds against the now-updated value — sequential, no
  duplicates, no gap.
- **First rolls back:** the second proceeds against the *original* value, receiving the exact
  number the first transaction would have received — no duplicate, no gap, no wasted number.

Two concurrent allocation attempts for **different countries**: no shared lock at all — fully
parallel, zero contention. Two tenants registering in the *same* country now correctly share one
lock and one sequence — this is the point of the design, not a limitation of it: it is what lets
`parcel_number` remain a real, database-wide unique identifier.

### Transaction model

Allocation executes in the **same request-scoped Unit-of-Work transaction** as the parcel
insert itself (`app.kernel.uow.get_db_session` — unchanged, frozen, ADR-009 §10). Both the
`ParcelNumberAllocator` and the `ParcelRepository` are built from the same per-request
`AsyncSession` via FastAPI's dependency caching (the identical pattern `get_auth_service`
already relies on to share one transaction across multiple repositories) — not a new mechanism,
a reuse of an existing one. `ParcelService.create_parcel` calls the allocator, then
`Parcel.allocate_parcel_number()` (the exact domain guard ADR-013 already built, unused until
now — no domain-layer change needed for this slice at all), then `ParcelRepository.add()`. All
three happen inside one transaction; if any step fails, the whole thing rolls back together,
including the counter increment.

### Failure handling, rollback, and recovery guarantees

- **Allocation has no distinct failure mode of its own.** The only precondition (a resolved
  `ctx.tenant_id`) is already checked, fail-closed, before the allocator is ever called
  (ADR-013's existing guard) — there is no "allocation denied" path requiring its own audit
  event beyond what already exists: the same audited event `create_parcel` already produces
  (§"Audit integration" below).
- **Rollback never creates a duplicate and never wastes a number** — proven both by the
  transaction model above and by live testing (§"Live verification" in the completion report): a
  forced rollback after allocation, followed by a fresh successful allocation, yields the *same*
  number the rolled-back attempt received.
- **Recovery / restart:** the allocator is entirely stateless in the application process — all
  state lives in `registry_parcel_counters`. A backend restart, a new replica, or any number of
  concurrent app-server processes all read/write the same Postgres rows with the same
  guarantees; there is no in-memory counter to lose, no leader election, no distributed
  consensus required. This is a direct consequence of choosing a database-native mechanism over
  an application-level one.

### Audit integration

No second audit mechanism. `registry.parcel.created`'s existing payload (ADR-013) is extended
to include the allocated `parcel_number` — allocation and creation are now one atomic operation
from the caller's perspective, so one audit entry describing the whole outcome is more accurate
than two entries describing an operation that was never actually separable.

### RLS on `registry_parcel_counters`

Unlike every other table since migration `0001`, this table holds no tenant-owned data — only a
country code and a counter, shared across every tenant operating in that country. Its RLS
policy therefore does not attempt to match a specific `tenant_id` (there is none to match);
instead it admits any *authenticated* request — `current_setting('app.tenant_id', true) <> ''`
(a real tenant-scoped session) `OR current_setting('app.is_super_admin', true) = 'true'` — and
denies a session with neither set, keeping the same fail-closed default every other table uses.
RLS is still `FORCE`d and the grant is still `SELECT, INSERT, UPDATE` only, no `DELETE`, matching
the codebase-wide least-privilege convention.

### Relationship to the Parcel Aggregate

The allocator does not touch parcel lifecycle, ownership, geometry, or authorization — it has
exactly one responsibility, producing a number, and hands it to the aggregate via the guard
method the aggregate already exposed for this purpose. The Parcel aggregate remains the sole
authority on whether that number may ever be reassigned (it may not — `allocate_parcel_number`
raises on a second call, unchanged from ADR-013).

### Alternatives considered and rejected

1. **Per-tenant counter (this ADR's own first draft)** — rejected on discovery, not merely
   considered: seemed reasonable in isolation (shards lock contention per tenant, no
   cross-tenant information leak through gaps), but contradicts `parcel_number`'s existing
   database-wide unique constraint the instant more than one tenant operates in the same
   country — the normal case for this platform, not an edge case. Found via live concurrent
   testing across two tenants sharing a country, not via review or inspection; see §"Revision
   note."
2. **Bare `SEQUENCE`** — rejected: non-transactional, produces implementation-artifact gaps on
   rollback (see above).
3. **Advisory lock (`pg_advisory_xact_lock`) around a `SELECT ... FOR UPDATE` + separate
   `UPDATE`** — rejected as unnecessary complexity: functionally similar to the chosen
   upsert-counter approach but requires two round-trips and manual lock-scoping instead of one
   atomic statement Postgres already guarantees is race-free.
4. **Client-generated numbers (UUID-based or random)** — rejected outright: parcel numbers need
   to be human-legible, sequential, and jurisdiction-meaningful for a real land registry; a UUID
   or random string satisfies uniqueness but none of the other requirements.

### Future scaling considerations

Per-country sharding of lock contention means the design scales with the number of countries the
platform operates in, not against it — a busy country's registration volume never slows down any
other country's. If a *single* country's own registration throughput ever becomes the bottleneck
(a much later-stage problem than this platform faces today), the standard next step is
partitioning that country's counter further (e.g., by state/region) — an additive change to this
table's key, not a redesign of the mechanism. Note that this is a genuinely harder problem than
the (incorrect) per-tenant design implied, precisely because the real uniqueness scope is
national, not tenant-private — any future partitioning must preserve database-wide uniqueness of
`parcel_number`, not merely per-partition uniqueness.

## Relationship to the frozen baseline

- **ADR-013** — reuses `Parcel.allocate_parcel_number()` exactly as designed, and reuses (does
  not modify) `0007_parcels.py`'s `ix_parcels_number_unique` global constraint; this ADR's
  allocator is designed to satisfy that existing constraint, not to change it.
- **ADR-009 §10 (Unit-of-Work)** — unchanged; the allocator is a new *consumer* of the existing
  per-request transaction, not a modification to how it works.
- **ADR-009 §7 / ADR-010 (RLS model)** — `registry_parcel_counters` gets `FORCE`d RLS and a
  least-privilege grant like every table since migration `0001`, with a policy shape adapted (not
  reusing the tenant-match template verbatim) because this table's data is not tenant-owned; see
  §"RLS on `registry_parcel_counters`."
- **No frozen decision required amendment.**

## Consequences

- Every parcel now receives a real, unique, nationally-scoped `parcel_number` at creation time —
  the `parcel_number: None` behavior ADR-013 documented for Slice 1 is gone; this is a
  deliberate, documented behavior change for this slice, not a regression.
- B3 Slice 3 (mutation commands) can rely on `parcel_number` always being populated for any
  parcel it operates on going forward.
- The per-country_code counter table is a new, small piece of durable state with its own
  migration, RLS policy, and grants — reviewed with the same rigor as every table since `0001`.
- Two tenants registering parcels in the same country now correctly share lock contention on
  that country's counter row during concurrent registration — an intentional consequence of
  `parcel_number` being a real, database-wide unique identifier, not a design cost to be
  optimized away.
