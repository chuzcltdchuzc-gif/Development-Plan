# ADR-030 — Audit Chain Concurrency, Ordering, and Linearization

**Status:** **ACCEPTED — 2026-09-13, on explicit Governance Authority ratification. IN FORCE.** This
ADR authorizes exactly the architecture described below — the global hash-linked DAG topology, its
six verifier invariants, and the completeness/ordering limitations disclosed alongside them. It does
**not** authorize implementation of any of it: no code, migration, verifier change, lock, sequence,
constraint, anchor, or API is authorized by this ratification; see "Explicit exclusions" under
"Approval Gate" below.

**Date drafted:** 2026-09-12. **Ratified:** 2026-09-13.

**Drafted following:** GD-009 Batch 1's own mandatory concurrency-test requirement (§11/§15)
reproducing a live, real-Postgres audit-chain fork — confirmed both on the blocked Batch 1 branch
and, independently, on unmodified `origin/main`'s existing eager-independent audit path — recorded
in `docs/AUDIT_CHAIN_CONCURRENCY_REALITY_AUDIT.md`.

**Scope:** Decides the audit chain's required topology and the verification semantics that follow
from it — a decision `docs/adr/ADR-007-audit-trail-evidence-model.md` never explicitly made and
`docs/adr/ADR-029-audit-transaction-semantics-and-outcome-integrity.md` correctly did not attempt
(its own Alternatives table names concurrency "unaffected by this axis" — accurate for the
transaction-*atomicity* question it was deciding, silent on the chain-*topology* question this ADR
now decides). Does **not** implement anything — no code, migration, retry logic, or verifier
rewrite is created by this ADR. Does **not** itself resume GD-009 Batch 1, and does **not**
authorize `ADR-028`'s HTTP exposure.

**Constitutional anchors:** LV-000 v1.8 Article VIII §1 (attributable actor), §3 (audit chain,
resolvable reference — read closely in "What ADR-007/Article VIII §3 actually guarantee" below);
Article IV (non-adjudication, unaffected by anything this ADR decides).

## Ratification Record

Ratified by Governance Authority for AquaSavannah LandVault, **2026-09-13**, following a formal
Governance review (`ADR-030 GOVERNANCE REVIEW PASS WITH REQUIRED TEXTUAL REMEDIATION`) and the five
required textual remediations that review identified — the completeness limitation (§6), the
explicit reachability invariant (§2), ordering semantics (§7), the global-topology disclosure
statement (§4), and the persistent-environment scope correction ("Historical audit records") —
applied before ratification. This record does not alter the draft; it identifies what ratification
covers:

- **Global hash-linked DAG selected** (§1): multiple entries may legitimately share one predecessor;
  a fork is not, by itself, evidence of tampering.
- **Six verifier invariants required** (§2): genesis/root validity, per-entry hash validity,
  referential validity, reachability, acyclicity, branch legitimacy.
- **Partial-order semantics** (§7): `prev_hash` establishes a causal-reference order only; siblings
  have no chain-defined relative timing; `created_at`/insertion/commit order remain separate,
  non-cryptographic concepts.
- **Completeness classification: Acceptable with explicit limitation** (§6): DAG verification cannot,
  by itself, prove terminal-leaf, whole-branch, or tail deletion did not occur; this is a widened, not
  newly created, version of the prior linear model's own tail-truncation blind spot. Database
  access controls (`REVOKE UPDATE, DELETE`) remain the primary, distinct defense against ordinary
  deletion — not a cryptographic completeness proof.
- **No completeness anchor adopted** (§6): external checkpoints, signed manifests, WORM anchoring, or
  any related infrastructure are named, not authorized.
