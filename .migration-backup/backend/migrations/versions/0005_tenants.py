"""tenants (B2 slice 3 — Tenant/Organization aggregate, docs/adr/ADR-010)

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-17

Promotes `tenant_id` from an unstructured string (identity_users,
identity_invitations) into a first-class, FK-backed aggregate with its own
lifecycle (ACTIVE/SUSPENDED/ARCHIVED). Backward compatible by construction:
`tenants.id` uses the exact same string values already in use as
`identity_users.tenant_id` — no existing id is remapped, no existing
response shape changes.

Backfill: one `tenants` row per distinct tenant_id already present in
identity_users, `owner_user_id` set to the earliest-created user in that
tenant (the self-registration "founder", for tenants created before this
migration — going forward, register_local sets this explicitly at
creation time).

Same RLS-tenant-isolation and least-privilege-grant shape as every other
tenant-scoped table (identity_users, identity_invitations) — no DELETE
grant; archival, not deletion, is this table's one-way "removal" path,
matching the Registry aggregate's "Archive: one-way" convention (ADR-005).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

APP_ROLE = "landvault_app"


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="ACTIVE"),
        sa.Column(
            "owner_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_users.id"),
            nullable=True,
        ),
        sa.Column("suspension_reason", sa.String(), nullable=True),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.execute(
        """
        INSERT INTO tenants (id, name, status, owner_user_id, created_at, updated_at)
        SELECT DISTINCT ON (u.tenant_id)
            u.tenant_id, u.tenant_id, 'ACTIVE', u.id, now(), now()
        FROM identity_users u
        ORDER BY u.tenant_id, u.created_at ASC
        """
    )

    op.create_foreign_key(
        "fk_identity_users_tenant", "identity_users", "tenants", ["tenant_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_identity_invitations_tenant", "identity_invitations", "tenants", ["tenant_id"], ["id"]
    )

    op.execute("ALTER TABLE tenants ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenants FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenants_tenant_isolation ON tenants
        USING (
            id = current_setting('app.tenant_id', true)
            OR current_setting('app.is_super_admin', true) = 'true'
        )
        """
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON tenants TO {APP_ROLE}")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenants_tenant_isolation ON tenants")
    op.drop_constraint("fk_identity_invitations_tenant", "identity_invitations", type_="foreignkey")
    op.drop_constraint("fk_identity_users_tenant", "identity_users", type_="foreignkey")
    op.drop_table("tenants")
