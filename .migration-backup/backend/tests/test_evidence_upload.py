"""EvidenceService.upload_evidence — the real B5.3 upload orchestration
(B5 Slice B5.3, docs/adr/ADR-026-evidence-domain-model.md "Transaction
boundaries", docs/adr/ADR-007-audit-trail-evidence-model.md decision 4).

No HTTP surface exists yet (no upload endpoint), so these tests exercise
EvidenceService directly, the same pattern tests/test_evidence_service.py
already uses. Real database-transaction atomicity and real storage-adapter
behavior are DB/infrastructure-level guarantees with no equivalent in an
in-memory fake — rehearsed live against Docker Postgres separately
(docs/PHASE-B5-SLICE3_ACCEPTANCE_PACKAGE.md), the identical split
tests/test_registry_ownership_status_history.py already documents for
ADR-023 and tests/test_evidence_service.py documents for B5.2.
"""
from __future__ import annotations

import hashlib

import pytest
from fastapi import HTTPException

from app.contexts.evidence.application.evidence_service import (
    EvidenceIntegrityError,
    EvidenceService,
)
from app.contexts.evidence.domain.evidence_record import STATUS_HASHED, STATUS_RECEIVED
from app.kernel.audit import configure_audit_store
from app.kernel.context import ExecutionContext
from tests.fakes.audit_store import InMemoryAuditStore
from tests.fakes.evidence import InMemoryEvidenceRepository
from tests.fakes.storage import InMemoryStoragePort


class _CorruptingStoragePort(InMemoryStoragePort):
    """Test-only: returns different bytes on `get` than what was written on
    `put`, simulating storage-layer corruption/substitution — the exact
    scenario the independent read-back re-hash (ADR-007 decision 4) exists
    to catch. Not a reusable fake; deliberately broken for one negative
    test only."""

    async def get(self, key: str) -> bytes:
        data = await super().get(key)
        return data + b"\x00"


@pytest.fixture
def audit_store() -> InMemoryAuditStore:
    store = InMemoryAuditStore()
    configure_audit_store(store)
    return store


@pytest.fixture
def evidence_repo() -> InMemoryEvidenceRepository:
    return InMemoryEvidenceRepository()


@pytest.fixture
def storage() -> InMemoryStoragePort:
    return InMemoryStoragePort()


@pytest.fixture
def service(
    evidence_repo: InMemoryEvidenceRepository, storage: InMemoryStoragePort
) -> EvidenceService:
    return EvidenceService(evidence=evidence_repo, storage=storage)


def _ctx(
    *, tenant_id: str = "ten_1", principal_id: str = "usr_1", roles: tuple[str, ...] = ()
) -> ExecutionContext:
    return ExecutionContext(principal_id=principal_id, tenant_id=tenant_id, roles=roles)


async def _upload(
    service: EvidenceService, *, ctx: ExecutionContext | None = None, **overrides: object
) -> dict:
    defaults: dict[str, object] = dict(
        ctx=ctx or _ctx(),
        parcel_id="par_1",
        filename="survey.pdf",
        mime_type="application/pdf",
        data=b"the quick brown fox jumps over the lazy dog",
        basis="submitted by registrant as supporting survey documentation",
        evidence_type="SURVEY_PLAN",
    )
    defaults.update(overrides)
    return await service.upload_evidence(**defaults)  # type: ignore[arg-type]


# --- 1. Upload success -------------------------------------------------------


async def test_upload_success_reaches_hashed_status(
    service: EvidenceService, storage: InMemoryStoragePort
) -> None:
    result = await _upload(service)

    assert result["status"] == STATUS_HASHED
    assert result["sha256"] is not None
    stored = await storage.get(result["storage_key"])
    assert stored == b"the quick brown fox jumps over the lazy dog"


async def test_upload_persists_correct_metadata(service: EvidenceService) -> None:
    result = await _upload(service, filename="deed.pdf", mime_type="application/pdf")

    assert result["filename"] == "deed.pdf"
    assert result["mime_type"] == "application/pdf"
    assert result["size_bytes"] == len(b"the quick brown fox jumps over the lazy dog")
    assert result["tenant_id"] == "ten_1"
    assert result["parcel_id"] == "par_1"


