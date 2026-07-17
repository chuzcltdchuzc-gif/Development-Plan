"""SQLAlchemy ORM models for the Identity context (User, Session). The
audit log lives in app.kernel.audit_orm — it's a cross-cutting kernel
concern, not Identity's.

Every table here ships its Postgres RLS policy in the same migration
(docs/ENGINEERING_RULES.md #1) — see
migrations/versions/0001_identity_and_audit.py (schema/RLS) and 0002/0003
(least-privilege role, timezone-aware timestamps — both fixes to real
defects found by running against a live Postgres, see CLAUDE.md).

All datetime columns are timezone-aware (TIMESTAMPTZ) — the domain layer
works exclusively in aware UTC datetimes (datetime.now(UTC)), and asyncpg
correctly refuses to silently coerce an aware value into a naive column.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.kernel.db import Base

TZDateTime = DateTime(timezone=True)


class UserRecord(Base):
    __tablename__ = "identity_users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    keycloak_subject: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String, nullable=False)
    organization_id: Mapped[str | None] = mapped_column(String, nullable=True)
    roles: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    account_status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    suspension_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        TZDateTime, server_default=func.now(), nullable=False
    )
    # No onupdate=func.now() here deliberately: the User aggregate already
    # manages updated_at itself (assign_role(), activate(), etc. all set
    # it) — a server-side onupdate trigger marks the column "expired" after
    # an UPDATE flush, and accessing it without an explicit async refresh()
    # trips SQLAlchemy's greenlet bridge (confirmed against a live Postgres:
    # `MissingGreenlet: greenlet_spawn has not been called`).
    updated_at: Mapped[datetime] = mapped_column(
        TZDateTime, server_default=func.now(), nullable=False
    )
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)

    __table_args__ = (Index("ix_identity_users_tenant", "tenant_id"),)


class SessionRecord(Base):
    __tablename__ = "identity_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("identity_users.id"), nullable=False)
    refresh_token_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    # Server-side only — see app.contexts.identity.domain.session.Session's
    # docstring on why this should be encrypted at rest in production.
    idp_refresh_token: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="ACTIVE")
    expires_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    rotated_from: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TZDateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_identity_sessions_user", "user_id"),)


class InvitationRecord(Base):
    """Tenant-membership invitation (B2 — migrations/versions/
    0004_identity_invitations.py). `token_hash` only — see
    app.contexts.identity.domain.invitation's docstring on why the
    plaintext token is never persisted."""

    __tablename__ = "identity_invitations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String, nullable=False)
    invited_email: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    invited_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("identity_users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="PENDING")
    expires_at: Mapped[datetime] = mapped_column(TZDateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TZDateTime, server_default=func.now(), nullable=False
    )
    accepted_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(TZDateTime, nullable=True)

    __table_args__ = (Index("ix_identity_invitations_tenant", "tenant_id"),)
