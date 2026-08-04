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

from pydantic import BaseModel, ConfigDict


class SubmitGeometryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    boundary: str
