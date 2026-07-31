# ADR-023 — Registry Ownership and Status History

**Status:** Accepted — Implemented, 2026-07-31. Migration `0011`, the domain value objects
(`OwnershipAssertion`/`StatusAssertion`), the `ParcelHistoryRepository` port with its Postgres
adapter and in-memory fake, and the history-writing calls inside `create_parcel`/`update_parcel`/
`archive_parcel` are merged on `feat/adr-023-ownership-status-history`. Verified: 158/158 tests
passing (148 pre-existing + 10 new), `ruff`/`mypy` clean, and a full live rehearsal against real
Docker Postgres — migration up/down/up repeatability, RLS cross-tenant isolation, both independent
append-only layers, FK parent-relationship enforcement, and end-to-end HTTP creation/update/archive
flows with `audit_ref` resolving to real, payload-consistent audit entries. See the implementation
report for exact evidence and the one honestly-flagged gap: "no orphan row on failure" is backed by
a unit test plus the kernel's existing rollback-on-exception behavior, not a live fault-injection
demonstration. Originally accepted 2026-07-30, after one revision addressing four governance
requirements raised on review (migration/backfill strategy; append-only enforcement strengthened to
two independent layers; explicit Unit-of-Work/transaction confirmation; explicit RLS parity
confirmation).

**Date:** 2026-07-30 (proposed and accepted same day, after revision)

**Revision note:** The version first drafted described append-only enforcement, the transaction
boundary, and RLS parity in prose, and was silent on backfill entirely. This revision makes all
four explicit and, for append-only enforcement, adds a genuinely new mechanism (the trigger layer)
rather than only restating the original privilege-based one more emphatically — see "Append-only,
enforced at the database" and "Migration and backfill strategy" below.

**Scope:** Registry only. Adds two append-only history tables (`parcel_ownership_history`,
`parcel_status_history`), each populated as a side effect of the *existing* mutation commands
`ParcelService.create_parcel` / `update_parcel` / `archive_parcel` — no new API endpoint, no new
mutation command, no new authorization model. Out of scope: ownership *transfer* as a distinct
command (ADR-015 already left this open — "a decision for whichever slice builds it"), the
non-adjudication automated check required by `docs/ENGINEERING_RULES.md` §10 / LV-000 v1.8 Article
IV §4 (tracked separately, see "Relationship to the non-adjudication rule" below), evidence,
survey, spatial, payments, notifications, or AI.

**Constitutional anchors:** LV-000 v1.8 Article IV (evidence over assertion, non-adjudication);
Article V (bounded context sovereignty — this stays inside Registry, no new context); Article VII
§6 (corrections append, history retained and marked superseded); Article VIII §2–§3 (RLS ships
with the migration; every state change writes to the audit chain); Article X §3 (single
authorisation path — no new one introduced).

## Context

