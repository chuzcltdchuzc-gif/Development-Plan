"""Spatial API request/response shapes (B4 Slice 1, docs/adr/ADR-018).

`boundary` is accepted as a raw WKT string (e.g.
`"POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))"`) — the simplest possible structural
input for this slice, requiring no GeoJSON-parsing dependency. Real
geometric validation (self-intersection, coordinate bounds, containment)
is explicitly ADR-020's job; this slice's DTO only confirms a string was
sent, the same "structural, not semantic" boundary the domain layer's own
`ParcelGeometry.new()` guard applies.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, WithJsonSchema


class SubmitGeometryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    boundary: str


class GeometryStatus(StrEnum):
    """The two values `app.contexts.spatial.domain.parcel_geometry.
    ParcelGeometry.status` can ever hold (STATUS_ACTIVE/STATUS_SUPERSEDED)."""

    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"


class GeometryResponse(BaseModel):
    """Mirrors `spatial_service._geometry_view` field-for-field."""

    geometry_id: str
    tenant_id: str
    parcel_id: str
    boundary: str
    # OpenAPI `type: number`, not the more precise `integer` — Wire/Python
    # value is still a plain int (this only overrides the *documented*
    # schema, WithJsonSchema doesn't touch (de)serialization). Orval
    # 8.23.0's zod generator emits the zod-v4-only top-level `z.int()` for
    # any `type: integer` field regardless of target zod version, which
    # doesn't exist on this workspace's pinned zod v3
    # (pnpm-workspace.yaml's `zod: ^3.25.76` catalog entry) — `number`
    # sidesteps that generator bug without any wire-format change.
    srid: Annotated[int, WithJsonSchema({"type": "number", "title": "Srid"})]
    status: GeometryStatus
    created_by: str
    created_at: str
    superseded_at: str | None = None