# --- 2. Upload failure --------------------------------------------------------


async def test_upload_requires_tenant(service: EvidenceService) -> None:
    ctx = ExecutionContext(principal_id="usr_1", tenant_id=None, roles=())

    with pytest.raises(HTTPException) as exc_info:
        await _upload(service, ctx=ctx)
    assert exc_info.value.status_code == 400


async def test_upload_rejects_empty_content(service: EvidenceService) -> None:
    with pytest.raises(HTTPException) as exc_info:
        await _upload(service, data=b"")
    assert exc_info.value.status_code == 400


async def test_upload_rejects_unknown_evidence_type(service: EvidenceService) -> None:
    with pytest.raises(HTTPException) as exc_info:
        await _upload(service, evidence_type="NOT_A_REAL_TYPE")
    assert exc_info.value.status_code == 400


# --- 3. Hash correctness ------------------------------------------------------


async def test_hash_matches_independently_computed_sha256(service: EvidenceService) -> None:
    data = b"content whose hash we will verify independently"
    result = await _upload(service, data=data)

    assert result["sha256"] == hashlib.sha256(data).hexdigest()


async def test_different_content_yields_different_hash(service: EvidenceService) -> None:
    first = await _upload(service, data=b"content A")
    second = await _upload(service, data=b"content B")

    assert first["sha256"] != second["sha256"]


# --- 4. Duplicate upload behaviour (not defined by ADR-026) ------------------


async def test_uploading_identical_content_twice_creates_two_independent_records(
    service: EvidenceService,
) -> None:
    """ADR-026 does not define duplicate-detection behaviour for Evidence —
    confirmed by re-reading the ADR's own "Decision" and "Out of scope"
    sections, neither of which mentions deduplication, and by the
    authorization's explicit exclusion of "evidence review"/"evidence
    verification" from B5.3's scope. No dedup logic is implemented. This
    test documents that fact as an observed behaviour, not an assumption:
    two uploads of byte-identical content produce two separate
    EvidenceRecord rows, each with its own evidence_id and storage_key."""
    data = b"identical content uploaded twice"

    first = await _upload(service, data=data)
    second = await _upload(service, data=data)

    assert first["evidence_id"] != second["evidence_id"]
    assert first["storage_key"] != second["storage_key"]
    assert first["sha256"] == second["sha256"]


# --- 5/8. Ordering, rollback-adjacent behaviour, StoragePort/repository failure --


async def test_storage_put_failure_prevents_any_record_creation(
    service: EvidenceService,
    evidence_repo: InMemoryEvidenceRepository,
    storage: InMemoryStoragePort,
    audit_store: InMemoryAuditStore,
) -> None:
    """ADR-026 "Transaction boundaries": the storage write must complete
    before the EvidenceRecord row is persisted. If it fails, no row is ever
    created — proven here directly, not inferred from the code's ordering
    alone."""
    storage.fail_next_put = RuntimeError("simulated storage outage")

    with pytest.raises(RuntimeError, match="simulated storage outage"):
        await _upload(service)

    assert await evidence_repo.list_for_parcel("par_1") == []
    assert (await audit_store.all_entries()) == []


async def test_repository_add_failure_after_storage_write_leaves_orphan_object(
    service: EvidenceService,
    evidence_repo: InMemoryEvidenceRepository,
    storage: InMemoryStoragePort,
    audit_store: InMemoryAuditStore,
) -> None:
    """The accepted, named residual risk from ADR-026 "Transaction
    boundaries": a storage write that succeeds followed by a database write
    that fails can leave an orphaned object in storage with no
    EvidenceRecord referencing it. This is not a defect — it is the
    documented cost of the required ordering (the alternative, DB-row-first,
    would let a caller observe a record claiming data that was never
    written, which is strictly worse). Proven here: the object exists in
    storage, no EvidenceRecord was persisted, no audit entry was written."""
    evidence_repo.fail_next_add = RuntimeError("simulated database outage")

    with pytest.raises(RuntimeError, match="simulated database outage"):
        await _upload(service)

    assert await evidence_repo.list_for_parcel("par_1") == []
    assert (await audit_store.all_entries()) == []
    keys = await storage.list_keys("evidence/ten_1/par_1/")
    assert len(keys) == 1  # the orphaned object, exactly as documented


