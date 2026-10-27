"""In-memory fakes for the Spatial ports — implement the exact same
protocols as the real Postgres adapters (app.contexts.spatial.adapters),
so application-service tests exercise real business logic without a live
database.
"""
from __future__ import annotations

from copy import deepcopy

from app.contexts.spatial.domain.parcel_geometry import ParcelGeometry
from app.contexts.spatial.ports import ParcelAuthorityInfo
from tests.fakes.registry import InMemoryParcelRepository


class InMemoryParcelGeometryRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, ParcelGeometry] = {}

    async def add(self, geometry: ParcelGeometry) -> ParcelGeometry:
        self._by_id[geometry.geometry_id] = deepcopy(geometry)
        return deepcopy(geometry)

    async def get(self, geometry_id: str) -> ParcelGeometry | None:
        geometry = self._by_id.get(geometry_id)
        return deepcopy(geometry) if geometry else None

    async def get_active_for_parcel(self, parcel_id: str) -> ParcelGeometry | None:
        for geometry in self._by_id.values():
            if geometry.parcel_id == parcel_id and geometry.status == "ACTIVE":
                return deepcopy(geometry)
        return None

    async def update(self, geometry: ParcelGeometry) -> ParcelGeometry:
        self._by_id[geometry.geometry_id] = deepcopy(geometry)
        return deepcopy(geometry)


class FakeParcelExistencePort:
    """Wraps the SAME InMemoryParcelRepository instance the test harness
    gives to Registry — so a test can create a real parcel via Registry's
    own endpoints and immediately submit geometry against that exact
    parcel_id, the same cross-context relationship the real
    PostgresParcelExistenceAdapter has against the real `parcels` table,
    without needing a live Postgres."""

    def __init__(self, parcels: InMemoryParcelRepository) -> None:
        self._parcels = parcels

    async def get_parcel_authority(self, *, parcel_id: str) -> ParcelAuthorityInfo | None:
        parcel = await self._parcels.get(parcel_id)
        if parcel is None:
            return None
        return ParcelAuthorityInfo(
            tenant_id=parcel.tenant_id, created_by=parcel.created_by, status=parcel.status
        )
