# LandVault Audit Chain Concurrency — Reality Audit

**Type:** Governance reality audit. Read-only against `main`; no backend file on `main` was
modified. Produced against `origin/main` at `cdda3c318fa6cbb22a0e5591769dfb38097112e4` (GD-009
ratified, Batch 1 implementation attempted and blocked on a separate, unmerged local branch — see
§4).

**Date:** 2026-09-12

**Triggering event:** GD-009 Batch 1 implementation, driven by its own mandatory concurrency-test
requirement (§11/§15 of `docs/GD-009-...md`), reproduced a live, real-Postgres hash-chain fork —
two committed `audit_log` rows sharing the same `prev_hash` — 5/5 times under a deterministic,
controlled-barrier interleaving. Per GD-009's own explicit instruction, implementation halted
immediately without attempting a fix, and this audit was commissioned to determine the fork's true
scope and origin before any architecture decision is drafted.

## Executive conclusion

**The fork is a pre-existing defect in the audit kernel's original design (ADR-007-era), not
something introduced by ADR-029/GD-009's transaction-coupled successful-mutation audit path.**
Reproduced directly, twice, independently:

1. Against the **unmodified `origin/main` eager-independent path** (`app.kernel.audit.audit()` /
   `app.kernel.audit_postgres.EagerPostgresAuditStore`, exactly as merged, in a separate detached
   git worktree containing zero modification from any line on `main`) — **fork reproduced.**
2. Against the **blocked GD-009 Batch 1 branch's new transaction-coupled path**
   (`audit_staged()`) — **fork reproduced**, both transactional-vs-transactional and
   transactional-vs-eager.

Batch 1 did not create this vulnerability. It inherited it, and — because a transaction-coupled
audit row's flush-to-commit window can be materially longer than the eager path's single,
near-instantaneous round trip — Batch 1 plausibly **widens** the pre-existing window for whichever
call sites are migrated to it. The underlying mechanism, however, is identical and was already
present in every audited-mutation code path on `main` before GD-009 existed.

## 1. Baseline verified

- `origin/main` SHA: `cdda3c318fa6cbb22a0e5591769dfb38097112e4`. `docs/adr/ADR-007-...md`: Accepted.
  `docs/adr/ADR-029-...md`: ACCEPTED/IN FORCE. `docs/GD-009-...md`: ACCEPTED/IN FORCE.
- Blocked implementation branch `feat/gd009-batch1-transactional-audit` exists locally,
  **uncommitted, unpushed**, containing the Batch 1 changes and the concurrency test that
  triggered the stop condition — preserved unchanged per GD-009 §11's own instruction; not treated
  as repository baseline anywhere in this document.

## 2. Current audit-chain mechanism, read directly

- `audit_log` schema (`migrations/versions/0001_identity_and_audit.py`, unmodified): `id` (UUID PK),
  `action`, `resource_type`, `resource_id`, `decision`, `principal_id`, `payload` (JSONB),
  `prev_hash` (`String(64)`, **no index, no constraint**), `hash` (`String(64)`, **`UNIQUE`**),
  `created_at` (indexed). **No `tenant_id` column** — tenant identity, where present, lives only
  inside the untyped `payload` JSONB, not as a queryable/constrainable column.
- `app.kernel.audit._compute_hash`: a pure function of one row's own content
  (`entry_id, action, resource_type, resource_id, decision, principal_id, payload, created_at,
  prev_hash`) — never depends on any other row's live state at verification time.
- `app.kernel.audit.audit()` / `_build_entry` (the shape unchanged since ADR-007): `prev_hash =
  await store.last_hash()` (a `SELECT hash FROM audit_log ORDER BY created_at DESC LIMIT 1`), then,
  separately, `store.append(entry)`. **No lock, no transaction spanning both steps, no
  `prev_hash` uniqueness constraint at the database level.**
- `EagerPostgresAuditStore.last_hash()` and `.append()` (unmodified): **each opens its own, separate
  session** from the shared `session_factory()` — confirmed directly from source. This means even a
  single, ordinary, already-shipped `audit()` call performs its predecessor read and its durable
  write as two distinct Postgres round trips, with nothing holding them together.
- `app.kernel.audit.verify_chain()` (unmodified): walks `all_entries()` (ordered by `created_at`
  ascending) as a **single linear sequence**, asserting each entry's `prev_hash` equals the
  immediately-preceding entry's `hash`. It has no concept of, and cannot represent, more than one
  valid successor per predecessor.

## 3. Live reproduction — unmodified `origin/main`

