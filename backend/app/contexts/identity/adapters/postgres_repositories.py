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

from app.contexts.identity.adapters.orm import (
    DelegationRecord,
    InvitationRecord,
    SessionRecord,
    TenantRecord,
    UserRecord,
)
from app.contexts.identity.domain.delegation import Delegation
from app.contexts.identity.domain.invitation import Invitation
from app.contexts.identity.domain.session import Session
from app.contexts.identity.domain.tenant import Tenant
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


def _invitation_from_record(record: InvitationRecord) -> Invitation:
    return Invitation(
        invitation_id=str(record.id),
        tenant_id=record.tenant_id,
        invited_email=record.invited_email,
        role=record.role,
        invited_by=str(record.invited_by),
        token_hash=record.token_hash,
        expires_at=record.expires_at.isoformat(),
        status=record.status,
        created_at=record.created_at.isoformat(),
        accepted_at=record.accepted_at.isoformat() if record.accepted_at else None,
        revoked_at=record.revoked_at.isoformat() if record.revoked_at else None,
    )


class PostgresInvitationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, invitation: Invitation) -> Invitation:
        record = InvitationRecord(
            id=uuid.UUID(invitation.invitation_id)
            if _looks_like_uuid(invitation.invitation_id)
            else uuid.uuid4(),
            tenant_id=invitation.tenant_id,
            invited_email=invitation.invited_email,
            role=invitation.role,
            invited_by=uuid.UUID(invitation.invited_by),
            token_hash=invitation.token_hash,
            status=invitation.status,
            expires_at=datetime.fromisoformat(invitation.expires_at),
        )
        self._session.add(record)
        await self._session.flush()
        return _invitation_from_record(record)

    async def get(self, invitation_id: str) -> Invitation | None:
        if not _looks_like_uuid(invitation_id):
            return None
        record = await self._session.get(InvitationRecord, uuid.UUID(invitation_id))
        return _invitation_from_record(record) if record else None

    async def get_by_token_hash(self, token_hash: str) -> Invitation | None:
        result = await self._session.execute(
            select(InvitationRecord).where(InvitationRecord.token_hash == token_hash)
        )
        record = result.scalar_one_or_none()
        return _invitation_from_record(record) if record else None

    async def list_for_tenant(self, tenant_id: str) -> list[Invitation]:
        result = await self._session.execute(
            select(InvitationRecord)
            .where(InvitationRecord.tenant_id == tenant_id)
            .order_by(InvitationRecord.created_at.desc())
        )
        return [_invitation_from_record(record) for record in result.scalars()]

    async def get_pending_by_email(self, tenant_id: str, email: str) -> Invitation | None:
        result = await self._session.execute(
            select(InvitationRecord).where(
                InvitationRecord.tenant_id == tenant_id,
                InvitationRecord.invited_email == email.strip().lower(),
                InvitationRecord.status == "PENDING",
            )
        )
        record = result.scalar_one_or_none()
        return _invitation_from_record(record) if record else None

    async def update(self, invitation: Invitation) -> Invitation:
        record = await self._session.get(InvitationRecord, uuid.UUID(invitation.invitation_id))
        if record is None:
            raise ValueError(f"invitation {invitation.invitation_id} not found")
        record.status = invitation.status
        record.accepted_at = (
            datetime.fromisoformat(invitation.accepted_at) if invitation.accepted_at else None
        )
        record.revoked_at = (
            datetime.fromisoformat(invitation.revoked_at) if invitation.revoked_at else None
        )
        await self._session.flush()
        return _invitation_from_record(record)


def _tenant_from_record(record: TenantRecord) -> Tenant:
    return Tenant(
        tenant_id=record.id,
        name=record.name,
        owner_user_id=str(record.owner_user_id) if record.owner_user_id else None,
        status=record.status,
        created_at=record.created_at.isoformat(),
        updated_at=record.updated_at.isoformat(),
        suspended_at=record.suspended_at.isoformat() if record.suspended_at else None,
        suspension_reason=record.suspension_reason,
        archived_at=record.archived_at.isoformat() if record.archived_at else None,
    )


class PostgresTenantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, tenant: Tenant) -> Tenant:
        record = TenantRecord(
            id=tenant.tenant_id,
            name=tenant.name,
            status=tenant.status,
            owner_user_id=uuid.UUID(tenant.owner_user_id) if tenant.owner_user_id else None,
        )
        self._session.add(record)
        await self._session.flush()
        return _tenant_from_record(record)

    async def get(self, tenant_id: str) -> Tenant | None:
        record = await self._session.get(TenantRecord, tenant_id)
        return _tenant_from_record(record) if record else None

    async def list_all(self) -> list[Tenant]:
        result = await self._session.execute(
            select(TenantRecord).order_by(TenantRecord.created_at.desc())
        )
        return [_tenant_from_record(record) for record in result.scalars()]

    async def update(self, tenant: Tenant) -> Tenant:
        record = await self._session.get(TenantRecord, tenant.tenant_id)
        if record is None:
            raise ValueError(f"tenant {tenant.tenant_id} not found")
        record.name = tenant.name
        record.status = tenant.status
        record.owner_user_id = uuid.UUID(tenant.owner_user_id) if tenant.owner_user_id else None
        record.suspension_reason = tenant.suspension_reason
        record.suspended_at = (
            datetime.fromisoformat(tenant.suspended_at) if tenant.suspended_at else None
        )
        record.archived_at = (
            datetime.fromisoformat(tenant.archived_at) if tenant.archived_at else None
        )
        record.updated_at = datetime.fromisoformat(tenant.updated_at)
        await self._session.flush()
        return _tenant_from_record(record)


def _delegation_from_record(record: DelegationRecord) -> Delegation:
    return Delegation(
        delegation_id=str(record.id),
        tenant_id=record.tenant_id,
        delegator_user_id=str(record.delegator_user_id),
        delegate_user_id=str(record.delegate_user_id),
        delegated_roles=list(record.delegated_roles),
        scope=record.scope,
        status=record.status,
        created_at=record.created_at.isoformat(),
        updated_at=record.updated_at.isoformat(),
        expires_at=record.expires_at.isoformat() if record.expires_at else None,
        revoked_at=record.revoked_at.isoformat() if record.revoked_at else None,
        revoked_by=str(record.revoked_by) if record.revoked_by else None,
    )


class PostgresDelegationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, delegation: Delegation) -> Delegation:
        record = DelegationRecord(
            id=uuid.UUID(delegation.delegation_id)
            if _looks_like_uuid(delegation.delegation_id)
            else uuid.uuid4(),
            tenant_id=delegation.tenant_id,
            delegator_user_id=uuid.UUID(delegation.delegator_user_id),
            delegate_user_id=uuid.UUID(delegation.delegate_user_id),
            delegated_roles=list(delegation.delegated_roles),
            scope=delegation.scope,
            status=delegation.status,
            expires_at=datetime.fromisoformat(delegation.expires_at)
            if delegation.expires_at
            else None,
        )
        self._session.add(record)
        await self._session.flush()
        return _delegation_from_record(record)

    async def get(self, delegation_id: str) -> Delegation | None:
        if not _looks_like_uuid(delegation_id):
            return None
        record = await self._session.get(DelegationRecord, uuid.UUID(delegation_id))
        return _delegation_from_record(record) if record else None

    async def list_for_tenant(self, tenant_id: str) -> list[Delegation]:
        result = await self._session.execute(
            select(DelegationRecord)
            .where(DelegationRecord.tenant_id == tenant_id)
            .order_by(DelegationRecord.created_at.desc())
        )
        return [_delegation_from_record(record) for record in result.scalars()]

    async def list_active_for_delegate(
        self, tenant_id: str, delegate_user_id: str
    ) -> list[Delegation]:
        if not _looks_like_uuid(delegate_user_id):
            return []
        result = await self._session.execute(
            select(DelegationRecord).where(
                DelegationRecord.tenant_id == tenant_id,
                DelegationRecord.delegate_user_id == uuid.UUID(delegate_user_id),
                DelegationRecord.status == "ACTIVE",
            )
        )
        return [_delegation_from_record(record) for record in result.scalars()]

    async def update(self, delegation: Delegation) -> Delegation:
        record = await self._session.get(DelegationRecord, uuid.UUID(delegation.delegation_id))
        if record is None:
            raise ValueError(f"delegation {delegation.delegation_id} not found")
        record.status = delegation.status
        record.expires_at = (
            datetime.fromisoformat(delegation.expires_at) if delegation.expires_at else None
        )
        record.revoked_at = (
            datetime.fromisoformat(delegation.revoked_at) if delegation.revoked_at else None
        )
        record.revoked_by = uuid.UUID(delegation.revoked_by) if delegation.revoked_by else None
        record.updated_at = datetime.fromisoformat(delegation.updated_at)
        await self._session.flush()
        return _delegation_from_record(record)


def _looks_like_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True