async def test_repository_mark_hashed_failure_leaves_record_at_received(
    service: EvidenceService,
    evidence_repo: InMemoryEvidenceRepository,
    audit_store: InMemoryAuditStore,
) -> None:
    """If persisting the HASHED transition fails after the RECEIVED row and
    its "evidence.uploaded" audit entry already committed, the record is
    left at RECEIVED in the repository — a real, observable intermediate
    state, not silently advanced past a failed write."""
    evidence_repo.fail_next_mark_hashed = RuntimeError("simulated database outage")

    with pytest.raises(RuntimeError, match="simulated database outage"):
        await _upload(service)

    records = await evidence_repo.list_for_parcel("par_1")
    assert len(records) == 1
    assert records[0].status == STATUS_RECEIVED
    entries = await audit_store.all_entries()
    assert [e.action for e in entries] == ["evidence.uploaded"]


async def test_storage_get_failure_during_readback_leaves_record_at_received(
    service: EvidenceService,
    evidence_repo: InMemoryEvidenceRepository,
    storage: InMemoryStoragePort,
) -> None:
    """A StoragePort failure during the independent read-back (not the
    initial write) also leaves the record at RECEIVED, never HASHED —
    the record must never claim a confirmed hash it was never able to
    confirm."""
    original_put = storage.put

    async def put_then_break_get(key: str, data: bytes, *, content_type: str | None = None) -> None:
        await original_put(key, data, content_type=content_type)
        storage.fail_next_get = RuntimeError("simulated read-back failure")

    storage.put = put_then_break_get  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="simulated read-back failure"):
        await _upload(service)

    records = await evidence_repo.list_for_parcel("par_1")
    assert len(records) == 1
    assert records[0].status == STATUS_RECEIVED


# --- 9. Audit linkage ---------------------------------------------------------


async def test_upload_audit_ref_resolves_and_hashed_event_follows(
    service: EvidenceService, audit_store: InMemoryAuditStore
) -> None:
    result = await _upload(service)

    entries = {e.entry_id: e for e in await audit_store.all_entries()}
    actions = [e.action for e in await audit_store.all_entries()]

    assert result["audit_ref"] in entries
    assert entries[result["audit_ref"]].action == "evidence.uploaded"
    assert actions == ["evidence.uploaded", "evidence.hashed"]

    hashed_entry = next(e for e in await audit_store.all_entries() if e.action == "evidence.hashed")
    assert hashed_entry.payload["sha256"] == result["sha256"]


# --- 11. Service / domain invariants under integrity failure -----------------


async def test_integrity_mismatch_raises_and_leaves_record_at_received(
    evidence_repo: InMemoryEvidenceRepository, audit_store: InMemoryAuditStore
) -> None:
    corrupting_storage = _CorruptingStoragePort()
    service = EvidenceService(evidence=evidence_repo, storage=corrupting_storage)

    with pytest.raises(EvidenceIntegrityError):
        await _upload(service)

    records = await evidence_repo.list_for_parcel("par_1")
    assert len(records) == 1
    assert records[0].status == STATUS_RECEIVED
    assert records[0].sha256 is None

    actions = [e.action for e in await audit_store.all_entries()]
    assert actions == ["evidence.uploaded", "evidence.integrity_check_failed"]
    failure_entry = next(
        e for e in await audit_store.all_entries() if e.action == "evidence.integrity_check_failed"
    )
    assert failure_entry.decision == "DENY"
    assert failure_entry.payload["upload_sha256"] != failure_entry.payload["readback_sha256"]


async def test_upload_is_tenant_scoped(service: EvidenceService) -> None:
    result = await _upload(service, ctx=_ctx(tenant_id="ten_a"))

    assert result["tenant_id"] == "ten_a"
