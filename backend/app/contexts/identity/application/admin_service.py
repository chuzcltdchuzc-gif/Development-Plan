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

from app.contexts.identity.domain.delegation import (
    VALID_SCOPES,
    Delegation,
    delegation_is_effective,
)
from app.contexts.identity.domain.invitation import Invitation
from app.contexts.identity.domain.tenant import Tenant
from app.contexts.identity.domain.value_objects import ALL_ROLES, Email, highest_rank
from app.contexts.identity.ports import (
    DelegationRepository,
    InvitationRepository,
    TenantRepository,
    UserRepository,
)
from app.kernel.audit import audit
from app.kernel.context import ExecutionContext
from app.kernel.security.tokens import new_opaque_token

INVITATION_TTL_SECONDS = 7 * 24 * 3600  # 7 days


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _in_scope(ctx: ExecutionContext, resource_tenant_id: str) -> bool:
    """Mirrors the RLS policy shape every tenant-scoped table uses
    (`tenant_id = current_setting('app.tenant_id') OR is_super_admin`,
    docs/adr/ADR-009 §7) at the application layer. Without the
    super_admin bypass here, a super_admin operating on a resource outside
    their OWN (largely irrelevant) tenant would be incorrectly 404'd by
    this explicit check even though RLS itself already grants them full
    cross-tenant reach — found via B2 slice 4 test coverage and fixed
    consistently everywhere this shape appears, not just in the new code."""
    return resource_tenant_id == ctx.tenant_id or ctx.has_any_role("super_admin")


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


def _delegation_summary(
    delegation: Delegation, *, effective: bool | None = None, ineffective_reason: str | None = None
) -> dict:
    summary: dict[str, object] = {
        "delegation_id": delegation.delegation_id,
        "tenant_id": delegation.tenant_id,
        "delegator_user_id": delegation.delegator_user_id,
        "delegate_user_id": delegation.delegate_user_id,
        "delegated_roles": list(delegation.delegated_roles),
        "scope": delegation.scope,
        "status": delegation.status,
        "expires_at": delegation.expires_at,
        "created_at": delegation.created_at,
        "updated_at": delegation.updated_at,
        "revoked_at": delegation.revoked_at,
        "revoked_by": delegation.revoked_by,
    }
    if effective is not None:
        summary["effective"] = effective
        summary["ineffective_reason"] = ineffective_reason
    return summary


