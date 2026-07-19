"""registry parcel counters (B3 slice 2 — atomic allocation, docs/adr/ADR-014)

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-19

One row per country_code, created lazily on that country's first-ever
allocation via
`INSERT ... ON CONFLICT (country_code) DO UPDATE ... RETURNING last_allocated`
— see ADR-014 for why this is the chosen mechanism (not a bare SEQUENCE,
not a literal port of Emergent's MongoDB `$inc`/upsert allocator).

Scoped by country_code, not tenant_id: `parcels.parcel_number` carries a
database-wide unique constraint (0007_parcels.py's
`ix_parcels_number_unique`), so a per-tenant counter would hand out
colliding numbers the moment two tenants register parcels in the same
country — discovered via live concurrency verification and corrected
before this slice's initial review (ADR-014's revision note). This table
holds no tenant-owned data (only a country code and a counter), so its RLS
policy admits any authenticated request rather than matching a specific
tenant_id — still fail-closed against anonymous/unauthenticated database
sessions, same as every table since 0001. No DELETE grant — counters are
never removed, only incremented.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

APP_ROLE = "landvault_app"


def upgrade() -> None:
    op.create_table(
        "registry_parcel_counters",
        sa.Column("country_code", sa.String(length=2), primary_key=True),
        sa.Column("last_allocated", sa.BigInteger(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.execute("ALTER TABLE registry_parcel_counters ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE registry_parcel_counters FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY registry_parcel_counters_authenticated_only ON registry_parcel_counters
        USING (
            current_setting('app.tenant_id', true) <> ''
            OR current_setting('app.is_super_admin', true) = 'true'
        )
        """
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON registry_parcel_counters TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS registry_parcel_counters_authenticated_only "
        "ON registry_parcel_counters"
    )
    op.drop_table("registry_parcel_counters")
