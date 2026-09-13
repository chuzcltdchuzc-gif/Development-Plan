"""ParcelGeometry aggregate — Spatial Intelligence's canonical representation
of one parcel's boundary submission (B4 Slice 1, docs/adr/ADR-018).

`geometry_id` is the exact value Registry's `parcels.geometry_reference`
stores once accepted (docs/adr/ADR-018 §"The aggregate") — there is no
separate "reference" field on this aggregate; identity itself serves as
the reference Registry holds.

Append-only, mirroring Parcel's own "ownership history is append-only"
principle (ADR-013), generalized here to geometry history: a correction
is a new `ParcelGeometry` row, never an in-place edit of `boundary`. The
row being corrected transitions `ACTIVE -> SUPERSEDED` and is retained
forever (no delete grant, matching the platform's universal convention).

Validation gates persistence (ADR-018 §"Validation gates persistence"):
`ParcelGeometry.new()` is the only constructor and performs real
structural validation (`app.contexts.spatial.domain.geometry_validation`,
B4 Slice 2) before an instance can exist at all — there is no
`PENDING`/`REJECTED` status, and no code path can construct an instance
representing invalid geometry. Validation remains structural only —
well-formedness, ring closure, minimum point count, coordinate sanity,
winding order, SRID — never self-intersection or administrative-boundary
containment, which stay ADR-020's job.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.contexts.spatial.domain.geometry_validation import validate_wkt_polygon

STATUS_ACTIVE = "ACTIVE"
STATUS_SUPERSEDED = "SUPERSEDED"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class ParcelGeometryAlreadySupersededError(Exception):
    """Raised when `supersede()` is called on a row that is already
    `SUPERSEDED` — mirrors `ParcelArchivedError`'s role for `Parcel`
    (ADR-013): the one guard every mutator on this aggregate calls first,
    so "superseded rows are immutable" is enforced structurally."""


@dataclass
class ParcelGeometry:
    geometry_id: str
    tenant_id: str
    parcel_id: str
    boundary: str  # WKT `POLYGON(...)`, always SRID 4326 (ADR-018)
    created_by: str
    status: str = STATUS_ACTIVE
    srid: int = 4326
    created_at: str = field(default_factory=_now_iso)
    superseded_at: str | None = None

    @classmethod
    def new(
        cls, *, tenant_id: str, parcel_id: str, boundary: str, created_by: str
    ) -> ParcelGeometry:
        validated_boundary = validate_wkt_polygon(boundary)
        return cls(
            geometry_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            parcel_id=parcel_id,
            boundary=validated_boundary,
            created_by=created_by,
        )

    def is_active(self) -> bool:
        return self.status == STATUS_ACTIVE

    def supersede(self) -> None:
        """The only mutation this aggregate ever undergoes: transitioning
        the row a correction replaces from ACTIVE to SUPERSEDED. Never
        called on an already-SUPERSEDED row — that would mean two
        corrections both claiming to replace the same prior state, which
        cannot happen if `SpatialService` always supersedes the current
        ACTIVE row (at most one per parcel, DB-enforced, see migration
        `0010`) before inserting the new one."""
        if self.status == STATUS_SUPERSEDED:
            raise ParcelGeometryAlreadySupersededError(
                "cannot supersede a geometry that is already superseded"
            )
        self.status = STATUS_SUPERSEDED
        self.superseded_at = _now_iso()
