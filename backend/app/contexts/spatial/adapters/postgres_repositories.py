"""Postgres-backed adapter for the Spatial ports (app.contexts.spatial.
ports) — implements ParcelGeometryRepository against the ORM model in
app.contexts.spatial.adapters.orm. tests/fakes/spatial.py implements the
same protocol for the hermetic unit-test suite.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.spatial.adapters.orm import ParcelGeometryRecord
from app.contexts.spatial.domain.parcel_geometry import ParcelGeometry


def _geometry_from_record(record: ParcelGeometryRecord) -> ParcelGeometry:
    return ParcelGeometry(
        geometry_id=str(record.id),
        tenant_id=record.tenant_id,
        parcel_id=str(record.parcel_id),
        boundary=record.boundary,
        created_by=str(record.created_by),
        status=record.status,
        srid=record.srid,
        created_at=record.created_at.isoformat(),
        superseded_at=record.superseded_at.isoformat() if record.superseded_at else None,
    )


class PostgresParcelGeometryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, geometry: ParcelGeometry) -> ParcelGeometry:
        record = ParcelGeometryRecord(
            id=uuid.UUID(geometry.geometry_id),
            tenant_id=geometry.tenant_id,
            parcel_id=uuid.UUID(geometry.parcel_id),
            boundary=geometry.boundary,
            srid=geometry.srid,
            status=geometry.status,
            created_by=uuid.UUID(geometry.created_by),
        )
        self._session.add(record)
        await self._session.flush()
        return _geometry_from_record(record)

    async def get(self, geometry_id: str) -> ParcelGeometry | None:
        record = await self._session.get(ParcelGeometryRecord, uuid.UUID(geometry_id))
        return _geometry_from_record(record) if record else None

    async def get_active_for_parcel(self, parcel_id: str) -> ParcelGeometry | None:
        result = await self._session.execute(
            select(ParcelGeometryRecord).where(
                ParcelGeometryRecord.parcel_id == uuid.UUID(parcel_id),
                ParcelGeometryRecord.status == "ACTIVE",
            )
        )
        record = result.scalar_one_or_none()
        return _geometry_from_record(record) if record else None

    async def update(self, geometry: ParcelGeometry) -> ParcelGeometry:
        record = await self._session.get(ParcelGeometryRecord, uuid.UUID(geometry.geometry_id))
        if record is None:
            raise ValueError(f"parcel geometry {geometry.geometry_id} not found")
        record.status = geometry.status
        record.superseded_at = (
            datetime.fromisoformat(geometry.superseded_at) if geometry.superseded_at else None
        )
        await self._session.flush()
        return _geometry_from_record(record)


class PostgresParcelExistenceAdapter:
    """Implements ParcelExistencePort via a read-only query against
    Registry's `parcels` table, through the same request-scoped session
    — RLS (already in effect via the Unit-of-Work's session variables)
    makes this return no row for a parcel outside the caller's tenant
    scope, exactly as it already does for Registry's own queries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_tenant_id(self, *, parcel_id: str) -> str | None:
        result = await self._session.execute(
            text("SELECT tenant_id FROM parcels WHERE id = :parcel_id"), {"parcel_id": parcel_id}
        )
        return result.scalar_one_or_none()
