"""parcels.geometry_reference (B3 slice 4 — Geometry Port Boundary, docs/adr/ADR-016)

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-20

Adds exactly one nullable column: an opaque pointer to a future Spatial
Intelligence context's own geometry data (ADR-016). Deliberately NOT a
PostGIS `geometry` type — Registry depends only on the GeometryPort
contract, never on PostGIS directly, so this column carries no spatial
semantics at all. Purely additive: no existing column, index, RLS policy,
or grant is touched. Backward compatible with every row inserted by
Slices 1–3 (defaults to NULL, meaning "no geometry associated yet").
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("parcels", sa.Column("geometry_reference", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("parcels", "geometry_reference")
