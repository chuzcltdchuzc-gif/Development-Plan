# GD-010 — Audit DAG Verifier Implementation Authorization

**Status:** **ACCEPTED — 2026-09-14, on explicit Governance Authority ratification. IN FORCE.** This
Decision authorizes exactly the DAG-aware audit verifier implementation described below — the same
category of authorization `docs/adr/ADR-026-evidence-domain-model.md` gave its own "B5.2"
implementation and `docs/GD-009-...md` gave Batch 1. It does **not** authorize GD-009 Batch 1
resumption, `ADR-028`'s HTTP exposure, or anything beyond this Decision's own bounded scope; see
"Explicit exclusions" under "Approval Gate" below.

**Date drafted:** 2026-09-13. **Ratified:** 2026-09-14.

**Operative authority:** **Article XVI §2** — this is a later numbered decision that explicitly
names and relies on `docs/adr/ADR-030-audit-chain-concurrency-ordering-and-linearization.md`
(Accepted, 2026-09-13) as its governing architecture, and explicitly names
`docs/GD-009-audit-transaction-semantics-implementation-authorization-and-adr-007-regularisation.md`
to state precisely what this Decision does **not** do to it. It is not proposed under Article XIV
and does not amend this Constitution. It follows the same architecture-acceptance-≠-implementation-
authorization precedent `docs/adr/ADR-026-evidence-domain-model.md` established and GD-009 itself
already relied on.

## Ratification Record

Ratified by Governance Authority for AquaSavannah LandVault, **2026-09-14**. This record does not
alter the draft; it identifies what ratification covers:

- **Architecture authority: `ADR-030`.** Implementation authority granted: implementation of the
  `ADR-030`-conforming DAG-aware audit verifier only — exactly the six invariants §3 states (genesis/
  root validity, per-entry hash validity, referential validity, reachability, acyclicity, branch
  legitimacy), replacing `verify_chain()`'s current strict-linear walk.
- **No write-path change** (§13): `audit()`, `EagerPostgresAuditStore`, the suspended
  `audit_staged()` design, predecessor selection, hash generation, and every transaction boundary are
  unaffected.
- **No schema migration and no new runtime dependency** are authorized (§14, §15); either stop
  condition, if triggered, halts implementation and returns to Governance rather than being engineered
  around within this Decision's own authority.
- **GD-009 Batch 1 remains suspended** (§20): ratification and implementation of this Decision do not,
  by themselves, resume it — resumption requires a further, separate, explicit Governance act after
  the verifier is implemented, formally reviewed, squash merged, and post-merge verified.
- **`ADR-028` HTTP/API authority remains ungranted** (§22): no router, DTO, OpenAPI change, generated
  client, frontend, or Surveyor Dashboard work is authorized.
- **The preserved branch** `feat/gd009-batch1-transactional-audit` (§21) remains reproduction evidence
  only; implementation proceeds from a clean branch/worktree off `origin/main`, never incorporating
  that branch's files.
- No Marketplace, Partner, Job, Assignment, Customer, accreditation, payments, SECI, EQF, PPI, Rights,
  Legacy Vault, `ADR-021`, or general Background Jobs authority is granted (§23).

## 1. Governance baseline verified for this drafting

Read directly against the current repository, not assumed or carried over from any prior document:

