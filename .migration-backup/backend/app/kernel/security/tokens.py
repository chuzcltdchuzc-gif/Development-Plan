"""Opaque refresh tokens.

Access tokens are short-lived RS256 JWTs issued by the IdP
(app.kernel.security.jwt). Refresh tokens are opaque, cryptographically
random secrets: only their SHA-256 hash is ever persisted, so a database
read does not yield a usable refresh token. The plaintext is sent to the
caller exactly once, as an httpOnly secure cookie.

Rotation: on every refresh call, the current token is marked ROTATED/REVOKED
and a fresh one issued. A replay of an already-rotated token is a token-theft
signal (docs/adr/ADR-004 point 4-adjacent rationale) and terminates the
session chain.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

TOKEN_BYTES = 32  # 256 bits of entropy


def new_opaque_token() -> tuple[str, str]:
    """Return (plaintext, sha256_hex). Persist the hash; return the plaintext once."""
    raw = secrets.token_urlsafe(TOKEN_BYTES)
    return raw, hash_token(raw)


def hash_token(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def refresh_expiry(ttl_seconds: int, now: datetime | None = None) -> datetime:
    now = now or datetime.now(UTC)
    return now + timedelta(seconds=ttl_seconds)
