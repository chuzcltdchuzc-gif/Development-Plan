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
from app.contexts.identity.domain.tenant import Tenant
from app.contexts.identity.domain.value_objects import ALL_ROLES, Email, highest_rank
from app.contexts.identity.ports import InvitationRepository, TenantRepository, UserRepository
from app.kernel.audit import audit
from app.kernel.context import ExecutionContext
from app.kernel.security.tokens import new_opaque_token

INVITATION_TTL_SECONDS = 7 * 24 * 3600  # 7 days


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _invitation_summary(invitation: Invitation) -> dict:
    """Shared by list/revoke — never includes the token (only its hash is
    ever persisted; the plaintext is returned once, at creation, in
    create_invitation's own response)."""
    return {
        "invitation_id": invitation.invitation_id,
        "email": invitation.invited_email,
        "role": invitation.role,
        "status": invitation.status,
        "expires_at": invitation.expires_at,
        "created_at": invitation.created_at,
    }


def _tenant_summary(tenant: Tenant) -> dict:
    return {
        "tenant_id": tenant.tenant_id,
        "name": tenant.name,
        "status": tenant.status,
        "owner_user_id": tenant.owner_user_id,
        "suspension_reason": tenant.suspension_reason,
        "created_at": tenant.created_at,
        "updated_at": tenant.updated_at,
    }


class AdminService:
    def __init__(
        self,
        *,
        users: UserRepository,
        invitations: InvitationRepository,
        tenants: TenantRepository,
    ) -> None:
        self.users = users
        self.invitations = invitations
        self.tenants = tenants

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

    async def list_invitations(self, *, ctx: ExecutionContext) -> list[dict]:
        if not ctx.tenant_id:
            return []
        # Explicit tenant filter in the query itself, not just reliance on
        # RLS — the same "two independent layers" pattern as the PDP's
        # tenant-isolation policy alongside Postgres RLS (docs/adr/ADR-009).
        invitations = await self.invitations.list_for_tenant(ctx.tenant_id)
        return [_invitation_summary(inv) for inv in invitations]

    async def revoke_invitation(self, *, ctx: ExecutionContext, invitation_id: str) -> dict:
        invitation = await self.invitations.get(invitation_id)
        # RLS already makes a cross-tenant row invisible at the database
        # layer (identity_invitations_tenant_isolation) — this explicit
        # check is the second, independent layer, not a substitute for it.
        if not invitation or invitation.tenant_id != ctx.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="invitation not found"
            )
        if invitation.status != "PENDING":
            raise _conflict("invitation is not pending")

        # No hierarchy check here, unlike create_invitation: revoking is
        # strictly de-escalating (destroying a not-yet-exercised grant, not
        # issuing a new one), so any governance-role member of the same
        # tenant may cancel any pending invitation in it, not only ones
        # they personally created.
        invitation.revoke()
        invitation = await self.invitations.update(invitation)
        await audit(
            "identity.invitation.revoked",
            resource_type="invitation",
            resource_id=invitation.invitation_id,
            decision="PERMIT",
            payload={"revoked_by": ctx.principal_id},
        )
        return _invitation_summary(invitation)

    # ---- Tenant lifecycle (B2 slice 3, docs/adr/ADR-010) -------------------
    # Suspend/reactivate/archive are gated `require_role("super_admin")`
    # only at the router (app.contexts.identity.api.admin_router) — not the
    # broader GOVERNANCE_ROLES used elsewhere in this file. Suspending an
    # entire organization is a platform-operations action, not tenant-
    # internal governance a compliance_officer/surveyor_general should be
    # able to do to their own tenant.

    async def get_my_tenant(self, *, ctx: ExecutionContext) -> dict:
        if not ctx.tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no tenant")
        tenant = await self.tenants.get(ctx.tenant_id)
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no tenant")
        return _tenant_summary(tenant)

    async def list_tenants(self) -> list[dict]:
        tenants = await self.tenants.list_all()
        return [_tenant_summary(t) for t in tenants]

    async def get_tenant(self, *, tenant_id: str) -> dict:
        tenant = await self.tenants.get(tenant_id)
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant not found")
        return _tenant_summary(tenant)

    async def suspend_tenant(self, *, ctx: ExecutionContext, tenant_id: str, reason: str) -> dict:
        tenant = await self.tenants.get(tenant_id)
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant not found")
        try:
            tenant.suspend(reason=reason)
        except ValueError as exc:
            raise _conflict(str(exc)) from exc
        tenant = await self.tenants.update(tenant)
        await audit(
            "identity.tenant.suspended",
            resource_type="tenant",
            resource_id=tenant.tenant_id,
            decision="PERMIT",
            payload={"reason": reason, "suspended_by": ctx.principal_id},
        )
        return _tenant_summary(tenant)

    async def reactivate_tenant(self, *, ctx: ExecutionContext, tenant_id: str) -> dict:
        tenant = await self.tenants.get(tenant_id)
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant not found")
        try:
            tenant.reactivate()
        except ValueError as exc:
            raise _conflict(str(exc)) from exc
        tenant = await self.tenants.update(tenant)
        await audit(
            "identity.tenant.reactivated",
            resource_type="tenant",
            resource_id=tenant.tenant_id,
            decision="PERMIT",
            payload={"reactivated_by": ctx.principal_id},
        )
        return _tenant_summary(tenant)

    async def archive_tenant(self, *, ctx: ExecutionContext, tenant_id: str) -> dict:
        tenant = await self.tenants.get(tenant_id)
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant not found")
        tenant.archive()
        tenant = await self.tenants.update(tenant)
        await audit(
            "identity.tenant.archived",
            resource_type="tenant",
            resource_id=tenant.tenant_id,
            decision="PERMIT",
            payload={"archived_by": ctx.principal_id},
        )
        return _tenant_summary(tenant)
