"""A fixed-keypair JWKS provider standing in for a real Keycloak realm in
tests — it implements the same `JWKSProvider` protocol the real Keycloak
adapter does (app.contexts.identity.adapters.keycloak.KeycloakJWKSProvider).
"""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta

import jwt as pyjwt
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

KID = "test-key-1"


class FakeKeycloak:
    """Issues RS256 tokens shaped like Keycloak's and exposes a matching JWKS,
    so the real `JwtVerifier` can be exercised without a live IdP."""

    def __init__(
        self,
        *,
        issuer: str = "https://idp.test/realms/landvault",
        audience: str = "landvault-api",
    ) -> None:
        self.issuer = issuer
        self.audience = audience
        self._private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    async def get_verify_key(self, kid: str) -> dict | None:
        if kid != KID:
            return None
        jwk = json.loads(RSAAlgorithm.to_jwk(self._private_key.public_key()))
        return {**jwk, "kid": KID, "use": "sig", "alg": "RS256"}

    def issue(
        self,
        *,
        subject: str,
        roles: list[str],
        email: str = "user@example.test",
        country: str = "NG",
        tenant_id: str = "ten_1",
        organization_id: str | None = None,
        attributes: dict | None = None,
        expires_in_seconds: int = 300,
        issued_at: datetime | None = None,
    ) -> str:
        now = issued_at or datetime.now(UTC)
        exp = now + timedelta(seconds=expires_in_seconds)
        claims = {
            "iss": self.issuer,
            "aud": self.audience,
            "sub": subject,
            "jti": uuid.uuid4().hex,
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "email": email,
            "country": country,
            "tenant_id": tenant_id,
            "organization_id": organization_id,
            "roles": roles,
            "attributes": attributes or {},
        }
        return pyjwt.encode(claims, self._private_key, algorithm="RS256", headers={"kid": KID})
