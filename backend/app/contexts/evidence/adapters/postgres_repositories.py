"""Postgres-backed adapter for the Evidence ports (app.contexts.evidence.
ports) — implements EvidenceRepository against the ORM model in
app.contexts.evidence.adapters.orm. tests/fakes/evidence.py implements the
same protocol for the hermetic unit-test suite.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.evidence.adapters.orm import EvidenceRecordModel
from app.contexts.evidence.domain.evidence_record import EvidenceRecord


def _record_from_model(model: EvidenceRecordModel) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=str(model.id),
        tenant_id=model.tenant_id,
        parcel_id=str(model.parcel_id),
        uploaded_by=str(model.uploaded_by),
        filename=model.filename,
        mime_type=model.mime_type,
        size_bytes=model.size_bytes,
        storage_key=model.storage_key,
        basis=model.basis,
        evidence_type=model.evidence_type,
        status=model.status,
        sha256=model.sha256,
        worm_grade=model.worm_grade,
        legal_hold=model.legal_hold,
        legal_hold_reason=model.legal_hold_reason,
        legal_hold_by=str(model.legal_hold_by) if model.legal_hold_by else None,
        audit_ref=model.audit_ref,
        created_at=model.created_at.isoformat(),
    )


class PostgresEvidenceRepository:
    """Constructed from the SAME AsyncSession as every other Registry/
    Evidence repository in a given request (app.contexts.evidence.
    dependencies), so an EvidenceRecord write and its corresponding audit
    entry flush into, and commit with, the identical per-request
    transaction — the same Unit-of-Work discipline docs/adr/
    ADR-023-registry-ownership-and-status-history.md established for
    ParcelHistoryRepository (docs/adr/ADR-026-evidence-domain-model.md
    "Transaction boundaries")."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: EvidenceRecord) -> EvidenceRecord:
        model = EvidenceRecordModel(
            id=uuid.UUID(record.evidence_id),
            tenant_id=record.tenant_id,
            parcel_id=uuid.UUID(record.parcel_id),
            uploaded_by=uuid.UUID(record.uploaded_by),
            filename=record.filename,
            mime_type=record.mime_type,
            size_bytes=record.size_bytes,
            storage_key=record.storage_key,
            basis=record.basis,
            evidence_type=record.evidence_type,
            status=record.status,
            sha256=record.sha256,
            worm_grade=record.worm_grade,
            legal_hold=record.legal_hold,
            legal_hold_reason=record.legal_hold_reason,
            legal_hold_by=uuid.UUID(record.legal_hold_by) if record.legal_hold_by else None,
            audit_ref=record.audit_ref,
        )
        self._session.add(model)
        await self._session.flush()
        return _record_from_model(model)

    async def get(self, evidence_id: str) -> EvidenceRecord | None:
        try:
            key = uuid.UUID(evidence_id)
        except ValueError:
            return None
        model = await self._session.get(EvidenceRecordModel, key)
        return _record_from_model(model) if model else None

    async def list_for_parcel(self, parcel_id: str) -> list[EvidenceRecord]:
        result = await self._session.execute(
            select(EvidenceRecordModel)
            .where(EvidenceRecordModel.parcel_id == uuid.UUID(parcel_id))
            .order_by(EvidenceRecordModel.created_at.desc())
        )
        return [_record_from_model(model) for model in result.scalars()]

    async def mark_hashed(self, record: EvidenceRecord) -> EvidenceRecord:
        model = await self._session.get(EvidenceRecordModel, uuid.UUID(record.evidence_id))
        if model is None:
            raise ValueError(f"evidence record {record.evidence_id} not found")
        model.status = record.status
        model.sha256 = record.sha256
        await self._session.flush()
        return _record_from_model(model)

    async def seal(self, record: EvidenceRecord) -> EvidenceRecord:
        model = await self._session.get(EvidenceRecordModel, uuid.UUID(record.evidence_id))
        if model is None:
            raise ValueError(f"evidence record {record.evidence_id} not found")
        model.status = record.status
        model.worm_grade = record.worm_grade
        await self._session.flush()
        return _record_from_model(model)

    async def set_legal_hold(self, record: EvidenceRecord) -> EvidenceRecord:
        model = await self._session.get(EvidenceRecordModel, uuid.UUID(record.evidence_id))
        if model is None:
            raise ValueError(f"evidence record {record.evidence_id} not found")
        model.legal_hold = record.legal_hold
        model.legal_hold_reason = record.legal_hold_reason
        model.legal_hold_by = uuid.UUID(record.legal_hold_by) if record.legal_hold_by else None
        await self._session.flush()
        return _record_from_model(model)
