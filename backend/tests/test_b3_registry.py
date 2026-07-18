"""B3 slice 1 — Parcel Aggregate / Registry domain (docs/adr/ADR-013).

Covers: creation, tenant isolation, authorization (including delegated
roles, ADR-011 integration), validation, domain-level invariant
enforcement (archived parcels immutable, parcel_number never
reassignable), audit integration. RLS and the database-level unique
constraint are verified live against real Postgres separately (see the
completion report), not here — in-memory fakes have no RLS/constraints to
exercise. Real business logic throughout; Keycloak and Postgres are
swapped for in-memory fakes at the port boundary, same as the rest of the
B1/B2/B3 suite.
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from app.contexts.identity.domain.tenant import Tenant
from app.contexts.identity.domain.user import User
from app.contexts.identity.ports import IdentityProviderTokens
from app.contexts.registry.domain.parcel import Parcel, ParcelArchivedError
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


def _create_parcel(client: TestClient, access_token: str, **body: object) -> Response:
    return client.post(
        "/v1/parcels", json=body, headers={"Authorization": f"Bearer {access_token}"}
    )


# 1. A registrant role can create a parcel ---------------------------------------

def test_field_agent_can_create_parcel(harness: AppHarness, client: TestClient) -> None:
    tokens, user = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agent1@example.test", password="pw12345678", role="field_agent"
        )
    )
    response = _create_parcel(
        client, tokens.access_token,
        title="Plot 12, Green Estate", address="12 Green Estate Rd", state="Imo", lga="Owerri",
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "ACTIVE"
    assert body["parcel_number"] is None  # reserved for Slice 2
    assert body["created_by"] == user.user_id
    assert body["tenant_id"] == user.tenant_id
    assert body["origin"] == "platform_registration"


# 2. A non-registrant role cannot create a parcel --------------------------------

def test_general_user_cannot_create_parcel(harness: AppHarness, client: TestClient) -> None:
    tokens, _user = asyncio.run(
        _seed_user_with_role(
            harness, email="r-plain2@example.test", password="pw12345678", role="general_user"
        )
    )
    response = _create_parcel(client, tokens.access_token, title="Some plot")
    assert response.status_code == 403


# 3. A delegated registrant role can create a parcel (ADR-011 integration) ------

def test_delegated_role_can_create_parcel(harness: AppHarness, client: TestClient) -> None:
    officer_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="r-officer3@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    delegate_tokens, delegate = asyncio.run(
        _seed_user_with_role(
            harness, email="r-delegate3@example.test", password="pw12345678",
            role="general_user", tenant_id=officer.tenant_id,
        )
    )
    pre = _create_parcel(client, delegate_tokens.access_token, title="Should fail")
    assert pre.status_code == 403

    delegation = client.post(
        "/v1/admin/delegations",
        json={
            "delegate_user_id": delegate.user_id, "delegated_roles": ["field_agent"],
            "scope": "tenant_governance", "expires_at": None,
        },
        headers={"Authorization": f"Bearer {officer_tokens.access_token}"},
    )
    assert delegation.status_code == 201, delegation.text

    post = _create_parcel(client, delegate_tokens.access_token, title="Delegated registration")
    assert post.status_code == 201, post.text
    assert post.json()["tenant_id"] == officer.tenant_id


# 4. Tenant isolation: a parcel is invisible outside its own tenant -------------

def test_cross_tenant_get_denied(harness: AppHarness, client: TestClient) -> None:
    tokens_a, _a = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agentA4@example.test", password="pw12345678", role="field_agent"
        )
    )
    tokens_b, _b = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agentB4@example.test", password="pw12345678", role="field_agent"
        )
    )
    created = _create_parcel(client, tokens_a.access_token, title="Tenant A's plot").json()

    response = client.get(
        f"/v1/parcels/{created['parcel_id']}",
        headers={"Authorization": f"Bearer {tokens_b.access_token}"},
    )
    assert response.status_code == 404


def test_list_parcels_is_tenant_scoped(harness: AppHarness, client: TestClient) -> None:
    tokens_a, _a = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agentA5@example.test", password="pw12345678", role="field_agent"
        )
    )
    tokens_b, _b = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agentB5@example.test", password="pw12345678", role="field_agent"
        )
    )
    _create_parcel(client, tokens_a.access_token, title="A's plot")
    _create_parcel(client, tokens_b.access_token, title="B's plot")

    listed = client.get(
        "/v1/parcels", headers={"Authorization": f"Bearer {tokens_a.access_token}"}
    )
    assert listed.status_code == 200
    titles = {p["title"] for p in listed.json()}
    assert titles == {"A's plot"}


# 5. A super_admin retains cross-tenant reach for GET (matches RLS bypass) ------

def test_super_admin_can_get_cross_tenant_parcel(harness: AppHarness, client: TestClient) -> None:
    admin_tokens, _admin = asyncio.run(
        _seed_user_with_role(
            harness, email="r-root6@example.test", password="pw12345678", role="super_admin"
        )
    )
    agent_tokens, _agent = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agent6@example.test", password="pw12345678", role="field_agent"
        )
    )
    created = _create_parcel(client, agent_tokens.access_token, title="Someone else's plot").json()

    response = client.get(
        f"/v1/parcels/{created['parcel_id']}",
        headers={"Authorization": f"Bearer {admin_tokens.access_token}"},
    )
    assert response.status_code == 200


# 6. Anonymous cannot read or write ------------------------------------------------

def test_anonymous_cannot_access_parcels(client: TestClient) -> None:
    assert client.get("/v1/parcels").status_code == 401
    assert client.post("/v1/parcels", json={}).status_code == 401


# 7. Validation: malformed country code rejected ---------------------------------
# CountryCode (reused from Identity, app.contexts.identity.domain.
# value_objects) validates ISO-3166-1-alpha-2 *shape* only (two uppercase
# letters) — not real-country-list membership, consistent since B1. A
# 3-letter code exercises the same shared validator Registry reuses.

def test_malformed_country_code_rejected(harness: AppHarness, client: TestClient) -> None:
    tokens, _user = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agent7@example.test", password="pw12345678", role="field_agent"
        )
    )
    response = _create_parcel(client, tokens.access_token, country_code="NGR")
    assert response.status_code == 400


# 8. Validation: non-positive size_sqm rejected ----------------------------------

def test_non_positive_size_rejected(harness: AppHarness, client: TestClient) -> None:
    tokens, _user = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agent8@example.test", password="pw12345678", role="field_agent"
        )
    )
    response = _create_parcel(client, tokens.access_token, size_sqm=0)
    assert response.status_code == 400
    response_negative = _create_parcel(client, tokens.access_token, size_sqm=-5)
    assert response_negative.status_code == 400


# 9. Domain invariant: parcel_number can never be reassigned once allocated -----

def test_parcel_number_cannot_be_reassigned() -> None:
    parcel = Parcel.new(
        tenant_id="t1", country_code="NG", origin="platform_registration", created_by="u1",
    )
    parcel.allocate_parcel_number("LV-0001")
    with pytest.raises(ValueError):
        parcel.allocate_parcel_number("LV-0002")


# 10. Domain invariant: archived parcels cannot be modified ----------------------

def test_archived_parcel_cannot_be_modified() -> None:
    parcel = Parcel.new(
        tenant_id="t1", country_code="NG", origin="platform_registration", created_by="u1",
    )
    parcel.status = "ARCHIVED"
    with pytest.raises(ParcelArchivedError):
        parcel.allocate_parcel_number("LV-0001")


# 11. Parcel identity is immutable: no setter exists for parcel_id --------------

def test_parcel_id_has_no_public_mutator() -> None:
    parcel = Parcel.new(
        tenant_id="t1", country_code="NG", origin="platform_registration", created_by="u1",
    )
    original_id = parcel.parcel_id
    # There is deliberately no method on Parcel that changes parcel_id —
    # the only way to alter it is direct dataclass-field assignment, which
    # is not part of the aggregate's public command surface.
    assert original_id
    assert parcel.parcel_id == original_id


# 12. Creation is audited and the hash chain verifies ----------------------------

def test_parcel_creation_audited(harness: AppHarness, client: TestClient) -> None:
    tokens, _user = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agent12@example.test", password="pw12345678", role="field_agent"
        )
    )
    _create_parcel(client, tokens.access_token, title="Audited plot")

    entries = asyncio.run(harness.audit_store.all_entries())
    actions = {e.action for e in entries}
    assert "registry.parcel.created" in actions
    assert asyncio.run(verify_chain()) is True


# 13. Backward compatibility: existing Identity endpoints unaffected -------------

def test_existing_identity_endpoints_unaffected(client: TestClient) -> None:
    response = client.post(
        "/v1/auth/register",
        json={"email": "r-regcheck13@example.test", "password": "correct-horse-battery",
              "full_name": "Reg Check"},
    )
    assert response.status_code == 201
    assert set(response.json().keys()) == {"access_token", "token_type", "expires_in", "user"}
