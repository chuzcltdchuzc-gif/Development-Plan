"""evidence_records (B5 Slice B5.2, docs/adr/ADR-026-evidence-domain-model.md)

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-02

The EvidenceRecord aggregate's persisted shape. Unlike migration 0011's
parcel_ownership_history/parcel_status_history (append-only, GRANT SELECT,
INSERT only, plus a BEFORE UPDATE OR DELETE trigger), this table is a
mutable aggregate root with a guarded terminal state — the same shape
0007_parcels.py already established for `parcels` (GRANT SELECT, INSERT,
UPDATE, no DELETE; field-level immutability once SEALED is enforced at the
domain/application layers, ADR-026 invariant #4, not by a database trigger,
because ADR-026 does not declare this table append-only the way the history
tables are). No backfill applies — this is a new table with no pre-existing
rows to reconcile.

storage_key is NOT NULL by design (ADR-026 "Transaction boundaries"): a row
is only ever persisted after the corresponding StoragePort write already
succeeded and returned a key, so no row can exist that references storage
that was never written.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

APP_ROLE = "landvault_app"


def upgrade() -> None:
    op.create_table(
        "evidence_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column(
            "parcel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("parcels.id"),
            nullable=False,
        ),
        sa.Column(
            "uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("identity_users.id"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(), nullable=False),
        sa.Column("basis", sa.String(), nullable=False),
        sa.Column("evidence_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="RECEIVED"),
        # Nullable until the HASHED transition; immutable once set
        # (EvidenceRecord.mark_hashed, domain layer).
        sa.Column("sha256", sa.String(), nullable=True),
        # Nullable until the SEALED transition; immutable once set
        # (EvidenceRecord.seal, domain layer).
        sa.Column("worm_grade", sa.String(), nullable=True),
        sa.Column("legal_hold", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("legal_hold_reason", sa.String(), nullable=True),
        sa.Column(
            "legal_hold_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("identity_users.id"),
            nullable=True,
        ),
        sa.Column("audit_ref", sa.String(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_evidence_records_tenant", "evidence_records", ["tenant_id"])
    op.create_index("ix_evidence_records_parcel", "evidence_records", ["parcel_id"])

    op.execute("ALTER TABLE evidence_records ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE evidence_records FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY evidence_records_tenant_isolation ON evidence_records
        USING (
            tenant_id = current_setting('app.tenant_id', true)
            OR current_setting('app.is_super_admin', true) = 'true'
        )
        """
    )
    # SELECT, INSERT, UPDATE — matching parcels' own shape (0007), not the
    # append-only history tables' shape (0011). No DELETE, matching every
    # tenant-scoped table in this codebase since migration 0001.
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON evidence_records TO {APP_ROLE}")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS evidence_records_tenant_isolation ON evidence_records")
    op.drop_index("ix_evidence_records_parcel", table_name="evidence_records")
    op.drop_index("ix_evidence_records_tenant", table_name="evidence_records")
    op.drop_table("evidence_records")
