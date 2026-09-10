"""evidence_actor_attributions (docs/adr/ADR-028-evidence-actor-and-commissioning-provenance.md)

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-10

The EvidenceActorAttribution value object's persisted shape — one row per
ORIGINATED_BY/REVIEWED_BY/COMMISSIONED_BY attribution claim against an
evidence_records row. Append-only, matching migration 0011's shape
(parcel_ownership_history/parcel_status_history), not migration 0012's
mutable-aggregate shape: GRANT SELECT, INSERT only — no UPDATE, no
DELETE — plus a BEFORE UPDATE OR DELETE trigger that unconditionally
raises, regardless of which role executes the statement. Reuses the exact
trigger FUNCTION migration 0011 already created
(registry_history_reject_mutation) rather than defining a second,
duplicate one — that function is fully generic (it only raises using
TG_TABLE_NAME, no table-specific logic), so this migration attaches a new
TRIGGER to it and must not drop that shared function on downgrade, since
0011's own tables still depend on it.

Two invariants beyond migration 0011's own precedent, per ADR-028's
explicit "Supersession integrity" decision (a governance requirement
ADR-023 itself never needed to state):

  1. CHECK (id <> supersedes_id) — no row may supersede itself.
  2. UNIQUE (supersedes_id) — at most one row may supersede any given
     attribution, so a concurrent double-correction of the same row
     cannot both succeed (Postgres UNIQUE permits unlimited NULLs, so
     ordinary, non-superseding rows are unaffected).

No self-supersession, and no fork, are enforced this way rather than by
an ordinary SQL CHECK alone where the invariant is genuinely cross-row
(ADR-028's own text: acceptance "does not prescribe an ordinary SQL CHECK
constraint for an invariant the database engine cannot enforce that way").
Cycles (A supersedes B supersedes A) are not separately enforced by a
trigger here because they are already structurally impossible given (a)
supersedes_id's FK requires the referenced row to already exist at INSERT
time, and (b) rows are never UPDATEd after insert — so no row can ever be
retargeted to point at a row that did not yet exist when it was written.

No backfill of any kind, mirroring migration 0011's own stated
discipline: existing evidence_records receive zero attribution rows
retroactively. An EvidenceRecord with no attribution rows remains exactly
as valid as one with several (ADR-028); nothing infers uploaded_by as an
ORIGINATED_BY claim.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

APP_ROLE = "landvault_app"
TABLE = "evidence_actor_attributions"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column(
            "evidence_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("evidence_records.id"),
            nullable=False,
        ),
        sa.Column("attribution_role", sa.String(), nullable=False),
        sa.Column("actor_reference_kind", sa.String(), nullable=False),
        sa.Column(
            "actor_principal_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("identity_users.id"), nullable=True,
        ),
        sa.Column("actor_name", sa.String(), nullable=True),
        sa.Column("actor_organization_name", sa.String(), nullable=True),
        sa.Column("actor_type", sa.String(), nullable=False),
        sa.Column("basis", sa.String(), nullable=False),
        sa.Column("review_method", sa.String(), nullable=True),
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
    # supersedes_id: self-referencing FK + UNIQUE, added after CREATE TABLE
    # since the table must exist before it can reference itself (the same
    # sequencing migration 0011 already used for the identical reason).
    op.add_column(
        TABLE,
        sa.Column(
            "supersedes_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{TABLE}.id"),
            nullable=True,
        ),
    )
    op.create_unique_constraint(
        "uq_evidence_actor_attributions_supersedes_once", TABLE, ["supersedes_id"]
    )
    op.create_check_constraint(
        "ck_evidence_actor_attributions_no_self_supersede", TABLE, "id <> supersedes_id"
    )

    op.create_index("ix_evidence_actor_attributions_tenant", TABLE, ["tenant_id"])
    op.create_index("ix_evidence_actor_attributions_evidence", TABLE, ["evidence_id"])

    op.execute(f"ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {TABLE} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY {TABLE}_tenant_isolation ON {TABLE}
        USING (
            tenant_id = current_setting('app.tenant_id', true)
            OR current_setting('app.is_super_admin', true) = 'true'
        )
        """
    )
    # SELECT, INSERT only — no UPDATE, no DELETE, ever, to landvault_app.
    op.execute(f"GRANT SELECT, INSERT ON {TABLE} TO {APP_ROLE}")

    # Reuses migration 0011's trigger FUNCTION (registry_history_reject_
    # mutation) — fully generic, no table-specific logic, so no second
    # CREATE FUNCTION is needed here.
    op.execute(
        f"""
        CREATE TRIGGER {TABLE}_append_only
        BEFORE UPDATE OR DELETE ON {TABLE}
        FOR EACH ROW EXECUTE FUNCTION registry_history_reject_mutation()
        """
    )


def downgrade() -> None:
    # Drops only the trigger this migration created — never the shared
    # registry_history_reject_mutation() function, which migration 0011's
    # own tables still depend on.
    op.execute(f"DROP TRIGGER IF EXISTS {TABLE}_append_only ON {TABLE}")
    op.execute(f"DROP POLICY IF EXISTS {TABLE}_tenant_isolation ON {TABLE}")
    op.drop_index("ix_evidence_actor_attributions_evidence", table_name=TABLE)
    op.drop_index("ix_evidence_actor_attributions_tenant", table_name=TABLE)
    op.drop_table(TABLE)
