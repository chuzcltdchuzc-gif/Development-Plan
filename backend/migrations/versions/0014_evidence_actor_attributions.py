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

**Revision note (pre-merge remediation, same day):** the first draft of
this migration claimed cycles in the `supersedes_id` chain were "already
structurally impossible" from the FK-must-preexist-plus-append-only
combination alone. That claim was tested directly against real Postgres
and disproved: a single multi-row `INSERT` can set up two (or more) rows
that mutually reference each other as `supersedes_id`, because Postgres
checks a `NOT DEFERRABLE` foreign key at the end of the SQL statement, not
synchronously as each row of a multi-row statement is processed, and the
`UNIQUE (supersedes_id)` constraint does not catch a mutual pair (the two
referenced values differ). This revision adds two genuinely new database
objects to close that gap and the related actor-state gap the same review
found; nothing above this note changes.

**Revision note 2 (pre-merge remediation, same day):** a follow-up
database-boundary review found two further gaps in the *first*
remediation, both now closed below. First, nothing enforced
`evidence_actor_attributions.tenant_id` matching the `tenant_id` of the
`evidence_records` row its `evidence_id` names — proven directly: as the
ordinary `landvault_app` role scoped to tenant A (no RLS bypass), an
`INSERT` claiming `tenant_id = A` but `evidence_id` belonging to tenant B
persisted successfully, including when the row's `actor_principal_id`
was itself a legitimate same-tenant-A reference (the actor-reference
check alone cannot catch a mismatch between the row's own tenant and the
Evidence it claims to describe — they are independent facts). A third
`BEFORE INSERT` trigger, `evidence_actor_attributions_check_evidence_tenant`,
closes this by rejecting any insert whose `tenant_id` does not match the
referenced `evidence_records.tenant_id`. Second, the cycle-rejection
trigger's `depth < 10000` guard silently permitted an insert whenever the
ancestry walk was truncated by that bound before reaching either a
natural chain end or the new row's own id — a fail-*open* ceiling that
would have missed a cycle whose closing reference lay beyond the bound.
The trigger now distinguishes "the walk reached a natural end without
seeing the new row's id" (safe) from
"the walk was still going when the bound was hit" (unproven, and now
rejected rather than assumed safe) — see "Cycle-depth ceiling: fails
closed, not silently" below.

Five invariants beyond migration 0011's own precedent, per ADR-028's
explicit "Supersession integrity", "Actor-state representation", and
"Tenant isolation" decisions (requirements ADR-023 itself never needed to
state):

  1. CHECK (id <> supersedes_id) — no row may supersede itself.
  2. UNIQUE (supersedes_id) — at most one row may supersede any given
     attribution, so a concurrent double-correction of the same row
     cannot both succeed (Postgres UNIQUE permits unlimited NULLs, so
     ordinary, non-superseding rows are unaffected). Verified live under
     genuine concurrent transactions.
  3. A BEFORE INSERT trigger (`evidence_actor_attributions_reject_cycle`)
     that walks the new row's `supersedes_id` ancestry and rejects the
     insert if that ancestry ever reaches the new row's own id — see
     "Why a plain trigger, not a CHECK or a CONSTRAINT TRIGGER" below.
  4. A BEFORE INSERT trigger
     (`evidence_actor_attributions_check_same_tenant`) that rejects an
     insert whose `actor_principal_id` resolves (via a read-only lookup
     against `identity_users`) to a different tenant than the row's own
     `tenant_id` — ADR-028 "Tenant isolation" §2's same-tenant rule,
     previously enforced only in `EvidenceActorAttributionService`
     (application-layer only, bypassable by any direct repository/SQL
     write). This does not alter `identity_users` or the identity/tenant
     architecture in any way — it only adds a read-only query inside a
     trigger owned entirely by this table's own migration, mirroring
     `PostgresPrincipalTenantAdapter`'s own read-only cross-context
     lookup at the database layer instead of the application layer.
  5. A BEFORE INSERT trigger
     (`evidence_actor_attributions_check_evidence_tenant`) that rejects an
     insert whose `tenant_id` does not match the `tenant_id` of the
     `evidence_records` row named by its own `evidence_id` — a durable
     attribution row must never disagree with the Evidence it claims to
     describe about which tenant it belongs to; RLS alone only protects
     rows whose own `tenant_id` is already correct, it does not verify
     that the row's `tenant_id` and `evidence_id` are mutually
     consistent. Proven necessary directly: without this trigger, the
     ordinary application role, scoped to tenant A via RLS exactly as a
     real request would be, could `INSERT` a row claiming `tenant_id = A`
     against tenant B's own `evidence_id`, and it persisted — including
     when the row's `actor_principal_id` was itself a legitimate,
     same-tenant-A reference, since that check has no visibility into
     whether the row's tenant matches its named Evidence at all.

