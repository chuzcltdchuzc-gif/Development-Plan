"""Identity Admin Service — role assignment with a real hierarchy check.

Fixes the confirmed Emergent defect (docs/adr/ADR-004): `assign_role` had no
check preventing a principal from granting a role ranked higher than their
own, nor from elevating themselves. Both are hard-denied here, before the
aggregate is ever touched.
"""
from __future__ import annotations

from fastapi import HTTPException, status

from app.contexts.identity.domain.value_objects import ALL_ROLES, highest_rank
from app.contexts.identity.ports import UserRepository
from app.kernel.audit import audit
from app.kernel.context import ExecutionContext


class AdminService:
    def __init__(self, *, users: UserRepository) -> None:
        self.users = users

    async def assign_role(self, *, ctx: ExecutionContext, target_user_id: str, role: str) -> dict:
        if role not in ALL_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"unknown role: {role}"
            )

        if target_user_id == ctx.principal_id:
            await audit(
                "identity.role.assign_denied",
                resource_type="user",
                resource_id=target_user_id,
                decision="DENY",
                payload={"reason": "cannot_change_own_role", "role": role},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="cannot change your own role"
            )

        assigner_rank = highest_rank(ctx.roles)
        target_rank = highest_rank([role])
        if target_rank > assigner_rank:
            await audit(
                "identity.role.assign_denied",
                resource_type="user",
                resource_id=target_user_id,
                decision="DENY",
                payload={"reason": "role_exceeds_assigner_rank", "role": role},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="cannot grant a role higher than your own",
            )

        user = await self.users.get(target_user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

        prev_roles = list(user.roles)
        prev_version = user.version
        user.assign_role(role)
        user = await self.users.update(user, expected_version=prev_version)
        await audit(
            "identity.role.assigned",
            resource_type="user",
            resource_id=user.user_id,
            decision="PERMIT",
            payload={
                "previous_roles": prev_roles,
                "new_role": role,
                "assigned_by": ctx.principal_id,
            },
        )
        return user.public_view()
