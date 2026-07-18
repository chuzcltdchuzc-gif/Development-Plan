"""Postgres-backed adapter for the Registry ports (app.contexts.registry.
ports) — implements ParcelRepository against the ORM model in
app.contexts.registry.adapters.orm. tests/fakes/registry.py implements the
same protocol for the hermetic unit-test suite.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.registry.adapters.orm import ParcelRecord
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
        await self._session.flush()
        return _parcel_from_record(record)
