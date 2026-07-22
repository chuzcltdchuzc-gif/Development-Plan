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
`ParcelGeometry.new()` is the only constructor and performs structural
validation before an instance can exist at all — there is no
`PENDING`/`REJECTED` status, and no code path can construct an instance
representing invalid geometry. The validation performed here is
deliberately structural only (non-empty, well-formed WKT `POLYGON`
syntax) — real geometric validity (self-intersection, coordinate-bounds
sanity, administrative-boundary containment) is explicitly ADR-020's job,
not this slice's.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

STATUS_ACTIVE = "ACTIVE"
STATUS_SUPERSEDED = "SUPERSEDED"

# Deliberately minimal: confirms the payload at least looks like a WKT
# POLYGON (case-insensitive keyword, a parenthesized body) — not a real
# geometric validator. Self-intersection, ring closure, coordinate-bounds
# sanity, and administrative-boundary containment are ADR-020's job; this
# slice only guarantees "the database will not be asked to store something
# that isn't shaped like a polygon at all."
_WKT_POLYGON_RE = re.compile(r"^\s*POLYGON\s*\(\(.+\)\)\s*$", re.IGNORECASE | re.DOTALL)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class InvalidGeometryError(ValueError):
    """Raised by `ParcelGeometry.new()` when the submitted payload fails
    structural validation — the payload never becomes a `ParcelGeometry`
    instance, so it can never reach persistence (ADR-018's binding
    requirement, docs/B4_THREAT_MODEL.md §6 item 1)."""


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
        if not _WKT_POLYGON_RE.match(boundary or ""):
            raise InvalidGeometryError(
                "boundary must be a well-formed WKT POLYGON, e.g. "
                "'POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))'"
            )
        return cls(
            geometry_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            parcel_id=parcel_id,
            boundary=boundary,
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
