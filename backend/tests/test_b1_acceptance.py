"""B1 acceptance tests — the 11-item checklist the Operator specified before
B1 is considered done. Real business logic throughout; Keycloak and Postgres
are swapped for in-memory fakes at the port boundary (tests/app_factory.py,
tests/fakes/) — see CLAUDE.md for what that scope does and doesn't cover.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.contexts.identity.domain.user import User
from app.contexts.identity.ports import IdentityProviderTokens
from app.kernel.audit import verify_chain
from tests.app_factory import AppHarness, build_test_app


@pytest.fixture
def harness() -> AppHarness:
    return build_test_app()


@pytest.fixture
def client(harness: AppHarness) -> TestClient:
    return TestClient(harness.app)


def _register(
    client: TestClient, email: str = "user@example.test", password: str = "correct-horse"
) -> dict:
    response = client.post(
        "/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Ada Lovelace"},
    )
    assert response.status_code == 201, response.text
    return response.json()


# 1. Anonymous user cannot access any protected route ------------------------

def test_anonymous_user_cannot_access_any_protected_route(client: TestClient) -> None:
    response = client.get("/v1/test/protected")
    assert response.status_code == 401

    response = client.get("/v1/auth/me")
    assert response.status_code == 401


# 2. Expired JWT rejected -----------------------------------------------------

def test_expired_jwt_rejected(harness: AppHarness, client: TestClient) -> None:
    stale = datetime.now(UTC) - timedelta(hours=1)
    expired_token = harness.keycloak.issue(
        subject="usr_whatever", roles=[], issued_at=stale, expires_in_seconds=60
    )
    response = client.get(
        "/v1/test/protected", headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401


# 3. Refresh token rotates -----------------------------------------------------

def test_refresh_token_rotates(client: TestClient) -> None:
    _register(client)
    refresh_before = client.cookies.get("lv_refresh")
    assert refresh_before

    response = client.post("/v1/auth/refresh")
    assert response.status_code == 200, response.text
    refresh_after = client.cookies.get("lv_refresh")

    assert refresh_after
    assert refresh_after != refresh_before


# 4. Logout invalidates refresh token ------------------------------------------

def test_logout_invalidates_refresh_token(client: TestClient) -> None:
    tokens = _register(client)
    access_token = tokens["access_token"]

    logout_response = client.post(
        "/v1/auth/logout", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert logout_response.status_code == 204

    refresh_response = client.post("/v1/auth/refresh")
    assert refresh_response.status_code == 401


# 5. Stolen refresh token rejected (replay detection) --------------------------

def test_stolen_refresh_token_rejected(client: TestClient) -> None:
    _register(client)
    stolen_refresh_token = client.cookies.get("lv_refresh")
    assert stolen_refresh_token

    # Legitimate rotation: the real client refreshes, advancing past the token
    # a thief captured a moment earlier.
    legit_response = client.post("/v1/auth/refresh")
    assert legit_response.status_code == 200
    current_refresh_token = client.cookies.get("lv_refresh")
    assert current_refresh_token != stolen_refresh_token

    # The thief replays the captured (now-rotated-away-from) token.
    replay_response = client.post(
        "/v1/auth/refresh", headers={"Cookie": f"lv_refresh={stolen_refresh_token}"}
    )
    assert replay_response.status_code == 401

    # Replay detection revokes every active session for the user — even the
    # legitimate, just-rotated token chain is now dead.
    victim_response = client.post(
        "/v1/auth/refresh", headers={"Cookie": f"lv_refresh={current_refresh_token}"}
    )
    assert victim_response.status_code == 401


# 6. Role escalation impossible ------------------------------------------------

async def _seed_user_with_role(
    harness: AppHarness, *, email: str, password: str, role: str
) -> IdentityProviderTokens:
    subject = await harness.identity_provider.create_user(
        email=email, password=password, full_name="Seed User"
    )
    user = User.new(keycloak_subject=subject, email=email, full_name="Seed User", country="NG")
    user.roles = [role]
    await harness.users.add(user)
    return await harness.identity_provider.authenticate(email=email, password=password)


def test_role_escalation_impossible(harness: AppHarness, client: TestClient) -> None:
    import asyncio

    idp_tokens = asyncio.run(
        _seed_user_with_role(
            harness, email="officer@example.test", password="pw12345678", role="compliance_officer"
        )
    )
    officer_user = asyncio.run(harness.users.get_by_keycloak_subject(idp_tokens.subject))
    assert officer_user is not None

    target = _register(client, email="target@example.test", password="pw12345678")
    target_user_id = target["user"]["user_id"]

    # A compliance_officer (rank 40) may not grant super_admin (rank 100) to
    # someone else — that would exceed their own rank.
    response = client.post(
        f"/v1/admin/users/{target_user_id}/roles",
        json={"role": "super_admin"},
        headers={"Authorization": f"Bearer {idp_tokens.access_token}"},
    )
    assert response.status_code == 403

    # Nor may they elevate themselves, even to a role they could grant others.
    response = client.post(
        f"/v1/admin/users/{officer_user.user_id}/roles",
        json={"role": "licensed_surveyor"},
        headers={"Authorization": f"Bearer {idp_tokens.access_token}"},
    )
    assert response.status_code == 403


# 7. Self registration cannot assign roles -------------------------------------

def test_self_registration_cannot_assign_roles(client: TestClient) -> None:
    tokens = _register(client)
    assert tokens["user"]["roles"] == ["general_user"]

    # The DTO forbids extra fields outright — there is no role field to send.
    response = client.post(
        "/v1/auth/register",
        json={
            "email": "other@example.test",
            "password": "correct-horse",
            "full_name": "Eve",
            "role": "super_admin",
        },
    )
    assert response.status_code == 422


# 8. Policy engine denies by default -------------------------------------------

def test_policy_engine_denies_by_default(client: TestClient) -> None:
    tokens = _register(client)
    response = client.get(
        "/v1/test/governance-only",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 403


# 9. CORS rejects unknown origins ----------------------------------------------

def test_cors_rejects_unknown_origins() -> None:
    from app.main import app as b0_app  # CORS middleware is wired at app.main level

    with TestClient(b0_app) as b0_client:
        response = b0_client.get("/health/live", headers={"Origin": "https://evil.example"})
        assert "access-control-allow-origin" not in {k.lower() for k in response.headers}


# 10. Rate limiting enabled -----------------------------------------------------

def test_rate_limiting_enabled(client: TestClient) -> None:
    responses = [
        client.post("/v1/auth/login", json={"email": "nobody@example.test", "password": "wrong"})
        for _ in range(11)
    ]
    assert responses[-1].status_code == 429
    assert any(r.status_code == 429 for r in responses)


# 11. All auth events audited --------------------------------------------------

def test_all_auth_events_audited(harness: AppHarness, client: TestClient) -> None:
    tokens = _register(client)
    client.post("/v1/auth/refresh")
    client.post(
        "/v1/auth/logout", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )

    import asyncio

    entries = asyncio.run(harness.audit_store.all_entries())
    actions = {e.action for e in entries}
    assert "identity.user.registered" in actions
    assert "identity.login.success" in actions
    assert "identity.logout" in actions

    assert asyncio.run(verify_chain()) is True
