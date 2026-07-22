"""Ports the Spatial application layer depends on (B4 Slice 1,
docs/adr/ADR-018). Concrete adapters (Postgres repository) implement
these; tests use in-memory fakes. Neither the domain nor the application
layer imports an adapter directly (docs/adr/ADR-002).
"""
from __future__ import annotations

from typing import Protocol

from app.contexts.spatial.domain.parcel_geometry import ParcelGeometry


class ParcelGeometryRepository(Protocol):
    async def add(self, geometry: ParcelGeometry) -> ParcelGeometry: ...
    async def get(self, geometry_id: str) -> ParcelGeometry | None: ...
    async def get_active_for_parcel(self, parcel_id: str) -> ParcelGeometry | None: ...
    async def update(self, geometry: ParcelGeometry) -> ParcelGeometry: ...


class ParcelExistencePort(Protocol):
    """Read-only existence/tenant lookup against Registry's `parcels`
    table (B4 Slice 1) — the one place Spatial reads across the context
    boundary (docs/adr/ADR-018 forbids writes in either direction; this is
    a read, the same kind of cross-context database relationship
    `parcels.tenant_id -> tenants.id` already relies on). Returns the
    parcel's own `tenant_id` if it exists (and, for the real adapter, is
    visible under `parcels`' own RLS policy — the identical fail-closed
    behavior Registry's own queries already get for free), `None`
    otherwise. Kept as its own port (not a raw session dependency) so
    SpatialService stays testable against an in-memory fake, exactly like
    every other application service in this codebase."""

    async def get_tenant_id(self, *, parcel_id: str) -> str | None: ...
