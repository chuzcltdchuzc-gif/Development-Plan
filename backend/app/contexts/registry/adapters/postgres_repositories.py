"""Postgres-backed adapter for the Registry ports (app.contexts.registry.
ports) — implements ParcelRepository against the ORM model in
app.contexts.registry.adapters.orm. tests/fakes/registry.py implements the
same protocol for the hermetic unit-test suite.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.registry.adapters.orm import (
    ParcelOwnershipHistoryRecord,
    ParcelRecord,
    ParcelStatusHistoryRecord,
    RegistryParcelCounterRecord,
)
from app.contexts.registry.domain.history import OwnershipAssertion, StatusAssertion
from app.contexts.registry.domain.parcel import Parcel


def _looks_like_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


def _parcel_from_record(record: ParcelRecord) -> Parcel:
    return Parcel(
        parcel_id=str(record.id),
        tenant_id=record.tenant_id,
        country_code=record.country_code,
        origin=record.origin,
        created_by=str(record.created_by),
        status=record.status,
        parcel_number=record.parcel_number,
        title=record.title,
        address=record.address,
        state=record.state,
        lga=record.lga,
        ward=record.ward,
        community=record.community,
        property_type=record.property_type,
        size_sqm=record.size_sqm,
        ownership_type=record.ownership_type,
        current_owner_name=record.current_owner_name,
        current_owner_contact=record.current_owner_contact,
        created_at=record.created_at.isoformat(),
        updated_at=record.updated_at.isoformat(),
        updated_by=str(record.updated_by) if record.updated_by else None,
        archived_at=record.archived_at.isoformat() if record.archived_at else None,
        geometry_reference=record.geometry_reference,
    )


class PostgresParcelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, parcel: Parcel) -> Parcel:
        record = ParcelRecord(
            id=uuid.UUID(parcel.parcel_id) if _looks_like_uuid(parcel.parcel_id) else uuid.uuid4(),
            tenant_id=parcel.tenant_id,
            country_code=parcel.country_code,
            origin=parcel.origin,
            created_by=uuid.UUID(parcel.created_by),
            status=parcel.status,
            parcel_number=parcel.parcel_number,
            title=parcel.title,
            address=parcel.address,
            state=parcel.state,
            lga=parcel.lga,
            ward=parcel.ward,
            community=parcel.community,
            property_type=parcel.property_type,
            size_sqm=parcel.size_sqm,
            ownership_type=parcel.ownership_type,
            current_owner_name=parcel.current_owner_name,
            current_owner_contact=parcel.current_owner_contact,
            geometry_reference=parcel.geometry_reference,
        )
        self._session.add(record)
        await self._session.flush()
        return _parcel_from_record(record)

    async def get(self, parcel_id: str) -> Parcel | None:
        if not _looks_like_uuid(parcel_id):
            return None
        record = await self._session.get(ParcelRecord, uuid.UUID(parcel_id))
        return _parcel_from_record(record) if record else None

    async def list_for_tenant(self, tenant_id: str) -> list[Parcel]:
        result = await self._session.execute(
            select(ParcelRecord)
            .where(ParcelRecord.tenant_id == tenant_id)
            .order_by(ParcelRecord.created_at.desc())
        )
        return [_parcel_from_record(record) for record in result.scalars()]

    async def update(self, parcel: Parcel) -> Parcel:
        record = await self._session.get(ParcelRecord, uuid.UUID(parcel.parcel_id))
        if record is None:
            raise ValueError(f"parcel {parcel.parcel_id} not found")
        record.status = parcel.status
        record.parcel_number = parcel.parcel_number
        record.title = parcel.title
        record.address = parcel.address
        record.state = parcel.state
        record.lga = parcel.lga
        record.ward = parcel.ward
        record.community = parcel.community
        record.property_type = parcel.property_type
        record.size_sqm = parcel.size_sqm
        record.ownership_type = parcel.ownership_type
        record.current_owner_name = parcel.current_owner_name
        record.current_owner_contact = parcel.current_owner_contact
        record.updated_by = uuid.UUID(parcel.updated_by) if parcel.updated_by else None
        record.updated_at = datetime.fromisoformat(parcel.updated_at)
        record.archived_at = (
            datetime.fromisoformat(parcel.archived_at) if parcel.archived_at else None
        )
        record.geometry_reference = parcel.geometry_reference
        await self._session.flush()
        return _parcel_from_record(record)


def _ownership_from_record(record: ParcelOwnershipHistoryRecord) -> OwnershipAssertion:
    return OwnershipAssertion(
        id=str(record.id),
        tenant_id=record.tenant_id,
        parcel_id=str(record.parcel_id),
        asserted_holder_ref=record.asserted_holder_ref,
        basis=record.basis,
        recorded_by=str(record.recorded_by),
        audit_ref=record.audit_ref,
        supersedes_id=str(record.supersedes_id) if record.supersedes_id else None,
        recorded_at=record.recorded_at.isoformat(),
    )


def _status_from_record(record: ParcelStatusHistoryRecord) -> StatusAssertion:
    return StatusAssertion(
        id=str(record.id),
        tenant_id=record.tenant_id,
        parcel_id=str(record.parcel_id),
        asserted_status=record.asserted_status or "",
        basis=record.basis,
        recorded_by=str(record.recorded_by),
        audit_ref=record.audit_ref,
        supersedes_id=str(record.supersedes_id) if record.supersedes_id else None,
        recorded_at=record.recorded_at.isoformat(),
    )


class PostgresParcelHistoryRepository:
    """Append-only by construction, not only by the database grant/trigger
    (migrations/versions/0011) — this class simply never issues an UPDATE
    or DELETE against either table; there is no method here that could.
    Constructed from the SAME AsyncSession as PostgresParcelRepository
    (app.contexts.registry.dependencies), so a history write and the parcel
    mutation that produced it flush into, and commit with, the identical
    per-request transaction (docs/adr/ADR-023 "Same Unit of Work")."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_ownership(self, assertion: OwnershipAssertion) -> OwnershipAssertion:
        record = ParcelOwnershipHistoryRecord(
            id=uuid.UUID(assertion.id),
            tenant_id=assertion.tenant_id,
            parcel_id=uuid.UUID(assertion.parcel_id),
            asserted_holder_ref=assertion.asserted_holder_ref,
            basis=assertion.basis,
            recorded_by=uuid.UUID(assertion.recorded_by),
            audit_ref=assertion.audit_ref,
            supersedes_id=uuid.UUID(assertion.supersedes_id) if assertion.supersedes_id else None,
        )
        self._session.add(record)
        await self._session.flush()
        return _ownership_from_record(record)

    async def record_status(self, assertion: StatusAssertion) -> StatusAssertion:
        record = ParcelStatusHistoryRecord(
            id=uuid.UUID(assertion.id),
            tenant_id=assertion.tenant_id,
            parcel_id=uuid.UUID(assertion.parcel_id),
            asserted_status=assertion.asserted_status,
            basis=assertion.basis,
            recorded_by=uuid.UUID(assertion.recorded_by),
            audit_ref=assertion.audit_ref,
            supersedes_id=uuid.UUID(assertion.supersedes_id) if assertion.supersedes_id else None,
        )
        self._session.add(record)
        await self._session.flush()
        return _status_from_record(record)

    async def latest_ownership(self, parcel_id: str) -> OwnershipAssertion | None:
        result = await self._session.execute(
            select(ParcelOwnershipHistoryRecord)
            .where(ParcelOwnershipHistoryRecord.parcel_id == uuid.UUID(parcel_id))
            .order_by(ParcelOwnershipHistoryRecord.recorded_at.desc())
            .limit(1)
        )
        record = result.scalar_one_or_none()
        return _ownership_from_record(record) if record else None

    async def latest_status(self, parcel_id: str) -> StatusAssertion | None:
        result = await self._session.execute(
            select(ParcelStatusHistoryRecord)
            .where(ParcelStatusHistoryRecord.parcel_id == uuid.UUID(parcel_id))
            .order_by(ParcelStatusHistoryRecord.recorded_at.desc())
            .limit(1)
        )
        record = result.scalar_one_or_none()
        return _status_from_record(record) if record else None


