"""identity invitations (B2 — tenant membership provisioning)

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-17

Tenant-scoped invitations so a governance-role principal can bring a new
member into their own tenant, rather than every registration creating an
isolated single-user tenant (see docs/adr/ADR-009 §"tenant provisioning"
gap, and docs/REBUILD_PLAN.md's B2 row).

Ships RLS and the least-privilege grant in the same migration
(docs/ENGINEERING_RULES.md #1) — unlike 0001, the `landvault_app` role
already exists by this point (created in 0002), so there's no need to
split role-creation into a separate migration this time.

The partial unique index enforces "at most one pending invitation per
(tenant, email)" at the database level, not just in application code —
belt-and-braces against a race between two concurrent invite requests for
the same email.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

APP_ROLE = "landvault_app"


def upgrade() -> None:
    op.create_table(
        "identity_invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("invited_email", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column(
            "invited_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_users.id"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(), nullable=False, unique=True),
        sa.Column("status", sa.String(), nullable=False, server_default="PENDING"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_identity_invitations_tenant", "identity_invitations", ["tenant_id"])
    op.create_index(
        "ix_identity_invitations_pending_email",
        "identity_invitations",
        ["tenant_id", "invited_email"],
        unique=True,
        postgresql_where=sa.text("status = 'PENDING'"),
    )

    op.execute("ALTER TABLE identity_invitations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE identity_invitations FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY identity_invitations_tenant_isolation ON identity_invitations
        USING (
            tenant_id = current_setting('app.tenant_id', true)
            OR current_setting('app.is_super_admin', true) = 'true'
        )
        """
    )

    op.execute(f"GRANT SELECT, INSERT, UPDATE ON identity_invitations TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS identity_invitations_tenant_isolation ON identity_invitations"
    )
    op.drop_index("ix_identity_invitations_pending_email", table_name="identity_invitations")
    op.drop_index("ix_identity_invitations_tenant", table_name="identity_invitations")
    op.drop_table("identity_invitations")
