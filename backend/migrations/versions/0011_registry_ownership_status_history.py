"""parcel ownership & status history (B3, docs/adr/ADR-023)

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-31

Two append-only history tables, populated as a side effect of the existing
ParcelService.create_parcel/update_parcel/archive_parcel — no new endpoint,
no new mutation command. Same RLS predicate as parcels (migration 0007),
enabled AND forced. Append-only is enforced at two independent layers,
neither a substitute for the other: (1) GRANT SELECT, INSERT only to
landvault_app — no UPDATE, no DELETE, matching 0002's precedent for
audit_log; (2) a BEFORE UPDATE OR DELETE trigger on both tables that
unconditionally raises, regardless of which role executes the statement —
this is the layer that binds even the schema-owning migration role, which
necessarily bypasses (1) since it IS how this migration creates these
tables at all.

No backfill of any kind (ADR-023 "Migration and backfill strategy") —
history begins at this migration's epoch. Parcels that already exist
receive zero history rows retroactively; their first row is written
honestly at their next mutation, describing that assertion, not a
reconstruction of the past.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

APP_ROLE = "landvault_app"

# Both tables share this exact shape (docs/adr/ADR-023 "Schema") —
# asserted_holder_ref and asserted_status are both nullable and present on
# both tables; each table populates exactly one and leaves the other NULL,
# rather than two differently-shaped tables with no shared column at all.
#
# A FACTORY, not a shared tuple: a live rehearsal against Postgres caught
# that a Column/ForeignKey instance can only ever belong to one Table —
# reusing the same tuple of Column objects across two create_table() calls
# silently dropped every ForeignKey on the second table (parcel_id,
# recorded_by, tenant_id all missing, confirmed via \d against a live
# database). Each call to this function returns brand-new Column objects.
def _history_columns() -> tuple[sa.Column, ...]:
    return (
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column(
            "parcel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("parcels.id"),
            nullable=False,
        ),
        sa.Column("asserted_holder_ref", sa.String(), nullable=True),
        sa.Column("asserted_status", sa.String(), nullable=True),
        sa.Column("basis", sa.String(), nullable=False),
        sa.Column(
            "recorded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("identity_users.id"),
            nullable=False,
        ),
        sa.Column(
            "recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("audit_ref", sa.String(), nullable=True),
    )


_TABLES = ("parcel_ownership_history", "parcel_status_history")


def _create_history_table(name: str) -> None:
    op.create_table(name, *_history_columns())
    # supersedes_id: self-referencing FK, added after CREATE TABLE since the
    # table must exist before it can reference itself.
    op.add_column(
        name,
        sa.Column(
            "supersedes_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{name}.id"),
            nullable=True,
        ),
    )
    op.create_index(f"ix_{name}_tenant", name, ["tenant_id"])
    op.create_index(f"ix_{name}_parcel", name, ["parcel_id"])
    op.create_index(f"ix_{name}_supersedes", name, ["supersedes_id"])

    op.execute(f"ALTER TABLE {name} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {name} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY {name}_tenant_isolation ON {name}
        USING (
            tenant_id = current_setting('app.tenant_id', true)
            OR current_setting('app.is_super_admin', true) = 'true'
        )
        """
    )
    # SELECT, INSERT only — no UPDATE, no DELETE, ever, to landvault_app.
    op.execute(f"GRANT SELECT, INSERT ON {name} TO {APP_ROLE}")


def upgrade() -> None:
    for table_name in _TABLES:
        _create_history_table(table_name)

    # One shared trigger function; two distinctly-named triggers (matching
    # ADR-023's own naming: parcel_ownership_history_append_only,
    # parcel_status_history_append_only). Fires for ANY role, including the
    # schema-owning migration role — a privilege GRANT alone cannot say
    # that, since the owning role bypasses privilege checks entirely.
    op.execute(
        """
        CREATE FUNCTION registry_history_reject_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION '% is append-only; use supersedes_id, never UPDATE/DELETE',
                TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table_name in _TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table_name}_append_only
            BEFORE UPDATE OR DELETE ON {table_name}
            FOR EACH ROW EXECUTE FUNCTION registry_history_reject_mutation()
            """
        )


def downgrade() -> None:
    for table_name in _TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS {table_name}_append_only ON {table_name}")
    op.execute("DROP FUNCTION IF EXISTS registry_history_reject_mutation()")
    for table_name in _TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table_name}_tenant_isolation ON {table_name}")
        op.drop_index(f"ix_{table_name}_supersedes", table_name=table_name)
        op.drop_index(f"ix_{table_name}_parcel", table_name=table_name)
        op.drop_index(f"ix_{table_name}_tenant", table_name=table_name)
        op.drop_table(table_name)
