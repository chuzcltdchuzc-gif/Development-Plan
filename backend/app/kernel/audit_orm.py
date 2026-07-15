"""SQLAlchemy ORM model for the kernel audit log.

Lives in the kernel, not a bounded context's adapters — audit logging is a
cross-cutting concern every future bounded context uses (app.kernel.audit),
not something Identity owns. Ships its RLS policy in the same migration
(docs/ENGINEERING_RULES.md #1) — see
migrations/versions/0001_identity_and_audit.py (schema/RLS) and
0002 (least-privilege grants), 0003 (timezone-aware timestamps).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.kernel.db import Base

TZDateTime = DateTime(timezone=True)


class AuditLogRecord(Base):
    """Append-only, hash-chained (app.kernel.audit). No ORM update/delete
    path exists anywhere in this codebase; the migration additionally
    revokes UPDATE/DELETE at the database grant level as defence in depth."""

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action: Mapped[str] = mapped_column(String, nullable=False)
    resource_type: Mapped[str] = mapped_column(String, nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String, nullable=True)
    decision: Mapped[str | None] = mapped_column(String, nullable=True)
    principal_id: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        TZDateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_audit_log_created_at", "created_at"),)
