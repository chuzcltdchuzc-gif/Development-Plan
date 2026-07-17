"""AuthService — Identity context's authentication use-cases.

Orchestrates register / login / refresh / logout. Keycloak (via the
IdentityProvider port) authenticates credentials and issues access tokens;
this service owns session/refresh-token rotation and replay-detection on
top of that (docs/adr/ADR-004 — see the Operator's decision that refresh
rotation stays this side's code, not Keycloak's realm-level setting).
"""
from __future__ import annotations

import logging

from fastapi import HTTPException, status

from app.contexts.identity.domain.session import Session, utcnow
from app.contexts.identity.domain.tenant import Tenant
from app.contexts.identity.domain.user import User
from app.contexts.identity.domain.value_objects import CountryCode, Email, highest_rank
from app.contexts.identity.ports import (
    IdentityProvider,
    IdentityProviderError,
    IdentityProviderTokens,
    InvitationRepository,
    SessionRepository,
    TenantRepository,
    UserRepository,
)
from app.kernel.audit import audit
from app.kernel.security.tokens import hash_token, new_opaque_token, refresh_expiry

logger = logging.getLogger("contexts.identity.auth")

REFRESH_TOKEN_TTL_SECONDS = 30 * 24 * 3600  # 30 days
DEFAULT_COUNTRY = "NG"


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _unauthenticated(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


class AuthService:
    def __init__(
        self,
        *,
        users: UserRepository,
        sessions: SessionRepository,
        identity_provider: IdentityProvider,
        invitations: InvitationRepository,
        tenants: TenantRepository,
    ) -> None:
        self.users = users
        self.sessions = sessions
        self.identity_provider = identity_provider
        self.invitations = invitations
        self.tenants = tenants

    # ---- Shared validation / IdP provisioning ------------------------------
    def _validate_credentials(
        self, *, password: str, full_name: str, country: str | None
    ) -> tuple[str, str]:
        """Shared by register_local and accept_invitation — both create a
        brand-new local account and IdP credential, differing only in where
        the email and role come from."""
        if not password or len(password) < 8:
            raise _bad_request("password must be at least 8 characters")
        if not full_name or not full_name.strip():
            raise _bad_request("full_name required")
        country_code = (country or DEFAULT_COUNTRY).upper()
        try:
            country_code = CountryCode(country_code).value
        except ValueError as exc:
            raise _bad_request(str(exc)) from exc
        return full_name.strip(), country_code

    async def _create_idp_user(self, *, email: str, password: str, full_name: str) -> str:
        try:
            return await self.identity_provider.create_user(
                email=email, password=password, full_name=full_name
            )
        except IdentityProviderError as exc:
            if exc.code == "identity.email_taken":
                raise _conflict("Email already registered") from exc
            raise _bad_request(str(exc)) from exc

    # ---- Registration -----------------------------------------------------
    async def register_local(
        self, *, email: str, password: str, full_name: str, country: str | None = None
    ) -> dict:
        try:
            normalized_email = Email.parse(email).value
        except ValueError as exc:
            raise _bad_request(str(exc)) from exc
        full_name_clean, country_code = self._validate_credentials(
            password=password, full_name=full_name, country=country
        )

        if await self.users.get_by_email(normalized_email):
            raise _conflict("Email already registered")

        subject = await self._create_idp_user(
            email=normalized_email, password=password, full_name=full_name_clean
        )

        # Self-registration creates its own tenant (B2 slice 3) — a fresh
        # Organization boundary with this user as its founder/owner.
        # tenants.owner_user_id -> identity_users.id and identity_users.
        # tenant_id -> tenants.id are a genuine mutual FK pair, so neither
        # row can carry a *valid* forward reference to the other at insert
        # time: the tenant is inserted first with no owner (nullable),
        # then the user (referencing the now-real tenant), then the tenant
        # is updated with its owner — three round-trips, not a deferred-
        # constraint trick, so the ordering stays obvious from reading it.
        tenant = Tenant.new(name=f"{full_name_clean}'s Organization")
        await self.tenants.add(tenant)

        # Self-registration ALWAYS gets the default role — there is no role
        # field on the register request for a caller to send (ADR-004 pt. 4).
        user = User.new(
            keycloak_subject=subject,
            email=normalized_email,
            full_name=full_name_clean,
            country=country_code,
            tenant_id=tenant.tenant_id,
        )
        await self.users.add(user)

        tenant.owner_user_id = user.user_id
        await self.tenants.update(tenant)

        await audit(
            "identity.user.registered",
            resource_type="user",
            resource_id=user.user_id,
            payload={"country": country_code},
        )
        return await self.login_local(
            email=normalized_email, password=password, user_agent=None, ip=None
        )

    # ---- Invitation acceptance (B2 — tenant membership provisioning) ------
    async def accept_invitation(
        self,
        *,
        token: str,
        password: str,
        full_name: str,
        country: str | None,
        user_agent: str | None,
        ip: str | None,
    ) -> dict:
        """Redemption-time validation re-checks the inviter's account and
        rank (below) AND the target tenant's own status (B2 slice 3) — not
        just the invitation's own status/expiry. Both are re-checked
        against their CURRENT state, not the state captured when the
        invitation was created."""
        if not token:
            raise _unauthenticated("Invalid or expired invitation")
        invitation = await self.invitations.get_by_token_hash(hash_token(token))
        if not invitation or not invitation.is_redeemable_at(utcnow()):
            await audit(
                "identity.invitation.redemption_denied",
                resource_type="invitation",
                resource_id=invitation.invitation_id if invitation else None,
                decision="DENY",
                payload={"reason": "invalid_or_expired"},
            )
            # Generic message on purpose — unknown, expired, already-
            # accepted, and revoked all look identical to the caller, same
            # rationale as login's generic "Invalid email or password".
            raise _unauthenticated("Invalid or expired invitation")

        # Redemption-time authority re-check (B2 slice 2): the hierarchy
        # check at invite-creation time (AdminService.create_invitation)
        # only proves the inviter had authority *then*. An invitation can
        # sit PENDING for days; if the inviter is deactivated or demoted
        # below the invited role's rank in the meantime, redeeming it must
        # not silently grant a role its issuer could no longer grant today.
        # Re-run the identical highest_rank() check against the inviter's
        # CURRENT roles, not the ones captured at creation time.
        inviter = await self.users.get(invitation.invited_by)
        target_tenant = await self.tenants.get(invitation.tenant_id)
        authority_lost_reason: str | None = None
        if not inviter or not inviter.can_authenticate():
            authority_lost_reason = "inviter_inactive"
        elif highest_rank([invitation.role]) > highest_rank(inviter.roles):
            authority_lost_reason = "inviter_authority_lost"
        elif inviter.tenant_id != invitation.tenant_id:
            # Currently unreachable: nothing in this codebase ever mutates
            # User.tenant_id after creation, so an inviter's tenant can't
            # drift away from the invitation's tenant today. Kept as a
            # forward-compatible guard against a future tenant-transfer
            # feature, not dead weight.
            authority_lost_reason = "tenant_mismatch"
        elif not target_tenant or not target_tenant.is_active():
            # B2 slice 3: the tenant itself may have been suspended or
            # archived after the invitation was issued.
            authority_lost_reason = "tenant_not_active"

        if authority_lost_reason:
            invitation.revoke()
            await self.invitations.update(invitation)
            await audit(
                "identity.invitation.redemption_denied",
                resource_type="invitation",
                resource_id=invitation.invitation_id,
                decision="DENY",
                payload={"reason": authority_lost_reason},
            )
            raise _unauthenticated("Invalid or expired invitation")

        full_name_clean, country_code = self._validate_credentials(
            password=password, full_name=full_name, country=country
        )

        # Re-check even though create_invitation already checked at invite
        # time — someone could have registered with this email in the
        # window between invitation creation and acceptance.
        if await self.users.get_by_email(invitation.invited_email):
            raise _conflict("Email already registered")

        subject = await self._create_idp_user(
            email=invitation.invited_email, password=password, full_name=full_name_clean
        )

        # Tenant and role come from the invitation, not from the caller —
        # the hierarchy check already happened once, at creation time
        # (AdminService.create_invitation), against the inviter's rank.
        # There is no acting principal here to re-check against: the
        # invitee has no account yet.
        user = User.new(
            keycloak_subject=subject,
            email=invitation.invited_email,
            full_name=full_name_clean,
            country=country_code,
            tenant_id=invitation.tenant_id,
        )
        user.roles = [invitation.role]
        await self.users.add(user)

        invitation.accept()
        await self.invitations.update(invitation)

        await audit(
            "identity.user.registered",
            resource_type="user",
            resource_id=user.user_id,
            payload={"country": country_code, "via_invitation": invitation.invitation_id},
        )
        await audit(
            "identity.invitation.accepted",
            resource_type="invitation",
            resource_id=invitation.invitation_id,
            decision="PERMIT",
            payload={"user_id": user.user_id},
        )
        return await self.login_local(
            email=invitation.invited_email, password=password, user_agent=user_agent, ip=ip
        )

    # ---- Login --------------------------------------------------------
    async def login_local(
        self, *, email: str, password: str, user_agent: str | None, ip: str | None
    ) -> dict:
        normalized = Email.parse(email).value
        try:
            idp_tokens = await self.identity_provider.authenticate(
                email=normalized, password=password
            )
        except IdentityProviderError as exc:
            await audit(
                "identity.login.failed",
                resource_type="user",
                decision="DENY",
                payload={"email": normalized, "reason": exc.code},
            )
            raise _unauthenticated("Invalid email or password") from exc

        user = await self.users.get_by_keycloak_subject(idp_tokens.subject)
        if not user or not user.can_authenticate():
            await audit(
                "identity.login.failed",
                resource_type="user",
                decision="DENY",
                payload={"email": normalized, "reason": "account_not_found_or_inactive"},
            )
            raise _unauthenticated("Invalid email or password")

        # B2 slice 3: a suspended/archived tenant locks out every one of its
        # members at login too, not only on subsequent requests (the PEP's
        # context hydrator — app.contexts.identity.context_hydration — is
        # the layer that locks out an *already-issued* access token; this
        # check additionally stops a new token from being issued at all).
        tenant = await self.tenants.get(user.tenant_id)
        if not tenant or not tenant.is_active():
            await audit(
                "identity.login.failed",
                resource_type="user",
                decision="DENY",
                payload={"email": normalized, "reason": "tenant_not_active"},
            )
            raise _unauthenticated("Invalid email or password")

        return await self._issue_tokens(user, idp_tokens, user_agent=user_agent, ip=ip)

    # ---- Refresh --------------------------------------------------------
    async def refresh(
        self, *, refresh_token: str, user_agent: str | None, ip: str | None
    ) -> dict:
        if not refresh_token:
            raise _unauthenticated("Missing refresh token")
        rhash = hash_token(refresh_token)
        session = await self.sessions.get_by_refresh_hash(rhash)
        if not session:
            await audit(
                "identity.refresh.unknown_token", resource_type="session", decision="DENY"
            )
            raise _unauthenticated("Invalid refresh token")

        if session.status != "ACTIVE":
            # Replay of an already-rotated/revoked token: kill every active
            # session for this user as a token-theft response.
            await self.sessions.revoke_all_active_for_user(
                session.user_id, "refresh_token_replay"
            )
            await audit(
                "identity.refresh.replay_detected",
                resource_type="user",
                resource_id=session.user_id,
                decision="DENY",
            )
            raise _unauthenticated("Refresh token reuse detected")

        if not session.is_active_at(utcnow()):
            session.revoke("expired")
            await self.sessions.update(session)
            raise _unauthenticated("Refresh token expired")

        user = await self.users.get(session.user_id)
        if not user or not user.can_authenticate():
            session.revoke("user_inactive")
            await self.sessions.update(session)
            raise _unauthenticated("Account inactive")

        try:
            idp_tokens = await self.identity_provider.refresh_access_token(
                idp_refresh_token=session.idp_refresh_token
            )
        except IdentityProviderError as exc:
            session.revoke("idp_refresh_rejected")
            await self.sessions.update(session)
            raise _unauthenticated("Session could not be refreshed") from exc

        session.revoke("rotated")
        await self.sessions.update(session)
        return await self._issue_tokens(
            user, idp_tokens, user_agent=user_agent, ip=ip, rotated_from=session.session_id
        )

    # ---- Logout -----------------------------------------------------------
    async def logout(self, *, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        session = await self.sessions.get_by_refresh_hash(hash_token(refresh_token))
        if session and session.status == "ACTIVE":
            session.revoke("user_logout")
            await self.sessions.update(session)
            await audit(
                "identity.logout", resource_type="session", resource_id=session.session_id
            )

    # ---- Internal: token/session issuance --------------------------------
    async def _issue_tokens(
        self,
        user: User,
        idp_tokens: IdentityProviderTokens,
        *,
        user_agent: str | None,
        ip: str | None,
        rotated_from: str | None = None,
    ) -> dict:
        plaintext_refresh, rhash = new_opaque_token()
        expires_at = refresh_expiry(REFRESH_TOKEN_TTL_SECONDS).isoformat()
        session = Session.new(
            user_id=user.user_id,
            refresh_token_hash=rhash,
            idp_refresh_token=idp_tokens.idp_refresh_token,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip,
            rotated_from=rotated_from,
        )
        session = await self.sessions.add(session)

        user.mark_logged_in()
        try:
            user = await self.users.update(user, expected_version=user.version)
        except Exception:  # noqa: BLE001 — last_login is best-effort
            logger.warning("could not stamp last_login_at for %s", user.user_id)

        await audit(
            "identity.login.success",
            resource_type="user",
            resource_id=user.user_id,
            decision="PERMIT",
            payload={"session_id": session.session_id, "rotated_from": rotated_from},
        )
        return {
            "access_token": idp_tokens.access_token,
            "token_type": "Bearer",
            "expires_in": idp_tokens.expires_in,
            "refresh_token": plaintext_refresh,
            "refresh_expires_at": expires_at,
            "session_id": session.session_id,
            "user": user.public_view(),
        }
