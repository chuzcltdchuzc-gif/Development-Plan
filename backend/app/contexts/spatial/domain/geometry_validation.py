"""Structural WKT `POLYGON` validation (B4 Slice 2, docs/adr/ADR-018 §3,
ADR-022's own scope boundary — "validation should include only structural
correctness").

Deliberately excludes anything requiring real GIS computation:
self-intersection detection, administrative-boundary containment, and
any form of topology or overlap analysis are explicitly out of this
slice's scope (ADR-020/021's job, once written). What this module *does*
check is real, non-decorative structural validation, achievable in pure
Python with no external dependency (this codebase deliberately does not
add `shapely`/`geoalchemy2` for this slice — see
`app/contexts/spatial/adapters/orm.py`'s own docstring for the identical
reasoning applied to storage):

- well-formed WKT `POLYGON(...)` syntax, optionally EWKT-prefixed
  (`SRID=4326;POLYGON(...)`) — malformed input of any kind is rejected;
- ring closure (first point equals last point in every ring);
- minimum point count (at least 3 distinct vertices per ring);
- each coordinate is a genuine, in-range `(longitude, latitude)` pair;
- ring winding order (exterior ring counter-clockwise, holes clockwise —
  the OGC Simple Features convention), via the shoelace formula's sign,
  pure arithmetic, no GIS library required;
- the SRID, if declared via an EWKT prefix, must be `4326` — the one
  CRS ADR-018 decided this platform supports; anything else is rejected
  as an unsupported CRS, not silently reprojected or ignored.
"""
from __future__ import annotations

import re

_EWKT_SRID_RE = re.compile(r"^SRID=(\d+);", re.IGNORECASE)
_POLYGON_RE = re.compile(r"^POLYGON\s*\((.*)\)\s*$", re.IGNORECASE | re.DOTALL)
_RING_RE = re.compile(r"\(([^()]*)\)")
_POINT_RE = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*$"
)

SUPPORTED_SRID = 4326
_LONGITUDE_RANGE = (-180.0, 180.0)
_LATITUDE_RANGE = (-90.0, 90.0)


class InvalidGeometryError(ValueError):
    """Raised for any structural defect in a submitted WKT payload — never
    raised for a semantically-questionable but structurally sound polygon
    (self-intersection and similar are explicitly out of this slice's
    scope)."""


def _parse_point(raw: str) -> tuple[float, float]:
    match = _POINT_RE.match(raw)
    if not match:
        raise InvalidGeometryError(f"invalid coordinate pair: {raw!r}")
    x, y = float(match.group(1)), float(match.group(2))
    if not (_LONGITUDE_RANGE[0] <= x <= _LONGITUDE_RANGE[1]):
        raise InvalidGeometryError(f"longitude out of range: {x}")
    if not (_LATITUDE_RANGE[0] <= y <= _LATITUDE_RANGE[1]):
        raise InvalidGeometryError(f"latitude out of range: {y}")
    return x, y


def _parse_ring(raw: str) -> list[tuple[float, float]]:
    raw_points = [p for p in raw.split(",") if p.strip()]
    if len(raw_points) < 4:
        raise InvalidGeometryError(
            "each ring needs at least 4 points (3 distinct vertices plus the closing "
            f"point); got {len(raw_points)}"
        )
    points = [_parse_point(p) for p in raw_points]
    if points[0] != points[-1]:
        raise InvalidGeometryError("ring is not closed: first and last points differ")
    return points


def _signed_area(points: list[tuple[float, float]]) -> float:
    """Shoelace formula — sign only matters here (positive = counter-
    clockwise under the standard mathematical y-up convention), never the
    magnitude (which would be a real area computation, out of scope)."""
    total = 0.0
    for (x1, y1), (x2, y2) in zip(points, points[1:], strict=False):
        total += x1 * y2 - x2 * y1
    return total


def _validate_ring_winding(points: list[tuple[float, float]], *, is_exterior: bool) -> None:
    signed_area = _signed_area(points)
    is_ccw = signed_area > 0
    if is_exterior and not is_ccw:
        raise InvalidGeometryError(
            "exterior ring must be wound counter-clockwise (OGC Simple Features convention)"
        )
    if not is_exterior and is_ccw:
        raise InvalidGeometryError(
            "interior ring (hole) must be wound clockwise (OGC Simple Features convention)"
        )


def validate_wkt_polygon(raw: str) -> str:
    """Validates `raw` as a well-formed WKT (optionally EWKT-prefixed)
    `POLYGON`. Returns the bare WKT (SRID prefix stripped, since SRID is
    fixed platform-wide per ADR-018 and never varies per row) on success;
    raises `InvalidGeometryError` with a specific reason on any structural
    defect. Never returns a value for invalid input — this is the
    boundary `ParcelGeometry.new()` relies on to guarantee "invalid
    geometry never reaches persistence" (ADR-018)."""
    text = (raw or "").strip()
    if not text:
        raise InvalidGeometryError("boundary must not be empty")

    srid_match = _EWKT_SRID_RE.match(text)
    if srid_match:
        srid = int(srid_match.group(1))
        if srid != SUPPORTED_SRID:
            raise InvalidGeometryError(
                f"unsupported CRS: SRID {srid} (only {SUPPORTED_SRID} is supported)"
            )
        text = text[srid_match.end():].strip()

    polygon_match = _POLYGON_RE.match(text)
    if not polygon_match:
        raise InvalidGeometryError(
            "boundary must be a well-formed WKT POLYGON, e.g. "
            "'POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))'"
        )

    body = polygon_match.group(1).strip()
    if not body:
        raise InvalidGeometryError("polygon has no rings")

    ring_matches = _RING_RE.findall(body)
    if not ring_matches:
        raise InvalidGeometryError("polygon has no well-formed rings")

    for index, ring_raw in enumerate(ring_matches):
        points = _parse_ring(ring_raw)
        _validate_ring_winding(points, is_exterior=(index == 0))

    return f"POLYGON({body})"
