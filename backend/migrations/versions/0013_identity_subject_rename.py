"""rename identity_users.keycloak_subject to identity_subject (IMVP-3, ADR-025)

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-29

Pure rename, no data transformation. ADR-025 retires Keycloak as the production
identity provider in favour of Supabase Auth; the column's stable meaning
("the trusted IdP's `sub` claim for this user") is unchanged, only its name
was Keycloak-specific. Values are untouched — a Keycloak-issued subject already
stored here remains exactly as it was; no reinterpretation of historical IDs
as Supabase IDs happens here or anywhere else.

Does not touch roles, tenant membership, delegation, or any RLS policy —
confirmed by inspection that no policy in migration 0001 (or any later one)
references this column by name; RLS here filters on tenant_id only. Fully
reversible: the downgrade is the identical rename in reverse.
"""
from __future__ import annotations

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("identity_users", "keycloak_subject", new_column_name="identity_subject")


def downgrade() -> None:
    op.alter_column("identity_users", "identity_subject", new_column_name="keycloak_subject")
