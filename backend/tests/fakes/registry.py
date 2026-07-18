"""In-memory fake for the Registry ports — implements the exact same
protocol as the real Postgres adapter (app.contexts.registry.adapters),
so application-service tests exercise real business logic without a live
database.
"""
from __future__ import annotations

from copy import deepcopy

from app.contexts.registry.domain.parcel import Parcel


class InMemoryParcelRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, Parcel] = {}

    async def add(self, parcel: Parcel) -> Parcel:
        self._by_id[parcel.parcel_id] = deepcopy(parcel)
        return deepcopy(parcel)

    async def get(self, parcel_id: str) -> Parcel | None:
        parcel = self._by_id.get(parcel_id)
        return deepcopy(parcel) if parcel else None

    async def list_for_tenant(self, tenant_id: str) -> list[Parcel]:
        return sorted(
            (deepcopy(p) for p in self._by_id.values() if p.tenant_id == tenant_id),
            key=lambda p: p.created_at,
            reverse=True,
        )

    async def update(self, parcel: Parcel) -> Parcel:
        self._by_id[parcel.parcel_id] = deepcopy(parcel)
        return deepcopy(parcel)
