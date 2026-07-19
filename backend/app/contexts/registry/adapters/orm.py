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
    # Populated at creation time by the B3 slice 2 atomic allocator
    # (ParcelNumberAllocator, docs/adr/ADR-014) — nullable because parcels
    # created before that allocator existed (none in production, but the
    # column itself predates it, ADR-013) never got one retroactively.
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


class RegistryParcelCounterRecord(Base):
    """Per-country_code atomic allocation counter (B3 slice 2,
    docs/adr/ADR-014 — migrations/versions/0008_registry_parcel_counters.py).
    Scoped by country_code, not tenant_id: `parcel_number` is a
    database-wide unique registry identifier (0007_parcels.py's
    `ix_parcels_number_unique`), so every tenant registering parcels in
    the same country shares one sequence. Never read or written via the
    ORM's normal add()/get() flow — always through the single atomic
    `INSERT ... ON CONFLICT DO UPDATE ... RETURNING` statement in
    app.contexts.registry.adapters.postgres_repositories.
    PostgresParcelNumberAllocator. Declared here purely so Alembic
    autogenerate and the rest of the ORM tooling see this table, matching
    every other table in this codebase."""

    __tablename__ = "registry_parcel_counters"

    country_code: Mapped[str] = mapped_column(String(2), primary_key=True)
    last_allocated: Mapped[int] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TZDateTime, server_default=func.now(), nullable=False
    )
