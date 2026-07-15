"""application role with least privilege (fixes ineffective audit_log REVOKE)

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-15

0001 ran `REVOKE UPDATE, DELETE ON audit_log FROM PUBLIC`, intending to make
audit_log append-only even for the application's own database role. Verified
against a live Postgres, that revoke was a no-op: the role the app/migrations
connect as (from POSTGRES_USER) owns the tables it created, and table
ownership grants full privileges regardless of REVOKE — only non-owner roles
are restricted by GRANT/REVOKE (or RLS). This migration creates a distinct,
non-owning `landvault_app` role for the application's runtime connections;
migrations continue to run as the owning role. `landvault_app`'s password
comes from the POSTGRES_APP_PASSWORD env var, never hardcoded here.
"""
from __future__ import annotations

import os

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

APP_ROLE = "landvault_app"


def upgrade() -> None:
    password = os.environ.get("POSTGRES_APP_PASSWORD")
    if not password:
        raise RuntimeError(
            "POSTGRES_APP_PASSWORD must be set to run this migration "
            "(it becomes the application runtime role's password)"
        )
    # Postgres's CREATE/ALTER ROLE ... PASSWORD clause is DDL — it does not
    # accept a bind parameter there (confirmed against a live Postgres:
    # "syntax error at or near $1"). The value must be a SQL string literal.
    # Safe here because it's our own generated secret, never user input —
    # but still reject anything that would break out of the quoted literal.
    if "'" in password or "\\" in password:
        raise RuntimeError("POSTGRES_APP_PASSWORD must not contain quotes or backslashes")
    escaped_password = password.replace("'", "''")

    connection = op.get_bind()
    exists = connection.execute(
        sa.text("SELECT 1 FROM pg_roles WHERE rolname = :role"), {"role": APP_ROLE}
    ).scalar()
    verb = "ALTER" if exists else "CREATE"
    connection.execute(sa.text(f"{verb} ROLE {APP_ROLE} WITH LOGIN PASSWORD '{escaped_password}'"))

    op.execute(f"GRANT USAGE ON SCHEMA public TO {APP_ROLE}")
    op.execute(
        f"GRANT SELECT, INSERT, UPDATE ON identity_users, identity_sessions TO {APP_ROLE}"
    )
    # audit_log: deliberately SELECT + INSERT only — no UPDATE, DELETE, or
    # TRUNCATE, for the exact append-only guarantee 0001 claimed but didn't
    # actually achieve for the owning role.
    op.execute(f"GRANT SELECT, INSERT ON audit_log TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM {APP_ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA public FROM {APP_ROLE}")
    op.execute(f"DROP ROLE IF EXISTS {APP_ROLE}")
