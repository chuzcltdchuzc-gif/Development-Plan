"""Identity admin API router — /v1/admin/*.

Every route here requires a governance role via the PEP's `require_role`
dependency — the hierarchy check inside AdminService is defence in depth on
top of that, not a substitute for it. AdminService is built fresh per
request (Depends(get_admin_service)) — see
app.contexts.identity.dependencies for why.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.contexts.identity.api.dtos import (
    AssignRoleRequest,
    CreateDelegationRequest,
    CreateInvitationRequest,
    ExtendDelegationRequest,
    SuspendTenantRequest,
)
from app.contexts.identity.application.admin_service import AdminService
from app.contexts.identity.dependencies import get_admin_service
from app.contexts.identity.domain.value_objects import GOVERNANCE_ROLES
from app.kernel.authorization.pep import require_role
from app.kernel.context import ExecutionContext

router = APIRouter(prefix="/v1/admin", tags=["identity-admin"])


@router.post("/users/{user_id}/roles")
async def assign_role(
    user_id: str,
    body: AssignRoleRequest,
    ctx: ExecutionContext = Depends(require_role(*GOVERNANCE_ROLES)),
    admin_service: AdminService = Depends(get_admin_service),
) -> dict:
    return await admin_service.assign_role(ctx=ctx, target_user_id=user_id, role=body.role)


@router.post("/invitations", status_code=201)
async def create_invitation(
    body: CreateInvitationRequest,
    ctx: ExecutionContext = Depends(require_role(*GOVERNANCE_ROLES)),
    admin_service: AdminService = Depends(get_admin_service),
) -> dict:
    return await admin_service.create_invitation(ctx=ctx, email=body.email, role=body.role)


@router.get("/invitations")
async def list_invitations(
    ctx: ExecutionContext = Depends(require_role(*GOVERNANCE_ROLES)),
    admin_service: AdminService = Depends(get_admin_service),
) -> list[dict]:
    return await admin_service.list_invitations(ctx=ctx)


@router.post("/invitations/{invitation_id}/revoke")
async def revoke_invitation(
    invitation_id: str,
    ctx: ExecutionContext = Depends(require_role(*GOVERNANCE_ROLES)),
    admin_service: AdminService = Depends(get_admin_service),
) -> dict:
    return await admin_service.revoke_invitation(ctx=ctx, invitation_id=invitation_id)


# ---- Tenant lifecycle (B2 slice 3, docs/adr/ADR-010) -----------------------
# super_admin only, deliberately narrower than GOVERNANCE_ROLES above:
# suspending/archiving an entire organization is a platform-operations
# action, not something a tenant's own compliance_officer/surveyor_general
# should be able to do to their own tenant.

@router.get("/tenants")
async def list_tenants(
    _ctx: ExecutionContext = Depends(require_role("super_admin")),
    admin_service: AdminService = Depends(get_admin_service),
) -> list[dict]:
    return await admin_service.list_tenants()


@router.get("/tenants/{tenant_id}")
async def get_tenant(
    tenant_id: str,
    _ctx: ExecutionContext = Depends(require_role("super_admin")),
    admin_service: AdminService = Depends(get_admin_service),
) -> dict:
    return await admin_service.get_tenant(tenant_id=tenant_id)


@router.post("/tenants/{tenant_id}/suspend")
async def suspend_tenant(
    tenant_id: str,
    body: SuspendTenantRequest,
    ctx: ExecutionContext = Depends(require_role("super_admin")),
    admin_service: AdminService = Depends(get_admin_service),
) -> dict:
    return await admin_service.suspend_tenant(ctx=ctx, tenant_id=tenant_id, reason=body.reason)


@router.post("/tenants/{tenant_id}/reactivate")
async def reactivate_tenant(
    tenant_id: str,
    ctx: ExecutionContext = Depends(require_role("super_admin")),
    admin_service: AdminService = Depends(get_admin_service),
) -> dict:
    return await admin_service.reactivate_tenant(ctx=ctx, tenant_id=tenant_id)


@router.post("/tenants/{tenant_id}/archive")
async def archive_tenant(
    tenant_id: str,
    ctx: ExecutionContext = Depends(require_role("super_admin")),
    admin_service: AdminService = Depends(get_admin_service),
) -> dict:
    return await admin_service.archive_tenant(ctx=ctx, tenant_id=tenant_id)


# ---- Delegated administration (B2 slice 4, docs/adr/ADR-011) ---------------
# GOVERNANCE_ROLES-gated, same tier as invitations — delegation is
# tenant-internal governance, unlike the super_admin-only tenant lifecycle
# actions above. Every delegated role is independently ceiling-checked
# against the caller's own current rank inside AdminService.

@router.post("/delegations", status_code=201)
async def create_delegation(
    body: CreateDelegationRequest,
    ctx: ExecutionContext = Depends(require_role(*GOVERNANCE_ROLES)),
    admin_service: AdminService = Depends(get_admin_service),
) -> dict:
    return await admin_service.create_delegation(
        ctx=ctx,
        delegate_user_id=body.delegate_user_id,
        delegated_roles=body.delegated_roles,
        scope=body.scope,
        expires_at=body.expires_at,
    )


@router.get("/delegations")
async def list_delegations(
    ctx: ExecutionContext = Depends(require_role(*GOVERNANCE_ROLES)),
    admin_service: AdminService = Depends(get_admin_service),
) -> list[dict]:
    return await admin_service.list_delegations(ctx=ctx)


@router.get("/delegations/{delegation_id}")
async def get_delegation(
    delegation_id: str,
    ctx: ExecutionContext = Depends(require_role(*GOVERNANCE_ROLES)),
    admin_service: AdminService = Depends(get_admin_service),
) -> dict:
    return await admin_service.get_delegation(ctx=ctx, delegation_id=delegation_id)


@router.post("/delegations/{delegation_id}/revoke")
async def revoke_delegation(
    delegation_id: str,
    ctx: ExecutionContext = Depends(require_role(*GOVERNANCE_ROLES)),
    admin_service: AdminService = Depends(get_admin_service),
) -> dict:
    return await admin_service.revoke_delegation(ctx=ctx, delegation_id=delegation_id)


@router.post("/delegations/{delegation_id}/extend")
async def extend_delegation(
    delegation_id: str,
    body: ExtendDelegationRequest,
    ctx: ExecutionContext = Depends(require_role(*GOVERNANCE_ROLES)),
    admin_service: AdminService = Depends(get_admin_service),
) -> dict:
    return await admin_service.extend_delegation(
        ctx=ctx, delegation_id=delegation_id, new_expires_at=body.expires_at
    )
