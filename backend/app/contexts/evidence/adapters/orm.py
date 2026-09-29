"""SQLAlchemy ORM model for the Evidence context (B5 Slice B5.2, docs/adr/
ADR-026-evidence-domain-model.md).

Ships its RLS policy in the same migration (docs/ENGINEERING_RULES.md #1) —
see migrations/versions/0012_evidence_records.py.

All datetime columns are timezone-aware (TIMESTAMPTZ), matching every other
table in this codebase since migration 0003 — the domain layer works
exclusively in aware UTC datetimes (as ISO strings on the dataclass, per
app.contexts.registry.domain.parcel's own convention).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.kernel.db import Base

TZDateTime = DateTime(timezone=True)


class EvidenceRecordModel(Base):
    """EvidenceRecord aggregate persistence (docs/adr/
    ADR-026-evidence-domain-model.md). Unlike parcel_ownership_history/
    parcel_status_history (docs/adr/ADR-023, append-only), this table IS
    mutated in place — status transitions, sha256/worm_grade population,
    legal-hold toggling — the same "mutable aggregate root with a guarded
    terminal state" shape app.contexts.registry.adapters.orm.ParcelRecord
    already has, not the append-only history shape. Field-level immutability
    once SEALED (ADR-026 invariant #4) is enforced at the domain layer
    (EvidenceRecord._ensure_not_sealed) and the application layer, the same
    two-layer discipline Parcel._ensure_mutable()/ParcelArchivedError
    already uses — no database trigger restricts which columns may change
    post-seal, because ADR-026 does not declare this table append-only the
    way migration 0011's history tables are; it declares a guarded mutable
    aggregate, matching Parcel's own precedent exactly."""

    __tablename__ = "evidence_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    parcel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("parcels.id"), nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("identity_users.id"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    # Opaque, adapter-chosen (StoragePort.put/put_immutable return value) —
    # never parsed or interpreted here (docs/adr/ADR-024 D1's replacement
    # criteria). NOT NULL: per ADR-026 "Transaction boundaries," a row is
    # only ever persisted after its storage write already succeeded, so a
    # row referencing no storage_key can never exist.
    storage_key: Mapped[str] = mapped_column(String, nullable=False)
    basis: Mapped[str] = mapped_column(String, nullable=False)
    evidence_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="RECEIVED")
    # Nullable until the HASHED transition (mark_hashed); immutable once set
    # (EvidenceRecord.mark_hashed raises on a second call).
    sha256: Mapped[str | None] = mapped_column(String, nullable=True)
    # Nullable until the SEALED transition (seal); immutable once set.
    worm_grade: Mapped[str | None] = mapped_column(String, nullable=True)
    legal_hold: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    legal_hold_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    legal_hold_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("identity_users.id"), nullable=True
    )
    audit_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TZDateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_evidence_records_tenant", "tenant_id"),
        Index("ix_evidence_records_parcel", "parcel_id"),
    )


