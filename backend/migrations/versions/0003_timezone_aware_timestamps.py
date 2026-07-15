"""timezone-aware timestamp columns (fixes naive/aware datetime mismatch)

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-15

0001 declared datetime columns without `timezone=True`, defaulting to
Postgres TIMESTAMP WITHOUT TIME ZONE. The domain layer works exclusively in
aware UTC datetimes (datetime.now(UTC)) — verified against a live Postgres,
inserting a Session with an aware `expires_at` raised
`asyncpg.exceptions.DataError: can't subtract offset-naive and
offset-aware datetimes`. Postgres can convert TIMESTAMP -> TIMESTAMPTZ
in-place (interpreting existing naive values as UTC, which matches how
server_default=func.now() values were actually written).
"""
from __future__ import annotations

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

_COLUMNS = [
    ("identity_users", "last_login_at"),
    ("identity_users", "created_at"),
    ("identity_users", "updated_at"),
    ("identity_users", "deleted_at"),
    ("identity_sessions", "expires_at"),
    ("identity_sessions", "revoked_at"),
    ("identity_sessions", "created_at"),
    ("audit_log", "created_at"),
]


def upgrade() -> None:
    for table, column in _COLUMNS:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} "
            f"TYPE TIMESTAMPTZ USING {column} AT TIME ZONE 'UTC'"
        )


def downgrade() -> None:
    for table, column in _COLUMNS:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} "
            f"TYPE TIMESTAMP WITHOUT TIME ZONE USING {column} AT TIME ZONE 'UTC'"
        )
