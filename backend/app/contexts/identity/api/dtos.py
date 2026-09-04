"""Identity API request/response shapes.

`RegisterRequest` deliberately has no `role` field — self-registration can
never assign a role (docs/adr/ADR-004 point 4); the service always defaults
to the platform's lowest-privilege role.
"""
from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, WithJsonSchema


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
    # OpenAPI `type: number`, not `integer` — see the identical comment on
    # spatial/api/dtos.py's `GeometryResponse.srid` (same orval/zod-v3
    # generator-compatibility workaround; wire value is still a plain int).
    expires_in: Annotated[int, WithJsonSchema({"type": "number", "title": "Expires In"})]
    user: dict


class UserContextResponse(BaseModel):
    """Mirrors `auth_router.me`'s existing dict literal field-for-field."""

    user_id: str
    email: str | None = None
    country: str | None = None
    tenant_id: str | None = None
    organization_id: str | None = None
    roles: list[str]


class RoleAssignmentResponse(BaseModel):
    """Mirrors `User.public_view()` — the same shape `UserView` above
    already models for the Supabase-invitation path, reused here for
    `assign_role`'s identical response."""

    model_config = ConfigDict(extra="allow")

    user_id: str
    email: str
    full_name: str
    country: str
    tenant_id: str
    roles: list[str]
    account_status: str


class InvitationCreatedResponse(BaseModel):
    """Mirrors `AdminService.create_invitation`'s response dict. `token` is
    the plaintext invitation token, returned exactly once, here only —
    never again (see AdminService's own comment)."""

    invitation_id: str
    email: str
    role: str
    expires_at: str
    token: str


class InvitationSummaryResponse(BaseModel):
    """Mirrors `_invitation_summary` — used by list/revoke, never the
    plaintext token."""

    invitation_id: str
    email: str
    role: str
    status: str
    expires_at: str
    created_at: str


class TenantSummaryResponse(BaseModel):
    """Mirrors `_tenant_summary`."""

    tenant_id: str
    name: str
    status: str
    owner_user_id: str | None = None
    suspension_reason: str | None = None
    created_at: str
    updated_at: str


class DelegationSummaryResponse(BaseModel):
    """Mirrors `_delegation_summary` called without `effective=` — the
    shape `create_delegation`/`revoke_delegation`/`extend_delegation`
    actually return."""

    delegation_id: str
    tenant_id: str
    delegator_user_id: str
    delegate_user_id: str
    delegated_roles: list[str]
    scope: str
    status: str
    expires_at: str | None = None
    created_at: str
    updated_at: str
    revoked_at: str | None = None
    revoked_by: str | None = None


class DelegationSummaryEffectiveResponse(DelegationSummaryResponse):
    """Mirrors `_delegation_summary` called *with* `effective=` — the
    shape `list_delegations`/`get_delegation` actually return, distinct
    from the plain summary above (Section 6's "genuinely heterogeneous
    per-route" case: these two extra fields are only ever computed, and
    only ever present, on the read paths)."""

    effective: bool
    ineffective_reason: str | None = None
