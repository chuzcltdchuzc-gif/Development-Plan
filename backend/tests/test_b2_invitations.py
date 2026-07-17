"""B2 — tenant membership invitations (docs/adr/ADR-009's "tenant
provisioning" gap, docs/REBUILD_PLAN.md's B2 row). Slice 1: create + accept.
Slice 2: listing, revocation, and redemption-time authority re-validation
(closing the "inviter loses authority after issuing the invite, before it's
redeemed" gap). Real business logic throughout; Keycloak and Postgres are
swapped for in-memory fakes at the port boundary (tests/app_factory.py,
tests/fakes/), same as the B1 acceptance suite.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from app.contexts.identity.domain.invitation import Invitation
from app.contexts.identity.domain.user import User
from app.contexts.identity.ports import IdentityProviderTokens
from app.kernel.audit import verify_chain
from app.kernel.security.tokens import new_opaque_token
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


# ---- Slice 2: listing, revocation, redemption-time authority re-check --------

def _list_invitations(client: TestClient, access_token: str) -> Response:
    return client.get(
        "/v1/admin/invitations", headers={"Authorization": f"Bearer {access_token}"}
    )


def _revoke_invitation(client: TestClient, access_token: str, invitation_id: str) -> Response:
    return client.post(
        f"/v1/admin/invitations/{invitation_id}/revoke",
        headers={"Authorization": f"Bearer {access_token}"},
    )


# 9. Listing returns only the caller's own tenant's invitations -----------------

def test_listing_returns_only_same_tenant_invitations(
    harness: AppHarness, client: TestClient
) -> None:
    tokens_a, _ = asyncio.run(
        _seed_user_with_role(
            harness, email="officer-a@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    tokens_b, _ = asyncio.run(
        _seed_user_with_role(
            harness, email="officer-b@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    _create_invitation(
        client, tokens_a.access_token, email="a-invitee@example.test", role="field_agent"
    )
    _create_invitation(
        client, tokens_b.access_token, email="b-invitee@example.test", role="field_agent"
    )

    response = _list_invitations(client, tokens_a.access_token)
    assert response.status_code == 200, response.text
    emails = {inv["email"] for inv in response.json()}
    assert emails == {"a-invitee@example.test"}


# 10. Revocation blocks subsequent redemption ------------------------------------

def test_revoke_blocks_redemption(harness: AppHarness, client: TestClient) -> None:
    idp_tokens, _officer = asyncio.run(
        _seed_user_with_role(
            harness, email="officer7@example.test", password="pw12345678", role="compliance_officer"
        )
    )
    invite = _create_invitation(
        client, idp_tokens.access_token, email="newhire7@example.test", role="field_agent"
    ).json()

    revoke_response = _revoke_invitation(client, idp_tokens.access_token, invite["invitation_id"])
    assert revoke_response.status_code == 200, revoke_response.text
    assert revoke_response.json()["status"] == "REVOKED"

    accept_response = client.post(
        "/v1/auth/invitations/accept",
        json={"token": invite["token"], "password": "correct-horse-battery", "full_name": "X"},
    )
    assert accept_response.status_code == 401


# 11. Revoking a non-pending invitation conflicts --------------------------------

def test_revoke_non_pending_invitation_conflicts(harness: AppHarness, client: TestClient) -> None:
    idp_tokens, _officer = asyncio.run(
        _seed_user_with_role(
            harness, email="officer8@example.test", password="pw12345678", role="compliance_officer"
        )
    )
    invite = _create_invitation(
        client, idp_tokens.access_token, email="newhire8@example.test", role="field_agent"
    ).json()

    first_revoke = _revoke_invitation(client, idp_tokens.access_token, invite["invitation_id"])
    assert first_revoke.status_code == 200

    second_revoke = _revoke_invitation(client, idp_tokens.access_token, invite["invitation_id"])
    assert second_revoke.status_code == 409


# 12. Revoking an unknown or cross-tenant invitation id returns 404 -------------

def test_revoke_unknown_invitation_returns_404(harness: AppHarness, client: TestClient) -> None:
    idp_tokens, _officer = asyncio.run(
        _seed_user_with_role(
            harness, email="officer9@example.test", password="pw12345678", role="compliance_officer"
        )
    )
    response = _revoke_invitation(
        client, idp_tokens.access_token, "00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


# 13. An expired invitation is rejected at redemption ---------------------------

def test_expired_invitation_rejected(harness: AppHarness, client: TestClient) -> None:
    idp_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="officer10@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    plaintext_token, token_hash = new_opaque_token()
    expired = Invitation.new(
        tenant_id=officer.tenant_id,
        invited_email="expired-invitee@example.test",
        role="field_agent",
        invited_by=officer.user_id,
        token_hash=token_hash,
        expires_at=(datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
    )
    asyncio.run(harness.invitations.add(expired))

    response = client.post(
        "/v1/auth/invitations/accept",
        json={"token": plaintext_token, "password": "correct-horse-battery", "full_name": "X"},
    )
    assert response.status_code == 401


# 14. Authority-loss scenario: inviter demoted below the invited role's rank
# after issuing the invitation, before it's redeemed -- the exact scenario
# this slice exists to close (an invitation must not silently outlive the
# authority that issued it).

def test_redemption_denied_after_inviter_demoted(harness: AppHarness, client: TestClient) -> None:
    idp_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="officer11@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    invite = _create_invitation(
        client, idp_tokens.access_token, email="newhire11@example.test", role="field_agent"
    ).json()

    async def _demote() -> None:
        current = await harness.users.get(officer.user_id)
        assert current is not None
        current.roles = ["general_user"]
        await harness.users.update(current, expected_version=current.version)

    asyncio.run(_demote())

    response = client.post(
        "/v1/auth/invitations/accept",
        json={"token": invite["token"], "password": "correct-horse-battery", "full_name": "X"},
    )
    assert response.status_code == 401

    # The invitation itself is left in a terminal REVOKED state, not still
    # PENDING and retryable if the inviter's authority is later restored.
    reloaded = asyncio.run(harness.invitations.get(invite["invitation_id"]))
    assert reloaded is not None
    assert reloaded.status == "REVOKED"


# 15. Authority-loss scenario: inviter's account suspended after issuing the
# invitation, before it's redeemed.

def test_redemption_denied_after_inviter_suspended(harness: AppHarness, client: TestClient) -> None:
    idp_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="officer12@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    invite = _create_invitation(
        client, idp_tokens.access_token, email="newhire12@example.test", role="field_agent"
    ).json()

    async def _suspend() -> None:
        current = await harness.users.get(officer.user_id)
        assert current is not None
        current.suspend(reason="test")
        await harness.users.update(current, expected_version=current.version)

    asyncio.run(_suspend())

    response = client.post(
        "/v1/auth/invitations/accept",
        json={"token": invite["token"], "password": "correct-horse-battery", "full_name": "X"},
    )
    assert response.status_code == 401


# 16. Revocation and authority-loss denials are audited, and the hash chain
# still verifies.

def test_revocation_and_authority_loss_audited(harness: AppHarness, client: TestClient) -> None:
    idp_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="officer13@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    invite = _create_invitation(
        client, idp_tokens.access_token, email="newhire13@example.test", role="field_agent"
    ).json()
    _revoke_invitation(client, idp_tokens.access_token, invite["invitation_id"])
    client.post(
        "/v1/auth/invitations/accept",
        json={"token": invite["token"], "password": "correct-horse-battery", "full_name": "X"},
    )

    entries = asyncio.run(harness.audit_store.all_entries())
    actions = {e.action for e in entries}
    assert "identity.invitation.revoked" in actions
    assert "identity.invitation.redemption_denied" in actions
    assert asyncio.run(verify_chain()) is True
