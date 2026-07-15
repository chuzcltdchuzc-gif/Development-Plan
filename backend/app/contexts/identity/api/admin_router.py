"""Identity admin API router — /v1/admin/*.

Every route here requires a governance role via the PEP's `require_role`
dependency — the hierarchy check inside AdminService is defence in depth on
top of that, not a substitute for it. AdminService is built fresh per
request (Depends(get_admin_service)) — see
app.contexts.identity.dependencies for why.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.contexts.identity.api.dtos import AssignRoleRequest
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
