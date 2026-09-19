"""IMVP-3 — 'a valid token with no corresponding governed identity must not
grant access' (authorization §9/§11). This is not new backend logic — it's
the same fail-closed hydration behavior ADR-009/B1 already established
(a token whose hydration comes back empty still passes `require_auth`, since
`is_anonymous` only checks the literal sentinel, but carries zero roles, so
every `require_role`-gated route denies it via the PDP). This test proves it
explicitly against a genuinely unregistered subject (not a suspended one —
see test_b2_tenants.py::test_suspend_locks_out_members_immediately for that
adjacent case), since IMVP-3 needed this property demonstrated by name, not
just inherited.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.app_factory import AppHarness, build_test_app


@pytest.fixture
def harness() -> AppHarness:
    return build_test_app()


@pytest.fixture
def client(harness: AppHarness) -> TestClient:
    return TestClient(harness.app)


def test_valid_token_unknown_subject_is_authenticated_but_unauthorized(
    harness: AppHarness, client: TestClient
) -> None:
    # A structurally valid, correctly-signed token — the IdP genuinely
    # authenticated this person — for a subject that was never registered as
    # a LandVault User. No InMemoryUserRepository entry exists for it.
    token = harness.keycloak.issue(subject="idp-subject-never-provisioned", roles=[])

    # require_auth alone (no role gate) treats this as authenticated — the
    # existing, documented B1 fallback — not a 401.
    me = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["tenant_id"] is None
    assert me.json()["roles"] == []

    # Any actually governance/role-gated route denies it — this is where
    # "authenticated but unauthorized" actually bites, per pep.py's own
    # documented reasoning.
    governance = client.get(
        "/v1/test/governance-only", headers={"Authorization": f"Bearer {token}"}
    )
    assert governance.status_code == 403

    # No default access, org, tenant, or role was silently created as a side
    # effect of this request — the fake repository this test constructed
    # remains empty for this subject.
    assert harness.users._by_id == {} or all(
        u.identity_subject != "idp-subject-never-provisioned"
        for u in harness.users._by_id.values()
    )


def test_missing_token_denied(client: TestClient) -> None:
    response = client.get("/v1/test/governance-only")
    assert response.status_code == 401


def test_malformed_token_denied(client: TestClient) -> None:
    response = client.get(
        "/v1/test/governance-only", headers={"Authorization": "Bearer not-a-real-jwt"}
    )
    assert response.status_code == 401


def test_forged_signature_denied(harness: AppHarness, client: TestClient) -> None:
    """A token signed by a different keypair than the one our JWKS provider
    publishes must be rejected — proves the signature check is real, not
    merely a shape check."""
    from tests.fakes.jwks import FakeKeycloak

    attacker_idp = FakeKeycloak(issuer=harness.keycloak.issuer, audience=harness.keycloak.audience)
    forged_token = attacker_idp.issue(subject="usr_attacker", roles=["super_admin"])

    response = client.get(
        "/v1/test/governance-only", headers={"Authorization": f"Bearer {forged_token}"}
    )
    assert response.status_code == 401