- **ADR-007 topology interpretation refined, not rewritten** ("Governance treatment of ADR-007 and
  GD-009"): ADR-007's tamper-evidence, append-only, and integrity objectives remain in force; the
  unstated one-successor-per-predecessor assumption is retired.
- **ADR-029 unchanged**: transaction-atomicity semantics and this ADR's topology/verification
  semantics remain distinct concerns; neither invariant is touched.
- **GD-009 remains Accepted/In Force; Batch 1 remains suspended** until a DAG-aware verifier is
  separately authorized, implemented, merged, and post-merge verified, and resumption is explicitly
  authorized — ratification of this ADR alone does not resume it.
- **ADR-028 HTTP/API exposure remains blocked**, independent of and unshortened by this ratification.
- **No implementation authority granted**: no verifier code, migration, constraint, lock,
  serialization, sequence, anchor, scheduled job, API, or frontend change is authorized here.

## Context

### The finding, precisely

`docs/AUDIT_KERNEL_ATOMICITY_REALITY_AUDIT.md` §4 named, but did not prove, a "Case D" concern:
`audit()`'s `prev_hash = await store.last_hash()` read and its later `INSERT` are not locked or
serialized, so two concurrent calls could compute the same `prev_hash` and both commit. GD-009
Batch 1's own mandatory concurrency test proved it, live, against real Postgres — and, critically, a
follow-up investigation (`docs/AUDIT_CHAIN_CONCURRENCY_REALITY_AUDIT.md` §3) proved the identical
fork occurs using **only the unmodified, already-merged `origin/main` eager-independent path** —
`app.kernel.audit.audit()` and `app.kernel.audit_postgres.EagerPostgresAuditStore`, exactly as they
exist in production today, no GD-009 code involved at all. **This is a pre-existing defect in the
audit kernel's original design, not something GD-009's transaction-coupled successful-mutation
audit path introduced.** GD-009 Batch 1 plausibly widens the pre-existing window for the two call
sites it would migrate (a transaction-coupled row's flush-to-commit gap can span an entire request,
versus the eager path's two-round-trip gap) — but it did not create the underlying vulnerability,
and fixing it is not, and should not be treated as, Batch-1-scoped work.

### What ADR-007/Article VIII §3 actually guarantee

Read closely, neither governing text requires what the current `verify_chain()` implementation
assumes:

- **`docs/adr/ADR-007-...md`, Decision 1 and Context:** requires event *atomicity* (now ADR-029's
  subject) and a "real `verify_chain()` integrity checker" closing the gap that "no function
  anywhere actually verified the hash chain for tampering." The word "tampering" is doing real work
  here — the stated concern is **detecting after-the-fact alteration of an existing entry**, not
  **guaranteeing a single, total, linear insertion order across concurrent writers**. ADR-007 never
  uses the words "linear," "total order," or "single successor."
- **LV-000 Article VIII §3:** *"Every state change writes to the audit chain, and every record that
  a change occurred carries a resolvable reference to its audit entry."* This requires (a) an entry
  exists for every state change, and (b) that entry is findable by reference (`audit_ref` resolves
  to a real `entry_id`). It says nothing about the chain's *topology* — a resolvable reference works
  identically whether the chain is a strict line or a DAG.

**The strict, single-predecessor linear-chain assumption is not a governance requirement at all —
it is an unstated implementation choice baked into `verify_chain()`'s specific walk logic** (§2
below), inherited from a Merkle/blockchain-style mental model the original Emergent audit's design
evidently carried over without anyone deciding, explicitly, that LandVault's own evidentiary needs
require it. This ADR is the first instrument to examine that choice directly.

### Fork consequence, precisely — not tamper, not corruption, a false alarm

`app.kernel.audit._compute_hash` hashes only one row's own content
(`entry_id, action, resource_type, resource_id, decision, principal_id, payload, created_at,
prev_hash`) — it never depends on any other row's state. **A fork does not compromise any
individual row's tamper-evidence**: `entry.recompute_hash() == entry.hash` still holds for every
row regardless of how many siblings share its predecessor. What breaks is only
`verify_chain()`'s own linear-walk assumption: on encountering the second of two forked rows (by
`created_at` order), it finds `entry.prev_hash != prev` and returns `False` — **indistinguishable,
today, from genuine tampering.** This is a false-positive corruption alarm, not a security
vulnerability: no deletion, substitution, or forgery becomes newly possible; no row's own integrity
degrades; the platform would, however, incorrectly report "chain broken" the first time two
legitimate concurrent writes happen to race, which is itself a real operational/governance risk
(false alarms erode trust in the mechanism and could mask a genuine future tampering signal in the
noise) — but a materially different, and less severe, category of problem than the one first
suspected.

## Decision

### 1. Required topology — Alternative D/F, a hash-linked DAG with redefined verification

LandVault's audit chain does not require, and should not claim, strict global total ordering.
**Selected topology: a hash-linked directed acyclic graph.** Each entry still references exactly one
`prev_hash` at write time (unchanged), but **more than one entry may legitimately reference the same
predecessor** — a concurrent-write fork is a normal, expected shape, not an error state. Verification
(§2 below) is redefined accordingly: per-entry hash correctness and per-edge referential validity are
required; a single successor per predecessor is not.

