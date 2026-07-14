"""identity and audit tables + RLS policies

Revision ID: 0001
Revises:
Create Date: 2026-07-14

Ships RLS in the same commit that creates each table
(docs/ENGINEERING_RULES.md #1) — not written yet, tested against a live
Postgres. See CLAUDE.md for what's verified vs. not.

Tenant isolation policy: the application sets `SET LOCAL app.tenant_id` and
`SET LOCAL app.is_super_admin` at the start of every request-scoped
transaction (from the ExecutionContext); the policies below read those
session variables. A missing/empty setting means the policy compares
against an empty string, matching nothing — fails closed, not open.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "identity_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("keycloak_subject", sa.String(), nullable=False, unique=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("country", sa.String(length=2), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=True),
        sa.Column("roles", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("account_status", sa.String(), nullable=False, server_default="active"),
        sa.Column("suspension_reason", sa.String(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_identity_users_tenant", "identity_users", ["tenant_id"])

    op.create_table(
        "identity_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_users.id"),
            nullable=False,
        ),
        sa.Column("refresh_token_hash", sa.String(), nullable=False, unique=True),
        sa.Column("idp_refresh_token", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="ACTIVE"),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("rotated_from", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_reason", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_identity_sessions_user", "identity_sessions", ["user_id"])

    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(), nullable=False),
        sa.Column("resource_id", sa.String(), nullable=True),
        sa.Column("decision", sa.String(), nullable=True),
        sa.Column("principal_id", sa.String(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("prev_hash", sa.String(length=64), nullable=False),
        sa.Column("hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])

    # ---- Row-level security ----------------------------------------------
    # identity_users / identity_sessions: tenant isolation, defence in depth
    # alongside the PDP's tenant check (docs/adr/ADR-003).
    op.execute("ALTER TABLE identity_users ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE identity_users FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY identity_users_tenant_isolation ON identity_users
        USING (
            tenant_id = current_setting('app.tenant_id', true)
            OR current_setting('app.is_super_admin', true) = 'true'
        )
        """
    )

    op.execute("ALTER TABLE identity_sessions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE identity_sessions FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY identity_sessions_tenant_isolation ON identity_sessions
        USING (
            EXISTS (
                SELECT 1 FROM identity_users u
                WHERE u.id = identity_sessions.user_id
                AND (
                    u.tenant_id = current_setting('app.tenant_id', true)
                    OR current_setting('app.is_super_admin', true) = 'true'
                )
            )
        )
        """
    )

    # audit_log: append-only for everyone, including the application role —
    # UPDATE/DELETE are revoked outright rather than merely policy-denied, so
    # even a superuser-equivalent app role can't bypass this via RLS quirks.
    op.execute("ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_log FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY audit_log_read_all ON audit_log
        FOR SELECT USING (true)
        """
    )
    op.execute(
        """
        CREATE POLICY audit_log_insert_only ON audit_log
        FOR INSERT WITH CHECK (true)
        """
    )
    op.execute("REVOKE UPDATE, DELETE ON audit_log FROM PUBLIC")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS audit_log_insert_only ON audit_log")
    op.execute("DROP POLICY IF EXISTS audit_log_read_all ON audit_log")
    op.execute("DROP POLICY IF EXISTS identity_sessions_tenant_isolation ON identity_sessions")
    op.execute("DROP POLICY IF EXISTS identity_users_tenant_isolation ON identity_users")
    op.drop_index("ix_audit_log_created_at", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_index("ix_identity_sessions_user", table_name="identity_sessions")
    op.drop_table("identity_sessions")
    op.drop_index("ix_identity_users_tenant", table_name="identity_users")
    op.drop_table("identity_users")