Why a plain `AFTER`/`BEFORE` row trigger, not a `CHECK` or a `CONSTRAINT
TRIGGER`, for cycle detection: a `CHECK` constraint cannot express a
cross-row ancestry walk (it sees only the one row being written).
PostgreSQL's own foreign-key enforcement uses `CONSTRAINT TRIGGER`
semantics specifically so it can be deferred to end-of-transaction when
declared `DEFERRABLE INITIALLY DEFERRED` — that is precisely the
mechanism that let the disproved claim's cycle slip through, because
`NOT DEFERRABLE` FK constraint triggers are still queued and fire at
end-of-*statement*, by which point every row of a multi-row `INSERT` is
already visible to every other row's check, in whichever order they
happen to be queued — not usefully orderable for a "was I already an
ancestor of myself" question. A plain (non-constraint) row-level trigger
instead fires synchronously, per row, in the exact order PostgreSQL
processes a multi-row statement's `VALUES` list, incrementing the command
counter after each row — so each already-processed row of the *same*
statement is genuinely visible to every later row's trigger. For a cycle
of any length created entirely inside one multi-row statement, the
*last*-inserted member of that cycle is always the one whose trigger
fires with every other member of the cycle already present, and it is
that member's own ancestry walk that closes the loop and gets rejected —
proven directly against Postgres for a 2-row single-statement mutual
reference (this migration's own regression coverage, plus
`tests/live/test_evidence_actor_attribution_live.py`), not merely
reasoned about. Cross-statement cycles remain additionally impossible for
the original reason (append-only: no existing row can ever be `UPDATE`d
to retarget its `supersedes_id`), which the append-only trigger continues
to guarantee unconditionally.

**Cycle-depth ceiling: fails closed, not silently.** The recursive walk
is bounded (depth < 10,000, matching the application service's own
`_MAX_LINEAGE_WALK` defensive bound) purely to keep the worst-case cost
of one insert finite even under a pathologically long lineage — not a
business rule, and no valid lineage in this system's design comes
anywhere close to that depth. The first version of this guard let the
walk simply stop at the bound and permit the insert whenever it had
neither found the new row's own id nor reached a natural chain end
(`supersedes_id IS NULL`) by then — a cycle whose closing reference
happened to lie beyond the bound would have been missed and silently
allowed. The trigger now computes both facts from the same walk — whether
the new row's id was found (a real cycle: always rejected, at any depth
up to the bound) and whether the walk was still going, unresolved, when
it hit the bound (an *unproven* lineage: also rejected, deliberately, on
the same principle ADR-028's own "does not prescribe an ordinary SQL
CHECK constraint for an invariant the database engine cannot enforce
that way" already established — a check that cannot prove safety must
not default to assuming it). A lineage that happens to end in exactly
10,000 hops is rejected too, indistinguishably from one that merely looks
that long from where the walk stopped; that is an intentional, safe
trade-off given no real lineage in this design approaches that depth.

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

_ATTRIBUTION_ROLES = ("ORIGINATED_BY", "REVIEWED_BY", "COMMISSIONED_BY")
_ACTOR_REFERENCE_KINDS = ("INTERNAL_PRINCIPAL", "EXTERNAL_NAMED", "HISTORICAL_ASSERTED", "UNKNOWN")
_ACTOR_TYPES = ("INDIVIDUAL", "ORGANIZATION", "UNKNOWN")


