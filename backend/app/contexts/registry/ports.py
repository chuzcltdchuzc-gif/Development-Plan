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


class GeometryPort(Protocol):
    """The entire seam Registry depends on for spatial capability (B3
    slice 4, docs/adr/ADR-016) — never PostGIS or any concrete GIS
    technology directly. Deliberately minimal: Registry needs to know only
    whether a reference makes sense to attach, never geometry content
    itself. `app.contexts.registry.adapters.geometry.
    PlaceholderGeometryAdapter` satisfies this with zero business logic;
    a future Spatial Intelligence context (B4) supplies the first real
    implementation without any change to ParcelService, Parcel, or this
    protocol.

    `tenant_id`/`parcel_id` (docs/adr/ADR-019, amending ADR-016) are the
    caller's own already-authorized context, passed through so a real
    adapter can verify a reference actually belongs to the tenant/parcel
    attaching it — without them, a real adapter could only confirm a
    `geometry_reference` exists *somewhere*, not that it belongs to this
    caller, letting one tenant attach another tenant's reference merely by
    guessing or observing a valid-looking value."""

    async def reference_is_valid(
        self, *, geometry_reference: str, tenant_id: str, parcel_id: str
    ) -> bool: ...
