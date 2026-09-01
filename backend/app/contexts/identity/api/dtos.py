"""Identity API request/response shapes.

`RegisterRequest` deliberately has no `role` field — self-registration can
never assign a role (docs/adr/ADR-004 point 4); the service always defaults
to the platform's lowest-privilege role.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str
    full_name: str
    country: str | None = None


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str


class AssignRoleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str


class CreateInvitationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    role: str


class AcceptInvitationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str
    password: str
    full_name: str
    country: str | None = None


class AcceptInvitationSupabaseRequest(BaseModel):
    """Supabase path (IMVP-3A) — deliberately has no password, identity_subject,
    email, tenant, or role field: extra="forbid" means a client attempting to
    supply any of those is rejected outright (422), not silently ignored. The
    identity comes exclusively from the caller's already-verified Supabase
    access token (require_auth); tenant/role come exclusively from the
    invitation itself."""

    model_config = ConfigDict(extra="forbid")

    token: str
    full_name: str
    country: str | None = None


class SuspendTenantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str


class CreateDelegationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delegate_user_id: str
    delegated_roles: list[str]
    scope: str = "tenant_governance"
    expires_at: str | None = None


class ExtendDelegationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expires_at: str | None = None


class UserView(BaseModel):
    model_config = ConfigDict(extra="allow")

    user_id: str
    email: str
    full_name: str
    country: str
    tenant_id: str
    roles: list[str]
    account_status: str


class SupabaseInvitationAcceptedResponse(BaseModel):
    """No access_token/refresh_token here (unlike TokenResponse) — Supabase
    already authenticated the caller and already owns their session; this
    side never issues one for this path."""

    user: UserView


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: dict
