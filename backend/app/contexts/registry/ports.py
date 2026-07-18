"""Ports the Registry application layer depends on. Concrete adapters
(Postgres repositories) implement these; tests use in-memory fakes.
Neither the domain nor the application layer imports an adapter directly
(docs/adr/ADR-002).
"""
from __future__ import annotations

from typing import Protocol

from app.contexts.registry.domain.parcel import Parcel


class ParcelRepository(Protocol):
    async def add(self, parcel: Parcel) -> Parcel: ...
    async def get(self, parcel_id: str) -> Parcel | None: ...
    async def list_for_tenant(self, tenant_id: str) -> list[Parcel]: ...
    async def update(self, parcel: Parcel) -> Parcel: ...