`docs/EXECUTION_PLAN.md` §4.1 and §7 require an append-only ownership/status history "owned by
Registry," explicit that **the Parcel aggregate's current-owner reference does not change** —
`current_owner_name`/`current_owner_contact` remain exactly what ADR-013 already made them: a
*current reference*, never a history (ADR-013 invariant #12, restated in ADR-015). This ADR adds
the history *alongside* that reference, not instead of it.

The constitutional driver is LV-000 v1.8 Article IV: every ownership-related record must be "a
recorded assertion by an identified actor, resting on a stated basis, at a recorded time" — never
a determination of who owns what. Today, when `update_parcel` changes `current_owner_name`, the
audit chain records *that* a change happened and *who* made it, but nothing records the *basis*
for the assertion (what the change rests on) in a structured, queryable form, and nothing
preserves the *prior* asserted holder once it's overwritten. This ADR closes that gap.

## Decision

### Two tables, two triggers, no new command

`parcel_ownership_history` records an assertion about who holds a parcel. `parcel_status_history`
records a status transition. Both are populated **automatically**, inside the same transaction as
the mutation that causes them — no new API endpoint or service method a caller invokes directly:

- **`parcel_ownership_history`** gets a new row whenever `update_parcel` changes
  `current_owner_name` and/or `current_owner_contact` (compared against the pre-mutation values,
  inside `ParcelService.update_parcel`), and once at `create_parcel` if either field was supplied
  at creation (the initial assertion). A row that changes neither field writes no ownership-history
  row at all — e.g. an `address`-only update writes to `parcels` and the audit chain exactly as it
  does today, nothing new.
- **`parcel_status_history`** gets a new row whenever `archive_parcel` succeeds (`ACTIVE ->
  ARCHIVED`) and once at `create_parcel` (the initial `ACTIVE` assertion, so the history is
  complete from the parcel's origin rather than starting mid-lifecycle). No restore path exists
  (ADR-015, unchanged), so this table is expected to hold at most two rows per parcel for the
  foreseeable future — that is a consequence of the existing one-way lifecycle, not a new
  constraint this ADR introduces.

Neither table is reachable through its own mutation endpoint. This is a deliberate, narrower scope
than "a generic ownership-assertion API" — it makes the history an honest *record of what Registry's
existing commands actually did*, with no second path that could assert a history entry disconnected
from a real parcel mutation.

### Schema

Both tables share the same shape, matching the minimum columns `docs/EXECUTION_PLAN.md` §7.1
specifies:

```
id               UUID, primary key
tenant_id        String, FK -> tenants.id, NOT NULL
parcel_id        UUID, FK -> parcels.id, NOT NULL
asserted_holder_ref   String, nullable   -- ownership table: current_owner_name/contact, joined;
                                          -- status table: unused (NULL) — status doesn't assert a holder
asserted_status       String, nullable   -- status table: the new status; ownership table: NULL
basis            String, NOT NULL       -- see "Basis" below
recorded_by      UUID, FK -> identity_users.id, NOT NULL
recorded_at      TIMESTAMPTZ, NOT NULL, server_default now()
audit_ref        String, nullable       -- the audit entry's entry_id (app.kernel.audit.AuditEntry)
supersedes_id    UUID, nullable, FK -> self (same table)
```

`asserted_holder_ref` and `asserted_status` are both nullable and mutually exclusive by table
(ownership rows populate the former and leave the latter unused; status rows the reverse) rather
than two separate single-purpose column sets, because the two tables are genuinely separate
tables (per the Execution Plan's own naming), not one polymorphic table — each has exactly one
"what changed" column that matters and the other stays `NULL`, which is simpler than two
differently-shaped tables with no shared column at all and avoids inventing a discriminator column
the Execution Plan doesn't ask for.

### Append-only, enforced at the database, not only by convention — two independent layers

A `GRANT`-only restriction is a convention that a future migration could silently loosen; this ADR
does not rely on it alone. Two independent enforcement layers, both required, neither a substitute
for the other:

1. **Privilege layer** (as in the original draft): `GRANT SELECT, INSERT` only to `landvault_app`
   — **no UPDATE, no DELETE grant**. Matches `parcels`' existing "no DELETE" convention (migration
   `0007`), extended here to "no UPDATE either."
2. **Structural layer (new in this revision):** a `BEFORE UPDATE OR DELETE` trigger on both
   tables (`parcel_ownership_history_append_only`, `parcel_status_history_append_only`) that
   unconditionally raises (`RAISE EXCEPTION 'parcel_ownership_history is append-only; use
   supersedes_id, never UPDATE/DELETE'`), regardless of which role executes the statement. This is
   the layer that actually answers "enforced at the database, not by convention alone": a
   privilege grant depends on which role runs the query; a trigger depends on nothing but the table
   itself, so even a future migration run as the schema-owning role — which necessarily bypasses
   `landvault_app`'s privilege restriction, since it *is* how migrations alter these tables at all
   — still cannot silently UPDATE or DELETE a row without first dropping the trigger explicitly, an
   action that would itself have to appear, reviewable, in a migration diff.

A correction is always a new row with `supersedes_id` pointing at the row it supersedes; the
superseded row is never touched, by construction, not merely by policy.

### RLS — identical in scope and strength to the Parcel aggregate's, confirmed

Both tables carry **exactly** the policy `parcels` has used since migration `0001`, not a
similar or independently-derived one:

```sql
tenant_id = current_setting('app.tenant_id', true)
  OR current_setting('app.is_super_admin', true) = 'true'
```

Confirmed identical on every dimension that matters: same predicate text (copy-pasted into the new
migration, not retyped from memory); `ENABLE ROW LEVEL SECURITY` **and** `FORCE ROW LEVEL SECURITY`
on both new tables, matching `parcels` exactly (`FORCE` is what makes the policy bind even for the
table-owning role — without it, RLS applies only to non-owning roles, which would be a strictly
*weaker* guarantee than `parcels` has, and this ADR requires strength parity, not merely "RLS
exists somewhere"); same session-variable mechanism (`app.tenant_id`, `app.is_super_admin`), set by
the same request-scoped middleware, not a new one; created in the **same migration** as the
`CREATE TABLE` statements (Article VIII §2), never as a follow-up. There is no dimension on which
these tables' RLS is weaker, narrower, or later than the Parcel aggregate's.

### Basis

`basis` is a free-text field recording what the assertion rests on. At this slice, with no
evidence-upload or document-verification capability yet built (B5, not yet started), the only
honest value available is a fixed string describing the mutation that produced it —
`"registrant declaration via update_parcel"` for ownership rows sourced from `update_parcel`,
`"initial registration"` for rows sourced from `create_parcel`, `"registrant declaration via
archive_parcel"` for status rows. This is deliberately not left `NULL` or invented as something
more sophisticated than what exists: Article II §8's discipline ("restating wrongly is worse than
not restating") applies equally here — recording an honest, narrow basis is better than fabricating
a `document_reference` or `evidence_id` this codebase has nothing yet to back. When B5 (Evidence)
ships, `basis` gains real evidence references as a follow-up, additive change — not something this
ADR should anticipate with a speculative schema now.

### Domain layer

A new, small aggregate-adjacent value object per table (`OwnershipAssertion`, `StatusAssertion`)
in `app.contexts.registry.domain`, constructed by `ParcelService` and persisted through a new
`ParcelHistoryRepository` port (`record_ownership`, `record_status`) — mirroring `ParcelRepository`'s
existing shape (a `Protocol`, a Postgres adapter, an in-memory fake), not a new pattern. Neither
history table is modelled as part of the `Parcel` dataclass itself: they are records *about* a
parcel's mutations, not part of the parcel's own mutable state, and `Parcel.update_details()`/
`archive()` continue to know nothing about history-recording — that responsibility stays in
`ParcelService`, which already orchestrates repository calls, exactly as it already orchestrates
`self.allocator.allocate()` alongside `self.parcels.add()` in `create_parcel` (ADR-014).

### Same Unit of Work, same transaction — confirmed, not implied

History writes are **not** a separate step that could commit independently of the parcel mutation
they record. `ParcelHistoryRepository`'s Postgres adapter is constructed from the identical
`AsyncSession` as `PostgresParcelRepository` and `PostgresParcelNumberAllocator` — the same
per-request Unit of Work (`app.kernel.uow.get_db_session`), wired through
`app.contexts.registry.dependencies` exactly as those two already are (FastAPI's dependency
caching resolves `get_db_session` once per request; every provider that depends on it shares one
session, one transaction). Concretely, in `ParcelService.update_parcel`: the parcel's `UPDATE`,
the history row's `INSERT`, and the audit entry's `INSERT` all happen against the same session
before that request's transaction commits. If any one of the three fails, the whole transaction
rolls back — there is no code path that persists a parcel mutation without its history row, or a
history row without the mutation that produced it. This is the identical guarantee ADR-014 already
established for parcel-number allocation ("a rollback undoes the counter increment along with
everything else"); this ADR extends the same transaction boundary to cover history, not a new one.

### Events (audit)

No new event-bus mechanism is introduced — none exists anywhere in this codebase yet, and
inventing one for this slice would be a materially larger architectural change than what
`docs/EXECUTION_PLAN.md` §7.3 asks for. "Emits domain events" is realised, consistent with every
prior slice (`registry.parcel.created`, `.updated`, `.archived`, `.geometry_attached/detached`),
as new `audit()` action names:

- `registry.parcel_ownership.recorded` — first assertion, at creation.
- `registry.parcel_ownership.changed` — a later assertion superseding a prior one.
- `registry.parcel_status.changed` — an archive transition.

Each history row's `audit_ref` is set to the corresponding `AuditEntry.entry_id`, the same
"resolvable reference" shape `docs/EXECUTION_PLAN.md` §7.3 and Article VIII §3 require, mirroring
how `registry.parcel.mutation_denied` already carries context without a dedicated column for it.

### Authorization

**No new authorization model.** History recording happens only as a side effect of
`update_parcel`/`archive_parcel`/`create_parcel`, which already run through
`_authorize_mutation`/`_can_mutate` (ADR-015, unchanged). There is no separate "who may write
history" question to answer, because nothing can write a history row without first passing the
exact creator-or-governance check that already gates the mutation producing it. This is a
deliberate consequence of "no new command, no new endpoint" above, not an oversight.

### The non-adjudication safeguard

Recording an assertion must never render as a determination. `asserted_holder_ref` and
`asserted_status` are surfaced (in any future API response that exposes this history) under
field names and documentation that say "asserted," never "owner" or "title" bare. The
build-time automated check required by `docs/ENGINEERING_RULES.md` §10 (added under
`docs/GOVERNANCE_BASELINE.md` Part C.3, itself required by LV-000 v1.8 Article IV §4) is **not**
implemented by this ADR — it is a cross-cutting CI check, not Registry-specific code, and is
tracked as follow-up work against `docs/EXECUTION_PLAN.md` §7.6's explicit requirement, to be
implemented before this feature's test-matrix gate is considered satisfied.

## Migration and backfill strategy

**History begins at the migration epoch. No backfill is performed.** Parcels that already exist
when migration `0011` runs (in this environment: whatever test/pilot parcels exist in the live
Docker Postgres at migration time) receive **zero** `parcel_ownership_history` /
`parcel_status_history` rows retroactively. This is a deliberate decision, not an oversight, stated
explicitly here per Article II §8's own logic extended from doctrine to data: Registry has no
reliable record of who asserted an existing parcel's current `current_owner_name` value, on what
basis, or exactly when — only that it is the value now on the row. Synthesising a backfilled row
that *looks* like a contemporaneous assertion (a `recorded_at` of "now," a `recorded_by` of
whichever principal happens to run the migration, a fabricated `basis` like "backfilled") would
misrepresent a migration-time snapshot as a recorded-at-the-time assertion — exactly the kind of
manufactured provenance Article IV exists to prevent, applied to this ADR's own data rather than to
a future feature's.

The practical consequence: a parcel created before this migration shows no ownership/status history
until its **next** mutation through `update_parcel`/`archive_parcel`, at which point the *first*
history row is written honestly — describing the new assertion being made *then*, not a
reconstruction of what was true before. A parcel's history being empty is therefore meaningful and
readable on its own terms ("no assertion has been recorded under this mechanism since it existed"),
never confused with "no assertion was ever made" (which the parcel's own `created_at`/
`current_owner_name` already answer, unchanged, exactly as today). If a future need arises to
report on pre-migration state, that is answered by querying `parcels` directly (which already
carries `created_at` and the current reference) — not by this ADR inventing history that was never
recorded.

## Migration

One new migration (`0011`), owned entirely by Registry, additive only:

- `CREATE TABLE parcel_ownership_history`, `CREATE TABLE parcel_status_history`.
- RLS enabled + forced + policy created for both, in the same migration (Article VIII §2), text
  identical to `parcels`' existing policy (see "RLS" above).
- `GRANT SELECT, INSERT` only — no `UPDATE`, no `DELETE`.
- The append-only trigger function and both `BEFORE UPDATE OR DELETE` triggers, created in this
  same migration (see "Append-only, enforced at the database" above) — not a follow-up migration.
- Indexes: `(tenant_id)` on both (matching `ix_parcels_tenant`'s existing shape), `(parcel_id)` on
  both (the expected read pattern — "history for this parcel"), `(supersedes_id)` on both.
- No backfill statement of any kind (see "Migration and backfill strategy" above).
- Tested `down`: drops both triggers, both trigger functions, both policies, and both tables. No
  data migration is needed downward because nothing existed in these tables before this migration
  created them, and nothing was backfilled into them either.

**Implementation note, 2026-07-31:** live rehearsal against Docker Postgres (upgrade 0010→0011,
downgrade back, upgrade again) caught a real defect the design text above could not have revealed —
the first implementation attempt built both tables from one shared tuple of SQLAlchemy `Column`/
`ForeignKey` objects, which silently dropped every foreign key except the self-referencing
`supersedes_id` on the second table created (`parcel_status_history`), confirmed via `\d` against
the live database. Fixed by generating fresh `Column` objects per table. Recorded here per Article
XI §2 — the observation governs, and this is exactly the class of defect "tested up/down" is
supposed to catch, not merely assert.

No change to the `parcels` table itself. No change to `Parcel`'s domain contract, its
`UPDATABLE_FIELDS`, or any existing endpoint's request/response shape (history is written, not yet
exposed — a read endpoint is explicitly deferred, see "Consequences").

## Test matrix (per `docs/EXECUTION_PLAN.md` §7.6 — all to be *observed*, not assumed, before this
ADR's implementation is considered complete)

**Observed, 2026-07-31** — items 1–6 and 8 confirmed both by the automated suite
(`backend/tests/test_registry_ownership_status_history.py`, 10 new tests, in-memory fakes) and by
a live rehearsal against real Docker Postgres (RLS, both append-only layers, FK enforcement, and
real end-to-end HTTP create/update/archive flows with `audit_ref` resolution — see the
implementation report for the exact evidence). Item 7 observed live: upgrade 0010→0011, downgrade
back to 0010 with full object removal confirmed, upgrade again, repeatably. Item 9 remains
genuinely unimplemented, as stated below — not claimed as satisfied.

1. Creating a parcel with an owner reference writes exactly one `parcel_ownership_history` row and
   one `parcel_status_history` row (the initial `ACTIVE` assertion); creating one with no owner
   reference writes zero ownership rows.
2. `update_parcel` changing `current_owner_name`/`current_owner_contact` writes exactly one new
   ownership row, `supersedes_id` pointing at the prior one; changing only unrelated fields
   (`address`, `title`, etc.) writes zero ownership rows.
3. `archive_parcel` writes exactly one status row, `supersedes_id` pointing at the initial `ACTIVE`
   row.
4. Append-only enforced at the database, both layers independently: (a) an attempted
   `UPDATE`/`DELETE` against either table as `landvault_app` fails on privilege (permission
   denied); (b) an attempted `UPDATE`/`DELETE` run as the schema-owning migration role — which
   bypasses (a) entirely — still fails, on the trigger raising its exception. Both must be
   observed failing independently; passing only one would not prove the other layer exists.
5. **Cross-tenant isolation, positive and negative:** tenant A cannot read tenant B's history rows
   (RLS); a `super_admin` can, across tenants (unchanged bypass).
6. Every history row's `audit_ref` resolves to a real `AuditEntry`, and that entry's payload is
   consistent with the history row it corresponds to.
7. Migration `0011` up and down; rollback rehearsed on a staging-like database before merge
   (Article XI §3).
8. Parcel aggregate regression: `Parcel.current_owner_name`/`current_owner_contact` behaviour is
   completely unchanged — history recording is additive, never a substitute for the existing
   reference (ADR-013 invariant #12 still holds).
9. Non-adjudication wording check (tracked separately, per "The non-adjudication safeguard" above
   — this ADR's own test matrix does not claim to satisfy it, since the check itself is
   cross-cutting CI work, not Registry code).

## Relationship to the frozen baseline

- **ADR-013** — `current_owner_name`/`current_owner_contact` remain a current reference, never a
  history, exactly as invariant #12 requires. This ADR adds a parallel, append-only record; it
  does not touch the reference's semantics.
- **ADR-014** — the atomic parcel-number allocator is untouched; this ADR's history tables have no
  relationship to `parcel_number` at all.
- **ADR-015** — the creator-or-governance mutation-authorization model is reused verbatim, with no
  new authorization branch. Ownership *transfer* as a distinct command remains exactly as open as
  ADR-015 left it — this ADR does not decide it.
- **ADR-016** — geometry association is untouched; this ADR's tables carry no geometry reference.
- **No frozen decision requires amendment.**

## Consequences

- Registry gains a genuine, queryable record of ownership and status assertions over time, closing
  the gap between "the audit chain proves a change happened" and "a structured table lets you ask
  what was asserted, by whom, on what basis, when" — the operative distinction LV-000 v1.8 Article
  IV draws.
- No read API is added by this ADR. `GET /v1/parcels/{id}/ownership-history` (or equivalent) is
  left for a follow-up slice, once there is an actual consumer (a portal, a due-diligence export)
  needing to read it — building it now, unused, would be speculative scope this ADR declines to
  add.
- The non-adjudication automated check (`docs/ENGINEERING_RULES.md` §10) remains outstanding after
  this ADR's implementation lands, as a separate, cross-cutting piece of CI work — this ADR's test
  matrix does not claim to close it, and it should not be marked done until that check actually
  exists and runs.
- Future ownership-transfer and evidence-backed `basis` values (B5+) are both explicitly compatible
  with this schema without a breaking change: transfer would write a new ownership-history row
  exactly like today's `update_parcel` path does; evidence-backed `basis` values replace the
  current fixed strings without a column-shape change.
