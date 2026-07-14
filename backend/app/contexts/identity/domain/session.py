"""Session aggregate — server-side record of an issued refresh token.

The refresh token plaintext is sent to the caller as an httpOnly cookie and
NEVER persisted — only its SHA-256 hash is stored, so a database read alone
does not yield a usable refresh token.

Lifecycle: ACTIVE -> rotated (on /refresh, previous session REVOKED with
reason "rotated" and a new one issued) or REVOKED (on /logout, or on replay
detection, which additionally revokes every other ACTIVE session for the
user as a token-theft response).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

STATUS_ACTIVE = "ACTIVE"
STATUS_REVOKED = "REVOKED"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class Session:
    session_id: str
    user_id: str
    refresh_token_hash: str
    # The IdP's own refresh token, server-side only, never sent to the
    # client — used to mint a fresh IdP access token on our /refresh call.
    # Production deployments should encrypt this column at rest (tracked as
    # a B13 Security hardening item, not blocking here).
    idp_refresh_token: str
    expires_at: str
    status: str = STATUS_ACTIVE
    created_at: str = field(default_factory=_now_iso)
    rotated_from: str | None = None
    user_agent: str | None = None
    ip_address: str | None = None
    revoked_at: str | None = None
    revoked_reason: str | None = None

    @classmethod
    def new(
        cls,
        *,
        user_id: str,
        refresh_token_hash: str,
        idp_refresh_token: str,
        expires_at: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
        rotated_from: str | None = None,
    ) -> Session:
        return cls(
            session_id="ses_" + uuid.uuid4().hex,
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            idp_refresh_token=idp_refresh_token,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
            rotated_from=rotated_from,
        )

    def is_active_at(self, when: datetime) -> bool:
        return self.status == STATUS_ACTIVE and datetime.fromisoformat(self.expires_at) > when

    def revoke(self, reason: str) -> None:
        self.status = STATUS_REVOKED
        self.revoked_at = _now_iso()
        self.revoked_reason = reason


def utcnow() -> datetime:
    return datetime.now(UTC)
