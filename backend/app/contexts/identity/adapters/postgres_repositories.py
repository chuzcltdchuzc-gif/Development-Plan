"""Postgres-backed adapters for the Identity ports (app.contexts.identity.
ports) — implements UserRepository and SessionRepository against the ORM
models in app.contexts.identity.adapters.orm. (The AuditStore adapter lives
in app.kernel.audit_postgres — audit logging is a kernel concern, not
Identity's.)

Verified against a live Postgres (B1 infrastructure validation) — see
CLAUDE.md for the full list of defects that verification found and fixed
here. tests/fakes/identity.py implements the same repository protocols for
the fast, hermetic 11-acceptance-test suite.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.adapters.orm import SessionRecord, UserRecord
from app.contexts.identity.domain.session import Session
from app.contexts.identity.domain.user import User
from app.contexts.identity.ports import OptimisticLockError


def _user_from_record(record: UserRecord) -> User:
    return User(
        user_id=str(record.id),
        keycloak_subject=record.keycloak_subject,
        email=record.email,
        full_name=record.full_name,
        country=record.country,
        tenant_id=record.tenant_id,
        roles=list(record.roles),
        account_status=record.account_status,
        organization_id=record.organization_id,
        created_at=record.created_at.isoformat(),
        updated_at=record.updated_at.isoformat(),
        last_login_at=record.last_login_at.isoformat() if record.last_login_at else None,
        suspension_reason=record.suspension_reason,
        version=record.version,
    )


class PostgresUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> User:
        record = UserRecord(
            id=uuid.UUID(user.user_id) if _looks_like_uuid(user.user_id) else uuid.uuid4(),
            keycloak_subject=user.keycloak_subject,
            email=user.email,
            full_name=user.full_name,
            country=user.country,
            tenant_id=user.tenant_id,
            organization_id=user.organization_id,
            roles=list(user.roles),
            account_status=user.account_status,
            version=user.version,
        )
        self._session.add(record)
        await self._session.flush()
        return _user_from_record(record)

    async def get(self, user_id: str) -> User | None:
        if not _looks_like_uuid(user_id):
            return None
        record = await self._session.get(UserRecord, uuid.UUID(user_id))
        return _user_from_record(record) if record else None

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(UserRecord).where(UserRecord.email == email.strip().lower())
        )
        record = result.scalar_one_or_none()
        return _user_from_record(record) if record else None

    async def get_by_keycloak_subject(self, subject: str) -> User | None:
        result = await self._session.execute(
            select(UserRecord).where(UserRecord.keycloak_subject == subject)
        )
        record = result.scalar_one_or_none()
        return _user_from_record(record) if record else None

    async def update(self, user: User, *, expected_version: int) -> User:
        record = await self._session.get(UserRecord, uuid.UUID(user.user_id))
        if record is None or record.version != expected_version:
            raise OptimisticLockError(f"stale version for user {user.user_id}")
        record.roles = list(user.roles)
        record.account_status = user.account_status
        record.suspension_reason = user.suspension_reason
        record.last_login_at = (
            datetime.fromisoformat(user.last_login_at) if user.last_login_at else None
        )
        record.updated_at = datetime.fromisoformat(user.updated_at)
        record.version = expected_version + 1
        await self._session.flush()
        return _user_from_record(record)


def _session_from_record(record: SessionRecord) -> Session:
    return Session(
        session_id=str(record.id),
        user_id=str(record.user_id),
        refresh_token_hash=record.refresh_token_hash,
        idp_refresh_token=record.idp_refresh_token,
        expires_at=record.expires_at.isoformat(),
        status=record.status,
        created_at=record.created_at.isoformat(),
        rotated_from=str(record.rotated_from) if record.rotated_from else None,
        user_agent=record.user_agent,
        ip_address=record.ip_address,
        revoked_at=record.revoked_at.isoformat() if record.revoked_at else None,
        revoked_reason=record.revoked_reason,
    )


class PostgresSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, session: Session) -> Session:
        record = SessionRecord(
            id=uuid.UUID(session.session_id) if _looks_like_uuid(session.session_id)
            else uuid.uuid4(),
            user_id=uuid.UUID(session.user_id),
            refresh_token_hash=session.refresh_token_hash,
            idp_refresh_token=session.idp_refresh_token,
            status=session.status,
            expires_at=datetime.fromisoformat(session.expires_at),
            rotated_from=uuid.UUID(session.rotated_from) if session.rotated_from else None,
            user_agent=session.user_agent,
            ip_address=session.ip_address,
        )
        self._session.add(record)
        await self._session.flush()
        return _session_from_record(record)

    async def get_by_refresh_hash(self, refresh_hash: str) -> Session | None:
        result = await self._session.execute(
            select(SessionRecord).where(SessionRecord.refresh_token_hash == refresh_hash)
        )
        record = result.scalar_one_or_none()
        return _session_from_record(record) if record else None

    async def update(self, session: Session) -> Session:
        record = await self._session.get(SessionRecord, uuid.UUID(session.session_id))
        if record is None:
            raise ValueError(f"session {session.session_id} not found")
        record.status = session.status
        record.revoked_at = (
            datetime.fromisoformat(session.revoked_at) if session.revoked_at else None
        )
        record.revoked_reason = session.revoked_reason
        await self._session.flush()
        return _session_from_record(record)

    async def revoke_all_active_for_user(self, user_id: str, reason: str) -> None:
        result = await self._session.execute(
            select(SessionRecord).where(
                SessionRecord.user_id == uuid.UUID(user_id), SessionRecord.status == "ACTIVE"
            )
        )
        now = datetime.now(UTC)
        for record in result.scalars():
            record.status = "REVOKED"
            record.revoked_at = now
            record.revoked_reason = reason
        await self._session.flush()


def _looks_like_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True
