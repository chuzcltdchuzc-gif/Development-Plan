"""Ports the Spatial application layer depends on (B4 Slice 1,
docs/adr/ADR-018; extended B4 Slice 2, docs/adr/ADR-022 §8). Concrete
adapters (Postgres repository) implement these; tests use in-memory
fakes. Neither the domain nor the application layer imports an adapter
directly (docs/adr/ADR-002).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.contexts.spatial.domain.parcel_geometry import ParcelGeometry


class ParcelGeometryRepository(Protocol):
    async def add(self, geometry: ParcelGeometry) -> ParcelGeometry: ...
    async def get(self, geometry_id: str) -> ParcelGeometry | None: ...
    async def get_active_for_parcel(self, parcel_id: str) -> ParcelGeometry | None: ...
    async def update(self, geometry: ParcelGeometry) -> ParcelGeometry: ...


@dataclass(frozen=True)
class ParcelAuthorityInfo:
    """The minimum information ADR-022 §§2/3/5/8 need about the parcel a
    geometry submission targets — tenant scope, creator authority, and
    archived-parcel status — in one round-trip (ADR-022 §8's explicit
    design consequence). Never exposes any other Registry-internal field;
    Spatial has no need for, and must not depend on, anything else about
    a parcel (ADR-018/ADR-022 bounded-context isolation)."""

    tenant_id: str
    created_by: str
    status: str


class ParcelExistencePort(Protocol):
    """Read-only existence/authority lookup against Registry's `parcels`
    table (B4 Slice 1; extended Slice 2 per ADR-022 §8) — the one place
    Spatial reads across the context boundary (docs/adr/ADR-018 forbids
    writes in either direction; this is a read, the same kind of
    cross-context database relationship `parcels.tenant_id -> tenants.id`
    already relies on). Returns `ParcelAuthorityInfo` if the parcel exists
    (and, for the real adapter, is visible under `parcels`' own RLS policy
    — the identical fail-closed behavior Registry's own queries already
    get for free), `None` otherwise. Kept as its own port (not a raw
    session dependency) so SpatialService stays testable against an
    in-memory fake, exactly like every other application service in this
    codebase."""

    async def get_parcel_authority(self, *, parcel_id: str) -> ParcelAuthorityInfo | None: ...
