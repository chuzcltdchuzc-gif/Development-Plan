"""A fixed-keypair JWKS provider standing in for a real Supabase project in
tests — implements the same `JWKSProvider` protocol the real adapter does
(app.contexts.identity.adapters.supabase.SupabaseJWKSProvider). ES256, not
RS256 — Supabase's own default signing algorithm for asymmetric project
keys, which is exactly the case `JwtVerifier`'s configurable `algorithms`
parameter (IMVP-3) exists to support.
"""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta

import jwt as pyjwt
from cryptography.hazmat.primitives.asymmetric import ec
from jwt.algorithms import ECAlgorithm

KID = "test-supabase-key-1"


class FakeSupabase:
    """Issues ES256 tokens shaped like Supabase's and exposes a matching JWKS."""

    def __init__(
        self,
        *,
        project_url: str = "https://test-project.supabase.test",
        audience: str = "authenticated",
    ) -> None:
        self.project_url = project_url
        self.issuer = f"{project_url}/auth/v1"
        self.audience = audience
        self._private_key = ec.generate_private_key(ec.SECP256R1())

    async def get_verify_key(self, kid: str) -> dict | None:
        if kid != KID:
            return None
        jwk = json.loads(ECAlgorithm.to_jwk(self._private_key.public_key()))
        return {**jwk, "kid": KID, "use": "sig", "alg": "ES256"}

    def issue(
        self,
        *,
        subject: str,
        email: str = "user@example.test",
        expires_in_seconds: int = 300,
        issued_at: datetime | None = None,
        audience: str | None = None,
    ) -> str:
        now = issued_at or datetime.now(UTC)
        exp = now + timedelta(seconds=expires_in_seconds)
        claims = {
            "iss": self.issuer,
            "aud": audience or self.audience,
            "sub": subject,
            "jti": uuid.uuid4().hex,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "email": email,
            "role": "authenticated",
        }
        return pyjwt.encode(claims, self._private_key, algorithm="ES256", headers={"kid": KID})
