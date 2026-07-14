"""Keycloak adapters — IdentityProvider (Direct Access Grant + admin user
creation) and JWKSProvider (fetches/caches the realm's public signing keys).

Not exercised against a live Keycloak in this session (no Keycloak instance
available where this was written) — verified via tests/fakes/jwks.py and
tests/fakes/identity.py instead, which implement the identical protocols
(app.kernel.security.jwt.JWKSProvider, app.contexts.identity.ports.
IdentityProvider). Requires a realm with Direct Access Grants enabled and a
confidential client whose service account has `manage-users` on
realm-management (docs/adr/ADR-004).
"""
from __future__ import annotations

import time

import httpx
import jwt as pyjwt

from app.contexts.identity.ports import IdentityProviderError, IdentityProviderTokens
from app.kernel.security.jwt import JWKSProvider


class KeycloakJWKSProvider(JWKSProvider):
    def __init__(self, *, realm_url: str, cache_ttl_seconds: int = 300) -> None:
        self._jwks_url = f"{realm_url}/protocol/openid-connect/certs"
        self._cache_ttl = cache_ttl_seconds
        self._cached_at: float = 0.0
        self._keys: dict[str, dict] = {}

    async def _refresh(self) -> None:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(self._jwks_url)
            response.raise_for_status()
            body = response.json()
        self._keys = {key["kid"]: key for key in body.get("keys", [])}
        self._cached_at = time.monotonic()

    async def get_verify_key(self, kid: str) -> dict | None:
        if kid not in self._keys or (time.monotonic() - self._cached_at) > self._cache_ttl:
            await self._refresh()
        return self._keys.get(kid)


class KeycloakIdentityProvider:
    def __init__(
        self,
        *,
        realm_url: str,
        client_id: str,
        client_secret: str,
        admin_token_url: str,
        admin_api_url: str,
    ) -> None:
        self._token_url = f"{realm_url}/protocol/openid-connect/token"
        self._client_id = client_id
        self._client_secret = client_secret
        self._admin_token_url = admin_token_url
        self._admin_api_url = admin_api_url

    async def _admin_token(self) -> str:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                self._admin_token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
            )
            response.raise_for_status()
            return str(response.json()["access_token"])

    async def create_user(self, *, email: str, password: str, full_name: str) -> str:
        token = await self._admin_token()
        first_name, _, last_name = full_name.partition(" ")
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{self._admin_api_url}/users",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "username": email,
                    "email": email,
                    "enabled": True,
                    "firstName": first_name or email,
                    "lastName": last_name or "",
                    "credentials": [
                        {"type": "password", "value": password, "temporary": False}
                    ],
                },
            )
            if response.status_code == 409:
                raise IdentityProviderError("identity.email_taken", "Email already registered")
            response.raise_for_status()
            location = str(response.headers.get("Location", ""))
            return location.rsplit("/", 1)[-1]

    def _tokens_from_response(self, body: dict, fallback_email: str) -> IdentityProviderTokens:
        access_token = body["access_token"]
        # Extracting claims from a token Keycloak just handed us directly,
        # over a trusted server-to-server channel — not verifying a token
        # presented by an untrusted caller, so signature verification isn't
        # needed here (the PEP verifies signatures for client-presented
        # tokens; this is different from that).
        claims = pyjwt.decode(access_token, options={"verify_signature": False})
        return IdentityProviderTokens(
            subject=str(claims["sub"]),
            email=claims.get("email", fallback_email),
            access_token=access_token,
            expires_in=int(body["expires_in"]),
            idp_refresh_token=body["refresh_token"],
        )

    async def authenticate(self, *, email: str, password: str) -> IdentityProviderTokens:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                self._token_url,
                data={
                    "grant_type": "password",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "username": email,
                    "password": password,
                    "scope": "openid",
                },
            )
        if response.status_code != 200:
            raise IdentityProviderError("auth.invalid_credentials", "Invalid email or password")
        return self._tokens_from_response(response.json(), email)

    async def refresh_access_token(self, *, idp_refresh_token: str) -> IdentityProviderTokens:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                self._token_url,
                data={
                    "grant_type": "refresh_token",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "refresh_token": idp_refresh_token,
                },
            )
        if response.status_code != 200:
            raise IdentityProviderError(
                "auth.invalid_idp_refresh", "IdP rejected the refresh token"
            )
        return self._tokens_from_response(response.json(), fallback_email="")
