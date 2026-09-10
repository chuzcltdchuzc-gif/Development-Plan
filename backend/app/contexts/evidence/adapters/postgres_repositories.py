"""Postgres-backed adapter for the Evidence ports (app.contexts.evidence.
ports) — implements EvidenceRepository against the ORM model in
app.contexts.evidence.adapters.orm. tests/fakes/evidence.py implements the
same protocol for the hermetic unit-test suite.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.evidence.adapters.orm import (
    EvidenceActorAttributionModel,
    EvidenceRecordModel,
)
from app.contexts.evidence.domain.attribution import EvidenceActorAttribution
from app.contexts.evidence.domain.evidence_record import EvidenceRecord
from app.contexts.evidence.ports import ParcelAuthorityInfo


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


class PostgresParcelExistenceAdapter:
    """Implements ParcelExistencePort via a read-only query against
    Registry's `parcels` table, through the same request-scoped session —
    RLS (already in effect via the Unit-of-Work's session variables) makes
    this return no row for a parcel outside the caller's tenant scope,
    identical to app.contexts.spatial.adapters.postgres_repositories.
    PostgresParcelExistenceAdapter (IMVP-5's Evidence-local copy of the
    same B4 Slice 2 pattern)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_parcel_authority(self, *, parcel_id: str) -> ParcelAuthorityInfo | None:
        result = await self._session.execute(
            text("SELECT tenant_id, created_by FROM parcels WHERE id = :parcel_id"),
            {"parcel_id": parcel_id},
        )
        row = result.one_or_none()
        if row is None:
            return None
        return ParcelAuthorityInfo(tenant_id=row.tenant_id, created_by=str(row.created_by))


def _attribution_from_model(model: EvidenceActorAttributionModel) -> EvidenceActorAttribution:
    return EvidenceActorAttribution(
        id=str(model.id),
        tenant_id=model.tenant_id,
        evidence_id=str(model.evidence_id),
        attribution_role=model.attribution_role,
        actor_reference_kind=model.actor_reference_kind,
        actor_principal_id=str(model.actor_principal_id) if model.actor_principal_id else None,
        actor_name=model.actor_name,
        actor_organization_name=model.actor_organization_name,
        actor_type=model.actor_type,
        basis=model.basis,
        review_method=model.review_method,
        recorded_by=str(model.recorded_by),
        audit_ref=model.audit_ref,
        supersedes_id=str(model.supersedes_id) if model.supersedes_id else None,
        recorded_at=model.recorded_at.isoformat(),
    )


class PostgresEvidenceActorAttributionRepository:
    """Append-only by construction, not only by the database grant/trigger
    (migrations/versions/0014) — this class never issues an UPDATE or
    DELETE against this table; there is no method here that could.
    Constructed from the SAME AsyncSession as PostgresEvidenceRepository
    (app.contexts.evidence.dependencies), so an attribution write and its
    corresponding audit entry flush into, and commit with, the identical
    per-request transaction — the same Unit-of-Work discipline ADR-023
    established and ADR-026 already reused."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, attribution: EvidenceActorAttribution) -> EvidenceActorAttribution:
        model = EvidenceActorAttributionModel(
            id=uuid.UUID(attribution.id),
            tenant_id=attribution.tenant_id,
            evidence_id=uuid.UUID(attribution.evidence_id),
            attribution_role=attribution.attribution_role,
            actor_reference_kind=attribution.actor_reference_kind,
            actor_principal_id=(
                uuid.UUID(attribution.actor_principal_id)
                if attribution.actor_principal_id
                else None
            ),
            actor_name=attribution.actor_name,
            actor_organization_name=attribution.actor_organization_name,
            actor_type=attribution.actor_type,
            basis=attribution.basis,
            review_method=attribution.review_method,
            recorded_by=uuid.UUID(attribution.recorded_by),
            audit_ref=attribution.audit_ref,
            supersedes_id=(
                uuid.UUID(attribution.supersedes_id) if attribution.supersedes_id else None
            ),
        )
        self._session.add(model)
        await self._session.flush()
        return _attribution_from_model(model)

    async def get(self, attribution_id: str) -> EvidenceActorAttribution | None:
        try:
            key = uuid.UUID(attribution_id)
        except ValueError:
            return None
        model = await self._session.get(EvidenceActorAttributionModel, key)
        return _attribution_from_model(model) if model else None

    async def list_for_evidence(self, evidence_id: str) -> list[EvidenceActorAttribution]:
        result = await self._session.execute(
            select(EvidenceActorAttributionModel)
            .where(EvidenceActorAttributionModel.evidence_id == uuid.UUID(evidence_id))
            .order_by(EvidenceActorAttributionModel.recorded_at.asc())
        )
        return [_attribution_from_model(m) for m in result.scalars()]

    async def get_successor(self, attribution_id: str) -> EvidenceActorAttribution | None:
        result = await self._session.execute(
            select(EvidenceActorAttributionModel)
            .where(EvidenceActorAttributionModel.supersedes_id == uuid.UUID(attribution_id))
        )
        model = result.scalar_one_or_none()
        return _attribution_from_model(model) if model else None


class PostgresPrincipalTenantAdapter:
    """Implements PrincipalTenantPort via a read-only query against
    Identity's `identity_users` table, through the same request-scoped
    session — mirroring PostgresParcelExistenceAdapter's exact shape and
    reasoning (a minimal, read-only cross-context lookup Evidence itself
    defines; Identity is never imported directly)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_tenant_id(self, principal_id: str) -> str | None:
        try:
            key = uuid.UUID(principal_id)
        except ValueError:
            return None
        result = await self._session.execute(
            text("SELECT tenant_id FROM identity_users WHERE id = :principal_id"),
            {"principal_id": str(key)},
        )
        row = result.one_or_none()
        return row.tenant_id if row is not None else None