Method: a detached git worktree checked out directly at `cdda3c318fa6cbb22a0e5591769dfb38097112e4`
(zero modified files, verified by `git worktree add ... origin/main --detach`), running only the
merged, unmodified `app.kernel.audit`/`app.kernel.audit_postgres` code against a real, throwaway
Postgres database with the actual Alembic migration chain applied. Two `EagerPostgresAuditStore`
calls' underlying primitives (`PostgresAuditStore.last_hash()`/`.append()` — the exact two calls
`EagerPostgresAuditStore.last_hash()`/`.append()` each make internally) were driven in a controlled
order: both predecessor reads completed before either write committed — reproducing, deterministically,
the same interleaving two genuinely concurrent `audit()` calls hitting the database at nearly the same
instant would experience under Postgres's default `READ COMMITTED` isolation.

**Result:**

```
prev_hash read by A: 0000...0000 (GENESIS)
prev_hash read by B: 0000...0000 (GENESIS)
committed row 1: hash=67a2863fedfd2d4d.. prev_hash=0000000000000000..
committed row 2: hash=cc198829134de915.. prev_hash=0000000000000000..
FORK CONFIRMED ON UNMODIFIED MAIN: True
```

Both writes committed successfully; no database mechanism rejected the second. **This is the
identical mechanism, and the identical outcome, as the reality audit's own original, narrower "Case
D" observation (`docs/AUDIT_KERNEL_ATOMICITY_REALITY_AUDIT.md` §4) — that document named it a
"plausible additional integrity question... not asserted as proven." This audit proves it.**

## 4. Live reproduction — blocked Batch 1 branch

Method and full results already recorded in the GD-009 Batch 1 implementation report and preserved,
unmodified, in `backend/tests/live/test_transactional_audit_concurrency_live.py` on the
`feat/gd009-batch1-transactional-audit` branch (uncommitted). Summary:

- **Case A (transactional vs. transactional):** two `audit_staged()` calls, each on its own session,
  each flushed before either committed — both read the same `prev_hash`, both committed. Fork.
- **Case B (transactional vs. eager-independent):** one `audit_staged()` call left uncommitted while
  a representative eager `audit()` call (unmodified path) committed in between — both read the same
  `prev_hash`, both committed. Fork.
- **Case C (repeated execution):** 5 independent throwaway-database runs of Case A — **5/5 forked.**

## 5. What actually differs between the two paths

The **mechanism** is identical (read-before-write, no lock, no constraint). The **exposure window**
differs:

- Eager path: the gap between `last_hash()`'s read and `append()`'s commit is two back-to-back
  Postgres round trips — small, but structurally always present (confirmed §3; not a hypothetical).
- Transaction-coupled path (Batch 1): the gap between `audit_staged()`'s read/flush and the
  caller's own request-transaction's eventual commit can span however long the rest of that
  request's business logic takes — materially longer, for the two call sites Batch 1 migrates.

Neither path is exempt; Batch 1 does not introduce a new category of risk, but it does plausibly
raise the probability of the existing one manifesting for the call sites it touches, exactly as
`docs/GD-009-...md` §11 (as textually remediated before ratification) already anticipated and
required proof for.

## 6. Verification-layer consequence, precisely stated

`verify_chain()`'s current linear-walk implementation treats a fork as **indistinguishable from
tampering**: on encountering the second of two forked rows (by `created_at` order), it finds that
row's `prev_hash` does not equal the immediately-preceding row's `hash`, and returns `False` — the
same signal a genuinely altered or deleted entry would produce. **This is a false-positive
corruption alarm, not an actual integrity breach**: `_compute_hash`'s per-row recomputation
(`entry.recompute_hash() != entry.hash`) is unaffected by a fork — every individual row's own
content-hash remains self-consistent and tamper-evident regardless of how many siblings share its
predecessor. A table can be simultaneously append-only, cryptographically self-consistent at the row
level, and topologically forked — these are independent properties, and the current `verify_chain()`
conflates the second with a linear-sequence assumption the schema and the governing text never
actually required (see the companion ADR-030 draft, §"What ADR-007/Article VIII §3 actually
guarantee").

## 7. Historical-fork status

No production or persistent-data deployment exists in this repository's current state (IMVP/pre-launch
phase; every live test in this repository, including the two run for this audit, uses a throwaway
database created and dropped within the test run). **No historical fork can be, or was, checked in
any persistent store, because none exists to check.** A Supabase-hosted project is referenced
elsewhere in this repository's CI configuration (`Supabase Preview` check) — this audit did not, and
was not authorized to, inspect any such live environment's actual data; if one holds real inserted
`audit_log` rows already, its history should be checked using the verification methodology ADR-030
proposes before that ADR is treated as closing this question definitively.

## Recommended next step

Raise this document, alongside the blocked Batch 1 evidence, to Governance Authority as the
evidentiary basis for a dedicated architecture decision (ADR-030) on audit-chain concurrency,
ordering, and linearization — scoped to the chain-topology/verification question this audit isolates,
independent of, and prior to, any resumed GD-009 Batch 1 implementation attempt.
