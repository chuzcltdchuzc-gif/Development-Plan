"""B2 slice 1 — tenant membership invitations (docs/adr/ADR-009's "tenant
provisioning" gap, docs/REBUILD_PLAN.md's B2 row). Real business logic
throughout; Keycloak and Postgres are swapped for in-memory fakes at the
port boundary (tests/app_factory.py, tests/fakes/), same as the B1
acceptance suite.
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from httpx import Response

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


async def _seed_user_with_role(
    harness: AppHarness, *, email: str, password: str, role: str
) -> tuple[IdentityProviderTokens, User]:
    subject = await harness.identity_provider.create_user(
        email=email, password=password, full_name="Seed User"
    )
    user = User.new(keycloak_subject=subject, email=email, full_name="Seed User", country="NG")
    user.roles = [role]
    user = await harness.users.add(user)
    idp_tokens = await harness.identity_provider.authenticate(email=email, password=password)
    return idp_tokens, user


def _create_invitation(
    client: TestClient, access_token: str, *, email: str, role: str
) -> Response:
    response = client.post(
        "/v1/admin/invitations",
        json={"email": email, "role": role},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    return response


# 1. Governance role can invite a member into their own tenant -----------------

def test_governance_role_can_create_invitation(harness: AppHarness, client: TestClient) -> None:
    idp_tokens, _officer = asyncio.run(
        _seed_user_with_role(
            harness, email="officer@example.test", password="pw12345678", role="compliance_officer"
        )
    )
    response = _create_invitation(
        client, idp_tokens.access_token, email="newhire@example.test", role="field_agent"
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == "newhire@example.test"
    assert body["role"] == "field_agent"
    assert body["token"]


# 2. Non-governance role cannot create invitations ------------------------------

def test_non_governance_role_cannot_create_invitation(
    harness: AppHarness, client: TestClient
) -> None:
    idp_tokens, _user = asyncio.run(
        _seed_user_with_role(
            harness, email="plain@example.test", password="pw12345678", role="general_user"
        )
    )
    response = _create_invitation(
        client, idp_tokens.access_token, email="anyone@example.test", role="general_user"
    )
    assert response.status_code == 403


# 3. Invitation cannot exceed the inviter's rank --------------------------------

def test_invitation_cannot_exceed_inviter_rank(harness: AppHarness, client: TestClient) -> None:
    idp_tokens, _officer = asyncio.run(
        _seed_user_with_role(
            harness, email="officer2@example.test", password="pw12345678", role="compliance_officer"
        )
    )
    response = _create_invitation(
        client, idp_tokens.access_token, email="wannabe@example.test", role="super_admin"
    )
    assert response.status_code == 403


# 4. Accepting joins the inviter's tenant with the invited role -----------------

def test_accept_invitation_joins_inviter_tenant_with_invited_role(
    harness: AppHarness, client: TestClient
) -> None:
    idp_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="officer3@example.test", password="pw12345678", role="compliance_officer"
        )
    )
    invite = _create_invitation(
        client, idp_tokens.access_token, email="newhire3@example.test", role="field_agent"
    ).json()

    response = client.post(
        "/v1/auth/invitations/accept",
        json={
            "token": invite["token"],
            "password": "correct-horse-battery",
            "full_name": "New Hire",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user"]["roles"] == ["field_agent"]
    assert body["user"]["tenant_id"] == officer.tenant_id


# 5. Accepting the same invitation twice fails ----------------------------------

def test_accept_invitation_twice_fails(harness: AppHarness, client: TestClient) -> None:
    idp_tokens, _officer = asyncio.run(
        _seed_user_with_role(
            harness, email="officer4@example.test", password="pw12345678", role="compliance_officer"
        )
    )
    invite = _create_invitation(
        client, idp_tokens.access_token, email="newhire4@example.test", role="field_agent"
    ).json()
    accept_body = {
        "token": invite["token"], "password": "correct-horse-battery", "full_name": "New Hire",
    }
    first = client.post("/v1/auth/invitations/accept", json=accept_body)
    assert first.status_code == 201

    second = client.post("/v1/auth/invitations/accept", json=accept_body)
    assert second.status_code == 401


# 6. Accepting an unknown token fails --------------------------------------------

def test_accept_unknown_token_fails(client: TestClient) -> None:
    response = client.post(
        "/v1/auth/invitations/accept",
        json={"token": "not-a-real-token", "password": "correct-horse-battery", "full_name": "X"},
    )
    assert response.status_code == 401


# 7. A second pending invitation for the same email conflicts -------------------

def test_duplicate_pending_invitation_conflicts(harness: AppHarness, client: TestClient) -> None:
    idp_tokens, _officer = asyncio.run(
        _seed_user_with_role(
            harness, email="officer5@example.test", password="pw12345678", role="compliance_officer"
        )
    )
    first = _create_invitation(
        client, idp_tokens.access_token, email="dup@example.test", role="field_agent"
    )
    assert first.status_code == 201

    second = _create_invitation(
        client, idp_tokens.access_token, email="dup@example.test", role="field_agent"
    )
    assert second.status_code == 409


# 8. Invitation lifecycle is audited and the hash chain still verifies ---------

def test_invitation_events_audited(harness: AppHarness, client: TestClient) -> None:
    idp_tokens, _officer = asyncio.run(
        _seed_user_with_role(
            harness, email="officer6@example.test", password="pw12345678", role="compliance_officer"
        )
    )
    invite = _create_invitation(
        client, idp_tokens.access_token, email="newhire6@example.test", role="field_agent"
    ).json()
    client.post(
        "/v1/auth/invitations/accept",
        json={
            "token": invite["token"], "password": "correct-horse-battery", "full_name": "New Hire",
        },
    )

    entries = asyncio.run(harness.audit_store.all_entries())
    actions = {e.action for e in entries}
    assert "identity.invitation.created" in actions
    assert "identity.invitation.accepted" in actions
    assert asyncio.run(verify_chain()) is True