This is selected over a strict single global chain (rejected — the exact defect this ADR exists to
close) and over a strict per-tenant chain (considered and not selected — §"Alternatives
considered," §"Global vs. tenant scope").

### 2. Chain-integrity invariants a future verifier must enforce

Replacing `verify_chain()`'s current single-predecessor linear walk, a DAG-aware verifier must
confirm, for every entry, all six of the following — **reachability is listed as its own invariant,
not left implicit in the combination of the others**, per direct Governance-review instruction and
per this ADR's own empirical red-team (§"Completeness limitation" below), which implemented and
exercised each of these six checks independently against a real, constructed graph:

1. **Genesis/root validity** — exactly the entries whose `prev_hash == GENESIS_HASH` are legitimate
   roots (today, in practice, exactly one per chain instance, but the invariant is "every root is a
   genesis reference," not "there is exactly one entry with no predecessor referenced by anyone" —
   see §"Global vs. tenant scope" for why plural roots may become legitimate).
2. **Per-entry hash validity** — `entry.recompute_hash() == entry.hash` for every entry, exactly as
   today, recomputed from the immutable fields the existing `_compute_hash` algorithm already uses.
   Unaffected by anything in this ADR.
3. **Referential validity** — every non-genesis entry's `prev_hash` equals the `hash` of some entry
   that exists in the store. A `prev_hash` with no matching row is invalid — this is the actual
   tamper/deletion signal for *interior* nodes, distinct from the old "at most one successor"
   assumption.
4. **Reachability** — every audit entry, following zero or more valid `prev_hash` edges backward,
   must ultimately reach the recognised genesis/root. This is **not** the same check as referential
   validity: referential validity confirms each individual edge points somewhere real; reachability
   confirms the *entire chain of edges* from any given entry actually terminates at genesis, rather
   than, say, looping indefinitely or dangling on a technicality referential validity alone would
   miss. This ADR's own red-team investigation (§"Completeness limitation" below) implemented this as
   a distinct recursive check, separate from invariant 3, and confirmed it is needed as its own,
   explicitly stated requirement — not something the other five invariants happen to already imply.
5. **Acyclicity** — no predecessor traversal, following `prev_hash` backward from any entry, may
   revisit an entry already seen in that same traversal. Structurally very unlikely given `prev_hash`
   must reference an *already-existing* hash at write time (an entry cannot reference its own
   not-yet-computed hash, nor a not-yet-written descendant's), but stated explicitly rather than
   merely assumed, mirroring this repository's own established discipline (`docs/adr/ADR-028-...md`'s
   `evidence_actor_attributions` cycle-rejection precedent, which found a theoretically-impossible-
   sounding cycle *was* achievable via a multi-row `INSERT` and required an explicit guard — this ADR
   does not assume `audit_log`'s insertion pattern is immune to an analogous surprise merely because
   it looks structurally impossible).
6. **Branch legitimacy** — explicitly, not merely tolerated: two or more entries legitimately sharing
   one `prev_hash` must verify as `True`, not `False`.

**What these six invariants can and cannot detect, stated plainly:** together, they reliably detect
altered entry contents (invariant 2), a missing *interior* predecessor that a surviving descendant
still references (invariants 3–4), and cycles (invariant 5). **They cannot, by themselves, prove the
dataset is complete** — see "Completeness limitation" below, a distinction this ADR's own
Governance review specifically required be stated here rather than left to be discovered later.

### 3. What this does NOT require

- **No schema migration.** `prev_hash`/`hash` columns and their current types are unchanged; no
  `UNIQUE(prev_hash)`, no new column, no chain-head table, no sequence.
- **No lock, no `SERIALIZABLE`, no retry logic** anywhere in the write path. `audit()` and
  `audit_staged()` (as GD-009 Batch 1 already designed them) require **zero change** under this
  decision — the fix is entirely in how the chain is *read and verified*, never in how it is
  *written*.
- **No new runtime dependency.**

### 4. Global vs. tenant scope

`audit_log` has no `tenant_id` column today — tenant identity, where present, lives only inside the
untyped `payload` JSONB (confirmed directly, migration `0001`). A per-tenant chain (Alternative B)
would require adding that column (a real schema change this ADR does not authorize), and would still
need a principled answer for genuinely tenant-less entries — registration-time events (the tenant
does not exist yet), `super_admin` cross-tenant actions, and PEP-layer deny audits that fire before
any tenant context is resolved. A single, global DAG sidesteps this entirely: every entry, tenant-
scoped or not, participates in the same graph, and per-tenant *querying* (which is what operators
and future WORM/export tooling actually need — "show me tenant X's history") remains fully
achievable by filtering on `payload->>'tenant_id'` (already how every existing consumer of
`audit_log` reads tenant information) without requiring the chain's own topology to be partitioned.
Partitioning by tenant would also not have solved the concurrency problem outright — two concurrent
writers *within the same tenant* (a realistic, even common, case: two field agents submitting
evidence for the same tenant seconds apart) would still race under a per-tenant chain-head lock,
just with a smaller blast radius than a single global lock would have.

**Cross-tenant disclosure — no new risk is introduced.** Keeping one global graph, rather than
partitioning by tenant, was checked explicitly for whether it opens a new authorization or
disclosure path, against the actual current repository facts: `audit_log` has no tenant-partitioned
chain topology today, and its existing RLS `SELECT` policy is already unconditional
(`FOR SELECT USING (true)`, migration `0001`) — a fact predating this ADR and already reviewed under
`docs/adr/ADR-029-...md`'s own "RLS treatment" analysis, not something this ADR alters in any way.
`hash` and `prev_hash` are one-way SHA-256 digest values; possessing another tenant's entry's hash
reveals nothing about that entry's actual `payload` content on its own (pre-image resistance). No
current tenant-facing runtime API exposes chain traversal or `verify_chain()` — both remain internal,
called today only from the hermetic test suite. **The change from a strict-linear interpretation to
a DAG interpretation therefore introduces no new cross-tenant authorization or disclosure path** —
this ADR governs topology and verification semantics only, and this section's finding must not be
read as approving, expanding, or otherwise deciding anything about broader tenant-facing audit
access, which remains entirely ungoverned by this document.

### 5. Denial/failure audit compatibility

Denial and failure audits (the unmodified `EagerPostgresAuditStore` path, unaffected by ADR-029/
GD-009) participate in the same global DAG on exactly the same terms as successful-mutation entries
— they already do today, since `audit_log` has never distinguished write-path by schema, only by
which session performed the `INSERT`. Nothing about this decision changes their durability
guarantee, their independence from the caller's business transaction, or their eligibility to be a
`prev_hash` predecessor or successor for any other entry, including a concurrently-racing
successful-mutation entry (exactly the Case B scenario reproduced in
`docs/AUDIT_CHAIN_CONCURRENCY_REALITY_AUDIT.md` §4) — under the redefined verifier, that race
resolves to two legitimate siblings, not a false corruption alarm.

### 6. Completeness limitation — branch-pruning and tail-truncation are not detectable by this model alone

**This section records an empirically-proven limitation of the selected model, surfaced by formal
Governance review of this ADR's own first draft, which did not originally disclose it.** A
red-team investigation constructed the following graph directly in a real, throwaway Postgres
database — `Genesis → A`, `A → B`, `A → C`, `B → D`, `D → E` — and ran the six-invariant verifier
from §2 against it after each of four deletion scenarios, executed as the schema-owning role
(deliberately bypassing the ordinary application role's `REVOKE UPDATE, DELETE`, to test the
verifier's own logic independent of that access control):

| Case | Deletion performed | Surviving rows | §2 verifier result |
|---|---|---|---|
| Baseline | none | A, B, C, D, E | **valid** |
| A | interior node B (D still references it) | A, C, D, E | **invalid — detected** (dangling reference on D; E unreachable) |
| B | terminal leaf C only (nothing references it) | A, B, D, E | **valid — undetected** |
| C | entire terminal branch D→E | A, B, C | **valid — undetected** |
| D | everything after A (tail truncation) | A only | **valid — undetected** |

**Interior-node deletion — where a surviving entry still references the deleted one — is reliably
detected** by invariants 3 and 4 (referential validity, reachability). **Terminal-leaf deletion,
whole-branch deletion, and full tail-truncation are all silently undetectable by §2's invariants
acting alone**, because nothing surviving in the dataset references what was removed — there is
nothing left to notice the absence.

**This is not a defect specific to the DAG.** The prior strict-linear model shares the identical
limitation for its own single deletable tail: a linear verifier cannot cryptographically detect
deletion of its current terminal entry, for the same reason — no surviving row references it. **What
the DAG genuinely widens is the *surface* of that pre-existing blind spot**: a linear chain has
exactly one deletable-without-detection entry at any time (the current tail); a DAG legitimately
permits multiple simultaneous leaves across concurrent branches, and every one of them is
independently, silently prunable, without leaving any dangling surviving reference.

**Database access control and cryptographic verification are two separate controls, and this ADR
does not conflate them.** `audit_log`'s `REVOKE UPDATE, DELETE` grant (already in force, unaffected
by this ADR) is the actual, primary defense against deletion through the ordinary application
pathway — the `landvault_app` role that every real request uses simply cannot issue the `DELETE`
statements this red-team used. The hash-linked DAG's own guarantee is narrower and must never be
stated or implied more broadly than it is: **it provides tamper evidence for the records and
references that remain present; it does not, on its own, establish that no privileged actor (a
schema-owning role, direct database console access, or any future capability with `DELETE`
privilege) removed all evidence of a terminal branch.** "The DAG verifies" must never be read as "no
deletion occurred" — only as "everything currently present is internally consistent and every
interior reference resolves."

**Classification: Acceptable with explicit limitation.** Neither `docs/adr/ADR-007-...md` nor LV-000
Article VIII §3 (re-confirmed in "What ADR-007/Article VIII §3 actually guarantee" above) requires
cryptographic proof of complete-history inclusion — both require tamper-evidence of what exists and
a resolvable reference for each mutation, both of which this model provides. This ADR therefore
selects the DAG as **acceptable for LandVault's actual governed requirement**, while explicitly
disclosing, rather than silently omitting, that it does not close the tail-pruning gap — a gap that
was never closed by the prior linear model either, and that this ADR does not judge disproportionate
to leave open given the cost of closing it fully (see below).

**Future completeness anchoring — named, not adopted.** If Governance later determines that
cryptographic proof of dataset completeness (detecting even a privileged-actor branch or tail
deletion) is a required property, the following mechanisms exist and would need their own,
separately governed architecture decision: an externally committed periodic graph checkpoint; a
signed manifest or root commitment stored outside `audit_log` itself; a WORM/archive checkpoint (the
same category of mechanism `docs/adr/ADR-007-...md` Decision 2 and its WORM storage decision already
gesture toward for Evidence, not yet extended to the audit chain); or another minimal completeness
anchor. **This ADR does not authorize, and does not adopt, any of these** — it names them solely so a
future reader does not need to rediscover the option space if stronger completeness is ever required.
No external anchor, checkpoint, WORM implementation, schema change, or background job is created by
this document.

### 7. Ordering semantics

**`prev_hash` under this ADR establishes a partial, causal-reference order — never a platform-wide
chronological total order.** This must be stated explicitly, not left to be inferred from §1's
passing remark that strict total ordering is not required: a future reader of the chain must not
mistake DAG position for proof of relative timing.

Concretely, for a graph shaped

```
      B
     /
A
     \
      C
```

**B and C have no chain-defined relative order.** Both referencing `A` establishes only that `A` was
the most recent entry each one's own writer observed as available when it computed its own
`prev_hash` — it does **not** establish, and must never be read to imply, whether B occurred before
C, C occurred before B, or the two were genuinely concurrent. The chain structure alone cannot answer
that question once more than one entry may legitimately share a predecessor.

Separately, and independently:

- **`created_at` remains ordinary metadata** — a server-stamped timestamp, not a cryptographic
  ordering guarantee, and already known (per the original reality audit) to sometimes run behind the
  true event order for the eager-independent path specifically (an eager audit entry can be stamped
  and committed before the business row it describes even exists, if that business transaction is
  still open).
- **Database insertion order is not automatically business-event order** — two entries can be
  inserted in either order relative to when the real-world events they describe actually happened,
  independent of anything this ADR decides.
- **Commit order is not encoded by sibling position in the graph** — the earlier "Fork consequence"
  discussion already noted that an eager entry can commit before a transaction-coupled sibling that
  was staged first; the DAG's topology does not resolve, hide, or worsen this — it simply does not
  claim to answer the question at all.
- **Consumers — human or automated — must not infer legal, causal, or chronological priority from
  branch position.** Any future feature that needs a genuine "which of these two happened first"
  answer must obtain it from a source this ADR does not provide (e.g., an application-level sequence
  or explicit business-logic ordering), not from `prev_hash` topology.

## Alternatives considered

| | A — Advisory lock | B — Per-tenant chain-head row lock | C — Sequence-derived predecessor | D/F — DAG + redefined verification (selected) | E — `UNIQUE(prev_hash)` + retry | G — Transactional outbox / single writer |
|---|---|---|---|---|---|---|
| Eliminates the fork | Yes, for lock holders | Yes, within a tenant only | Only if combined with A/B or G | N/A — redefines "fork" as legitimate, not eliminated | Yes — forces the losing writer to retry against the new head | Yes — single serial writer |
| Preserves strict linearity | Yes | Yes, per tenant | Only combined with A/B/G | **No, deliberately** | Yes | Yes |
| Schema/migration impact | None | New `tenant_id` column + chain-head table | New `sequence` column (BIGSERIAL) | **None** | New `UNIQUE` index on `prev_hash` | New outbox table |
| New runtime dependency | None | None | None | **None** | None | A background worker/scheduler this codebase has never had (Engineering Rule #5 territory) |
| ADR-029/GD-009 write-path compatibility | Requires holding a lock for the caller's *entire* business transaction duration on the transaction-coupled path — see §"Deadlock/duration analysis" | Same concern, scoped to tenant | Sequence allocation alone doesn't resolve the race without also locking or going async | **Trivial — zero change to `audit()`/`audit_staged()`** | Requires `SAVEPOINT`-based retry *inside* the caller's own transaction for the transaction-coupled path — real complexity exactly where ADR-029 wanted simplicity | Outbox row shares the caller's transaction trivially; the *chain materialization* is a separate, async, eventually-consistent step — reintroduces exactly what ADR-029 already rejected as disproportionate |
| Denial/failure-path compatibility | Must acquire the same lock from a session-less context (PEP) — awkward | Same, plus "which tenant's lock" is undefined pre-authentication | Unaffected | **Unaffected — no change to that path at all** | Eager path's own retry is simple (self-contained in `PostgresAuditStore.append()`); transactional path's retry is the hard case | Unaffected for the outbox row; materialization ordering across eager/staged rows becomes a new design question |
| Contention/throughput | Global serialization point — see §"Performance" | Reduced, not eliminated (same-tenant concurrent writers still serialize) | N/A alone | **None — fully concurrent, no lock anywhere** | Retry-on-conflict under load, not blocking, but retry storms possible under high same-instant concurrency | Single writer is the throughput ceiling by construction |
| Operational complexity | Low–moderate | Moderate (new table, per-tenant key management) | Low, but incomplete alone | **Low — a verifier-logic change only** | Moderate (retry loop, savepoint handling, index) | High (new worker, delivery semantics, idempotency) |
| Verifier complexity | Unchanged (still linear) | Unchanged (linear per tenant) | Unchanged if sequence used only for ordering | **Moderate — new DAG-walk verifier, invariants stated in §2** | Unchanged (still linear) | Unchanged for the materialized chain; new verification surface for outbox-to-chain consistency |
| Matches what ADR-007/Article VIII §3 actually require | Stricter than required | Stricter than required | Stricter than required, and incomplete alone | **Matches exactly — tamper-evidence + resolvable reference, no more** | Stricter than required | Stricter than required, plus reintroduces ADR-029's already-rejected eventual-consistency gap |

**Alternative A (advisory lock) is not selected**: holding a lock across an entire request's
business transaction on the transaction-coupled path (to serialize predecessor selection against
every other writer, globally) would make every `record_attribution`/`correct_attribution` call (and,
eventually, every migrated successful-mutation call) wait on every other one, platform-wide, for the
duration of the *slowest* concurrently-committing request — a global serialization bottleneck this
ADR's own §"Minimal architecture" principle argues against building when a zero-cost alternative (D)
exists.

**Alternative B (per-tenant lock) is not selected**: reduces but does not eliminate the underlying
race (same-tenant concurrency still forks), requires a schema change this ADR would need to justify
independently, and leaves tenant-less entries (registration, PEP-layer denials, `super_admin`
actions) without a principled lock scope. Named as the most defensible fallback if a future,
concrete operational need for genuine per-tenant total ordering emerges — not needed today.

**Alternative C (sequence-derived predecessor) is not selected standalone**: a monotonic counter
alone does not resolve the race — allocating sequence numbers is itself concurrency-safe in
Postgres (`BIGSERIAL`/`IDENTITY`), but *deriving the hash-chain predecessor from "whichever row
currently holds sequence N−1"* still requires either a lock (converging to Alternative A) or async
materialization (converging to Alternative G) to know that predecessor has actually committed.
**A version of this idea survives as an optional, non-required complement** — see "Future,
separately-decidable enhancement" below.

**Alternative E (`UNIQUE(prev_hash)` + retry) is the closest runner-up**, and is not selected
primarily on ADR-029/GD-009 compatibility grounds (item 10 of this investigation's own charter): it
preserves strict linearity, which D deliberately gives up, but at a real cost this ADR judges
disproportionate given D achieves everything the governing text actually requires for free. Making
it work for the transaction-coupled path specifically requires `SAVEPOINT`-based retry *inside* the
caller's own business transaction (catch the unique-violation, `ROLLBACK TO SAVEPOINT`, re-read
`last_hash()`, recompute the hash, re-`flush()`) — achievable, but real complexity precisely where
ADR-029 chose transaction-coupling *because* it was simpler than every alternative it compared
against. If a future, concrete requirement for strict linearity emerges that D cannot satisfy, E is
the next alternative to revisit, not A/B/G.

**Alternative G (transactional outbox) is not selected**, for the same reasons ADR-029 already gave
and this ADR does not need to re-litigate: a new background-worker dependency (Engineering Rule #5),
and it would only make the *materialized* chain eventually consistent — worse, not better, than what
D achieves immediately.

### Future, separately-decidable enhancement (not authorized by this ADR)

A purely additive `BIGSERIAL`/`IDENTITY` `sequence` column, populated automatically by Postgres at
insert time, used **only** for approximate operational/export ordering (e.g., "list entries in the
order Postgres happened to durably assign them," useful for WORM archival or forensic review) —
**never** as an input to `prev_hash` computation or chain verification, and never a claim of causal
or total order across concurrent writers (Postgres assigns sequence values without regard to
commit order, so a `sequence`-ordered list can still show a later-value row committing before an
earlier-value row's own transaction commits — this must be documented plainly if the column is ever
added, not silently assumed away). **None of the six invariants in §2 requires this column to exist**
— it is not needed for DAG validity, and this ADR names it as worth a future, separate,
narrowly-scoped proposal if an operational need for it is identified — it does not authorize
creating it, and any future proposal to add it requires its own schema and architecture authority,
exactly as any other migration in this repository would.

## ADR-029 compatibility — confirmed, not merely asserted

Checked directly against `docs/adr/ADR-029-...md`'s two invariants: the successful-mutation
invariant ("commit or roll back together") and the denial/failure invariant ("independently
durable") are both entirely about **when** an entry becomes durable relative to the mutation it
describes — this ADR does not touch that question at all. The selected topology (D/F) requires zero
change to `audit()`, `audit_staged()`, `PostgresAuditStore`, or `EagerPostgresAuditStore` — only to
the separate, read-time `verify_chain()` function. A future GD-009 Batch 1 resumption can proceed
exactly as already designed, once this ADR is accepted, without revisiting any part of its write-path
implementation.

## Historical audit records

No destructive action of any kind is proposed. Existing entries are never rewritten, and no entry's
prior tamper-evidence claim is weakened. **A historically linear dataset is a valid special case of
the selected DAG** — every invariant in §2 is satisfied trivially by a chain that happens to have
exactly one entry at each generation, so no historical row anywhere requires rewriting, backfilling,
or reinterpretation merely because this ADR is accepted.

**Scope of what this investigation actually inspected — stated precisely, not categorically.** This
investigation inspected repository state and throwaway local PostgreSQL environments only, created
and dropped within each test run (confirmed: every live test run to produce this ADR and
`docs/AUDIT_CHAIN_CONCURRENCY_REALITY_AUDIT.md` used such a database). **It did not inspect or verify
the audit history of any external persistent environment, including any Supabase-hosted environment
referenced by repository configuration or CI.** The presence or absence of historical audit forks in
any such environment is therefore **unknown** to this ADR — this document does not claim persistent
environments exist, and does not claim they do not; either claim would exceed what this investigation
actually established.

**If historical forks are later discovered in a persistent environment**, they must be treated
neutrally, not retroactively assigned a cause this ADR cannot support: **do not automatically label
them tampering, and do not automatically declare them legitimate concurrency** — report them as
historical branches requiring contextual evaluation (timestamps, known deployment/traffic patterns
around the time they were created, and whichever other evidence is actually available), the same
evidentiary discipline this repository already applies to every other historical-record question. If
and when a persistent database begins accumulating real entries, the DAG-aware verifier (§2) should
be run against it before any question about its historical integrity is treated as closed; a `False`
result under the *old* linear verifier against real historical data would need to be re-evaluated
under the *new* DAG-aware one before concluding it represents genuine tampering rather than a
previously-undetected, and entirely legitimate, concurrent-write fork.

## Governance treatment of ADR-007 and GD-009

This ADR does not rewrite ADR-007. It resolves an ambiguity ADR-007's own text left open (chain
topology was never explicitly decided) in the direction its actual stated purpose (tamper evidence,
resolvable reference) already supports — the same category of relationship ADR-029 already
established with ADR-007 Decision 1's atomicity language: refinement of an underspecified area, not
a reversal of anything actually decided.

**GD-009 disposition**: GD-009 remains Accepted/In Force. Its Batch 1 implementation authority is
**not** revoked, superseded, or amended by this ADR — Batch 1's write-path design (transaction-
coupled staging, explicit per-call opt-in, the two named attribution events) requires no change
under the selected topology. **Batch 1 implementation remains suspended** (per GD-009 §11's own
stop-and-return instruction) until this ADR — or whichever architecture Governance ultimately
accepts for the chain-concurrency question — is itself Accepted, and until a verifier consistent
with the accepted topology exists to re-confirm GD-009 §15's mandatory concurrency tests pass under
it. This ADR does not itself lift that suspension or grant any new implementation authority; per
"Governance Decision question" below, resuming Batch 1 implementation requires its own explicit
Governance act once this architecture question is settled.

## Governance Decision question

- **Is this ADR sufficient on its own to decide the architecture?** Yes — this is exactly the
  category of decision an ADR exists to make in this repository (a chain-topology/verification
  question, decided before implementation, per Article VI §1), following the same precedent
  ADR-029 already set for a closely related audit-kernel question.
- **Is a separate Governance Decision required before implementation?** Yes, on the same ADR-026/
  ADR-029 precedent GD-009 itself already relied on: architecture acceptance ≠ implementation
  authorization. A future implementation phase (rewriting `verify_chain()` to the DAG-aware
  invariants in §2, plus re-running GD-009 §15's concurrency tests against it) requires its own
  Governance Decision, separate from this ADR's acceptance.
- **Does accepting this ADR, by itself, resume GD-009 Batch 1?** No. GD-009's own implementation
  authority already covers Batch 1's write-path scope; what was missing was confidence that the
  chain-verification layer would not falsely flag Batch 1's own legitimate concurrent writes as
  corruption. Once this ADR is accepted and a DAG-aware verifier exists (a future, separately
  authorized implementation step), Batch 1 may resume under GD-009's existing authority — this ADR
  does not require GD-009 to be re-ratified, only for its stop condition's underlying concern to be
  architecturally resolved first.

## ADR-028 HTTP gate

Unaffected and unchanged. `docs/adr/ADR-028-...md`'s mutating Evidence Attribution HTTP endpoints
remain prohibited, independent of this ADR, until GD-009 Batch 1 is implemented, tested, formally
reviewed, squash merged, and post-merge verified — which itself now additionally depends on this
ADR (or an equivalent architecture decision) being accepted first, per the GD-009 disposition above.

## Deadlock, retry, and failure analysis (for the alternatives considered, not the selected design)

Since D/F requires no lock or retry mechanism at all, this section applies only to alternatives A, B,
and E, recorded here for completeness of the comparison rather than as design detail for what is
actually selected:

- **A/B (locking):** lock ordering risk is low (a single chain-head resource per scope, never
  acquired alongside a second lockable chain-head in the same transaction) but **lock duration** is
  the real concern — for the transaction-coupled path, the lock would need to be held from
  `audit_staged()`'s call until the caller's own final commit, i.e., for the remainder of whatever
  business logic follows in that request. A slow downstream call (e.g., a future Storage write, per
  `docs/adr/ADR-026-...md`'s Evidence upload sequence) inside that same transaction would hold the
  chain-head lock for its entire duration, serializing every other writer against that one slow
  request — a genuine, quantifiable throughput risk under any realistic concurrent load, and the
  central reason D is preferred.
- **E (unique constraint + retry):** no lock held, so no lock-duration risk — but a `SAVEPOINT`-based
  retry inside an active business transaction adds a new failure mode (the retry loop itself failing,
  or a bounded retry count being exhausted under sustained contention) that does not exist under D,
  and duplicates work (re-reading `last_hash()`, recomputing the hash) proportional to contention.
- **Denial/failure racing success (all alternatives):** under D, this is not a special case — both
  paths simply write, independently, and both may legitimately share a predecessor. Under A/B, the
  session-less PEP-layer deny path cannot participate in a lock acquired via a request-scoped
  session at all, forcing either an exception for that path (weakening the lock's own guarantee) or
  a separate, connection-level locking primitive — added complexity D avoids entirely.
- **Process crash while a lock is held (A/B only):** Postgres releases a session-scoped advisory
  lock or a transaction-scoped row lock automatically on connection loss/rollback — no orphaned lock
  persists past the crashed session, but any writer that was blocked waiting on it during the crash
  window experienced real, if bounded, added latency. Not applicable to D.

## Performance implications

D adds no contention at all — verification is a read-time, offline/batch concern (`verify_chain()`
is not, and per this ADR's design remains not, called on any write's hot path), and the write path is
completely unchanged. This scales identically to how `audit()`/`audit_staged()` already scale today,
for every future tenant, field agent, surveyor, automated job, or evidence upload this platform
adds — because nothing about how they write changes. This is the direct, load-bearing reason D was
selected over every alternative that adds contention: this ADR does not need to guess at future
scale to know D introduces zero new bottleneck, where A/B provably do.

## Minimal architecture

No message queue, distributed ledger, blockchain, or external consensus service is proposed,
considered necessary, or would be justified by this problem — explicitly named here, per this
investigation's own instruction, precisely because a PostgreSQL-only, zero-new-dependency,
zero-schema-change solution (D) already fully resolves the actual defect.

## Implementation consequences (future work — not authorized here)

- **Verifier rewrite**: `app.kernel.audit.verify_chain()` would need to change from a single linear
  walk to the DAG-validating logic in §2 — a future, separately authorized implementation step.
- **No migration.**
- **No change to `audit()`, `audit_staged()`, `PostgresAuditStore`, or `EagerPostgresAuditStore`.**
- **GD-009 §15's concurrency tests** (already written, on the blocked branch) would need to be
  re-run against the new verifier's semantics as part of that future implementation's own acceptance
  criteria — not merely "no fork occurs" (which will still occur, legitimately, under D) but "the
  new verifier correctly accepts the legitimate fork and correctly rejects a genuinely broken
  reference."

## Consequences

- The audit chain's actual guarantee (tamper-evidence + resolvable reference) becomes precisely
  matched by its verification logic, closing a gap between what was claimed and what was checked
  that has existed, unnoticed, since ADR-007's original implementation.
- GD-009 Batch 1's write-path design requires no change and may resume once this architecture is
  accepted and implemented.
- No new operational bottleneck, schema change, or dependency is introduced.
- A previously-unstated assumption (strict linear ordering) is retired in favor of the topology this
  platform's actual governing texts always actually required.

## Approval Gate

This ADR is **ACCEPTED**, per the Ratification Record above. Acceptance authorizes only the
architecture described above — the global hash-linked DAG topology, its six verifier invariants, and
the completeness/ordering semantics disclosed alongside them — never implementation of any of it.

**Explicit exclusions.** Acceptance of this ADR does not authorize: any change to
`app.kernel.audit.verify_chain()` or any other code; any database migration; any new constraint,
index, lock, or serialization mechanism; any sequence or monotonic-ordering column; any external
anchor, checkpoint, or manifest mechanism (named, not adopted, in "Completeness limitation" above);
any scheduled verifier job; any external/WORM storage integration; any modification to GD-009 Batch
1's blocked implementation; any API, router, or frontend change; and any background-job
infrastructure. Every one of these, if ever pursued, requires its own, separate Governance
authorization — exactly as "Governance Decision question" above already states for the verifier
rewrite specifically.

**GD-009 dependency, restated.** GD-009 remains Accepted/In Force; its Batch 1 execution remains
suspended under its own concurrency hard stop. Resumption requires, in sequence: this ADR's
acceptance (satisfied); separate Governance authorization for a DAG-aware verifier implementation;
that verifier formally reviewed, squash merged, and post-merge verified; and explicit Governance
authorization to resume GD-009 Batch 1. Acceptance of this ADR alone does not satisfy any of the
remaining three conditions.

See the companion readiness report, `docs/ADR-030_READINESS_REPORT.md`, and the subsequent Governance
review and textual-remediation verification that preceded this ratification.
