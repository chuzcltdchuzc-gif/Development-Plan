"""Access-token verification against an external IdP's JWKS.

The IdP (Keycloak) issues access tokens; this side only verifies them
(ADR-004) — there is no token issuer/signing-key store here. `JWKSProvider`
is a port so tests substitute a fixed keypair instead of a real realm.
"""
from __future__ import annotations

import json
from typing import Protocol

import jwt as pyjwt
from jwt import InvalidTokenError

ALGORITHM = "RS256"


class JWKSProvider(Protocol):
    async def get_verify_key(self, kid: str) -> dict | None:
        """Return a JWK dict (or None if unknown) for the given key id."""
        ...


class JwtVerifier:
    def __init__(self, *, jwks: JWKSProvider, issuer: str, audience: str) -> None:
        self._jwks = jwks
        self._issuer = issuer
        self._audience = audience

    async def verify(self, token: str) -> dict:
        """Return verified claims, or raise InvalidTokenError."""
        try:
            header = pyjwt.get_unverified_header(token)
        except Exception as exc:
            raise InvalidTokenError("unparseable token header") from exc

        kid = header.get("kid")
        if not kid:
            raise InvalidTokenError("missing kid")

        jwk = await self._jwks.get_verify_key(kid)
        if not jwk:
            raise InvalidTokenError(f"unknown kid {kid}")

        public_key = pyjwt.PyJWK.from_json(json.dumps(jwk)).key
        return pyjwt.decode(
            token,
            public_key,
            algorithms=[ALGORITHM],
            audience=self._audience,
            issuer=self._issuer,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
