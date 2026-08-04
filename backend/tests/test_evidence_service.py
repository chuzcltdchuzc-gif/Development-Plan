"""EvidenceService — application-layer use cases (B5 Slice B5.2, docs/adr/
ADR-026-evidence-domain-model.md).

No HTTP surface exists yet (no upload endpoint — B5.3), so these tests
exercise EvidenceService directly against ExecutionContext and
InMemoryEvidenceRepository, the same pattern tests/test_authorization.py
already uses for kernel-level tests that have no router to go through.
Tenant isolation, lifecycle-transition wiring, and audit_ref resolution are
proven here; RLS and real transactional behavior are DB-level guarantees
rehearsed live against Postgres separately (docs/
PHASE-B5-SLICE2_ACCEPTANCE_PACKAGE.md), the identical split
tests/test_registry_ownership_status_history.py already documents for
ADR-023.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.contexts.evidence.application.evidence_service import EvidenceService
from app.kernel.audit import configure_audit_store
from app.kernel.context import ExecutionContext
from tests.fakes.audit_store import InMemoryAuditStore
from tests.fakes.evidence import InMemoryEvidenceRepository
from tests.fakes.storage import InMemoryStoragePort


@pytest.fixture
def audit_store() -> InMemoryAuditStore:
    store = InMemoryAuditStore()
    configure_audit_store(store)
    return store


@pytest.fixture
def evidence_repo() -> InMemoryEvidenceRepository:
    return InMemoryEvidenceRepository()


@pytest.fixture
def service(evidence_repo: InMemoryEvidenceRepository) -> EvidenceService:
    # B5.3 added a required `storage` dependency to EvidenceService; these
    # B5.2-era tests exercise record_upload/mark_hashed/seal/legal-hold only
    # (never upload_evidence, which is the only method that touches
    # storage), so a bare fake with no calls made against it is sufficient
    # here — see tests/test_evidence_upload.py for storage-path coverage.
    return EvidenceService(evidence=evidence_repo, storage=InMemoryStoragePort())


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
        size_bytes=2048,
        storage_key="evidence/ten_1/par_1/survey.pdf",
        basis="submitted by registrant as supporting survey documentation",
        evidence_type="SURVEY_PLAN",
    )
    defaults.update(overrides)
    return await service.record_upload(**defaults)  # type: ignore[arg-type]


async def test_record_upload_creates_received_record(
    service: EvidenceService, audit_store: InMemoryAuditStore
) -> None:
    result = await _upload(service)

    assert result["status"] == "RECEIVED"
    assert result["tenant_id"] == "ten_1"
    assert result["parcel_id"] == "par_1"
    entries = await audit_store.all_entries()
    assert any(e.action == "evidence.uploaded" for e in entries)


async def test_record_upload_requires_tenant(service: EvidenceService) -> None:
    ctx = ExecutionContext(principal_id="usr_1", tenant_id=None, roles=())

    with pytest.raises(HTTPException) as exc_info:
        await _upload(service, ctx=ctx)
    assert exc_info.value.status_code == 400


async def test_record_upload_rejects_unknown_evidence_type(service: EvidenceService) -> None:
    with pytest.raises(HTTPException) as exc_info:
        await _upload(service, evidence_type="NOT_A_REAL_TYPE")
    assert exc_info.value.status_code == 400


async def test_get_evidence_returns_view_when_in_scope(service: EvidenceService) -> None:
    created = await _upload(service)

    fetched = await service.get_evidence(ctx=_ctx(), evidence_id=created["evidence_id"])

    assert fetched["evidence_id"] == created["evidence_id"]


async def test_get_evidence_404_when_out_of_scope(service: EvidenceService) -> None:
    created = await _upload(service, ctx=_ctx(tenant_id="ten_1"))

    with pytest.raises(HTTPException) as exc_info:
        await service.get_evidence(ctx=_ctx(tenant_id="ten_2"), evidence_id=created["evidence_id"])
    assert exc_info.value.status_code == 404


async def test_get_evidence_404_when_missing(service: EvidenceService) -> None:
    with pytest.raises(HTTPException) as exc_info:
        await service.get_evidence(ctx=_ctx(), evidence_id="00000000-0000-0000-0000-000000000000")
    assert exc_info.value.status_code == 404


async def test_super_admin_can_read_cross_tenant(service: EvidenceService) -> None:
    created = await _upload(service, ctx=_ctx(tenant_id="ten_1"))

    admin_ctx = _ctx(tenant_id="ten_admin_home", roles=("super_admin",))
    fetched = await service.get_evidence(ctx=admin_ctx, evidence_id=created["evidence_id"])

    assert fetched["evidence_id"] == created["evidence_id"]


async def test_list_evidence_for_parcel_filters_out_of_tenant_results(
    service: EvidenceService,
) -> None:
    await _upload(service, ctx=_ctx(tenant_id="ten_1"), parcel_id="par_shared")
    await _upload(service, ctx=_ctx(tenant_id="ten_2"), parcel_id="par_shared")

    results = await service.list_evidence_for_parcel(
        ctx=_ctx(tenant_id="ten_1"), parcel_id="par_shared"
    )

    assert len(results) == 1
    assert results[0]["tenant_id"] == "ten_1"


async def test_mark_hashed_transitions_and_audits(
    service: EvidenceService, audit_store: InMemoryAuditStore
) -> None:
    created = await _upload(service)

    result = await service.mark_hashed(
        ctx=_ctx(), evidence_id=created["evidence_id"], sha256="a" * 64
    )

    assert result["status"] == "HASHED"
    assert result["sha256"] == "a" * 64
    entries = await audit_store.all_entries()
    assert any(e.action == "evidence.hashed" for e in entries)


async def test_mark_hashed_out_of_scope_returns_404(service: EvidenceService) -> None:
    created = await _upload(service, ctx=_ctx(tenant_id="ten_1"))

    with pytest.raises(HTTPException) as exc_info:
        await service.mark_hashed(
            ctx=_ctx(tenant_id="ten_2"), evidence_id=created["evidence_id"], sha256="a" * 64
        )
    assert exc_info.value.status_code == 404


async def test_seal_after_hash_transitions_and_audits(
    service: EvidenceService, audit_store: InMemoryAuditStore
) -> None:
    created = await _upload(service)
    await service.mark_hashed(ctx=_ctx(), evidence_id=created["evidence_id"], sha256="a" * 64)

    result = await service.seal(
        ctx=_ctx(), evidence_id=created["evidence_id"], worm_grade="governance"
    )

    assert result["status"] == "SEALED"
    assert result["worm_grade"] == "governance"
    entries = await audit_store.all_entries()
    assert any(e.action == "evidence.sealed" for e in entries)


async def test_seal_before_hash_returns_409(service: EvidenceService) -> None:
    created = await _upload(service)

    with pytest.raises(HTTPException) as exc_info:
        await service.seal(ctx=_ctx(), evidence_id=created["evidence_id"], worm_grade="governance")
    assert exc_info.value.status_code == 409


async def test_seal_twice_returns_409(service: EvidenceService) -> None:
    created = await _upload(service)
    await service.mark_hashed(ctx=_ctx(), evidence_id=created["evidence_id"], sha256="a" * 64)
    await service.seal(ctx=_ctx(), evidence_id=created["evidence_id"], worm_grade="governance")

    with pytest.raises(HTTPException) as exc_info:
        await service.seal(ctx=_ctx(), evidence_id=created["evidence_id"], worm_grade="compliance")
    assert exc_info.value.status_code == 409


async def test_apply_legal_hold_and_audit(
    service: EvidenceService, audit_store: InMemoryAuditStore
) -> None:
    created = await _upload(service)

    result = await service.apply_legal_hold(
        ctx=_ctx(), evidence_id=created["evidence_id"], reason="pending dispute review"
    )

    assert result["legal_hold"] is True
    assert result["legal_hold_reason"] == "pending dispute review"
    entries = await audit_store.all_entries()
    assert any(e.action == "evidence.legal_hold.applied" for e in entries)


async def test_apply_legal_hold_on_sealed_record_still_succeeds(service: EvidenceService) -> None:
    created = await _upload(service)
    await service.mark_hashed(ctx=_ctx(), evidence_id=created["evidence_id"], sha256="a" * 64)
    await service.seal(ctx=_ctx(), evidence_id=created["evidence_id"], worm_grade="governance")

    result = await service.apply_legal_hold(
        ctx=_ctx(), evidence_id=created["evidence_id"], reason="post-seal dispute"
    )

    assert result["legal_hold"] is True
    assert result["status"] == "SEALED"


async def test_release_legal_hold_and_audit(
    service: EvidenceService, audit_store: InMemoryAuditStore
) -> None:
    created = await _upload(service)
    await service.apply_legal_hold(ctx=_ctx(), evidence_id=created["evidence_id"], reason="hold")

    result = await service.release_legal_hold(ctx=_ctx(), evidence_id=created["evidence_id"])

    assert result["legal_hold"] is False
    assert result["legal_hold_reason"] is None
    entries = await audit_store.all_entries()
    assert any(e.action == "evidence.legal_hold.released" for e in entries)


async def test_upload_audit_ref_resolves_to_a_real_consistent_audit_entry(
    service: EvidenceService, audit_store: InMemoryAuditStore
) -> None:
    created = await _upload(service)

    entries = {e.entry_id: e for e in await audit_store.all_entries()}

    assert created["audit_ref"] in entries
    entry = entries[created["audit_ref"]]
    assert entry.action == "evidence.uploaded"
    assert entry.resource_id == created["evidence_id"]
    assert entry.payload["parcel_id"] == created["parcel_id"]
