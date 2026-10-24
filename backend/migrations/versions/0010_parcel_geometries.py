"""parcel_geometries (B4 slice 1 — Spatial Domain Foundation, docs/adr/ADR-018)

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-22

The Spatial bounded context's own table — never written to by Registry,
never writing to `parcels` (docs/adr/ADR-018's boundary). `boundary` is
`geometry(Polygon, 4326)` — SRID enforced at the column level by Postgres
itself, per ADR-018's decision. Append-only: `status` transitions
`ACTIVE -> SUPERSEDED` only (docs/adr/ADR-018 domain invariant #2/#3); the
partial unique index below enforces "only one ACTIVE geometry per
parcel" at the database level, not merely as an application-layer
convention.

Same RLS-tenant-isolation and least-privilege-grant shape as every
tenant-scoped table since 0001 — no DELETE grant; superseding (domain-
enforced status transition) is this table's one-way "removal" path,
matching Parcel's own archival convention (ADR-013) and Tenant's before
that (ADR-010).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

APP_ROLE = "landvault_app"


def upgrade() -> None:
    op.create_table(
        "parcel_geometries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column(
            "parcel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("parcels.id"),
            nullable=False,
        ),
        # geometry(Polygon, 4326): SRID and geometry subtype enforced at
        # the column level (ADR-018) — Postgres itself rejects any INSERT
        # whose value isn't a Polygon in SRID 4326, before application
        # code ever runs. Added via raw DDL (no sqlalchemy Column type
        # maps to this natively without geoalchemy2, which this slice
        # deliberately does not add as a dependency — app.contexts.
        # spatial.adapters.orm.Geometry is the read/write-side type).
        sa.Column("srid", sa.SmallInteger(), nullable=False, server_default="4326"),
        sa.Column("status", sa.String(), nullable=False, server_default="ACTIVE"),
        sa.Column(
            "created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("identity_users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("ALTER TABLE parcel_geometries ADD COLUMN boundary geometry(Polygon, 4326) NOT NULL")

    op.create_index("ix_parcel_geometries_tenant", "parcel_geometries", ["tenant_id"])
    op.create_index(
        "ix_parcel_geometries_one_active_per_parcel",
        "parcel_geometries",
        ["parcel_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    op.execute("ALTER TABLE parcel_geometries ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE parcel_geometries FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY parcel_geometries_tenant_isolation ON parcel_geometries
        USING (
            tenant_id = current_setting('app.tenant_id', true)
            OR current_setting('app.is_super_admin', true) = 'true'
        )
        """
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON parcel_geometries TO {APP_ROLE}")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS parcel_geometries_tenant_isolation ON parcel_geometries")
    op.drop_index("ix_parcel_geometries_one_active_per_parcel", table_name="parcel_geometries")
    op.drop_index("ix_parcel_geometries_tenant", table_name="parcel_geometries")
    op.drop_table("parcel_geometries")
