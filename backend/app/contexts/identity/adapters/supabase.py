"""Supabase Auth adapter — JWKSProvider only (ADR-025 production identity provider).

Unlike Keycloak, Supabase Auth is never proxied by this backend: the frontend
authenticates directly against Supabase's own API/SDK and presents the
resulting access token to us. There is no Supabase equivalent of
`KeycloakIdentityProvider` (no register/login/refresh proxying) — this
adapter's only job is fetching the project's published signing keys so
`JwtVerifier` can verify a token it never issued.

Same caching shape as `KeycloakJWKSProvider` deliberately — this is a
provider swap at the `JWKSProvider` boundary, not a redesign of how JWKS
fetching/caching works.
"""
from __future__ import annotations

import time

import httpx

from app.kernel.security.jwt import JWKSProvider


class SupabaseJWKSProvider(JWKSProvider):
    def __init__(self, *, project_url: str, cache_ttl_seconds: int = 300) -> None:
        # Supabase publishes its (per-project) JWKS at this fixed path for
        # projects using asymmetric (ES256) signing keys — the current
        # Supabase-recommended configuration, superseding the legacy shared
        # HS256 secret model (which has no JWKS at all and is not supported
        # by this adapter).
        self._jwks_url = f"{project_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
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


def supabase_issuer(project_url: str) -> str:
    """Supabase's standard issuer claim for a given project URL."""
    return f"{project_url.rstrip('/')}/auth/v1"
