"""In-memory fakes for the Identity ports — implement the exact same
protocols as the real Postgres/Keycloak adapters (app.contexts.identity.
adapters), so application-service tests exercise real business logic
without a live database or IdP.
"""
from __future__ import annotations

import secrets
import uuid
from copy import deepcopy

from app.contexts.identity.domain.invitation import Invitation
from app.contexts.identity.domain.session import Session
from app.contexts.identity.domain.tenant import Tenant
from app.contexts.identity.domain.user import User
from app.contexts.identity.ports import (
    IdentityProviderError,
    IdentityProviderTokens,
    OptimisticLockError,
)
from tests.fakes.jwks import FakeKeycloak


class InMemoryUserRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, User] = {}

    async def add(self, user: User) -> User:
        self._by_id[user.user_id] = deepcopy(user)
        return deepcopy(user)

    async def get(self, user_id: str) -> User | None:
        user = self._by_id.get(user_id)
        return deepcopy(user) if user else None

    async def get_by_email(self, email: str) -> User | None:
        for user in self._by_id.values():
            if user.email == email.strip().lower():
                return deepcopy(user)
        return None

    async def get_by_keycloak_subject(self, subject: str) -> User | None:
        for user in self._by_id.values():
            if user.keycloak_subject == subject:
                return deepcopy(user)
        return None

    async def update(self, user: User, *, expected_version: int) -> User:
        current = self._by_id.get(user.user_id)
        if current is None or current.version != expected_version:
            raise OptimisticLockError(f"stale version for user {user.user_id}")
        user.version = expected_version + 1
        self._by_id[user.user_id] = deepcopy(user)
        return deepcopy(user)


class InMemorySessionRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, Session] = {}

    async def add(self, session: Session) -> Session:
        self._by_id[session.session_id] = deepcopy(session)
        return deepcopy(session)

    async def get_by_refresh_hash(self, refresh_hash: str) -> Session | None:
        for session in self._by_id.values():
            if session.refresh_token_hash == refresh_hash:
                return deepcopy(session)
        return None

    async def update(self, session: Session) -> Session:
        self._by_id[session.session_id] = deepcopy(session)
        return deepcopy(session)

    async def revoke_all_active_for_user(self, user_id: str, reason: str) -> None:
        for session in self._by_id.values():
            if session.user_id == user_id and session.status == "ACTIVE":
                session.revoke(reason)


class InMemoryInvitationRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, Invitation] = {}

    async def add(self, invitation: Invitation) -> Invitation:
        self._by_id[invitation.invitation_id] = deepcopy(invitation)
        return deepcopy(invitation)

    async def get(self, invitation_id: str) -> Invitation | None:
        invitation = self._by_id.get(invitation_id)
        return deepcopy(invitation) if invitation else None

    async def list_for_tenant(self, tenant_id: str) -> list[Invitation]:
        return sorted(
            (deepcopy(inv) for inv in self._by_id.values() if inv.tenant_id == tenant_id),
            key=lambda inv: inv.created_at,
            reverse=True,
        )

    async def get_by_token_hash(self, token_hash: str) -> Invitation | None:
        for invitation in self._by_id.values():
            if invitation.token_hash == token_hash:
                return deepcopy(invitation)
        return None

    async def get_pending_by_email(self, tenant_id: str, email: str) -> Invitation | None:
        for invitation in self._by_id.values():
            if (
                invitation.tenant_id == tenant_id
                and invitation.invited_email == email.strip().lower()
                and invitation.status == "PENDING"
            ):
                return deepcopy(invitation)
        return None

    async def update(self, invitation: Invitation) -> Invitation:
        self._by_id[invitation.invitation_id] = deepcopy(invitation)
        return deepcopy(invitation)


class InMemoryTenantRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, Tenant] = {}

    async def add(self, tenant: Tenant) -> Tenant:
        self._by_id[tenant.tenant_id] = deepcopy(tenant)
        return deepcopy(tenant)

    async def get(self, tenant_id: str) -> Tenant | None:
        tenant = self._by_id.get(tenant_id)
        return deepcopy(tenant) if tenant else None

    async def list_all(self) -> list[Tenant]:
        return sorted(
            (deepcopy(t) for t in self._by_id.values()), key=lambda t: t.created_at, reverse=True
        )

    async def update(self, tenant: Tenant) -> Tenant:
        self._by_id[tenant.tenant_id] = deepcopy(tenant)
        return deepcopy(tenant)


class FakeIdentityProvider:
    """Stands in for Keycloak's Direct Access Grant + admin user-create API.
    Issues real RS256 tokens via the given FakeKeycloak so the same
    JwtVerifier the PEP uses can verify them — this lets acceptance tests
    exercise the full register -> login -> protected-route -> refresh ->
    logout path for real."""

    def __init__(self, keycloak: FakeKeycloak) -> None:
        self._keycloak = keycloak
        self._credentials: dict[str, tuple[str, str]] = {}  # email -> (subject, password)
        self._idp_refresh_tokens: dict[str, str] = {}  # idp_refresh_token -> subject

    async def create_user(self, *, email: str, password: str, full_name: str) -> str:
        normalized = email.strip().lower()
        if normalized in self._credentials:
            raise IdentityProviderError("identity.email_taken", "Email already registered")
        subject = "kc_" + uuid.uuid4().hex
        self._credentials[normalized] = (subject, password)
        return subject

    def _issue_tokens_for(self, subject: str, email: str) -> IdentityProviderTokens:
        access_token = self._keycloak.issue(subject=subject, roles=[], email=email)
        idp_refresh_token = secrets.token_urlsafe(24)
        self._idp_refresh_tokens[idp_refresh_token] = subject
        return IdentityProviderTokens(
            subject=subject, email=email, access_token=access_token,
            expires_in=300, idp_refresh_token=idp_refresh_token,
        )

    async def authenticate(self, *, email: str, password: str) -> IdentityProviderTokens:
        normalized = email.strip().lower()
        record = self._credentials.get(normalized)
        if not record or record[1] != password:
            raise IdentityProviderError("auth.invalid_credentials", "Invalid email or password")
        subject, _ = record
        return self._issue_tokens_for(subject, normalized)

    async def refresh_access_token(self, *, idp_refresh_token: str) -> IdentityProviderTokens:
        subject = self._idp_refresh_tokens.pop(idp_refresh_token, None)
        if not subject:
            raise IdentityProviderError("auth.invalid_idp_refresh", "Unknown IdP refresh token")
        email = next(
            (e for e, (s, _) in self._credentials.items() if s == subject), "unknown@example.test"
        )
        return self._issue_tokens_for(subject, email)
