"""RealGeometryAdapter — the first real implementation of Registry's
`GeometryPort` (docs/adr/ADR-016, amended docs/adr/ADR-019), supplied by
Spatial (B4 Slice 2, docs/adr/ADR-022's "Deferred responsibilities: ADR-020"
item, brought forward into this slice per the Slice 2 authorization brief).

Satisfies `app.contexts.registry.ports.GeometryPort` structurally (Python
Protocols are structural — this class never imports anything from
`app.contexts.registry`, preserving the bounded-context isolation
docs/adr/ADR-018 requires). Depends only on the already-existing
`ParcelGeometryRepository` port (Slice 1) — no new raw SQL, no new
repository method.

`geometry_reference` is exactly a `ParcelGeometry.geometry_id`
(docs/adr/ADR-018 §"The aggregate": "there is no separate 'reference'
field on this aggregate; identity itself serves as the reference Registry
holds"). A reference is valid only if it resolves to a geometry that is
both `ACTIVE` (a `SUPERSEDED` row no longer represents the parcel's
current boundary) and actually belongs to the calling `tenant_id`/
`parcel_id` — otherwise one tenant could attach another tenant's (or
another parcel's) geometry merely by guessing or observing a valid-looking
UUID, the exact gap docs/adr/ADR-019 introduced these parameters to close.
Any lookup failure (not found, malformed reference) fails closed to
`False`, never raises past this boundary — Registry only ever needs a
boolean answer.
"""
from __future__ import annotations

from app.contexts.spatial.ports import ParcelGeometryRepository


class RealGeometryAdapter:
    def __init__(self, geometries: ParcelGeometryRepository) -> None:
        self._geometries = geometries

    async def reference_is_valid(
        self, *, geometry_reference: str, tenant_id: str, parcel_id: str
    ) -> bool:
        try:
            geometry = await self._geometries.get(geometry_reference)
        except (ValueError, LookupError):
            # Malformed reference (e.g. not a UUID) — fail closed, never a 500.
            return False
        if geometry is None:
            return False
        return (
            geometry.status == "ACTIVE"
            and geometry.tenant_id == tenant_id
            and geometry.parcel_id == parcel_id
        )
