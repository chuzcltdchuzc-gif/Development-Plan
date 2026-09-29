"""StoragePort — Slice B5.1 (docs/adr/ADR-024-...md D1, ADR-025-...md E3,
docs/adr/ADR-026-evidence-domain-model.md "Relationship to Slice B5.1").

Exercises the in-memory fake (tests.fakes.storage.InMemoryStoragePort) — the
only StoragePort implementation in this codebase today. Real adapters
(Supabase Storage, Cloudflare R2) are not implemented in this slice: both
require a new external dependency (docs/ENGINEERING_RULES.md rule 5) and real
credentials for a live rehearsal (docs/ENGINEERING_RULES.md rule 7), neither
of which this slice can supply. What these tests *do* prove, against the
fake, is the one behavior that actually matters architecturally: once a key
is sealed via put_immutable, nothing — not a plain put, not a second
put_immutable — can silently overwrite it. That is the mechanical content of
"sealed evidence cannot be altered" (docs/EXECUTION_PLAN.md's Phase-3 gate
text), and it is exactly what a real adapter must also guarantee, whatever
provider ultimately backs it.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.contexts.evidence.ports import (
    StorageImmutabilityViolationError,
    StorageObjectNotFoundError,
)
from tests.fakes.storage import InMemoryStoragePort


async def test_put_then_get_returns_same_bytes() -> None:
    storage = InMemoryStoragePort()
    await storage.put("evidence/t1/e1.pdf", b"hello world", content_type="application/pdf")

    assert await storage.get("evidence/t1/e1.pdf") == b"hello world"


async def test_get_missing_key_raises_not_found() -> None:
    storage = InMemoryStoragePort()

    with pytest.raises(StorageObjectNotFoundError):
        await storage.get("evidence/t1/does-not-exist.pdf")


async def test_list_keys_filters_by_prefix_and_sorts() -> None:
    storage = InMemoryStoragePort()
    await storage.put("evidence/t1/b.pdf", b"b")
    await storage.put("evidence/t1/a.pdf", b"a")
    await storage.put("evidence/t2/c.pdf", b"c")

    assert await storage.list_keys("evidence/t1/") == ["evidence/t1/a.pdf", "evidence/t1/b.pdf"]


async def test_list_keys_no_match_returns_empty_list() -> None:
    storage = InMemoryStoragePort()

    assert await storage.list_keys("evidence/nonexistent-tenant/") == []


async def test_ordinary_put_can_overwrite_before_sealing() -> None:
    storage = InMemoryStoragePort()
    await storage.put("evidence/t1/e1.pdf", b"first version")
    await storage.put("evidence/t1/e1.pdf", b"corrected version")

    assert await storage.get("evidence/t1/e1.pdf") == b"corrected version"


async def test_put_immutable_seals_key_and_is_readable() -> None:
    storage = InMemoryStoragePort()
    retention = datetime.now(UTC) + timedelta(days=3650)
    await storage.put_immutable("evidence/t1/e1.pdf", b"sealed content", retention_until=retention)

    assert await storage.get("evidence/t1/e1.pdf") == b"sealed content"
    assert storage.is_sealed("evidence/t1/e1.pdf") is True


async def test_ordinary_put_after_seal_is_rejected() -> None:
    storage = InMemoryStoragePort()
    retention = datetime.now(UTC) + timedelta(days=3650)
    await storage.put_immutable("evidence/t1/e1.pdf", b"sealed content", retention_until=retention)

    with pytest.raises(StorageImmutabilityViolationError):
        await storage.put("evidence/t1/e1.pdf", b"tampered content")

    # the sealed content survives the rejected attempt, unchanged
    assert await storage.get("evidence/t1/e1.pdf") == b"sealed content"


async def test_second_put_immutable_after_seal_is_rejected() -> None:
    storage = InMemoryStoragePort()
    retention = datetime.now(UTC) + timedelta(days=3650)
    await storage.put_immutable("evidence/t1/e1.pdf", b"sealed content", retention_until=retention)

    with pytest.raises(StorageImmutabilityViolationError):
        await storage.put_immutable(
            "evidence/t1/e1.pdf", b"re-sealed content", retention_until=retention
        )

    assert await storage.get("evidence/t1/e1.pdf") == b"sealed content"


async def test_worm_grade_defaults_to_governance() -> None:
    storage = InMemoryStoragePort()

    assert storage.worm_grade() == "governance"


async def test_worm_grade_reflects_configured_grade() -> None:
    storage = InMemoryStoragePort(worm_grade="compliance")

    assert storage.worm_grade() == "compliance"


async def test_unsealed_key_reports_not_sealed() -> None:
    storage = InMemoryStoragePort()
    await storage.put("evidence/t1/e1.pdf", b"draft")

    assert storage.is_sealed("evidence/t1/e1.pdf") is False