- `origin/main` SHA: **`0275b483d1c4fcdd5de2cfeada3f8407cb6d8dd8`** (the ADR-030 ratification squash
  commit, PR #31).
- `docs/adr/ADR-030-...md`: **ACCEPTED — 2026-09-13, on explicit Governance Authority ratification.
  IN FORCE.**
- `docs/adr/ADR-029-...md`: **ACCEPTED — 2026-09-11, on explicit Governance Authority ratification.
  IN FORCE.**
- `docs/adr/ADR-007-...md`: **Accepted.**
- `docs/GD-009-...md`: **ACCEPTED — 2026-09-11, on explicit Governance Authority ratification. IN
  FORCE** — its own text (§11/§15) already states the exact stop condition that was triggered; Batch
  1 implementation is suspended pending resolution of that condition, which `docs/adr/ADR-030-...md`
  provides at the architecture level and this Decision would provide at the implementation level.
- `docs/adr/ADR-028-...md`: HTTP exposure gate unaffected by anything since its own ratification;
  re-confirmed unchanged in this drafting.
- Article XVI Governance Decision Log (`docs/LV-000-constitution.md`): entries **GD-001 through
  GD-009** exist. No `GD-010` or higher entry exists anywhere in the repository (checked by direct
  search, not assumed).
- **Next available Governance Decision number, confirmed by repository reality: GD-010.**
- **`verify_chain()` consumers, re-derived fresh** (not reused from the ADR-030 governance review):
  `grep -rn "verify_chain"` against a clean worktree at the confirmed baseline finds the identical 11
  call sites across 9 hermetic test files (`test_b1_acceptance.py`, `test_b2_delegations.py`,
  `test_b2_invitations.py` ×2, `test_b2_tenants.py`, `test_b3_registry.py` ×3, `test_b4_spatial.py`,
  `test_imvp3a_supabase_invitation_provisioning.py`, `test_registry_ownership_status_history.py`),
  every one asserting `asyncio.run(verify_chain()) is True` — no runtime endpoint, admin CLI, or
  scheduled job calls it anywhere. No drift since ADR-030's own review of this fact.
- **`audit_log` schema, re-confirmed unchanged**: `hash` carries `UNIQUE`; `prev_hash` carries no
  constraint or index; no `tenant_id` column exists. Every column this Decision's verifier needs
  already exists.

## 2. Purpose

This Governance Decision does exactly one thing: **authorizes implementation of a DAG-aware audit
verifier conforming to the six invariants `docs/adr/ADR-030-...md` §2 already decided**, replacing
`app.kernel.audit.verify_chain()`'s current strict single-predecessor linear walk. It explicitly
names `ADR-030` (its architecture authority) and `GD-009` (to state precisely what it does not
authorize with respect to it — §5 below).

This Decision does **not** authorize: GD-009 Batch 1 resumption; any transactional/successful-
mutation audit implementation; any audit write-path change; any schema migration; any lock,
serialization, retry, or sequence mechanism; any external anchor/checkpoint; any `ADR-028` HTTP/API
work; or any frontend change. Every one of these remains governed exactly as it already is,
unaffected by anything in this Decision.

## 3. Implementation authority — exactly the six ADR-030 invariants, nothing else

The implementation this Decision authorizes must produce a verifier (replacing or refining
`verify_chain()`'s current body — the public function name and zero-argument, `bool`-returning
contract may be preserved unless implementation reality demonstrates otherwise, per §16 below)
enforcing **all six** of the following, exactly as `docs/adr/ADR-030-...md` §2 already decided them:

1. **Genesis/root validity** — entries whose `prev_hash == GENESIS_HASH` are recognised roots.
   `GENESIS_HASH` is a fixed sentinel value, never itself a physical audit row, and **more than one
   entry may legitimately reference it directly** — including two concurrent first-writes that both
   observed an empty audit history before either committed. The verifier must not impose an
   at-most-one-root rule; §5 below requires this be proven, not merely permitted in principle.
2. **Per-entry hash validity** — `entry.recompute_hash() == entry.hash` for every entry, using the
   existing, unmodified `_compute_hash` algorithm and its existing field set. This Decision does not
   authorize changing what is hashed or how.
3. **Referential validity** — every non-genesis entry's `prev_hash` equals the `hash` of some entry
   that exists in the store.
4. **Reachability** — every entry, following valid `prev_hash` edges backward, ultimately reaches a
   recognised genesis/root. For this finite, one-predecessor-per-row model, this is logically implied
   by invariants 3 and 5 together (see §8 below for the reasoning) — it is checked explicitly anyway,
   for conceptual clarity and defense-in-depth, per `ADR-030` §2's own treatment of it as a named,
   separate invariant.
5. **Acyclicity** — no predecessor traversal, from any entry, may revisit an entry already seen in
   that same traversal.
6. **Branch legitimacy** — two or more entries legitimately sharing one `prev_hash` must verify as
   valid, not invalid.

**This Decision authorizes the capability and its six invariants — not a specific internal API
shape, helper-function name, or module layout beyond what §18 below requires.** Implementation-time
engineering judgment, consistent with this codebase's existing conventions, governs the exact
internal form.

**Duplicate-hash handling.** `audit_log.hash` already carries a database-level `UNIQUE` constraint
(confirmed directly, migration `0001`) — under real Postgres, two rows can never share a `hash`. The
implementation will naturally want to build an in-memory lookup structure (e.g., a `hash → entry`
mapping) to achieve the performance shape §17 below requires. **The implementation must not silently
overwrite or discard an entry when constructing that structure if it is ever handed a duplicate-hash
input** (for example, from a fake, test-only, or otherwise non-conforming store) — a naive dictionary
construction that let a second entry silently replace a first sharing the same key could mask the
anomaly and incorrectly report a reduced, incomplete graph as valid. The implementation must do one
of: (a) explicitly detect a duplicate-hash input and treat it as invalid; or (b) use a structure that
cannot silently discard a row on key collision, and explicitly document that it relies on, and is
entitled to assume, the storage layer's own `UNIQUE(hash)` guarantee for production input. **The
prohibited behavior, under either approach, is silently overwriting one entry with another and then
reporting the reduced graph valid.** This does not authorize, and is not evidence of a need for, any
schema change or new constraint — the production constraint already exists; this requirement is
about the verifier's own in-memory correctness when it cannot assume every possible caller respects
that constraint.

## 4. Linear histories remain valid — required proof, not merely assumed

The implementation must include a test proving that an existing, genuinely linear (non-forked)
audit history — the shape every hermetic test's `audit_log` state already takes today, since none
of them exercises real concurrency — verifies as valid under the new implementation, with no
rewriting, backfilling, or reinterpretation of any existing row. `ADR-030`'s own text already states
this is a valid special case of the DAG; this Decision requires it be demonstrated, not merely
asserted, against the actual new implementation.

**Empty-history semantics — preserve existing behavior explicitly.** The current, unmodified
`verify_chain()` returns `True` for a completely empty `audit_log` (its loop over zero entries never
executes, so the function reaches its final `return True` vacuously). **This behavior must be
preserved** — nothing in `ADR-030`'s six invariants requires changing it, since all six are
vacuously satisfied by an empty entry set (there are no entries to violate any of them). The
implementation must not manufacture a physical genesis row, or otherwise treat an empty history as
invalid, in order to give the six invariants "something to check."

## 5. Legitimate forks must pass — required proof

The implementation must include a test proving a branched structure —

```
      B
     /
A
     \
      C
```

— verifies as valid when: A is itself valid; B and C each independently recompute their own hash
correctly; both validly reference A as `prev_hash`; both remain reachable from genesis through A;
and no cycle exists anywhere in the structure. **A duplicate `prev_hash` value, by itself, must
never cause verification failure** — this is the specific defect `ADR-030` exists to close, and a
regression here would silently reintroduce it.

**A second, separate required test: multiple simultaneous genesis-linked roots.**

```
GENESIS
  ├── A
  └── B
```

The implementation must include a test proving that two (or more) entries, each independently
correctly hashed and each directly referencing `GENESIS_HASH` as `prev_hash` — the shape two
concurrent first-writes on an empty audit history would actually produce — both verify as valid.
This is not the same test as the `A→{B,C}` case above: that case forks off a real, existing row;
this case forks off the genesis sentinel itself. **Multiple genesis-linked entries must not be
rejected merely because there is more than one** — an implementation that silently imposed an
at-most-one-root rule would pass every other test in this Decision while still reintroducing
linearity exactly where `ADR-030` §2 explicitly said plural roots may become legitimate.

## 6. Tampered hash must fail — required proof

The implementation must include at least two tests: (a) an entry whose immutable content fields
were modified after the fact without recomputing `hash` — verification must fail; (b) an entry whose
stored `hash` was deliberately replaced with an unrelated, incorrect value — verification must fail.
Both exercise invariant 2 (§3) directly.

## 7. Dangling predecessor must fail — required proof

The implementation must include a test constructing a surviving entry whose `prev_hash` refers to no
existing entry in the store — verification must fail. This exercises invariant 3 directly, and is
the actual interior-deletion/tamper signal `docs/AUDIT_CHAIN_CONCURRENCY_REALITY_AUDIT.md` and
`ADR-030`'s own red-team already proved this class of defect *is* detected by the selected
architecture.

## 8. Reachability — a logically implied invariant, checked explicitly, not an independently constructible failure case

For the audit model as it actually exists — a **finite** set of rows, each carrying exactly **one**
predecessor reference (`prev_hash`, resolving either to `GENESIS_HASH` or to another row) —
**referential validity (invariant 3) together with acyclicity (invariant 5) already logically
guarantee reachability to genesis for every row.** The reasoning: following any row's `prev_hash`
backward must, at each step, either (a) terminate at `GENESIS_HASH`, (b) move to a row that does not
exist, or (c) revisit a row already seen earlier in that same walk. Referential validity excludes
outcome (b); acyclicity excludes outcome (c). No fourth outcome exists in a finite graph where every
node has exactly one outgoing edge — so outcome (a) is the only one left. **A test fixture that is
simultaneously referentially valid, acyclic, and unreachable from genesis therefore cannot exist**
under this model; requiring one would be requiring the implementation to satisfy an impossible test.

**This does not remove reachability from the six `ADR-030` invariants.** `ADR-030` §2 is correct to
name it separately, for conceptual clarity and for defense-in-depth: an implementation bug in either
the referential-validity check or the acyclicity check could otherwise let an actually-broken state
slip through if reachability were never checked at all. In practice, the most natural implementation
computes all three (referential validity, acyclicity, reachability) via **one unified backward
traversal per row** — a walk that terminates successfully at genesis (reachability confirmed),
fails on a missing hash (referential validity's own failure, §7 above), or fails on revisiting an
already-seen node (acyclicity's own failure, §9 below). The implementation must perform this
traversal and must be able to report a reachability failure conceptually; **it need not, and cannot,
be tested by a fixture independent of a dangling reference (§7) or a cycle (§9)** — any concrete
"unreachable" fixture will necessarily be one of those two, and the implementation's §7/§9 tests
already cover the only ways unreachability can actually arise.

Mere row-presence in the table remains insufficient validity — the traversal must actually walk the
full predecessor chain to genesis, not stop after confirming one hop resolves; the §7 and §9 tests,
correctly implemented, already prove this (a fixture that only checked one hop would incorrectly
pass a dangling-reference-two-hops-away or a longer cycle).

## 9. Cycles must fail, safely — required proof, using realistic fixtures

**`_compute_hash` includes `prev_hash` as one of its inputs.** Consequently, a genuinely
hash-consistent cycle — one where every row involved *also* independently passes ordinary per-entry
hash recomputation (invariant 2) — is not a realistically constructible test fixture: a self-cycle
would require `A.hash` to equal `SHA256(..., prev_hash=A.hash, ...)`, and a two-node cycle would
require `A.hash` and `B.hash` to simultaneously satisfy `A.hash = H(..., B.hash)` and
`B.hash = H(..., A.hash)`. Finding such values is equivalent to finding a SHA-256 fixed point —
infeasible in practice, exactly the property SHA-256's preimage resistance exists to guarantee. This
Decision does not require, and no implementation may be faulted for failing to produce, a
cryptographically self-consistent cycle fixture.

The implementation is still required to be cycle-safe, proven via one of the following two
realistic techniques (either is acceptable; this Decision does not prescribe which):

**A. Deliberately corrupted synthetic audit entries** — construct a self-cycle, a two-node cycle, and
a longer (three-or-more-node) cycle using fixtures whose predecessor topology is cyclic even though
their stored hashes cannot all simultaneously satisfy invariant 2 (they will independently also fail
per-entry hash validity — this is expected and acceptable, not a test-design flaw; see "Validation
order" below).

**B. Direct testing of a naturally extracted internal graph/traversal helper** — if the
implementation factors out a graph-validation helper operating on plain in-memory structures (hash →
entry, or an equivalent adjacency representation) rather than on `AuditEntry` objects requiring valid
hashes, that helper may be tested directly against synthetic cyclic structures. **This does not
authorize creating a new public or production-facing API solely to enable this testing** — the same
"no large public error-reporting API... merely because convenient" principle §18 below already states
applies equally here: any such helper must remain internal unless the implementation's natural shape
already calls for it to be otherwise.

**Required outcome, either way:** the traversal terminates (no infinite recursion or loop, no
unbounded resource consumption); the malformed cyclic topology is rejected; and the implementation
demonstrates this via a bounded/safe traversal (e.g., a visited-set guard during the backward walk) —
consistent with how this repository's own `evidence_actor_attributions` cycle-rejection precedent,
`docs/adr/ADR-028-...md`, already required a bounded/guarded walk for an analogous concern, after
finding a cycle *was* achievable via an unexpected mechanism despite looking structurally impossible
in advance. This Decision does not require a cycle fixture to simultaneously satisfy per-entry hash
validity — the following paragraph states how the two failure modes interact.

**Validation order — this Decision governs the final result and safe termination, not a required
sequence of isolated checks.** Because a Technique-A cycle fixture (above) will typically *also*
independently violate invariant 2 (per-entry hash validity), a malformed dataset may legitimately be
correctly identified as invalid by more than one check at once, or by whichever check the
implementation's traversal happens to reach first. **This Decision does not require that cycle
detection be shown to fire in isolation, before or instead of hash-validity detection, for a given
fixture to count as satisfying §9.** The only requirements are: the final result is invalid; the
traversal is safe (bounded, no infinite loop, no unbounded resource consumption); and the
implementation is demonstrably capable of cycle-safe graph handling in general (proven by Technique
A or B above) — not that any single malformed input be artificially constructed to isolate exactly
one cause. An implementer must not read §9 as requiring implementation-specific validation ordering
beyond what correctness itself demands.

## 10. Completeness limitation must remain visible — not solved, not hidden

The implementation's own tests and any accompanying documentation must preserve, not silently drop,
`ADR-030`'s own explicit disclosure: terminal-leaf deletion, whole-terminal-branch pruning, and tail
truncation may all remain undetected by this verifier, because nothing in the surviving graph
references what was removed. **The verifier must not claim, in its docstring, its test names, or any
accompanying documentation, to prove complete-history inclusion.** No anchor, checkpoint, or manifest
mechanism is authorized under this Decision — `ADR-030` named those solely as a future, separately
governed option, not as work this Decision performs.

## 11. Database access controls remain separate

The implementation must not conflate, in code, comments, or tests, cryptographic graph verification
with database-level `UPDATE`/`DELETE` prevention. `audit_log`'s existing `REVOKE UPDATE, DELETE`
grant (unaffected by this Decision) remains the primary, distinct defense against ordinary
deletion — the verifier's own guarantee is narrower, exactly as `ADR-030` §6 already stated, and this
Decision's implementation must not imply otherwise.

## 12. Ordering semantics preserved

The implementation must treat `prev_hash` as a predecessor/reference relation only, never a total
chronological order. The verifier must not reject two legitimately branching siblings based on
`created_at`, insertion order, row `id`, or commit order, and must not use any of those fields to
manufacture an artificial linear ordering the graph itself does not have. A test must exist proving
that two siblings inserted in either possible `created_at` order both verify as valid.

## 13. Write-path boundary — read/verification only

**This Decision does not authorize any change to**: `app.kernel.audit.audit()`; the existing eager,
independently-committing persistence path (`EagerPostgresAuditStore`, `PostgresAuditStore.append()`);
the future, already-designed-but-suspended `audit_staged()`/transaction-coupled path; predecessor
selection at write time (`last_hash()`); hash generation (`_compute_hash`); or any transaction
boundary. This is a read-path/verification change only. **If implementation reality demonstrates that
some genuinely tiny, shared helper (e.g., a hash-recomputation utility already used by both the write
path and the new verifier) requires refactoring, that refactor must not change any write-path
behavior** — exactly the same "extract, do not alter" discipline GD-009's own Batch 1 draft already
applied when it factored `_build_entry` out of `audit()` without changing `audit()`'s observable
behavior. Any change that would alter write-path *behavior*, however small, is outside this
Decision's authority and must stop.

## 14. No schema migration

No migration is authorized. `audit_log`'s existing columns (confirmed directly, unchanged since
`ADR-030`'s own review) already support every invariant in §3 — none requires a new column, index,
or constraint. If implementation reality proves a migration is unavoidable, the implementing
engineer must stop and return exactly:

**`AUDIT DAG VERIFIER BLOCKED — MIGRATION AUTHORITY REQUIRED`**

## 15. No new runtime dependency

No new runtime dependency is authorized. If implementation reality indicates one is required,
Engineering Rule #5 applies, and the implementing engineer must stop and return exactly:

**`AUDIT DAG VERIFIER BLOCKED — NEW DEPENDENCY AUTHORITY REQUIRED`**

## 16. Consumer impact and backward compatibility

The 11 existing `verify_chain()` call sites (§1 above) all assert `is True` against sequential,
non-forked hermetic test data — every one is expected to continue passing unchanged under the new
implementation, since a linear history is a valid special case of the accepted DAG (§4's own
required proof). **No runtime or API consumer may silently receive broader authority or disclosure
capability as a side effect of this change** — confirmed today, no such consumer exists
(`verify_chain()` is called nowhere outside the hermetic test suite); if the implementing engineer
finds this has changed since this drafting, that finding must be reported, not silently absorbed.

## 17. Snapshot consistency and performance

**Snapshot consistency is a correctness requirement, not merely a performance one.** The
implementation must fetch the verification dataset exactly once (`PostgresAuditStore.all_entries()`
already returns the full, fully-materialized entry set in a single query, exactly as
`verify_chain()`'s current implementation already relies on) and validate that one fixed, in-memory
snapshot — it must **not** re-query individual predecessors, or any other subset of the data, while
traversing the graph. Re-querying mid-traversal under concurrent writers could manufacture a false
dangling-reference or false unreachability finding purely as an artifact of mixing two different
database-visibility moments (a row visible to an early query might not be consistently visible to a
later one, or vice versa, depending on transaction timing) — a defect in the *verifier itself*, not a
real property of the data. **No locking is required to obtain this consistency** — a single-snapshot
read needs no coordination with concurrent writers; the verifier simply validates the one dataset it
already received.

Correctness precedes optimization, but is naturally compatible with it here: a single `all_entries()`
call followed by in-memory graph validation, using an indexed (`hash → entry`) lookup structure,
yields an implementation whose cost is approximately `O(V + E)` — effectively `O(V)`, since this data
model gives every row exactly one outgoing predecessor edge. The implementation should avoid an
obvious pathological design (e.g., re-querying the database once per entry, or repeatedly scanning
the full entry list once per predecessor lookup instead of using an indexed structure). **This
Decision does not authorize** Redis, a background worker, a graph database, an external service, or
any caching infrastructure — none is needed for a single-machine, in-memory graph-validation pass
over a query result already being fetched in full.

## 18. Failure/result contract

The implementing engineer must first determine `verify_chain()`'s exact current contract (a
zero-argument coroutine returning `bool`) and preserve repository-compatible behavior for the
existing 11 call sites' `is True`/`is False` usage, unless `ADR-030`'s invariants require a bounded
extension. At minimum, the test suite (§§4–9 above) must be able to distinguish, through its
assertions: a valid linear graph; a valid branched DAG, including multiple simultaneous genesis
roots; an invalid hash; a missing predecessor; and a cycle. **Reachability is not a seventh,
independently constructible case** — per §8 above, it is proven by the same dangling-reference (§7)
and cycle (§9) fixtures, not by a distinct "unreachable" test. **No large public error-reporting
API is authorized** merely because it might be convenient — if repository convention (a returned
`bool`, as today) is sufficient to express these distinctions through the *test suite's own* direct
inspection of the underlying data (not necessarily through the function's return value alone), that
remains the preferred, minimal shape.

## 19. Persistent-environment boundary

**This Decision does not authorize running any repair, mutation, or verification operation against
any persistent environment** — including any Supabase-hosted environment this repository's CI
references. The implementation's own tests must run exclusively against hermetic, in-memory fixtures
and/or throwaway, created-and-dropped-within-the-test-run databases, following this repository's
already-established live-test convention. Historical audit verification against any real,
persistent environment, if ever desired, requires its own, separate, explicit operational
authorization — not granted here, by omission or implication.

## 20. GD-009 disposition — critical, restated explicitly

**Ratification and implementation of this Decision do not themselves resume GD-009 Batch 1.** GD-009
remains Accepted/In Force; its Batch 1 execution remains suspended under its own audit-chain
concurrency hard stop (§11/§15 of `docs/GD-009-...md`) until, in the exact sequence `docs/adr/
ADR-030-...md` itself already established:

1. `ADR-030` Accepted (**satisfied**);
2. this Decision (verifier implementation authorization) Accepted;
3. the verifier actually implemented, formally human-reviewed, squash merged, and post-merge
   verified;
4. a **separate, explicit, future** Governance act authorizing resumption of GD-009 Batch 1.

This Decision satisfies step 2 only, once ratified — it does not, and cannot, satisfy step 4.

## 21. Blocked GD-009 branch

`feat/gd009-batch1-transactional-audit` (uncommitted, local) remains preserved reproduction
evidence, entirely untouched by this Decision and its drafting. **No file on that branch was
committed, rebased, cleaned, stashed, or otherwise modified in the course of drafting this
Decision.** When verifier implementation is eventually authorized and undertaken, it must proceed
from a clean branch/worktree created from whichever `origin/main` SHA is current at that time — never
from, or incorporating, that preserved branch's own files.

## 22. ADR-028 HTTP gate

This Decision grants **no** `ADR-028` HTTP/API authority of any kind: no router, no request/response
DTO, no OpenAPI specification change, no generated client, no frontend component, no Surveyor
Dashboard work. `ADR-028`'s existing gate (implement → test → formally review → squash merge →
post-merge verify GD-009 Batch 1, then a further, separate Governance act) is entirely unaffected
and unshortened by anything in this Decision.

## 23. Explicit programme exclusions

For auditability and consistency with `docs/GD-008-...md`, `docs/adr/ADR-026-...md`, `docs/adr/
ADR-028-...md`, and `docs/GD-009-...md`'s own out-of-scope conventions: this Decision does not
authorize Marketplace; the Partner programme; Job; Assignment; Customer; accreditation; payments;
SECI; EQF; the Professional Performance Index; Rights or licensing; Legacy Vault; `ADR-021`
functionality; or general Background Jobs infrastructure. None of these is touched, implied, or
brought closer to authorization by this Decision's subject matter.

## 24. Article XVI entry

The following text is inserted into `docs/LV-000-constitution.md`'s Article XVI Log by this
ratification (a separate edit to that file, not by this document itself):

> **GD-010 — Audit DAG Verifier Implementation Authorization.** *(Ratified 14 September 2026.)*
> Operative authority: **Article XVI §2** — GD-010 is a later numbered decision that explicitly
> relies on `docs/adr/ADR-030-audit-chain-concurrency-ordering-and-linearization.md` (Accepted,
> 2026-09-13) as its governing architecture, and explicitly names `docs/GD-009-audit-transaction-
> semantics-implementation-authorization-and-adr-007-regularisation.md` to state what it does not
> do to it; it is not proposed under Article XIV and does not amend this Constitution.
>
> **Decision.** Implementation of a DAG-aware audit-chain verifier, enforcing exactly the six
> invariants `ADR-030` §2 decided (genesis/root validity, per-entry hash validity, referential
> validity, reachability, acyclicity, branch legitimacy), replacing `app.kernel.audit.
> verify_chain()`'s current strict single-predecessor linear walk, is authorized. No schema
> migration, no new runtime dependency, and no change to any audit write path (`audit()`,
> `EagerPostgresAuditStore`, the suspended transaction-coupled design, hash generation, or any
> transaction boundary) is authorized or required.
>
> **Scope excluded — no retroactive expansion.** This decision does not authorise resumption of
> `GD-009`'s Batch 1 implementation; any transactional/successful-mutation audit work; any lock,
> serialization, retry, or sequence mechanism; any external completeness anchor or checkpoint; any
> repair or mutation operation against a persistent environment; any `ADR-028` HTTP/API exposure;
> or any frontend work. GD-009 remains Accepted/In Force with Batch 1 suspended; resumption requires
> this Decision's implementation to be merged and post-merge verified, followed by a further,
> separate, explicit Governance act — this Log entry does not itself grant that resumption
> authority.

## Approval Gate

This Governance Decision is **ACCEPTED**, per the Ratification Record above. Acceptance authorizes
only implementation of the DAG-aware audit verifier described in §3 — the same category of
authorization `docs/adr/ADR-026-evidence-domain-model.md` gave its own "B5.2" implementation and
GD-009 gave Batch 1 — never anything broader.

**Explicit exclusions.** Ratification does not authorize: resumption of GD-009 Batch 1; any
transactional/successful-mutation audit work; any change to `audit()`, `EagerPostgresAuditStore`, the
suspended `audit_staged()` design, hash generation, or any transaction boundary; any schema migration
or new runtime dependency absent a further stop-and-return to Governance (§14, §15); any lock,
serialization, retry, or sequence mechanism; any external completeness anchor or checkpoint; any
repair or mutation operation against a persistent environment (§19); any `ADR-028` HTTP/API exposure
(router, DTOs, OpenAPI, generated clients, frontend, or Surveyor Dashboard work); or any of the
programmes named in §23.

See the companion readiness report, `docs/GD-010_READINESS_REPORT.md`, for the independent challenge
of this draft that preceded ratification.
