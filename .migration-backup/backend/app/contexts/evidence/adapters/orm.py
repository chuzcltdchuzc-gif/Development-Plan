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

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, func
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
