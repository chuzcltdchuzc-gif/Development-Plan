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


class ParcelNumberAllocator(Protocol):
    """Atomic, nationally-scoped (per country_code) parcel-number
    allocation (B3 slice 2, docs/adr/ADR-014) — every tenant registering
    parcels in the same country draws from the same sequence, since
    `parcel_number` is a database-wide unique registry identifier
    (migrations/versions/0007_parcels.py's `ix_parcels_number_unique`),
    not a tenant-private reference number. Must run in the same
    transaction as the parcel insert it precedes — see
    ParcelService.create_parcel."""

    async def allocate(self, *, country_code: str) -> str: ...
