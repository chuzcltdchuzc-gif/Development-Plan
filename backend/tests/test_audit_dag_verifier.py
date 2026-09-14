"""DAG-aware `verify_chain()` (docs/adr/ADR-030, docs/GD-010-...md).

Exercises the six ADR-030 §2 invariants directly against constructed
`AuditEntry` fixtures and `tests/fakes/audit_store.py`'s `InMemoryAuditStore`
— no HTTP surface, no live database, exactly the hermetic-fixture boundary
GD-010 §19 requires. Every fixture here is built with the real
`_compute_hash` so "valid" fixtures are genuinely hash-consistent, except
where a test is deliberately proving a specific invariant's failure mode
(§6 tampered hash, §9 cycles), in which case the fixture's own docstring
says so.
"""
from __future__ import annotations

import pytest

from app.kernel.audit import (
    GENESIS_HASH,
    AuditEntry,
    _compute_hash,
    configure_audit_store,
    verify_chain,
)
from tests.fakes.audit_store import InMemoryAuditStore


@pytest.fixture
def audit_store() -> InMemoryAuditStore:
    store = InMemoryAuditStore()
    configure_audit_store(store)
    return store


def _entry(
    *,
    entry_id: str,
    prev_hash: str,
    action: str = "test.action",
    created_at: str = "2026-09-14T00:00:00+00:00",
    hash_override: str | None = None,
) -> AuditEntry:
    """Builds a real, hash-consistent AuditEntry unless `hash_override` is
    given, in which case the stored `hash` deliberately does not match
    `recompute_hash()` (used only by the tampered-hash tests, §6)."""
    kwargs = dict(
        entry_id=entry_id,
        action=action,
        resource_type="test_resource",
        resource_id=entry_id,
        decision=None,
        principal_id="principal-1",
        payload={"note": entry_id},
        created_at=created_at,
        prev_hash=prev_hash,
    )
    computed = _compute_hash(**kwargs)
    return AuditEntry(**kwargs, hash=hash_override if hash_override is not None else computed)


async def _seed(store: InMemoryAuditStore, *entries: AuditEntry) -> None:
    for entry in entries:
        await store.append(entry)


# 1. Empty history remains valid (GD-010 §4) ---------------------------------


async def test_empty_history_is_valid(audit_store: InMemoryAuditStore) -> None:
    assert await verify_chain() is True


# 2. Existing valid linear history remains valid, unmodified (GD-010 §4) -----


async def test_linear_history_remains_valid(audit_store: InMemoryAuditStore) -> None:
    a = _entry(entry_id="a", prev_hash=GENESIS_HASH)
    b = _entry(entry_id="b", prev_hash=a.hash)
    c = _entry(entry_id="c", prev_hash=b.hash)
    await _seed(audit_store, a, b, c)

    assert await verify_chain() is True


# 3. Legitimate branch A -> {B, C} verifies valid (GD-010 §5) ----------------


async def test_branch_from_shared_predecessor_is_valid(audit_store: InMemoryAuditStore) -> None:
    a = _entry(entry_id="a", prev_hash=GENESIS_HASH)
    b = _entry(entry_id="b", prev_hash=a.hash)
    c = _entry(entry_id="c", prev_hash=a.hash)
    await _seed(audit_store, a, b, c)

    assert await verify_chain() is True


async def test_branch_valid_regardless_of_created_at_order(audit_store: InMemoryAuditStore) -> None:
    """GD-010 §12: two siblings inserted in either created_at order both
    verify valid — the verifier must not manufacture ordering from
    created_at, insertion position, or commit order."""
    a = _entry(entry_id="a", prev_hash=GENESIS_HASH, created_at="2026-09-14T00:00:00+00:00")
    b = _entry(entry_id="b", prev_hash=a.hash, created_at="2026-09-14T00:00:02+00:00")
    c = _entry(entry_id="c", prev_hash=a.hash, created_at="2026-09-14T00:00:01+00:00")
    await _seed(audit_store, a, c, b)  # c (later logical, earlier created_at) inserted first

    assert await verify_chain() is True


# 4. Multiple simultaneous genesis-linked roots verify valid (GD-010 §5) -----


async def test_multiple_genesis_roots_are_valid(audit_store: InMemoryAuditStore) -> None:
    a = _entry(entry_id="a", prev_hash=GENESIS_HASH)
    b = _entry(entry_id="b", prev_hash=GENESIS_HASH)
    await _seed(audit_store, a, b)

    assert await verify_chain() is True


# 5. Tampered hash must fail (GD-010 §6) -------------------------------------


async def test_modified_content_without_recomputed_hash_fails(
    audit_store: InMemoryAuditStore,
) -> None:
    a = _entry(entry_id="a", prev_hash=GENESIS_HASH)
    await audit_store.append(a)
    tampered = AuditEntry(
        entry_id=a.entry_id,
        action=a.action,
        resource_type=a.resource_type,
        resource_id=a.resource_id,
        decision=a.decision,
        principal_id=a.principal_id,
        payload={"note": "tampered"},  # content changed post-hoc
        created_at=a.created_at,
        prev_hash=a.prev_hash,
        hash=a.hash,  # stale — never recomputed
    )
    audit_store._entries[0] = tampered

    assert await verify_chain() is False


