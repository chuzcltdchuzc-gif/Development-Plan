# ADR-007 — Audit Trail & Evidence Model

**Status:** Accepted
**Date:** 2026-07-13

## Context

Land-title evidence is the core trust proposition of this product, so its integrity guarantees have to be real, not aspirational. The Emergent audit found the *design* of its evidence pipeline sound — server-side hashing with an independent streamed read-back re-hash (no trust placed in any client-supplied hash claim), Merkle-tree batch anchoring to an internal certificate-transparency-style log plus OpenTimestamps as an independent secondary anchor, chain-of-custody and legal-hold as append-only chained aggregates — but found the *implementation* of "immutability" was fake at the storage layer: the only wired storage adapter was local-filesystem with a `chmod 0o400` "lock" (meaningless if the process runs as root, which is typical in containers) defaulting to `/tmp`, which most container platforms wipe on every restart; the real S3/R2 adapter was never implemented beyond a stub. Legal hold was a database record with no enforcement anywhere — the domain code's own docstring admitted enforcement was deferred to a "retention sweeper" that was never built, so an active legal hold currently blocks nothing. Two separate "integrity check" functions similarly checked a status flag rather than recomputing and comparing any actual hash — a pattern of security theater that recurred three separate times in that codebase.

Separately, both audits found the underlying audit-log mechanism itself (an append-only, hash-chained log of every domain event) to be a correct idea let down by one gap: no function anywhere actually *verified* the hash chain for tampering. A tamper-evident log nobody ever checks is not meaningfully different from a log that isn't tamper-evident.

## Decision

1. **Event sourcing with a transactional outbox** at the kernel level (`docs/REBUILD_PLAN.md` B0) — every domain event across every bounded context is written atomically with the state change that produced it, then published for downstream subscribers (Trust Engine, Knowledge Graph, notifications). This is Emergent's outbox design, reused, with its one gap closed: a real `verify_chain()` integrity checker ships as part of B1, run on a schedule, not left as a theoretical guarantee.
2. **Evidence storage is real S3-compatible object storage with Object Lock in Compliance mode from day one** — never local filesystem, never a chmod-based convention. The R2/S3 adapter is built *first*, not deferred, precisely because the audit showed what happens when it's left for later (it never gets built).
3. **Legal hold is enforced as a guard checked at every delete/archive/seal-release code path**, implemented once as a shared mechanism every relevant command calls through — not a record any individual code path might forget to check.
4. **Hash/integrity verification actually recomputes and compares hashes.** No function reports "valid" based on a status flag or field-presence check alone.
5. Break-glass cross-tenant/cross-country evidence access requires the dual-authorization it's documented to require, mechanically enforced (rejected if the second approver is absent), and the security-incident record is written durably *before* the unwrap operation returns.

## Consequences

- The evidence pipeline's hashing/verification/Merkle-anchoring *logic* ports from Emergent with high confidence (audited sound); the storage adapter and legal-hold enforcement are new work, not a port, because the audit confirmed neither existed in a real form.
- This is the single most implementation-heavy bounded context in the plan (`docs/REBUILD_PLAN.md` B5, 4–6 weeks) precisely because "real" WORM storage and enforced legal hold are non-trivial to get right — treated as core product risk, not a corner to cut for velocity.
- Every later context that needs tamper-evident records (Survey documents, Community attestations, Inheritance certificates) routes through this same pipeline rather than each building its own weaker version.
