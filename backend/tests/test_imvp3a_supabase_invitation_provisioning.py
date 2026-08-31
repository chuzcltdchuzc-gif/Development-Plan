"""IMVP-3A — Supabase invitation-provisioning bridge.

Closes the gap the IMVP-3A governance authorization named explicitly:
`AuthService.accept_invitation()` was Keycloak-specific and had no way to
attach an already-verified Supabase subject to a new LandVault identity
without minting a Keycloak account for it. `AuthService.
accept_invitation_supabase()` (app.contexts.identity.application.
auth_service) reuses the same provider-neutral invitation-validation and
provisioning core `accept_invitation` uses; only where identity_subject/
email come from differs (an already-verified Supabase JWT's own claims,
never the request body).

Uses its own harness (`_build_app`) rather than the shared
`tests.app_factory.build_test_app()` default, because production's PEP
verifier trusts Supabase exclusively (app.main) — these tests need a
verifier built against a fake Supabase JWKS, not Keycloak's, to accurately
reflect that. `build_test_app(supabase=...)` (added for this slice) does
exactly that while every other test file's call (no `supabase` arg) is
unaffected.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from app.contexts.identity.domain.invitation import Invitation
from app.contexts.identity.domain.tenant import Tenant
from app.contexts.identity.domain.user import User
from app.kernel.audit import verify_chain
from app.kernel.security.tokens import new_opaque_token
from tests.app_factory import AppHarness, build_test_app
from tests.fakes.supabase_jwks import FakeSupabase


@pytest.fixture
def supabase() -> FakeSupabase:
    return FakeSupabase()


@pytest.fixture
def harness(supabase: FakeSupabase) -> AppHarness:
    return build_test_app(supabase=supabase)


@pytest.fixture
def client(harness: AppHarness) -> TestClient:
    return TestClient(harness.app)


def _new_subject() -> str:
    return str(uuid.uuid4())


async def _seed_governance_inviter(
    harness: AppHarness, supabase: FakeSupabase, *, email: str, role: str
) -> tuple[str, User]:
    """A governance-role user, provisioned directly (not through any
    invitation flow — someone has to be tenant zero) and authenticated via a
    real (fake) Supabase-shaped token, matching production's Supabase-only
    identity model (ADR-025) rather than the historical Keycloak-seeded
    pattern the pre-IMVP-3A invitation tests use."""
    subject = _new_subject()
    user = User.new(identity_subject=subject, email=email, full_name="Inviter", country="NG")
    user.roles = [role]
    user = await harness.users.add(user)
    await harness.tenants.add(Tenant.new(name="Inviter Tenant", tenant_id=user.tenant_id))
    access_token = supabase.issue(subject=subject, email=email)
    return access_token, user


def _create_invitation(
    client: TestClient, access_token: str, *, email: str, role: str
) -> Response:
    return client.post(
        "/v1/admin/invitations",
        json={"email": email, "role": role},
        headers={"Authorization": f"Bearer {access_token}"},
    )


def _accept_supabase(
    client: TestClient,
    access_token: str,
    *,
    body: dict,
) -> Response:
    return client.post(
        "/v1/auth/invitations/accept-supabase",
        json=body,
        headers={"Authorization": f"Bearer {access_token}"},
    )


# 1. Valid Supabase identity + valid invitation -> success -----------------

def test_valid_identity_and_invitation_succeeds(
    harness: AppHarness, client: TestClient, supabase: FakeSupabase
) -> None:
    inviter_token, officer = asyncio.run(
        _seed_governance_inviter(
            harness, supabase, email="officer@example.test", role="compliance_officer"
        )
    )
    invite = _create_invitation(
        client, inviter_token, email="invitee@example.test", role="field_agent"
    ).json()

    invitee_subject = _new_subject()
    invitee_token = supabase.issue(subject=invitee_subject, email="invitee@example.test")
    response = _accept_supabase(
        client, invitee_token, body={"token": invite["token"], "full_name": "New Hire"}
    )
    assert response.status_code == 201, response.text
    body = response.json()["user"]
    assert body["tenant_id"] == officer.tenant_id
    assert body["roles"] == ["field_agent"]
    assert body["email"] == "invitee@example.test"

    stored = asyncio.run(harness.users.get_by_identity_subject(invitee_subject))
    assert stored is not None
    assert stored.tenant_id == officer.tenant_id
    assert stored.roles == ["field_agent"]


# 2. Valid Supabase identity + no invitation -> authenticated but unauthorized

def test_valid_identity_without_invitation_is_authenticated_but_unauthorized(
    harness: AppHarness, client: TestClient, supabase: FakeSupabase
) -> None:
    token = supabase.issue(subject=_new_subject(), email="nobody@example.test")

    me = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["roles"] == []
    assert me.json()["tenant_id"] is None

    denied = client.get(
        "/v1/test/governance-only", headers={"Authorization": f"Bearer {token}"}
    )
    assert denied.status_code == 403


# 3. Wrong authenticated email -> invitation denied -------------------------

def test_wrong_authenticated_email_denies_acceptance(
    harness: AppHarness, client: TestClient, supabase: FakeSupabase
) -> None:
    inviter_token, _officer = asyncio.run(
        _seed_governance_inviter(
            harness, supabase, email="officer2@example.test", role="compliance_officer"
        )
    )
    invite = _create_invitation(
        client, inviter_token, email="person-a@example.test", role="field_agent"
    ).json()

    wrong_token = supabase.issue(subject=_new_subject(), email="person-b@example.test")
    response = _accept_supabase(
        client, wrong_token, body={"token": invite["token"], "full_name": "Person B"}
    )
    assert response.status_code == 401

    reloaded = asyncio.run(harness.invitations.get(invite["invitation_id"]))
    assert reloaded is not None
    assert reloaded.status == "PENDING"  # untouched — still redeemable by person-a


# 4. Cannot supply another identity_subject ----------------------------------

def test_cannot_supply_alternate_identity_subject(
    harness: AppHarness, client: TestClient, supabase: FakeSupabase
) -> None:
    inviter_token, _officer = asyncio.run(
        _seed_governance_inviter(
            harness, supabase, email="officer3@example.test", role="compliance_officer"
        )
    )
    invite = _create_invitation(
        client, inviter_token, email="invitee4@example.test", role="field_agent"
    ).json()

    invitee_token = supabase.issue(subject=_new_subject(), email="invitee4@example.test")
    response = _accept_supabase(
        client,
        invitee_token,
        body={
            "token": invite["token"],
            "full_name": "Invitee Four",
            "identity_subject": "attacker-controlled-subject",
        },
    )
    assert response.status_code == 422  # extra="forbid" — rejected outright, not ignored


# 5. Cannot substitute another tenant ----------------------------------------

def test_cannot_supply_alternate_tenant(
    harness: AppHarness, client: TestClient, supabase: FakeSupabase
) -> None:
    inviter_token, _officer = asyncio.run(
        _seed_governance_inviter(
            harness, supabase, email="officer5@example.test", role="compliance_officer"
        )
    )
    invite = _create_invitation(
        client, inviter_token, email="invitee5@example.test", role="field_agent"
    ).json()

    invitee_token = supabase.issue(subject=_new_subject(), email="invitee5@example.test")
    response = _accept_supabase(
        client,
        invitee_token,
        body={
            "token": invite["token"],
            "full_name": "Invitee Five",
            "tenant_id": "some-other-tenant",
        },
    )
    assert response.status_code == 422


# 6. Cannot substitute another role ------------------------------------------

def test_cannot_supply_alternate_role(
    harness: AppHarness, client: TestClient, supabase: FakeSupabase
) -> None:
    inviter_token, _officer = asyncio.run(
        _seed_governance_inviter(
            harness, supabase, email="officer6@example.test", role="compliance_officer"
        )
    )
    invite = _create_invitation(
        client, inviter_token, email="invitee6@example.test", role="field_agent"
    ).json()

    invitee_token = supabase.issue(subject=_new_subject(), email="invitee6@example.test")
    response = _accept_supabase(
        client,
        invitee_token,
        body={"token": invite["token"], "full_name": "Invitee Six", "role": "super_admin"},
    )
    assert response.status_code == 422


# 7. Expired invitation -> denied --------------------------------------------

def test_expired_invitation_denied(
    harness: AppHarness, client: TestClient, supabase: FakeSupabase
) -> None:
    _inviter_token, officer = asyncio.run(
        _seed_governance_inviter(
            harness, supabase, email="officer7@example.test", role="compliance_officer"
        )
    )
    _plaintext_token, token_hash = new_opaque_token()
    expired = Invitation.new(
        tenant_id=officer.tenant_id,
        invited_email="invitee7@example.test",
        role="field_agent",
        invited_by=officer.user_id,
        token_hash=token_hash,
        expires_at=(datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
    )
    asyncio.run(harness.invitations.add(expired))

    invitee_token = supabase.issue(subject=_new_subject(), email="invitee7@example.test")
    response = _accept_supabase(
        client, invitee_token, body={"token": _plaintext_token, "full_name": "X"}
    )
    assert response.status_code == 401


# 8 & 9. Consumed invitation / duplicate acceptance -> denied, safely -------

def test_duplicate_acceptance_safely_denied(
    harness: AppHarness, client: TestClient, supabase: FakeSupabase
) -> None:
    inviter_token, _officer = asyncio.run(
        _seed_governance_inviter(
            harness, supabase, email="officer8@example.test", role="compliance_officer"
        )
    )
    invite = _create_invitation(
        client, inviter_token, email="invitee8@example.test", role="field_agent"
    ).json()

    invitee_token = supabase.issue(subject=_new_subject(), email="invitee8@example.test")
    body = {"token": invite["token"], "full_name": "Invitee Eight"}
    first = _accept_supabase(client, invitee_token, body=body)
    assert first.status_code == 201

    second = _accept_supabase(client, invitee_token, body=body)
    assert second.status_code == 401  # same generic denial as an unknown/expired token

    # Exactly one user exists for the inviter and one for the invitee — the
    # second (rejected) attempt did not create a duplicate.
    assert len(harness.users._by_id) == 2  # inviter + the one invitee


# 10. Duplicate external subject already mapped -> protected ----------------
#
# Once a subject is provisioned and active, the PEP's context hydrator
# (app.contexts.identity.context_hydration — existing B1 behavior, not
# introduced by IMVP-3A) resolves ctx.principal_id/ctx.email to that user's
# INTERNAL id and CURRENT email on every subsequent request, not the raw
# JWT claims — so a second acceptance attempt by an active, already-
# provisioned subject is already caught by the pre-existing email-mismatch
# path (test 3) before it would ever reach the identity_subject check. The
# scenario where identity_already_provisioned is the one that actually
# fires is a SUSPENDED user: hydration then returns None (can_authenticate()
# is false), so the PEP falls back to the raw subject/claims email again —
# exactly the case this check exists to close: a suspended user's still
# cryptographically-valid Supabase token must not be usable to acquire a
# brand-new LandVault identity/tenant/role via a second invitation, even one
# issued to a different email that the (suspended) email-registered check
# alone would not catch.

def test_duplicate_external_subject_protected(
    harness: AppHarness, client: TestClient, supabase: FakeSupabase
) -> None:
    inviter_token, officer = asyncio.run(
        _seed_governance_inviter(
            harness, supabase, email="officer10@example.test", role="compliance_officer"
        )
    )
    invite_one = _create_invitation(
        client, inviter_token, email="invitee10a@example.test", role="field_agent"
    ).json()

    subject = _new_subject()
    token_a = supabase.issue(subject=subject, email="invitee10a@example.test")
    first = _accept_supabase(
        client, token_a, body={"token": invite_one["token"], "full_name": "Invitee Ten"}
    )
    assert first.status_code == 201

    async def _suspend() -> None:
        provisioned = await harness.users.get_by_identity_subject(subject)
        assert provisioned is not None
        provisioned.suspend(reason="test")
        await harness.users.update(provisioned, expected_version=provisioned.version)

    asyncio.run(_suspend())

    invite_two = _create_invitation(
        client, inviter_token, email="invitee10b@example.test", role="surveyor_partner"
    ).json()
    token_b = supabase.issue(subject=subject, email="invitee10b@example.test")
    second = _accept_supabase(
        client, token_b, body={"token": invite_two["token"], "full_name": "Invitee Ten"}
    )
    assert second.status_code == 409

    stored = asyncio.run(harness.users.get_by_identity_subject(subject))
    assert stored is not None
    assert stored.roles == ["field_agent"]  # unchanged by the rejected second attempt
    assert stored.tenant_id == officer.tenant_id


# 11. Cross-tenant escalation impossible -------------------------------------

def test_cross_tenant_listing_denied(
    harness: AppHarness, client: TestClient, supabase: FakeSupabase
) -> None:
    inviter_a_token, _officer_a = asyncio.run(
        _seed_governance_inviter(
            harness, supabase, email="officer-a11@example.test", role="compliance_officer"
        )
    )
    inviter_b_token, _officer_b = asyncio.run(
        _seed_governance_inviter(
            harness, supabase, email="officer-b11@example.test", role="compliance_officer"
        )
    )
    _create_invitation(
        client, inviter_a_token, email="a-member@example.test", role="field_agent"
    )
    _create_invitation(
        client, inviter_b_token, email="b-member@example.test", role="field_agent"
    )

    # Provision a governance-role member INTO tenant A via the new Supabase
    # path, so they can legitimately call the tenant-scoped admin listing —
    # proving cross-tenant isolation holds for identities created through
    # this new path, not just the pre-existing Keycloak one.
    invite_a_officer = _create_invitation(
        client, inviter_a_token, email="a-officer2@example.test", role="compliance_officer"
    ).json()
    a_officer_token = supabase.issue(subject=_new_subject(), email="a-officer2@example.test")
    accepted = _accept_supabase(
        client,
        a_officer_token,
        body={"token": invite_a_officer["token"], "full_name": "A Officer 2"},
    )
    assert accepted.status_code == 201

    listing = client.get(
        "/v1/admin/invitations", headers={"Authorization": f"Bearer {a_officer_token}"}
    )
    assert listing.status_code == 200, listing.text
    emails = {inv["email"] for inv in listing.json()}
    assert "b-member@example.test" not in emails
    assert "a-member@example.test" in emails


# 12. Audit event recorded using the internal LandVault user identity -------

def test_provisioning_audited_with_internal_identity(
    harness: AppHarness, client: TestClient, supabase: FakeSupabase
) -> None:
    inviter_token, _officer = asyncio.run(
        _seed_governance_inviter(
            harness, supabase, email="officer12@example.test", role="compliance_officer"
        )
    )
    invite = _create_invitation(
        client, inviter_token, email="invitee12@example.test", role="field_agent"
    ).json()

    invitee_subject = _new_subject()
    invitee_token = supabase.issue(subject=invitee_subject, email="invitee12@example.test")
    response = _accept_supabase(
        client, invitee_token, body={"token": invite["token"], "full_name": "Invitee Twelve"}
    )
    assert response.status_code == 201
    internal_user_id = response.json()["user"]["user_id"]
    assert internal_user_id != invitee_subject  # internal id, not the raw external subject

    entries = asyncio.run(harness.audit_store.all_entries())
    registered = [e for e in entries if e.action == "identity.user.registered"]
    accepted_events = [e for e in entries if e.action == "identity.invitation.accepted"]
    assert len(registered) == 1
    assert registered[0].resource_id == internal_user_id  # internal id, never the raw sub
    assert len(accepted_events) == 1
    assert accepted_events[0].payload["user_id"] == internal_user_id
    assert asyncio.run(verify_chain()) is True