class EvidenceActorAttributionModel(Base):
    """EvidenceActorAttribution value object persistence (docs/adr/
    ADR-028-evidence-actor-and-commissioning-provenance.md). Append-only,
    matching parcel_ownership_history/parcel_status_history's shape
    (ADR-023, migration 0011), not evidence_records' own mutable-aggregate
    shape (migration 0012) — this table is never UPDATEd or DELETEd, only
    superseded by a new row referencing the one it corrects
    (`supersedes_id`), enforced at the database (migrations/versions/
    0014_evidence_actor_attributions.py: GRANT SELECT, INSERT only, plus a
    BEFORE UPDATE OR DELETE trigger), not only by this class never issuing
    an UPDATE/DELETE.

    `supersedes_id` carries a UNIQUE constraint — ADR-028's own "one direct
    successor per superseded attribution" invariant, enforced so a
    concurrent double-correction of the same row cannot both succeed —
    plus a BEFORE INSERT trigger that rejects any lineage a new row's
    supersedes_id ancestry would cycle back into, including a cycle
    assembled entirely inside one multi-row INSERT statement (a UNIQUE
    constraint alone does not catch that case — see migrations/versions/
    0014_evidence_actor_attributions.py's revision note for the direct
    Postgres evidence this was tested against). A second BEFORE INSERT
    trigger enforces ADR-028's same-tenant `actor_principal_id` rule at
    the database layer, not only in EvidenceActorAttributionService."""

    __tablename__ = "evidence_actor_attributions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_records.id"), nullable=False
    )
    attribution_role: Mapped[str] = mapped_column(String, nullable=False)
    actor_reference_kind: Mapped[str] = mapped_column(String, nullable=False)
    # Same-tenant-only by application-service enforcement (ADR-028 "Tenant
    # isolation") — this FK alone does not restrict which tenant's
    # identity_users row is referenced; app.contexts.evidence.application.
    # attribution_service.EvidenceActorAttributionService verifies tenancy
    # via PrincipalTenantPort before ever constructing this row.
    actor_principal_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("identity_users.id"), nullable=True
    )
    # Immutable snapshot (ADR-028 "Immutable snapshot requirement") —
    # never re-derived from a live join to identity_users at read time.
    actor_name: Mapped[str | None] = mapped_column(String, nullable=True)
    actor_organization_name: Mapped[str | None] = mapped_column(String, nullable=True)
    actor_type: Mapped[str] = mapped_column(String, nullable=False)
    basis: Mapped[str] = mapped_column(String, nullable=False)
    review_method: Mapped[str | None] = mapped_column(String, nullable=True)
    recorded_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("identity_users.id"), nullable=False
    )
    recorded_at: Mapped[datetime] = mapped_column(
        TZDateTime, server_default=func.now(), nullable=False
    )
    audit_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evidence_actor_attributions.id"), nullable=True
    )

    __table_args__ = (
        Index("ix_evidence_actor_attributions_tenant", "tenant_id"),
        Index("ix_evidence_actor_attributions_evidence", "evidence_id"),
        UniqueConstraint(
            "supersedes_id", name="uq_evidence_actor_attributions_supersedes_once"
        ),
        CheckConstraint(
            "id <> supersedes_id", name="ck_evidence_actor_attributions_no_self_supersede"
        ),
        CheckConstraint(
            "attribution_role IN ('ORIGINATED_BY', 'REVIEWED_BY', 'COMMISSIONED_BY')",
            name="ck_evidence_actor_attributions_role_bounded",
        ),
        CheckConstraint(
            "actor_reference_kind IN "
            "('INTERNAL_PRINCIPAL', 'EXTERNAL_NAMED', 'HISTORICAL_ASSERTED', 'UNKNOWN')",
            name="ck_evidence_actor_attributions_reference_kind_bounded",
        ),
        CheckConstraint(
            "actor_type IN ('INDIVIDUAL', 'ORGANIZATION', 'UNKNOWN')",
            name="ck_evidence_actor_attributions_actor_type_bounded",
        ),
        CheckConstraint(
            "review_method IS NULL OR attribution_role = 'REVIEWED_BY'",
            name="ck_evidence_actor_attributions_review_method_scoped",
        ),
        # Mirrors migration 0014's ck_evidence_actor_attributions_actor_shape
        # exactly — kept here for documentation parity with the migration,
        # which is the actual source of truth Alembic applies.
        CheckConstraint(
            "(actor_reference_kind = 'INTERNAL_PRINCIPAL' AND actor_principal_id IS NOT NULL "
            "AND actor_name IS NOT NULL) "
            "OR (actor_reference_kind IN ('EXTERNAL_NAMED', 'HISTORICAL_ASSERTED') "
            "AND actor_principal_id IS NULL "
            "AND (actor_name IS NOT NULL OR actor_organization_name IS NOT NULL)) "
            "OR (actor_reference_kind = 'UNKNOWN' AND actor_principal_id IS NULL "
            "AND actor_name IS NULL AND actor_organization_name IS NULL)",
            name="ck_evidence_actor_attributions_actor_shape",
        ),
    )
