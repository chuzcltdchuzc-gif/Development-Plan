"""parcels (B3 slice 1 — Parcel Aggregate / Registry domain, docs/adr/ADR-013)

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-18

The canonical, single Parcel aggregate — see ADR-013 for the full domain
model and invariants. `parcel_number` is nullable and reserved for Slice
2's atomic allocator; the partial unique index below enforces uniqueness
at the database level from this migration onward, so allocation never
needs a retrofit. No atomic allocation logic is implemented here.

Same RLS-tenant-isolation and least-privilege-grant shape as every
tenant-scoped table since 0001 — no DELETE grant; archival (status column,
domain-enforced) is this table's one-way "removal" path, matching the
Tenant aggregate's convention (ADR-010).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

APP_ROLE = "landvault_app"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "parcels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("origin", sa.String(), nullable=False),
        sa.Column(
            "created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("identity_users.id"),
            nullable=False,
        ),
        sa.Column(
            "updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("identity_users.id"),
            nullable=True,
        ),
        sa.Column("status", sa.String(), nullable=False, server_default="ACTIVE"),
        # Reserved for B3 Slice 2's atomic allocator — never populated by
        # Slice 1. Nullable until allocated; unique once set (see the
        # partial index below).
        sa.Column("parcel_number", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("lga", sa.String(), nullable=True),
        sa.Column("ward", sa.String(), nullable=True),
        sa.Column("community", sa.String(), nullable=True),
        sa.Column("property_type", sa.String(), nullable=True),
        sa.Column("size_sqm", sa.Float(), nullable=True),
        sa.Column("ownership_type", sa.String(), nullable=True),
        # Current ownership REFERENCE only — deliberately not a history
        # (ADR-013 invariant #12). No PII beyond free-text name/contact;
        # see ADR-013 on why nothing resembling a national ID field is
        # included here.
        sa.Column("current_owner_name", sa.String(), nullable=True),
        sa.Column("current_owner_contact", sa.String(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_parcels_tenant", "parcels", ["tenant_id"])
    op.create_index(
        "ix_parcels_number_unique",
        "parcels",
        ["parcel_number"],
        unique=True,
        postgresql_where=sa.text("parcel_number IS NOT NULL"),
    )

    op.execute("ALTER TABLE parcels ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE parcels FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY parcels_tenant_isolation ON parcels
        USING (
            tenant_id = current_setting('app.tenant_id', true)
            OR current_setting('app.is_super_admin', true) = 'true'
        )
        """
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON parcels TO {APP_ROLE}")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS parcels_tenant_isolation ON parcels")
    op.drop_index("ix_parcels_number_unique", table_name="parcels")
    op.drop_index("ix_parcels_tenant", table_name="parcels")
    op.drop_table("parcels")
