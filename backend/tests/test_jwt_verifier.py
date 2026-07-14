from datetime import UTC, datetime, timedelta

import pytest
from jwt import InvalidTokenError

from app.kernel.security.jwt import JwtVerifier
from tests.fakes.jwks import FakeKeycloak


@pytest.fixture
def keycloak() -> FakeKeycloak:
    return FakeKeycloak()


@pytest.fixture
def verifier(keycloak: FakeKeycloak) -> JwtVerifier:
    return JwtVerifier(jwks=keycloak, issuer=keycloak.issuer, audience=keycloak.audience)


async def test_valid_token_verifies(keycloak: FakeKeycloak, verifier: JwtVerifier) -> None:
    token = keycloak.issue(subject="usr_1", roles=["general_user"])
    claims = await verifier.verify(token)
    assert claims["sub"] == "usr_1"
    assert claims["roles"] == ["general_user"]


async def test_expired_jwt_rejected(keycloak: FakeKeycloak, verifier: JwtVerifier) -> None:
    stale_issue_time = datetime.now(UTC) - timedelta(hours=1)
    token = keycloak.issue(
        subject="usr_1",
        roles=["general_user"],
        issued_at=stale_issue_time,
        expires_in_seconds=60,  # expired 59 minutes ago
    )
    with pytest.raises(InvalidTokenError):
        await verifier.verify(token)


async def test_unknown_kid_rejected(verifier: JwtVerifier) -> None:
    with pytest.raises(InvalidTokenError):
        await verifier.verify("not.a.validtoken")


async def test_wrong_audience_rejected(keycloak: FakeKeycloak) -> None:
    token = keycloak.issue(subject="usr_1", roles=["general_user"])
    wrong_audience_verifier = JwtVerifier(
        jwks=keycloak, issuer=keycloak.issuer, audience="some-other-api"
    )
    with pytest.raises(InvalidTokenError):
        await wrong_audience_verifier.verify(token)