async def test_hash_replaced_with_unrelated_value_fails(audit_store: InMemoryAuditStore) -> None:
    a = _entry(entry_id="a", prev_hash=GENESIS_HASH, hash_override="f" * 64)
    await _seed(audit_store, a)

    assert await verify_chain() is False


# 6. Dangling predecessor must fail (GD-010 §7) -------------------------------


async def test_dangling_predecessor_fails(audit_store: InMemoryAuditStore) -> None:
    a = _entry(entry_id="a", prev_hash="ab" * 32)  # no entry has this hash, not genesis either
    await _seed(audit_store, a)

    assert await verify_chain() is False


# 7. Reachability distinct from one-hop referential validity (GD-010 §8) ----


async def test_multi_hop_dangling_reference_is_caught(audit_store: InMemoryAuditStore) -> None:
    """C -> B resolves (B exists); B's own prev_hash is dangling. A verifier
    that only checked C's immediate parent, without walking the full
    predecessor chain to genesis, would incorrectly pass this."""
    b = _entry(entry_id="b", prev_hash="cd" * 32)  # dangling one hop further back
    c = _entry(entry_id="c", prev_hash=b.hash)
    await _seed(audit_store, b, c)

    assert await verify_chain() is False


# 8. Cycles must fail, safely (GD-010 §9) ------------------------------------


async def test_self_cycle_fails_without_hanging(audit_store: InMemoryAuditStore) -> None:
    """A synthetic self-cycle: A.prev_hash == A.hash. Cannot be
    hash-consistent (SHA-256 fixed point is infeasible — GD-010 §9), so this
    fixture also independently fails invariant 2; §9 only requires the final
    result be invalid and the traversal bounded, not that cycle-detection
    fire in isolation."""
    self_hash = "11" * 32
    a = AuditEntry(
        entry_id="a",
        action="test.action",
        resource_type="test_resource",
        resource_id="a",
        decision=None,
        principal_id="principal-1",
        payload={},
        created_at="2026-09-14T00:00:00+00:00",
        prev_hash=self_hash,
        hash=self_hash,
    )
    await _seed(audit_store, a)

    assert await verify_chain() is False


async def test_two_node_cycle_fails_without_hanging(audit_store: InMemoryAuditStore) -> None:
    hash_a, hash_b = "22" * 32, "33" * 32
    a = AuditEntry(
        entry_id="a",
        action="test.action",
        resource_type="test_resource",
        resource_id="a",
        decision=None,
        principal_id="principal-1",
        payload={},
        created_at="2026-09-14T00:00:00+00:00",
        prev_hash=hash_b,
        hash=hash_a,
    )
    b = AuditEntry(
        entry_id="b",
        action="test.action",
        resource_type="test_resource",
        resource_id="b",
        decision=None,
        principal_id="principal-1",
        payload={},
        created_at="2026-09-14T00:00:01+00:00",
        prev_hash=hash_a,
        hash=hash_b,
    )
    await _seed(audit_store, a, b)

    assert await verify_chain() is False


async def test_three_node_cycle_fails_without_hanging(audit_store: InMemoryAuditStore) -> None:
    hash_a, hash_b, hash_c = "44" * 32, "55" * 32, "66" * 32
    entries = [
        AuditEntry(
            entry_id=entry_id,
            action="test.action",
            resource_type="test_resource",
            resource_id=entry_id,
            decision=None,
            principal_id="principal-1",
            payload={},
            created_at=f"2026-09-14T00:00:0{i}+00:00",
            prev_hash=prev_hash,
            hash=own_hash,
        )
        for i, (entry_id, own_hash, prev_hash) in enumerate(
            [("a", hash_a, hash_c), ("b", hash_b, hash_a), ("c", hash_c, hash_b)]
        )
    ]
    await _seed(audit_store, *entries)

    assert await verify_chain() is False


# 9. Duplicate hash input must not be silently collapsed (GD-010 §3) --------


async def test_duplicate_hash_entries_are_rejected_not_silently_merged(
    audit_store: InMemoryAuditStore,
) -> None:
    shared_hash = "77" * 32
    first = AuditEntry(
        entry_id="a",
        action="test.action",
        resource_type="test_resource",
        resource_id="a",
        decision=None,
        principal_id="principal-1",
        payload={"note": "first"},
        created_at="2026-09-14T00:00:00+00:00",
        prev_hash=GENESIS_HASH,
        hash=shared_hash,
    )
    second = AuditEntry(
        entry_id="b",
        action="test.action",
        resource_type="test_resource",
        resource_id="b",
        decision=None,
        principal_id="principal-1",
        payload={"note": "second"},
        created_at="2026-09-14T00:00:01+00:00",
        prev_hash=GENESIS_HASH,
        hash=shared_hash,  # collides with `first`
    )
    await _seed(audit_store, first, second)

    assert await verify_chain() is False
