"""B2 slice 3 — Tenant/Organization aggregate (docs/adr/ADR-010).

Covers: lifecycle (suspend/reactivate/archive), super_admin-only authority
over lifecycle mutations, fail-closed lockout of an ALREADY-ISSUED access
token the moment its tenant is suspended (not just on next login), login
and invitation-redemption denial for a suspended/archived target tenant,
and backward compatibility of the existing register/login response shapes.
Real business logic throughout; Keycloak and Postgres are swapped for
in-memory fakes at the port boundary (tests/app_factory.py, tests/fakes/).
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from app.contexts.identity.domain.tenant import Tenant
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
    await harness.tenants.add(Tenant.new(name="Seed Tenant", tenant_id=user.tenant_id))
    idp_tokens = await harness.identity_provider.authenticate(email=email, password=password)
    return idp_tokens, user


def _register(client: TestClient, email: str, password: str = "correct-horse-battery") -> dict:
    response = client.post(
        "/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Real User"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _suspend(
    client: TestClient, access_token: str, tenant_id: str, reason: str = "test"
) -> Response:
    return client.post(
        f"/v1/admin/tenants/{tenant_id}/suspend",
        json={"reason": reason},
        headers={"Authorization": f"Bearer {access_token}"},
    )


# 1. Self-registration creates an ACTIVE tenant owned by the new user ----------

def test_register_creates_active_tenant_with_owner(client: TestClient) -> None:
    tokens = _register(client, "founder@example.test")
    user = tokens["user"]

    me_tenant = client.get(
        "/v1/auth/me/tenant", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me_tenant.status_code == 200, me_tenant.text
    body = me_tenant.json()
    assert body["tenant_id"] == user["tenant_id"]
    assert body["status"] == "ACTIVE"
    assert body["owner_user_id"] == user["user_id"]


# 2. Existing response shapes are unchanged (backward compatibility) ----------

def test_register_response_shape_unchanged(client: TestClient) -> None:
    tokens = _register(client, "shape-check@example.test")
    assert set(tokens.keys()) == {"access_token", "token_type", "expires_in", "user"}
    assert isinstance(tokens["user"]["tenant_id"], str)


# 3. Only super_admin may suspend a tenant, not other governance roles ---------

def test_non_super_admin_cannot_suspend_tenant(harness: AppHarness, client: TestClient) -> None:
    idp_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="officer-t1@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    response = _suspend(client, idp_tokens.access_token, officer.tenant_id)
    assert response.status_code == 403


# 4. super_admin can suspend a tenant, and every member is locked out on their
# very next request, even with an access token issued before the suspension.

def test_suspend_locks_out_members_immediately(harness: AppHarness, client: TestClient) -> None:
    """The real security boundary a suspended tenant's already-issued token
    loses is *effective authorization* (require_role-gated routes, since
    hydration now returns empty roles), not `require_auth` itself.
    `ExecutionContext.is_anonymous` only checks the literal "anonymous"
    sentinel — a token whose hydration comes back empty still carries the
    raw IdP subject as its principal_id (frozen B1 behavior, ADR-009: "a
    valid Keycloak session with no local account yet" falls back the same
    way, on the documented reasoning that role-gated/PDP checks catch it).
    So `/v1/auth/me` alone doesn't demonstrate the lockout — a governance-
    gated route does.
    """
    admin_tokens, _admin = asyncio.run(
        _seed_user_with_role(
            harness, email="root-admin1@example.test", password="pw12345678", role="super_admin"
        )
    )
    officer_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="officer-t4@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )

    pre = client.get(
        "/v1/admin/invitations",
        headers={"Authorization": f"Bearer {officer_tokens.access_token}"},
    )
    assert pre.status_code == 200

    suspend_response = _suspend(client, admin_tokens.access_token, officer.tenant_id)
    assert suspend_response.status_code == 200, suspend_response.text
    assert suspend_response.json()["status"] == "SUSPENDED"

    # The SAME already-issued access token now hydrates with zero roles, so
    # the governance-gated route denies it — even though it was minted
    # before the tenant was suspended.
    post = client.get(
        "/v1/admin/invitations",
        headers={"Authorization": f"Bearer {officer_tokens.access_token}"},
    )
    assert post.status_code == 403


# 5. Reactivation restores access ------------------------------------------------

def test_reactivate_restores_access(harness: AppHarness, client: TestClient) -> None:
    admin_tokens, _admin = asyncio.run(
        _seed_user_with_role(
            harness, email="root-admin2@example.test", password="pw12345678", role="super_admin"
        )
    )
    officer_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="officer-t5x@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )

    _suspend(client, admin_tokens.access_token, officer.tenant_id)
    locked_out = client.get(
        "/v1/admin/invitations",
        headers={"Authorization": f"Bearer {officer_tokens.access_token}"},
    )
    assert locked_out.status_code == 403

    reactivate = client.post(
        f"/v1/admin/tenants/{officer.tenant_id}/reactivate",
        headers={"Authorization": f"Bearer {admin_tokens.access_token}"},
    )
    assert reactivate.status_code == 200, reactivate.text
    assert reactivate.json()["status"] == "ACTIVE"

    restored = client.get(
        "/v1/admin/invitations",
        headers={"Authorization": f"Bearer {officer_tokens.access_token}"},
    )
    assert restored.status_code == 200


# 6. Archive is terminal: cannot suspend or reactivate an archived tenant ------

def test_archive_is_terminal(harness: AppHarness, client: TestClient) -> None:
    admin_tokens, _admin = asyncio.run(
        _seed_user_with_role(
            harness, email="root-admin3@example.test", password="pw12345678", role="super_admin"
        )
    )
    member_tokens = _register(client, "member3@example.test")
    tenant_id = member_tokens["user"]["tenant_id"]

    archive = client.post(
        f"/v1/admin/tenants/{tenant_id}/archive",
        headers={"Authorization": f"Bearer {admin_tokens.access_token}"},
    )
    assert archive.status_code == 200, archive.text
    assert archive.json()["status"] == "ARCHIVED"

    reactivate_attempt = client.post(
        f"/v1/admin/tenants/{tenant_id}/reactivate",
        headers={"Authorization": f"Bearer {admin_tokens.access_token}"},
    )
    assert reactivate_attempt.status_code == 409

    suspend_attempt = _suspend(client, admin_tokens.access_token, tenant_id)
    assert suspend_attempt.status_code == 409


# 7. A fresh login attempt (not just an already-issued token) is also denied
# for a suspended tenant.

def test_login_denied_for_suspended_tenant(harness: AppHarness, client: TestClient) -> None:
    admin_tokens, _admin = asyncio.run(
        _seed_user_with_role(
            harness, email="root-admin4@example.test", password="pw12345678", role="super_admin"
        )
    )
    _register(client, "member4@example.test")
    login1 = client.post(
        "/v1/auth/login",
        json={"email": "member4@example.test", "password": "correct-horse-battery"},
    )
    tenant_id = login1.json()["user"]["tenant_id"]

    _suspend(client, admin_tokens.access_token, tenant_id)

    login2 = client.post(
        "/v1/auth/login",
        json={"email": "member4@example.test", "password": "correct-horse-battery"},
    )
    assert login2.status_code == 401


# 8. Invitation redemption is denied if the target tenant is suspended after
# the invitation was issued, and the invitation is durably revoked.

def test_invitation_redemption_denied_for_suspended_tenant(
    harness: AppHarness, client: TestClient
) -> None:
    admin_tokens, _admin = asyncio.run(
        _seed_user_with_role(
            harness, email="root-admin5@example.test", password="pw12345678", role="super_admin"
        )
    )
    officer_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="officer-t5@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    invite = client.post(
        "/v1/admin/invitations",
        json={"email": "newhire-t5@example.test", "role": "field_agent"},
        headers={"Authorization": f"Bearer {officer_tokens.access_token}"},
    ).json()

    _suspend(client, admin_tokens.access_token, officer.tenant_id)

    accept = client.post(
        "/v1/auth/invitations/accept",
        json={"token": invite["token"], "password": "correct-horse-battery", "full_name": "X"},
    )
    assert accept.status_code == 401

    reloaded = asyncio.run(harness.invitations.get(invite["invitation_id"]))
    assert reloaded is not None
    assert reloaded.status == "REVOKED"


# 9. Tenant listing/get are super_admin only ------------------------------------

def test_tenant_listing_and_get_are_super_admin_only(
    harness: AppHarness, client: TestClient
) -> None:
    officer_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="officer-t9@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    list_response = client.get(
        "/v1/admin/tenants", headers={"Authorization": f"Bearer {officer_tokens.access_token}"}
    )
    assert list_response.status_code == 403

    get_response = client.get(
        f"/v1/admin/tenants/{officer.tenant_id}",
        headers={"Authorization": f"Bearer {officer_tokens.access_token}"},
    )
    assert get_response.status_code == 403

    admin_tokens, _admin = asyncio.run(
        _seed_user_with_role(
            harness, email="root-admin9@example.test", password="pw12345678", role="super_admin"
        )
    )
    admin_list = client.get(
        "/v1/admin/tenants", headers={"Authorization": f"Bearer {admin_tokens.access_token}"}
    )
    assert admin_list.status_code == 200
    assert any(t["tenant_id"] == officer.tenant_id for t in admin_list.json())


# 10. Any authenticated user can see their OWN tenant --------------------------

def test_any_authenticated_user_can_see_own_tenant(client: TestClient) -> None:
    tokens = _register(client, "self-view@example.test")
    response = client.get(
        "/v1/auth/me/tenant", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 200
    assert response.json()["tenant_id"] == tokens["user"]["tenant_id"]


# 11. Tenant lifecycle actions are audited and the hash chain still verifies --

def test_tenant_lifecycle_audited(harness: AppHarness, client: TestClient) -> None:
    admin_tokens, _admin = asyncio.run(
        _seed_user_with_role(
            harness, email="root-admin11@example.test", password="pw12345678", role="super_admin"
        )
    )
    member_tokens = _register(client, "member11@example.test")
    tenant_id = member_tokens["user"]["tenant_id"]

    _suspend(client, admin_tokens.access_token, tenant_id)
    client.post(
        f"/v1/admin/tenants/{tenant_id}/reactivate",
        headers={"Authorization": f"Bearer {admin_tokens.access_token}"},
    )
    client.post(
        f"/v1/admin/tenants/{tenant_id}/archive",
        headers={"Authorization": f"Bearer {admin_tokens.access_token}"},
    )

    entries = asyncio.run(harness.audit_store.all_entries())
    actions = {e.action for e in entries}
    assert "identity.tenant.suspended" in actions
    assert "identity.tenant.reactivated" in actions
    assert "identity.tenant.archived" in actions
    assert asyncio.run(verify_chain()) is True
