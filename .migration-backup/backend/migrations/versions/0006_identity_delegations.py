"""identity delegations (B2 slice 4 — delegated administration, docs/adr/ADR-011)

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-18

Delegation is derived authority, scoped to one tenant, never independent
authority — see app.contexts.identity.domain.delegation for the
resolution rules this table's rows feed into. Purely additive: no existing
table's columns or constraints change, and every existing endpoint's
behavior is unaffected until a delegation actually exists.

Same RLS-tenant-isolation shape and least-privilege grant (no DELETE) as
every other tenant-scoped table (identity_users, identity_invitations,
tenants). `ix_identity_delegations_delegate` is the index the hot,
per-request context-hydration lookup depends on
(list_active_for_delegate) — without it, every authenticated request would
force a sequential scan of this table.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

APP_ROLE = "landvault_app"


def upgrade() -> None:
    op.create_table(
        "identity_delegations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column(
            "delegator_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_users.id"),
            nullable=False,
        ),
        sa.Column(
            "delegate_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_users.id"),
            nullable=False,
        ),
        sa.Column("delegated_roles", postgresql.JSONB(), nullable=False),
        sa.Column("scope", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="ACTIVE"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "revoked_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("identity_users.id"),
            nullable=True,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_identity_delegations_tenant", "identity_delegations", ["tenant_id"])
    op.create_index(
        "ix_identity_delegations_delegate",
        "identity_delegations",
        ["tenant_id", "delegate_user_id"],
    )
    op.create_index(
        "ix_identity_delegations_delegator", "identity_delegations", ["delegator_user_id"]
    )

    op.execute("ALTER TABLE identity_delegations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE identity_delegations FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY identity_delegations_tenant_isolation ON identity_delegations
        USING (
            tenant_id = current_setting('app.tenant_id', true)
            OR current_setting('app.is_super_admin', true) = 'true'
        )
        """
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON identity_delegations TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS identity_delegations_tenant_isolation ON identity_delegations"
    )
    op.drop_index("ix_identity_delegations_delegator", table_name="identity_delegations")
    op.drop_index("ix_identity_delegations_delegate", table_name="identity_delegations")
    op.drop_index("ix_identity_delegations_tenant", table_name="identity_delegations")
    op.drop_table("identity_delegations")