class AdminService:
    def __init__(
        self,
        *,
        users: UserRepository,
        invitations: InvitationRepository,
        tenants: TenantRepository,
        delegations: DelegationRepository,
    ) -> None:
        self.users = users
        self.invitations = invitations
        self.tenants = tenants
        self.delegations = delegations

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
        # _in_scope carries the same super_admin bypass RLS itself grants.
        if not invitation or not _in_scope(ctx, invitation.tenant_id):
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

    # ---- Delegated administration (B2 slice 4, docs/adr/ADR-011) -----------
    # Delegation is derived authority: every check here either reuses
    # highest_rank() verbatim (the exact rule create_invitation/assign_role
    # already use) or app.contexts.identity.domain.delegation.
    # delegation_is_effective (the exact function context_hydration.py uses
    # to resolve delegated roles on every request) — never a second,
    # divergent authorization path.

    async def create_delegation(
        self,
        *,
        ctx: ExecutionContext,
        delegate_user_id: str,
        delegated_roles: list[str],
        scope: str,
        expires_at: str | None,
    ) -> dict:
        if delegate_user_id == ctx.principal_id:
            raise _bad_request("cannot delegate to yourself")
        if not delegated_roles or any(role not in ALL_ROLES for role in delegated_roles):
            raise _bad_request("delegated_roles must be a non-empty list of known roles")
        if scope not in VALID_SCOPES:
            raise _bad_request(f"unknown scope: {scope}")
        if expires_at is not None:
            try:
                expires_dt = datetime.fromisoformat(expires_at)
            except ValueError as exc:
                raise _bad_request("expires_at must be an ISO-8601 datetime") from exc
            if expires_dt <= datetime.now(UTC):
                raise _bad_request("expires_at must be in the future")
        if not ctx.tenant_id:
            # Structurally unreachable — require_role already restricts this
            # endpoint to authenticated governance roles, which hydration
            # only grants with a resolved tenant_id (docs/adr/ADR-010). Fail
            # closed anyway rather than delegate into "None".
            raise _bad_request("caller has no tenant to delegate within")

        delegator_rank = highest_rank(ctx.roles)
        target_rank = highest_rank(delegated_roles)
        if target_rank > delegator_rank:
            await audit(
                "identity.delegation.denied",
                resource_type="delegation",
                decision="DENY",
                payload={
                    "reason": "role_exceeds_delegator_rank",
                    "delegated_roles": delegated_roles,
                    "delegate_user_id": delegate_user_id,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="cannot delegate a role higher than your own",
            )

        delegate = await self.users.get(delegate_user_id)
        # Same "RLS-adjacent explicit check, 404 not 403" pattern as
        # revoke_invitation/get_tenant: a cross-tenant target is invisible,
        # not merely forbidden — no oracle for cross-tenant user existence.
        if not delegate or delegate.tenant_id != ctx.tenant_id:
            await audit(
                "identity.delegation.denied",
                resource_type="delegation",
                decision="DENY",
                payload={
                    "reason": "delegate_not_found_in_tenant",
                    "delegate_user_id": delegate_user_id,
                },
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
        if not delegate.can_authenticate():
            raise _bad_request("delegate account is not active")

        delegation = Delegation.new(
            tenant_id=ctx.tenant_id,
            delegator_user_id=ctx.principal_id,
            delegate_user_id=delegate_user_id,
            delegated_roles=delegated_roles,
            scope=scope,
            expires_at=expires_at,
        )
        delegation = await self.delegations.add(delegation)
        await audit(
            "identity.delegation.created",
            resource_type="delegation",
            resource_id=delegation.delegation_id,
            decision="PERMIT",
            payload={
                "delegate_user_id": delegate_user_id,
                "delegated_roles": delegated_roles,
                "scope": scope,
                "expires_at": expires_at,
            },
        )
        return _delegation_summary(delegation)

    async def list_delegations(self, *, ctx: ExecutionContext) -> list[dict]:
        if not ctx.tenant_id:
            return []
        tenant = await self.tenants.get(ctx.tenant_id)
        delegations = await self.delegations.list_for_tenant(ctx.tenant_id)
        now = datetime.now(UTC)
        summaries = []
        for delegation in delegations:
            delegator = await self.users.get(delegation.delegator_user_id)
            effective, reason = delegation_is_effective(
                delegation, delegator=delegator, tenant=tenant, now=now
            )
            summaries.append(
                _delegation_summary(delegation, effective=effective, ineffective_reason=reason)
            )
        return summaries

    async def get_delegation(self, *, ctx: ExecutionContext, delegation_id: str) -> dict:
        delegation = await self.delegations.get(delegation_id)
        if not delegation or not _in_scope(ctx, delegation.tenant_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="delegation not found"
            )
        delegator = await self.users.get(delegation.delegator_user_id)
        tenant = await self.tenants.get(delegation.tenant_id)
        effective, reason = delegation_is_effective(
            delegation, delegator=delegator, tenant=tenant, now=datetime.now(UTC)
        )
        if not effective and delegation.status == "ACTIVE":
            # Only for reasons discovered here (expired / delegator_inactive
            # / authority_lost / tenant_suspended) — an explicit prior
            # revoke already has its own identity.delegation.revoked entry,
            # so this doesn't double-audit that case.
            await audit(
                "identity.delegation.invalidated",
                resource_type="delegation",
                resource_id=delegation.delegation_id,
                decision="DENY",
                payload={"reason": reason},
            )
        return _delegation_summary(delegation, effective=effective, ineffective_reason=reason)

    async def revoke_delegation(self, *, ctx: ExecutionContext, delegation_id: str) -> dict:
        delegation = await self.delegations.get(delegation_id)
        if not delegation or not _in_scope(ctx, delegation.tenant_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="delegation not found"
            )
        if delegation.status != "ACTIVE":
            raise _conflict("delegation is not active")

        # No hierarchy check here, same reasoning as revoke_invitation:
        # revoking only de-escalates, so any governance-role member of the
        # tenant may revoke any delegation in it, not only the original
        # delegator.
        delegation.revoke(revoked_by=ctx.principal_id)
        delegation = await self.delegations.update(delegation)
        await audit(
            "identity.delegation.revoked",
            resource_type="delegation",
            resource_id=delegation.delegation_id,
            decision="PERMIT",
            payload={"revoked_by": ctx.principal_id},
        )
        return _delegation_summary(delegation)

    async def extend_delegation(
        self, *, ctx: ExecutionContext, delegation_id: str, new_expires_at: str | None
    ) -> dict:
        delegation = await self.delegations.get(delegation_id)
        if not delegation or not _in_scope(ctx, delegation.tenant_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="delegation not found"
            )
        if delegation.status != "ACTIVE":
            raise _conflict("delegation is not active")
        if new_expires_at is not None:
            try:
                new_dt = datetime.fromisoformat(new_expires_at)
            except ValueError as exc:
                raise _bad_request("expires_at must be an ISO-8601 datetime") from exc
            if new_dt <= datetime.now(UTC):
                raise _bad_request("expires_at must be in the future")

        # Re-validate against the ORIGINAL delegator's CURRENT rank, not the
        # rank of whoever happens to call /extend — the delegator remains
        # the source of the derived authority for the delegation's entire
        # life (fail closed: if the delegator can no longer justify what
        # was delegated, extending it is denied, exactly like resolution
        # would deny it at hydration time).
        delegator = await self.users.get(delegation.delegator_user_id)
        if not delegator or not delegator.can_authenticate():
            await audit(
                "identity.delegation.invalidated",
                resource_type="delegation",
                resource_id=delegation.delegation_id,
                decision="DENY",
                payload={"reason": "delegator_inactive"},
            )
            raise _conflict("delegator is no longer active; cannot extend")
        if highest_rank(delegation.delegated_roles) > highest_rank(delegator.roles):
            await audit(
                "identity.delegation.invalidated",
                resource_type="delegation",
                resource_id=delegation.delegation_id,
                decision="DENY",
                payload={"reason": "authority_lost"},
            )
            raise _conflict("delegator no longer has sufficient authority; cannot extend")

        delegation.extend(new_expires_at=new_expires_at)
        delegation = await self.delegations.update(delegation)
        await audit(
            "identity.delegation.modified",
            resource_type="delegation",
            resource_id=delegation.delegation_id,
            decision="PERMIT",
            payload={"new_expires_at": new_expires_at, "extended_by": ctx.principal_id},
        )
        return _delegation_summary(delegation)
