"""Ports the Identity application layer depends on. Concrete adapters
(Postgres repositories, Keycloak identity provider) implement these; tests
use in-memory fakes. Neither the domain nor the application layer imports an
adapter directly (docs/adr/ADR-002).
"""
from __future__ import annotations

from typing import Protocol

from app.contexts.identity.domain.delegation import Delegation
from app.contexts.identity.domain.invitation import Invitation
from app.contexts.identity.domain.session import Session
from app.contexts.identity.domain.tenant import Tenant
from app.contexts.identity.domain.user import User


class OptimisticLockError(Exception):
    """Raised when an update targets a stale aggregate version."""


class UserRepository(Protocol):
    async def add(self, user: User) -> User: ...
    async def get(self, user_id: str) -> User | None: ...
    async def get_by_email(self, email: str) -> User | None: ...
    async def get_by_keycloak_subject(self, subject: str) -> User | None: ...
    async def update(self, user: User, *, expected_version: int) -> User: ...


class SessionRepository(Protocol):
    async def add(self, session: Session) -> Session: ...
    async def get_by_refresh_hash(self, refresh_hash: str) -> Session | None: ...
    async def update(self, session: Session) -> Session: ...
    async def revoke_all_active_for_user(self, user_id: str, reason: str) -> None: ...


class InvitationRepository(Protocol):
    async def add(self, invitation: Invitation) -> Invitation: ...
    async def get(self, invitation_id: str) -> Invitation | None: ...
    async def get_by_token_hash(self, token_hash: str) -> Invitation | None: ...
    async def get_pending_by_email(self, tenant_id: str, email: str) -> Invitation | None: ...
    async def list_for_tenant(self, tenant_id: str) -> list[Invitation]: ...
    async def update(self, invitation: Invitation) -> Invitation: ...


class TenantRepository(Protocol):
    async def add(self, tenant: Tenant) -> Tenant: ...
    async def get(self, tenant_id: str) -> Tenant | None: ...
    async def list_all(self) -> list[Tenant]: ...
    async def update(self, tenant: Tenant) -> Tenant: ...


class DelegationRepository(Protocol):
    async def add(self, delegation: Delegation) -> Delegation: ...
    async def get(self, delegation_id: str) -> Delegation | None: ...
    async def list_for_tenant(self, tenant_id: str) -> list[Delegation]: ...
    async def list_active_for_delegate(
        self, tenant_id: str, delegate_user_id: str
    ) -> list[Delegation]: ...
    async def update(self, delegation: Delegation) -> Delegation: ...


class IdentityProviderError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class IdentityProviderTokens:
    """The IdP's response to an authenticate/refresh call. `idp_refresh_token`
    is stored server-side only (Session.idp_refresh_token) and is used to
    mint fresh access tokens later — it is never sent to the client. The
    client-facing refresh token is our own opaque one (app.kernel.security.
    tokens), rotated independently of the IdP's."""

    def __init__(
        self, *, subject: str, email: str, access_token: str, expires_in: int,
        idp_refresh_token: str,
    ) -> None:
        self.subject = subject
        self.email = email
        self.access_token = access_token
        self.expires_in = expires_in
        self.idp_refresh_token = idp_refresh_token


class IdentityProvider(Protocol):
    """Authenticates credentials against the external IdP and provisions
    IdP-side accounts. Access tokens are always the IdP's own JWTs — this
    side never issues one (docs/adr/ADR-004)."""

    async def create_user(self, *, email: str, password: str, full_name: str) -> str:
        """Create the credential record in the IdP. Returns the IdP subject id."""
        ...

    async def authenticate(self, *, email: str, password: str) -> IdentityProviderTokens:
        """Verify credentials via the IdP's Direct Access Grant. Raises
        IdentityProviderError on failure."""
        ...

    async def refresh_access_token(self, *, idp_refresh_token: str) -> IdentityProviderTokens:
        """Exchange the IdP's own (server-side-only) refresh token for a
        fresh access token. Raises IdentityProviderError if the IdP rejects it."""
        ...
