"""SQLAlchemy ORM model for the Registry context (B3 slice 1, docs/adr/ADR-013).

Ships its RLS policy in the same migration (docs/ENGINEERING_RULES.md #1)
— see migrations/versions/0007_parcels.py.

All datetime columns are timezone-aware (TIMESTAMPTZ), matching every
other table in this codebase since migration 0003 — the domain layer
works exclusively in aware UTC datetimes.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.kernel.db import Base

TZDateTime = DateTime(timezone=True)


class ParcelRecord(Base):
    __tablename__ = "parcels"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    origin: Mapped[str] = mapped_column(String, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("identity_users.id"), nullable=False
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("identity_users.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="ACTIVE")
    # Reserved for B3 Slice 2's atomic allocator — never populated here.
    parcel_number: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    state: Mapped[str | None] = mapped_column(String, nullable=True)
    lga: Mapped[str | None] = mapped_column(String, nullable=True)
    ward: Mapped[str | None] = mapped_column(String, nullable=True)
    community: Mapped[str | None] = mapped_column(String, nullable=True)
    property_type: Mapped[str | None] = mapped_column(String, nullable=True)
    size_sqm: Mapped[float | None] = mapped_column(Float, nullable=True)
    ownership_type: Mapped[str | None] = mapped_column(String, nullable=True)
    current_owner_name: Mapped[str | None] = mapped_column(String, nullable=True)
    current_owner_contact: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TZDateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TZDateTime, server_default=func.now(), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)

    __table_args__ = (Index("ix_parcels_tenant", "tenant_id"),)