class PostgresParcelNumberAllocator:
    """One atomic `INSERT ... ON CONFLICT DO UPDATE ... RETURNING`
    statement — see docs/adr/ADR-014 for why this is the chosen mechanism
    (not a bare SEQUENCE, not a literal port of Emergent's MongoDB
    $inc/upsert allocator) and its concurrency/rollback guarantees.
    Scoped per country_code, not per tenant: `parcel_number` carries a
    database-wide unique constraint (0007_parcels.py's
    `ix_parcels_number_unique`), so every tenant registering parcels in
    the same country must draw from the same sequence — a per-tenant
    counter would hand out numbers that collide across tenants the moment
    more than one tenant operates in a country (found via live concurrency
    verification, see ADR-014's revision note). Must be constructed from
    the SAME AsyncSession (and therefore the same transaction) as the
    ParcelRepository call it precedes — app.contexts.registry.dependencies
    wires both from the same per-request session via FastAPI's dependency
    caching, the identical pattern
    app.contexts.identity.dependencies.get_auth_service already relies
    on."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def allocate(self, *, country_code: str) -> str:
        upsert = pg_insert(RegistryParcelCounterRecord).values(
            country_code=country_code, last_allocated=1
        )
        stmt = upsert.on_conflict_do_update(
            index_elements=[RegistryParcelCounterRecord.country_code],
            set_={"last_allocated": RegistryParcelCounterRecord.last_allocated + 1},
        ).returning(RegistryParcelCounterRecord.last_allocated)
        result = await self._session.execute(stmt)
        sequence_value = result.scalar_one()
        return f"LV-{country_code}-{sequence_value:06d}"
