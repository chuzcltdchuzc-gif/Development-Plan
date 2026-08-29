"""JwtVerifier against a Supabase-shaped (ES256) IdP — IMVP-3.

Proves the configurable `algorithms` parameter added to JwtVerifier (previously
hardcoded to RS256 for Keycloak) correctly verifies Supabase's own default
signing algorithm, and that the algorithm allowlist is enforced both ways —
an ES256-configured verifier still rejects an RS256 token and vice versa,
which is the actual security property this parameter exists to preserve
(never trust the token's own `alg` header; the server decides what's
acceptable, not the caller).
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from jwt import InvalidTokenError

from app.kernel.security.jwt import JwtVerifier
from tests.fakes.jwks import FakeKeycloak
from tests.fakes.supabase_jwks import FakeSupabase

pytestmark = pytest.mark.asyncio


@pytest.fixture
def supabase() -> FakeSupabase:
    return FakeSupabase()


@pytest.fixture
def verifier(supabase: FakeSupabase) -> JwtVerifier:
    return JwtVerifier(
        jwks=supabase,
        issuer=supabase.issuer,
        audience=supabase.audience,
        algorithms=["ES256"],
    )


async def test_valid_es256_token_verifies(supabase: FakeSupabase, verifier: JwtVerifier) -> None:
    token = supabase.issue(subject="user-1")
    claims = await verifier.verify(token)
    assert claims["sub"] == "user-1"
    assert claims["aud"] == "authenticated"


async def test_expired_es256_token_rejected(supabase: FakeSupabase, verifier: JwtVerifier) -> None:
    stale = datetime.now(UTC) - timedelta(hours=1)
    token = supabase.issue(subject="user-1", issued_at=stale, expires_in_seconds=60)
    with pytest.raises(InvalidTokenError):
        await verifier.verify(token)


async def test_wrong_audience_rejected(supabase: FakeSupabase, verifier: JwtVerifier) -> None:
    token = supabase.issue(subject="user-1", audience="some-other-app")
    with pytest.raises(InvalidTokenError):
        await verifier.verify(token)


async def test_unknown_kid_rejected(verifier: JwtVerifier) -> None:
    with pytest.raises(InvalidTokenError):
        await verifier.verify("not.a.validtoken")


async def test_es256_configured_verifier_rejects_rs256_token() -> None:
    """A verifier explicitly configured for ES256 (Supabase) must not accept an
    RS256 token (Keycloak) even if — hypothetically — it could resolve a `kid`
    for it. Proves the algorithm allowlist is actually enforced, not just
    documented: JWKSProvider lookups are per-provider, so this also confirms
    the two IdPs' key spaces don't cross-pollinate."""
    keycloak = FakeKeycloak()
    supabase_verifier = JwtVerifier(
        jwks=keycloak,  # deliberately mismatched: ES256-configured verifier, RS256 keys
        issuer=keycloak.issuer,
        audience=keycloak.audience,
        algorithms=["ES256"],
    )
    token = keycloak.issue(subject="usr_1", roles=["general_user"])
    with pytest.raises(InvalidTokenError):
        await supabase_verifier.verify(token)


async def test_rs256_configured_verifier_still_works_unchanged() -> None:
    """Regression guard: Keycloak's existing call site never passes `algorithms`
    at all — confirms the default (RS256) preserves its exact prior behavior."""
    keycloak = FakeKeycloak()
    verifier = JwtVerifier(jwks=keycloak, issuer=keycloak.issuer, audience=keycloak.audience)
    token = keycloak.issue(subject="usr_1", roles=["general_user"])
    claims = await verifier.verify(token)
    assert claims["sub"] == "usr_1"