def _sql_list(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


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

    # Bounded-value CHECKs — the same "reject an unknown member at the
    # persistence boundary" discipline migration 0012 leaves to the
    # domain layer alone for evidence_type, made explicit here at
    # Governance's instruction because ADR-028 states these three as
    # structural, bounded roles/kinds/types, not free text.
    op.create_check_constraint(
        "ck_evidence_actor_attributions_role_bounded", TABLE,
        f"attribution_role IN ({_sql_list(_ATTRIBUTION_ROLES)})",
    )
    op.create_check_constraint(
        "ck_evidence_actor_attributions_reference_kind_bounded", TABLE,
        f"actor_reference_kind IN ({_sql_list(_ACTOR_REFERENCE_KINDS)})",
    )
    op.create_check_constraint(
        "ck_evidence_actor_attributions_actor_type_bounded", TABLE,
        f"actor_type IN ({_sql_list(_ACTOR_TYPES)})",
    )
    # review_method is meaningful only for REVIEWED_BY (ADR-028).
    op.create_check_constraint(
        "ck_evidence_actor_attributions_review_method_scoped", TABLE,
        "review_method IS NULL OR attribution_role = 'REVIEWED_BY'",
    )
    # Actor-representation shape (ADR-028 "Actor-state representation" +
    # "Immutable snapshot requirement") — the same five red-team cases
    # tested directly against this table before this constraint existed:
    # INTERNAL_PRINCIPAL requires both a principal reference AND its
    # immutable name snapshot; EXTERNAL_NAMED/HISTORICAL_ASSERTED forbid a
    # live principal reference and require at least one snapshot field;
    # UNKNOWN forbids every identity field, so no identity is ever
    # fabricated for an actor that cannot be identified.
    op.create_check_constraint(
        "ck_evidence_actor_attributions_actor_shape", TABLE,
        """
        (
            actor_reference_kind = 'INTERNAL_PRINCIPAL'
            AND actor_principal_id IS NOT NULL
            AND actor_name IS NOT NULL
        )
        OR (
            actor_reference_kind IN ('EXTERNAL_NAMED', 'HISTORICAL_ASSERTED')
            AND actor_principal_id IS NULL
            AND (actor_name IS NOT NULL OR actor_organization_name IS NOT NULL)
        )
        OR (
            actor_reference_kind = 'UNKNOWN'
            AND actor_principal_id IS NULL
            AND actor_name IS NULL
            AND actor_organization_name IS NULL
        )
        """,
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

    # --- Cycle rejection (see module docstring for why BEFORE INSERT, not
    # a CHECK or a CONSTRAINT TRIGGER) ---
    op.execute(
        f"""
        CREATE FUNCTION {TABLE}_reject_cycle() RETURNS trigger AS $$
        DECLARE
            visited_count integer;
            found_self boolean;
        BEGIN
            IF NEW.supersedes_id IS NOT NULL THEN
                -- ancestry.id is a POINTER VALUE being followed backward
                -- (starting at NEW.supersedes_id itself), not necessarily
                -- an id this trigger has looked up as an existing row —
                -- the very value that closes a 2-row cycle (the second
                -- member's own id) is discovered as a VALUE (the first
                -- member's stored supersedes_id) without ever needing to
                -- look up the second member's row, which — for a cycle
                -- assembled inside one multi-row INSERT — usually does
                -- not exist yet at the point this trigger runs. Comparing
                -- against NEW.id must stay a value comparison for this
                -- reason; an earlier draft of this trigger required the
                -- pointer to resolve to an existing row before comparing
                -- it, which silently missed exactly the single-statement
                -- multi-row cycle this trigger exists to catch (caught by
                -- this migration's own regression test before merge).
                WITH RECURSIVE ancestry(id, depth) AS (
                    SELECT NEW.supersedes_id, 1
                    UNION ALL
                    SELECT e.supersedes_id, a.depth + 1
                    FROM {TABLE} e
                    JOIN ancestry a ON e.id = a.id
                    WHERE a.depth < 10000 AND e.supersedes_id IS NOT NULL
                )
                SELECT count(*), bool_or(id = NEW.id) INTO visited_count, found_self
                FROM ancestry;

                IF found_self THEN
                    RAISE EXCEPTION
                        'evidence_actor_attributions: supersedes_id lineage would cycle back to %',
                        NEW.id;
                END IF;
                -- Fails CLOSED, not silently: the recursive term's own
                -- "e.supersedes_id IS NOT NULL" filter means the walk only
                -- ever stops short of the depth bound when it has reached
                -- a genuine, natural chain end. Reaching the bound instead
                -- (visited_count at or past it) means safety was never
                -- proven — reject rather than assume the unseen remainder
                -- is safe. See the module docstring's "Cycle-depth
                -- ceiling" note.
                IF visited_count >= 10000 THEN
                    RAISE EXCEPTION
                        'evidence_actor_attributions: supersedes_id lineage exceeds the depth '
                        'this trigger can verify (%); rejected rather than assumed safe',
                        visited_count;
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER {TABLE}_reject_cycle
        BEFORE INSERT ON {TABLE}
        FOR EACH ROW EXECUTE FUNCTION {TABLE}_reject_cycle()
        """
    )

    # --- Same-tenant live-reference enforcement (ADR-028 "Tenant
    # isolation" §2) — a read-only lookup against identity_users; no
    # change to identity_users or the identity/tenant architecture. ---
    op.execute(
        f"""
        CREATE FUNCTION {TABLE}_check_same_tenant() RETURNS trigger AS $$
        DECLARE
            principal_tenant text;
        BEGIN
            IF NEW.actor_principal_id IS NOT NULL THEN
                SELECT tenant_id INTO principal_tenant
                FROM identity_users WHERE id = NEW.actor_principal_id;
                IF principal_tenant IS NULL OR principal_tenant <> NEW.tenant_id THEN
                    RAISE EXCEPTION
                        'evidence_actor_attributions: actor_principal_id must reference a '
                        'principal in the same tenant (%) as the attribution',
                        NEW.tenant_id;
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER {TABLE}_check_same_tenant
        BEFORE INSERT ON {TABLE}
        FOR EACH ROW EXECUTE FUNCTION {TABLE}_check_same_tenant()
        """
    )

    # --- Evidence/tenant binding enforcement — a durable attribution row
    # must never disagree with the Evidence it names about which tenant
    # it belongs to. RLS alone protects a row's OWN tenant_id from being
    # read by another tenant; it says nothing about whether that
    # tenant_id actually matches the evidence_id the row claims to
    # describe. Unconditional (evidence_id is always NOT NULL), unlike
    # the same-tenant-principal trigger above (actor_principal_id is
    # optional). ---
    op.execute(
        f"""
        CREATE FUNCTION {TABLE}_check_evidence_tenant() RETURNS trigger AS $$
        DECLARE
            evidence_tenant text;
        BEGIN
            SELECT tenant_id INTO evidence_tenant
            FROM evidence_records WHERE id = NEW.evidence_id;
            IF evidence_tenant IS NULL OR evidence_tenant <> NEW.tenant_id THEN
                RAISE EXCEPTION
                    'evidence_actor_attributions: tenant_id (%) must match the referenced '
                    'evidence_records.tenant_id',
                    NEW.tenant_id;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER {TABLE}_check_evidence_tenant
        BEFORE INSERT ON {TABLE}
        FOR EACH ROW EXECUTE FUNCTION {TABLE}_check_evidence_tenant()
        """
    )


def downgrade() -> None:
    # Drops only the triggers/functions this migration created — never the
    # shared registry_history_reject_mutation() function, which migration
    # 0011's own tables still depend on.
    op.execute(f"DROP TRIGGER IF EXISTS {TABLE}_check_evidence_tenant ON {TABLE}")
    op.execute(f"DROP FUNCTION IF EXISTS {TABLE}_check_evidence_tenant()")
    op.execute(f"DROP TRIGGER IF EXISTS {TABLE}_check_same_tenant ON {TABLE}")
    op.execute(f"DROP FUNCTION IF EXISTS {TABLE}_check_same_tenant()")
    op.execute(f"DROP TRIGGER IF EXISTS {TABLE}_reject_cycle ON {TABLE}")
    op.execute(f"DROP FUNCTION IF EXISTS {TABLE}_reject_cycle()")
    op.execute(f"DROP TRIGGER IF EXISTS {TABLE}_append_only ON {TABLE}")
    op.execute(f"DROP POLICY IF EXISTS {TABLE}_tenant_isolation ON {TABLE}")
    op.drop_index("ix_evidence_actor_attributions_evidence", table_name=TABLE)
    op.drop_index("ix_evidence_actor_attributions_tenant", table_name=TABLE)
    op.drop_table(TABLE)
