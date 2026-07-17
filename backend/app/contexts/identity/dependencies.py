"""FastAPI dependency providers for the Identity context.

Production route handlers depend on `get_auth_service`/`get_admin_service`,
which build a fresh AuthService/AdminService per request from the request-
scoped Unit-of-Work session (app.kernel.uow.get_db_session) — never a fixed
instance built once at startup, which would either share one AsyncSession
across concurrent requests (wrong) or go stale.

Tests override `get_user_repository`/`get_session_repository`/
`get_identity_provider` via FastAPI's `app.dependency_overrides` with
in-memory fakes (tests/app_factory.py) — get_db_session is then never
invoked in tests at all, since nothing downstream of the override needs it.
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.adapters.postgres_repositories import (
    PostgresInvitationRepository,
    PostgresSessionRepository,
    PostgresTenantRepository,
    PostgresUserRepository,
)
from app.contexts.identity.application.admin_service import AdminService
from app.contexts.identity.application.auth_service import AuthService
from app.contexts.identity.ports import (
    IdentityProvider,
    InvitationRepository,
    SessionRepository,
    TenantRepository,
    UserRepository,
)
from app.kernel.uow import get_db_session

_identity_provider: IdentityProvider | None = None


def configure_identity_provider(provider: IdentityProvider) -> None:
    """The Keycloak adapter is stateless (pure HTTP calls per invocation) —
    safe as a shared singleton across requests, unlike the per-request
    repositories below."""
    global _identity_provider
    _identity_provider = provider


def get_identity_provider() -> IdentityProvider:
    if _identity_provider is None:
        raise RuntimeError(
            "Identity provider not configured — call configure_identity_provider() at startup"
        )
    return _identity_provider


def get_user_repository(session: AsyncSession = Depends(get_db_session)) -> UserRepository:
    return PostgresUserRepository(session)


def get_session_repository(session: AsyncSession = Depends(get_db_session)) -> SessionRepository:
    return PostgresSessionRepository(session)


def get_invitation_repository(
    session: AsyncSession = Depends(get_db_session),
) -> InvitationRepository:
    return PostgresInvitationRepository(session)


def get_tenant_repository(session: AsyncSession = Depends(get_db_session)) -> TenantRepository:
    return PostgresTenantRepository(session)


def get_auth_service(
    users: UserRepository = Depends(get_user_repository),
    sessions: SessionRepository = Depends(get_session_repository),
    identity_provider: IdentityProvider = Depends(get_identity_provider),
    invitations: InvitationRepository = Depends(get_invitation_repository),
    tenants: TenantRepository = Depends(get_tenant_repository),
) -> AuthService:
    return AuthService(
        users=users, sessions=sessions, identity_provider=identity_provider,
        invitations=invitations, tenants=tenants,
    )


def get_admin_service(
    users: UserRepository = Depends(get_user_repository),
    invitations: InvitationRepository = Depends(get_invitation_repository),
    tenants: TenantRepository = Depends(get_tenant_repository),
) -> AdminService:
    return AdminService(users=users, invitations=invitations, tenants=tenants)
