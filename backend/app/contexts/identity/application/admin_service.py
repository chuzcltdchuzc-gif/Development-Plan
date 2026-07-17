"""Identity Admin Service — role assignment with a real hierarchy check,
plus tenant-membership invitations (B2 — docs/REBUILD_PLAN.md's B2 row:
"tenant provisioning").

Fixes the confirmed Emergent defect (docs/adr/ADR-004): `assign_role` had no
check preventing a principal from granting a role ranked higher than their
own, nor from elevating themselves. Both are hard-denied here, before the
aggregate is ever touched. Invitations reuse the identical hierarchy rule:
a governance-role principal may invite a new member into their own tenant
only at a role no higher than their own rank.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status

from app.contexts.identity.domain.invitation import Invitation
from app.contexts.identity.domain.value_objects import ALL_ROLES, Email, highest_rank
from app.contexts.identity.ports import InvitationRepository, UserRepository
from app.kernel.audit import audit
from app.kernel.context import ExecutionContext
from app.kernel.security.tokens import new_opaque_token

INVITATION_TTL_SECONDS = 7 * 24 * 3600  # 7 days


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


class AdminService:
    def __init__(self, *, users: UserRepository, invitations: InvitationRepository) -> None:
        self.users = users
        self.invitations = invitations

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

    # ---- Tenant membership invitations (B2) --------------------------------
    async def create_invitation(self, *, ctx: ExecutionContext, email: str, role: str) -> dict:
        if role not in ALL_ROLES:
            raise _bad_request(f"unknown role: {role}")
        try:
            normalized_email = Email.parse(email).value
        except ValueError as exc:
            raise _bad_request(str(exc)) from exc

        # Identical hierarchy rule to assign_role: never grant a role ranked
        # higher than the inviter's own — reuses highest_rank(), not a
        # second, divergent check.
        inviter_rank = highest_rank(ctx.roles)
        target_rank = highest_rank([role])
        if target_rank > inviter_rank:
            await audit(
                "identity.invitation.denied",
                resource_type="invitation",
                decision="DENY",
                payload={
                    "reason": "role_exceeds_inviter_rank",
                    "role": role,
                    "email": normalized_email,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="cannot invite a role higher than your own",
            )

        if await self.users.get_by_email(normalized_email):
            raise _conflict("Email already registered")
        if not ctx.tenant_id:
            # Anonymous/super_admin callers have no single tenant to invite
            # into — require_role already restricts this endpoint to
            # authenticated governance roles, so this should be unreachable
            # in practice, but fail closed rather than invite into "None".
            raise _bad_request("caller has no tenant to invite into")
        if await self.invitations.get_pending_by_email(ctx.tenant_id, normalized_email):
            raise _conflict("An invitation is already pending for this email")

        plaintext_token, token_hash = new_opaque_token()
        expires_at = (datetime.now(UTC) + timedelta(seconds=INVITATION_TTL_SECONDS)).isoformat()
        invitation = Invitation.new(
            tenant_id=ctx.tenant_id,
            invited_email=normalized_email,
            role=role,
            invited_by=ctx.principal_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        invitation = await self.invitations.add(invitation)
        await audit(
            "identity.invitation.created",
            resource_type="invitation",
            resource_id=invitation.invitation_id,
            decision="PERMIT",
            payload={"email": normalized_email, "role": role},
        )
        return {
            "invitation_id": invitation.invitation_id,
            "email": invitation.invited_email,
            "role": invitation.role,
            "expires_at": invitation.expires_at,
            # Returned once, here — there is no email-delivery integration
            # yet (no Notifications bounded context), so the inviter is
            # responsible for relaying this to the invitee out-of-band.
            "token": plaintext_token,
        }
