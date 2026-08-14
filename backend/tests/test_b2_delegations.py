"""B2 slice 4 — delegated administration (docs/adr/ADR-011).

Delegation is derived authority: a delegate never has more effective
authority than their delegator currently holds, re-validated live on every
request (no caching, no grace period on revocation). Real business logic
throughout; Keycloak and Postgres are swapped for in-memory fakes at the
port boundary (tests/app_factory.py, tests/fakes/), same as the rest of
the B1/B2 suite. RLS itself is verified live against real Postgres
separately (see the completion report), not here — in-memory fakes have
no RLS to exercise.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from app.contexts.identity.domain.delegation import Delegation
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
    harness: AppHarness, *, email: str, password: str, role: str, tenant_id: str | None = None
) -> tuple[IdentityProviderTokens, User]:
    subject = await harness.identity_provider.create_user(
        email=email, password=password, full_name="Seed User"
    )
    user = User.new(
        keycloak_subject=subject, email=email, full_name="Seed User", country="NG",
        tenant_id=tenant_id,
    )
    user.roles = [role]
    user = await harness.users.add(user)
    if tenant_id is None:
        await harness.tenants.add(Tenant.new(name="Seed Tenant", tenant_id=user.tenant_id))
    idp_tokens = await harness.identity_provider.authenticate(email=email, password=password)
    return idp_tokens, user


def _create_delegation(
    client: TestClient,
    access_token: str,
    *,
    delegate_user_id: str,
    delegated_roles: list[str],
    scope: str = "tenant_governance",
    expires_at: str | None = None,
) -> Response:
    return client.post(
        "/v1/admin/delegations",
        json={
            "delegate_user_id": delegate_user_id,
            "delegated_roles": delegated_roles,
            "scope": scope,
            "expires_at": expires_at,
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )


def _revoke_delegation(client: TestClient, access_token: str, delegation_id: str) -> Response:
    return client.post(
        f"/v1/admin/delegations/{delegation_id}/revoke",
        headers={"Authorization": f"Bearer {access_token}"},
    )


def _can_list_invitations(client: TestClient, access_token: str) -> bool:
    r = client.get(
        "/v1/admin/invitations", headers={"Authorization": f"Bearer {access_token}"}
    )
    return r.status_code == 200


# 1. Same-tenant delegation grants the delegate a role-gated capability -------

def test_same_tenant_delegation_grants_role(harness: AppHarness, client: TestClient) -> None:
    officer_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="d-officer1@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    delegate_tokens, delegate = asyncio.run(
        _seed_user_with_role(
            harness, email="d-delegate1@example.test", password="pw12345678",
            role="general_user", tenant_id=officer.tenant_id,
        )
    )

    assert not _can_list_invitations(client, delegate_tokens.access_token)

    response = _create_delegation(
        client, officer_tokens.access_token,
        delegate_user_id=delegate.user_id, delegated_roles=["compliance_officer"],
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "ACTIVE"
    assert body["delegated_roles"] == ["compliance_officer"]

    assert _can_list_invitations(client, delegate_tokens.access_token)


# 2. Cross-tenant delegation is denied (target invisible, not merely forbidden)

def test_cross_tenant_delegation_denied(harness: AppHarness, client: TestClient) -> None:
    officer_tokens, _officer = asyncio.run(
        _seed_user_with_role(
            harness, email="d-officer2@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    _other_tokens, other_user = asyncio.run(
        _seed_user_with_role(
            harness, email="d-other2@example.test", password="pw12345678", role="general_user",
        )
    )

    response = _create_delegation(
        client, officer_tokens.access_token,
        delegate_user_id=other_user.user_id, delegated_roles=["general_user"],
    )
    assert response.status_code == 404


# 3. Hierarchy ceiling: cannot delegate a role higher than the delegator's own -

def test_hierarchy_ceiling_denied(harness: AppHarness, client: TestClient) -> None:
    officer_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="d-officer3@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    _delegate_tokens, delegate = asyncio.run(
        _seed_user_with_role(
            harness, email="d-delegate3@example.test", password="pw12345678",
            role="general_user", tenant_id=officer.tenant_id,
        )
    )
    response = _create_delegation(
        client, officer_tokens.access_token,
        delegate_user_id=delegate.user_id, delegated_roles=["super_admin"],
    )
    assert response.status_code == 403


# 4. Cannot delegate to yourself ------------------------------------------------

def test_cannot_delegate_to_self(harness: AppHarness, client: TestClient) -> None:
    officer_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="d-officer4@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    response = _create_delegation(
        client, officer_tokens.access_token,
        delegate_user_id=officer.user_id, delegated_roles=["general_user"],
    )
    assert response.status_code == 400


# 5. Non-governance principals cannot create delegations ------------------------

def test_non_governance_role_cannot_create_delegation(
    harness: AppHarness, client: TestClient
) -> None:
    plain_tokens, plain = asyncio.run(
        _seed_user_with_role(
            harness, email="d-plain5@example.test", password="pw12345678", role="general_user",
        )
    )
    _other_tokens, other_user = asyncio.run(
        _seed_user_with_role(
            harness, email="d-other5@example.test", password="pw12345678",
            role="general_user", tenant_id=plain.tenant_id,
        )
    )
    response = _create_delegation(
        client, plain_tokens.access_token,
        delegate_user_id=other_user.user_id, delegated_roles=["general_user"],
    )
    assert response.status_code == 403


# 6. An expired delegation no longer grants its role ----------------------------

def test_expired_delegation_not_effective(harness: AppHarness, client: TestClient) -> None:
    officer_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="d-officer6@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    delegate_tokens, delegate = asyncio.run(
        _seed_user_with_role(
            harness, email="d-delegate6@example.test", password="pw12345678",
            role="general_user", tenant_id=officer.tenant_id,
        )
    )
    expired = Delegation.new(
        tenant_id=officer.tenant_id,
        delegator_user_id=officer.user_id,
        delegate_user_id=delegate.user_id,
        delegated_roles=["compliance_officer"],
        scope="tenant_governance",
        expires_at=(datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
    )
    asyncio.run(harness.delegations.add(expired))

    assert not _can_list_invitations(client, delegate_tokens.access_token)


# 7. Revocation is immediate — no cached authorization, no replay --------------

def test_revoke_is_immediate_no_replay(harness: AppHarness, client: TestClient) -> None:
    officer_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="d-officer7@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    delegate_tokens, delegate = asyncio.run(
        _seed_user_with_role(
            harness, email="d-delegate7@example.test", password="pw12345678",
            role="general_user", tenant_id=officer.tenant_id,
        )
    )
    created = _create_delegation(
        client, officer_tokens.access_token,
        delegate_user_id=delegate.user_id, delegated_roles=["compliance_officer"],
    ).json()
    assert _can_list_invitations(client, delegate_tokens.access_token)

    revoke = _revoke_delegation(client, officer_tokens.access_token, created["delegation_id"])
    assert revoke.status_code == 200, revoke.text

    # The delegate's access token is unchanged and unexpired — the SAME
    # token that worked a moment ago must now be denied, immediately, on
    # its very next use. No cache, no grace period.
    assert not _can_list_invitations(client, delegate_tokens.access_token)
    # And replaying the same request again still denies it (not a one-off
    # fluke of timing).
    assert not _can_list_invitations(client, delegate_tokens.access_token)


# 8. Delegator suspended invalidates the delegation ------------------------------

def test_delegator_suspended_invalidates_delegation(
    harness: AppHarness, client: TestClient
) -> None:
    officer_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="d-officer8@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    delegate_tokens, delegate = asyncio.run(
        _seed_user_with_role(
            harness, email="d-delegate8@example.test", password="pw12345678",
            role="general_user", tenant_id=officer.tenant_id,
        )
    )
    _create_delegation(
        client, officer_tokens.access_token,
        delegate_user_id=delegate.user_id, delegated_roles=["compliance_officer"],
    )
    assert _can_list_invitations(client, delegate_tokens.access_token)

    async def _suspend_officer() -> None:
        current = await harness.users.get(officer.user_id)
        assert current is not None
        current.suspend(reason="test")
        await harness.users.update(current, expected_version=current.version)

    asyncio.run(_suspend_officer())

    assert not _can_list_invitations(client, delegate_tokens.access_token)


# 9. Delegator demoted below the delegated role's rank invalidates the delegation

def test_delegator_demoted_invalidates_delegation(harness: AppHarness, client: TestClient) -> None:
    officer_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="d-officer9@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    delegate_tokens, delegate = asyncio.run(
        _seed_user_with_role(
            harness, email="d-delegate9@example.test", password="pw12345678",
            role="general_user", tenant_id=officer.tenant_id,
        )
    )
    _create_delegation(
        client, officer_tokens.access_token,
        delegate_user_id=delegate.user_id, delegated_roles=["compliance_officer"],
    )
    assert _can_list_invitations(client, delegate_tokens.access_token)

    async def _demote_officer() -> None:
        current = await harness.users.get(officer.user_id)
        assert current is not None
        current.roles = ["general_user"]
        await harness.users.update(current, expected_version=current.version)

    asyncio.run(_demote_officer())

    assert not _can_list_invitations(client, delegate_tokens.access_token)


# 10. A suspended delegate cannot exercise a delegation (trivially, via the
# existing can_authenticate() gate — verified explicitly here anyway).

def test_suspended_delegate_locked_out(harness: AppHarness, client: TestClient) -> None:
    officer_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="d-officer10@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    delegate_tokens, delegate = asyncio.run(
        _seed_user_with_role(
            harness, email="d-delegate10@example.test", password="pw12345678",
            role="general_user", tenant_id=officer.tenant_id,
        )
    )
    _create_delegation(
        client, officer_tokens.access_token,
        delegate_user_id=delegate.user_id, delegated_roles=["compliance_officer"],
    )
    assert _can_list_invitations(client, delegate_tokens.access_token)

    async def _suspend_delegate() -> None:
        current = await harness.users.get(delegate.user_id)
        assert current is not None
        current.suspend(reason="test")
        await harness.users.update(current, expected_version=current.version)

    asyncio.run(_suspend_delegate())

    assert not _can_list_invitations(client, delegate_tokens.access_token)


# 11. Suspending the whole tenant invalidates every delegation in it ------------

def test_tenant_suspension_invalidates_delegations(harness: AppHarness, client: TestClient) -> None:
    admin_tokens, _admin = asyncio.run(
        _seed_user_with_role(
            harness, email="d-root11@example.test", password="pw12345678", role="super_admin"
        )
    )
    officer_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="d-officer11@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    delegate_tokens, delegate = asyncio.run(
        _seed_user_with_role(
            harness, email="d-delegate11@example.test", password="pw12345678",
            role="general_user", tenant_id=officer.tenant_id,
        )
    )
    _create_delegation(
        client, officer_tokens.access_token,
        delegate_user_id=delegate.user_id, delegated_roles=["compliance_officer"],
    )
    assert _can_list_invitations(client, delegate_tokens.access_token)

    suspend = client.post(
        f"/v1/admin/tenants/{officer.tenant_id}/suspend",
        json={"reason": "test"},
        headers={"Authorization": f"Bearer {admin_tokens.access_token}"},
    )
    assert suspend.status_code == 200

    assert not _can_list_invitations(client, delegate_tokens.access_token)


# 12. Archiving the tenant permanently invalidates delegations (terminal) ------

def test_archived_tenant_delegation_permanently_ineffective(
    harness: AppHarness, client: TestClient
) -> None:
    admin_tokens, _admin = asyncio.run(
        _seed_user_with_role(
            harness, email="d-root12@example.test", password="pw12345678", role="super_admin"
        )
    )
    officer_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="d-officer12@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    delegate_tokens, delegate = asyncio.run(
        _seed_user_with_role(
            harness, email="d-delegate12@example.test", password="pw12345678",
            role="general_user", tenant_id=officer.tenant_id,
        )
    )
    _create_delegation(
        client, officer_tokens.access_token,
        delegate_user_id=delegate.user_id, delegated_roles=["compliance_officer"],
    )

    archive = client.post(
        f"/v1/admin/tenants/{officer.tenant_id}/archive",
        headers={"Authorization": f"Bearer {admin_tokens.access_token}"},
    )
    assert archive.status_code == 200

    assert not _can_list_invitations(client, delegate_tokens.access_token)

    # Archived is terminal — the tenant cannot be reactivated to restore it.
    reactivate = client.post(
        f"/v1/admin/tenants/{officer.tenant_id}/reactivate",
        headers={"Authorization": f"Bearer {admin_tokens.access_token}"},
    )
    assert reactivate.status_code == 409


# 13. List/get show computed effective status -----------------------------------

def test_list_and_get_show_effective_status(harness: AppHarness, client: TestClient) -> None:
    officer_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="d-officer13@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    _delegate_tokens, delegate = asyncio.run(
        _seed_user_with_role(
            harness, email="d-delegate13@example.test", password="pw12345678",
            role="general_user", tenant_id=officer.tenant_id,
        )
    )
    # A separate super_admin observer — after the officer is demoted below,
    # the officer's OWN token also loses require_role access, so a
    # different, still-privileged caller is needed to actually observe the
    # post-demotion "effective": false state via the API.
    admin_tokens, _admin = asyncio.run(
        _seed_user_with_role(
            harness, email="d-root13@example.test", password="pw12345678", role="super_admin"
        )
    )
    created = _create_delegation(
        client, officer_tokens.access_token,
        delegate_user_id=delegate.user_id, delegated_roles=["compliance_officer"],
    ).json()

    listed = client.get(
        "/v1/admin/delegations", headers={"Authorization": f"Bearer {officer_tokens.access_token}"}
    )
    assert listed.status_code == 200
    match = next(d for d in listed.json() if d["delegation_id"] == created["delegation_id"])
    assert match["effective"] is True

    got = client.get(
        f"/v1/admin/delegations/{created['delegation_id']}",
        headers={"Authorization": f"Bearer {officer_tokens.access_token}"},
    )
    assert got.status_code == 200
    assert got.json()["effective"] is True

    # Demote the officer; the same delegation should now report ineffective.
    async def _demote() -> None:
        current = await harness.users.get(officer.user_id)
        assert current is not None
        current.roles = ["general_user"]
        await harness.users.update(current, expected_version=current.version)

    asyncio.run(_demote())

    got_after = client.get(
        f"/v1/admin/delegations/{created['delegation_id']}",
        headers={"Authorization": f"Bearer {admin_tokens.access_token}"},
    )
    assert got_after.status_code == 200, got_after.text
    assert got_after.json()["effective"] is False
    assert got_after.json()["ineffective_reason"] == "authority_lost"


# 14. Revoking a non-active delegation conflicts --------------------------------

def test_revoke_non_active_delegation_conflicts(harness: AppHarness, client: TestClient) -> None:
    officer_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="d-officer14@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    _delegate_tokens, delegate = asyncio.run(
        _seed_user_with_role(
            harness, email="d-delegate14@example.test", password="pw12345678",
            role="general_user", tenant_id=officer.tenant_id,
        )
    )
    created = _create_delegation(
        client, officer_tokens.access_token,
        delegate_user_id=delegate.user_id, delegated_roles=["compliance_officer"],
    ).json()
    first = _revoke_delegation(client, officer_tokens.access_token, created["delegation_id"])
    assert first.status_code == 200
    second = _revoke_delegation(client, officer_tokens.access_token, created["delegation_id"])
    assert second.status_code == 409


# 15. Revoking an unknown delegation returns 404 --------------------------------

def test_revoke_unknown_delegation_404(harness: AppHarness, client: TestClient) -> None:
    officer_tokens, _officer = asyncio.run(
        _seed_user_with_role(
            harness, email="d-officer15@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    response = _revoke_delegation(
        client, officer_tokens.access_token, "00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


# 16. Extending updates the expiry and re-validates the delegator's authority --

def test_extend_delegation(harness: AppHarness, client: TestClient) -> None:
    officer_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="d-officer16@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    _delegate_tokens, delegate = asyncio.run(
        _seed_user_with_role(
            harness, email="d-delegate16@example.test", password="pw12345678",
            role="general_user", tenant_id=officer.tenant_id,
        )
    )
    soon = (datetime.now(UTC) + timedelta(minutes=1)).isoformat()
    created = _create_delegation(
        client, officer_tokens.access_token,
        delegate_user_id=delegate.user_id, delegated_roles=["compliance_officer"],
        expires_at=soon,
    ).json()

    later = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    extend = client.post(
        f"/v1/admin/delegations/{created['delegation_id']}/extend",
        json={"expires_at": later},
        headers={"Authorization": f"Bearer {officer_tokens.access_token}"},
    )
    assert extend.status_code == 200, extend.text
    assert extend.json()["expires_at"] == later


# 17. Extend is denied if the ORIGINAL delegator has since lost authority,
# even when a DIFFERENT, still-fully-ranked governance principal is the one
# calling /extend — this isolates AdminService.extend_delegation's own
# re-check from the router's require_role gate (a demoted delegator would
# also fail require_role themselves, which wouldn't prove this specific
# check fires).

def test_extend_denied_if_original_delegator_lost_authority(
    harness: AppHarness, client: TestClient
) -> None:
    delegator_tokens, delegator = asyncio.run(
        _seed_user_with_role(
            harness, email="d-officer17a@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    other_officer_tokens, _other_officer = asyncio.run(
        _seed_user_with_role(
            harness, email="d-officer17b@example.test", password="pw12345678",
            role="compliance_officer", tenant_id=delegator.tenant_id,
        )
    )
    _delegate_tokens, delegate = asyncio.run(
        _seed_user_with_role(
            harness, email="d-delegate17@example.test", password="pw12345678",
            role="general_user", tenant_id=delegator.tenant_id,
        )
    )
    created = _create_delegation(
        client, delegator_tokens.access_token,
        delegate_user_id=delegate.user_id, delegated_roles=["compliance_officer"],
    ).json()

    async def _demote_original_delegator() -> None:
        current = await harness.users.get(delegator.user_id)
        assert current is not None
        current.roles = ["general_user"]
        await harness.users.update(current, expected_version=current.version)

    asyncio.run(_demote_original_delegator())

    # other_officer still has full compliance_officer rank and can still
    # reach the endpoint — but AdminService.extend_delegation re-checks the
    # ORIGINAL delegator's current rank, not the caller's, and denies.
    extend = client.post(
        f"/v1/admin/delegations/{created['delegation_id']}/extend",
        json={"expires_at": (datetime.now(UTC) + timedelta(days=1)).isoformat()},
        headers={"Authorization": f"Bearer {other_officer_tokens.access_token}"},
    )
    assert extend.status_code == 409


# 18. Delegation lifecycle is audited and the hash chain still verifies --------

def test_delegation_audit_events_and_chain_integrity(
    harness: AppHarness, client: TestClient
) -> None:
    officer_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="d-officer18@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    _delegate_tokens, delegate = asyncio.run(
        _seed_user_with_role(
            harness, email="d-delegate18@example.test", password="pw12345678",
            role="general_user", tenant_id=officer.tenant_id,
        )
    )
    created = _create_delegation(
        client, officer_tokens.access_token,
        delegate_user_id=delegate.user_id, delegated_roles=["compliance_officer"],
    ).json()
    client.get(
        f"/v1/admin/delegations/{created['delegation_id']}",
        headers={"Authorization": f"Bearer {officer_tokens.access_token}"},
    )
    _revoke_delegation(client, officer_tokens.access_token, created["delegation_id"])

    entries = asyncio.run(harness.audit_store.all_entries())
    actions = {e.action for e in entries}
    assert "identity.delegation.created" in actions
    assert "identity.delegation.revoked" in actions
    assert asyncio.run(verify_chain()) is True