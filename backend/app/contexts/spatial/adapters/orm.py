"""SQLAlchemy ORM model for the Spatial context (B4 Slice 1, docs/adr/ADR-018).

Ships its RLS policy in the same migration (docs/ENGINEERING_RULES.md #1)
— see migrations/versions/0010_parcel_geometries.py.

`Geometry`, below, is a small, local, dependency-free `TypeEngine` — this
codebase deliberately does not add `geoalchemy2` (or any other GIS
library) as a dependency for this slice (docs/ENGINEERING_RULES.md #5:
"adding a new dependency requires explicit human approval," which this
slice's authorization did not grant). Slice 1 needs no spatial query
capability at all (no `ST_Overlaps`, no `ST_Intersects` — that's
ADR-020/021's job), so the column is treated as an opaque WKT string at
the application layer, with Postgres itself doing the WKT<->geometry
conversion via `ST_GeomFromText`/`ST_AsText` at the SQL boundary. If a
richer geometry type becomes genuinely necessary once ADR-020 needs real
spatial functions from Python, evaluating `geoalchemy2` then is a
one-line dependency addition, requested with its own justification — not
pre-emptively added now for a slice that doesn't need it.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ColumnElement, DateTime, ForeignKey, Index, SmallInteger, String, func, types
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.kernel.db import Base

TZDateTime = DateTime(timezone=True)


class Geometry(types.UserDefinedType):
    """Renders as PostGIS `geometry(Polygon, 4326)` in DDL (SRID enforced
    at the column level, ADR-018) and transparently wraps bound/selected
    values with `ST_GeomFromText`/`ST_AsText` so the Python side only ever
    sees a WKT string — never a geoalchemy2 object, never raw WKB bytes."""

    cache_ok = True

    def get_col_spec(self, **kw: object) -> str:
        return "geometry(Polygon, 4326)"

    def bind_expression(self, bindvalue: ColumnElement[str]) -> ColumnElement[str]:
        return func.ST_GeomFromText(bindvalue, 4326)

    def column_expression(self, col: ColumnElement[str]) -> ColumnElement[str]:
        return func.ST_AsText(col)


class ParcelGeometryRecord(Base):
    __tablename__ = "parcel_geometries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    parcel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parcels.id"), nullable=False
    )
    boundary: Mapped[str] = mapped_column(Geometry(), nullable=False)
    # Denormalized convenience mirror of the geometry column's own
    # DB-enforced SRID (always 4326 for this ADR's Polygon-only scope) —
    # not a second source of truth: the geometry column's embedded SRID,
    # enforced by Postgres itself via the column type, is authoritative.
    # Exists so API responses/audits can read the SRID without a spatial
    # function call.
    srid: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=4326)
    status: Mapped[str] = mapped_column(String, nullable=False, default="ACTIVE")
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("identity_users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TZDateTime, server_default=func.now(), nullable=False
    )
    superseded_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)

    __table_args__ = (Index("ix_parcel_geometries_tenant", "tenant_id"),)
