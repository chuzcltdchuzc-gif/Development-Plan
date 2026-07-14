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
from app.contexts.identity.domain.user import User
from app.contexts.identity.domain.value_objects import CountryCode, Email
from app.contexts.identity.ports import (
    IdentityProvider,
    IdentityProviderError,
    IdentityProviderTokens,
    SessionRepository,
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
    ) -> None:
        self.users = users
        self.sessions = sessions
        self.identity_provider = identity_provider

    # ---- Registration -----------------------------------------------------
    async def register_local(
        self, *, email: str, password: str, full_name: str, country: str | None = None
    ) -> dict:
        try:
            normalized_email = Email.parse(email).value
        except ValueError as exc:
            raise _bad_request(str(exc)) from exc
        if not password or len(password) < 8:
            raise _bad_request("password must be at least 8 characters")
        if not full_name or not full_name.strip():
            raise _bad_request("full_name required")
        country_code = (country or DEFAULT_COUNTRY).upper()
        try:
            country_code = CountryCode(country_code).value
        except ValueError as exc:
            raise _bad_request(str(exc)) from exc

        if await self.users.get_by_email(normalized_email):
            raise _conflict("Email already registered")

        try:
            subject = await self.identity_provider.create_user(
                email=normalized_email, password=password, full_name=full_name.strip()
            )
        except IdentityProviderError as exc:
            if exc.code == "identity.email_taken":
                raise _conflict("Email already registered") from exc
            raise _bad_request(str(exc)) from exc

        # Self-registration ALWAYS gets the default role — there is no role
        # field on the register request for a caller to send (ADR-004 pt. 4).
        user = User.new(
            keycloak_subject=subject,
            email=normalized_email,
            full_name=full_name.strip(),
            country=country_code,
        )
        await self.users.add(user)
        await audit(
            "identity.user.registered",
            resource_type="user",
            resource_id=user.user_id,
            payload={"country": country_code},
        )
        return await self.login_local(
            email=normalized_email, password=password, user_agent=None, ip=None
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
