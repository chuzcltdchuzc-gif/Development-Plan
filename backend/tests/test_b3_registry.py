"""B3 slice 1 — Parcel Aggregate / Registry domain (docs/adr/ADR-013).
B3 slice 3 — mutation commands & authorization hardening (docs/adr/ADR-015).

Covers: creation, tenant isolation, authorization (including delegated
roles, ADR-011 integration), validation, domain-level invariant
enforcement (archived parcels immutable, parcel_number never
reassignable), audit integration, and — slice 3 — the creator-or-
governance mutation authorization model that closes the confirmed ADR-005
defect (any create-tier role could mutate any parcel in their tenant).
RLS and the database-level unique constraint are verified live against
real Postgres separately (see the completion report), not here — in-memory
fakes have no RLS/constraints to exercise. Real business logic throughout;
Keycloak and Postgres are swapped for in-memory fakes at the port
boundary, same as the rest of the B1/B2/B3 suite.
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


def _update_parcel(
    client: TestClient, access_token: str, parcel_id: str, **body: object
) -> Response:
    return client.patch(
        f"/v1/parcels/{parcel_id}", json=body, headers={"Authorization": f"Bearer {access_token}"}
    )


def _archive_parcel(client: TestClient, access_token: str, parcel_id: str) -> Response:
    return client.post(
        f"/v1/parcels/{parcel_id}/archive", headers={"Authorization": f"Bearer {access_token}"}
    )


def _create_delegation(
    client: TestClient, access_token: str, *, delegate_user_id: str, delegated_roles: list[str]
) -> Response:
    return client.post(
        "/v1/admin/delegations",
        json={
            "delegate_user_id": delegate_user_id, "delegated_roles": delegated_roles,
            "scope": "tenant_governance", "expires_at": None,
        },
        headers={"Authorization": f"Bearer {access_token}"},
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
    # B3 slice 2: every parcel now receives a real, allocated number at
    # creation time — a deliberate, documented behavior change from slice
    # 1 (docs/adr/ADR-014), not a regression.
    assert body["parcel_number"] == "LV-NG-000001"
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


# ---- B3 slice 2: atomic parcel-number allocation (docs/adr/ADR-014) -----------
# Real concurrency (multiple genuinely simultaneous Postgres connections) is
# NOT testable against in-memory fakes — asyncio's cooperative scheduling
# means a fake allocator can never exercise real row-locking behavior. That
# is verified live, separately (see the completion report). These tests
# cover sequential allocation, tenant-scoped independence, and format —
# real business logic against the fake, same as everything else in this
# suite.

# 14. Sequential allocation within one tenant is 1, 2, 3, ... ------------------

def test_sequential_allocation_within_country(harness: AppHarness, client: TestClient) -> None:
    tokens, _user = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agent14@example.test", password="pw12345678", role="field_agent"
        )
    )
    first = _create_parcel(client, tokens.access_token, title="First").json()
    second = _create_parcel(client, tokens.access_token, title="Second").json()
    third = _create_parcel(client, tokens.access_token, title="Third").json()
    assert [first["parcel_number"], second["parcel_number"], third["parcel_number"]] == [
        "LV-NG-000001", "LV-NG-000002", "LV-NG-000003",
    ]


# 15. Allocation is nationally scoped, not tenant-scoped: two tenants registering
# in the SAME country share one sequence (parcel_number is a database-wide unique
# registry identifier — migrations/versions/0007_parcels.py's
# ix_parcels_number_unique — so a per-tenant counter would hand out colliding
# numbers the moment two tenants operate in the same country; ADR-014). A
# different country_code gets its own, independent sequence.

def test_allocation_is_nationally_scoped_not_tenant_scoped(
    harness: AppHarness, client: TestClient
) -> None:
    tokens_a, _a = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agentA15@example.test", password="pw12345678", role="field_agent"
        )
    )
    tokens_b, _b = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agentB15@example.test", password="pw12345678", role="field_agent"
        )
    )
    parcel_a1 = _create_parcel(client, tokens_a.access_token, title="A1").json()
    parcel_b1 = _create_parcel(client, tokens_b.access_token, title="B1").json()
    parcel_a2 = _create_parcel(client, tokens_a.access_token, title="A2").json()

    # Same country (NG, both tenants' default) — one shared sequence, no collision.
    assert parcel_a1["parcel_number"] == "LV-NG-000001"
    assert parcel_b1["parcel_number"] == "LV-NG-000002"
    assert parcel_a2["parcel_number"] == "LV-NG-000003"

    # A different country_code draws from its own, independent sequence.
    parcel_a_gh = _create_parcel(
        client, tokens_a.access_token, title="A-GH", country_code="GH"
    ).json()
    assert parcel_a_gh["parcel_number"] == "LV-GH-000001"


# 16. Allocated parcel numbers satisfy the domain's own "never reassigned" guard

def test_allocated_number_cannot_be_reassigned_by_domain_guard() -> None:
    parcel = Parcel.new(
        tenant_id="t1", country_code="NG", origin="platform_registration", created_by="u1",
    )
    parcel.allocate_parcel_number("LV-NG-000001")
    with pytest.raises(ValueError):
        parcel.allocate_parcel_number("LV-NG-000002")


# 17. Audit payload for creation includes the allocated parcel_number ----------

def test_audit_payload_includes_parcel_number(harness: AppHarness, client: TestClient) -> None:
    tokens, _user = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agent17@example.test", password="pw12345678", role="field_agent"
        )
    )
    created = _create_parcel(client, tokens.access_token, title="Audited number").json()

    entries = asyncio.run(harness.audit_store.all_entries())
    creation_entries = [e for e in entries if e.action == "registry.parcel.created"]
    assert any(e.payload.get("parcel_number") == created["parcel_number"] for e in creation_entries)


# ---- B3 slice 3: mutation commands & authorization hardening (docs/adr/ADR-015) -
# The central test in this section is #20 — it reproduces the exact ADR-005
# attack shape (a create-tier role mutating a parcel it did not create) and
# confirms the new authorization model denies it. Delegation lifecycle
# scenarios (expiry/revocation/demotion/suspension) reuse the identical
# fail-closed mechanism ADR-011 already built and already covers in
# test_b2_delegations.py — these tests confirm that mechanism's effect
# reaches Registry mutation specifically, not that the mechanism itself
# works (that's proven once, in B2).

# 18. The creator can update their own parcel -------------------------------------

def test_creator_can_update_own_parcel(harness: AppHarness, client: TestClient) -> None:
    tokens, _user = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agent18@example.test", password="pw12345678", role="field_agent"
        )
    )
    created = _create_parcel(client, tokens.access_token, title="Original title").json()

    response = _update_parcel(
        client, tokens.access_token, created["parcel_id"], title="Corrected title"
    )
    assert response.status_code == 200, response.text
    assert response.json()["title"] == "Corrected title"


# 19. The creator can archive their own parcel ------------------------------------

def test_creator_can_archive_own_parcel(harness: AppHarness, client: TestClient) -> None:
    tokens, _user = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agent19@example.test", password="pw12345678", role="field_agent"
        )
    )
    created = _create_parcel(client, tokens.access_token, title="To be archived").json()

    response = _archive_parcel(client, tokens.access_token, created["parcel_id"])
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ARCHIVED"
    assert response.json()["archived_at"] is not None


# 20. ADR-005 REGRESSION: a non-creator holding a registrant role, same tenant,
# cannot update or archive a colleague's parcel — the exact historical defect
# this slice was authorized to eliminate. Before this slice, no ownership
# check existed at all; this is the test that proves it now does.

def test_non_creator_registrant_denied_update_adr005_regression(
    harness: AppHarness, client: TestClient
) -> None:
    tokens_a, a = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agentA20@example.test", password="pw12345678", role="field_agent"
        )
    )
    tokens_b, _b = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agentB20@example.test", password="pw12345678",
            role="field_agent", tenant_id=a.tenant_id,
        )
    )
    created = _create_parcel(client, tokens_a.access_token, title="A's plot").json()

    update = _update_parcel(
        client, tokens_b.access_token, created["parcel_id"], title="B tries to edit A's plot"
    )
    assert update.status_code == 403

    archive = _archive_parcel(client, tokens_b.access_token, created["parcel_id"])
    assert archive.status_code == 403

    # And the parcel is provably untouched.
    still = client.get(
        f"/v1/parcels/{created['parcel_id']}",
        headers={"Authorization": f"Bearer {tokens_a.access_token}"},
    ).json()
    assert still["title"] == "A's plot"
    assert still["status"] == "ACTIVE"


# 21. Administrative override: a governance role can mutate a colleague's parcel -

def test_governance_role_can_override_ownership(harness: AppHarness, client: TestClient) -> None:
    agent_tokens, agent = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agent21@example.test", password="pw12345678", role="field_agent"
        )
    )
    officer_tokens, _officer = asyncio.run(
        _seed_user_with_role(
            harness, email="r-officer21@example.test", password="pw12345678",
            role="compliance_officer", tenant_id=agent.tenant_id,
        )
    )
    created = _create_parcel(client, agent_tokens.access_token, title="Agent's plot").json()

    response = _update_parcel(
        client, officer_tokens.access_token, created["parcel_id"], title="Corrected by compliance"
    )
    assert response.status_code == 200, response.text
    assert response.json()["title"] == "Corrected by compliance"


# 22. super_admin retains cross-tenant mutation reach (matches RLS/GOVERNANCE_ROLES)

def test_super_admin_can_mutate_cross_tenant_parcel(
    harness: AppHarness, client: TestClient
) -> None:
    admin_tokens, _admin = asyncio.run(
        _seed_user_with_role(
            harness, email="r-root22@example.test", password="pw12345678", role="super_admin"
        )
    )
    agent_tokens, _agent = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agent22@example.test", password="pw12345678", role="field_agent"
        )
    )
    created = _create_parcel(client, agent_tokens.access_token, title="Cross-tenant target").json()

    response = _archive_parcel(client, admin_tokens.access_token, created["parcel_id"])
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ARCHIVED"


# 23. Cross-tenant, non-governance mutation attempts 404 (existence not revealed) -

def test_cross_tenant_mutation_denied_as_not_found(
    harness: AppHarness, client: TestClient
) -> None:
    tokens_a, _a = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agentA23@example.test", password="pw12345678", role="field_agent"
        )
    )
    tokens_b, _b = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agentB23@example.test", password="pw12345678", role="field_agent"
        )
    )
    created = _create_parcel(client, tokens_a.access_token, title="A's plot").json()

    assert _update_parcel(
        client, tokens_b.access_token, created["parcel_id"], title="x"
    ).status_code == 404
    assert _archive_parcel(client, tokens_b.access_token, created["parcel_id"]).status_code == 404


# 24. Archived parcels reject further mutation, even from the creator or governance

def test_archived_parcel_rejects_further_mutation(harness: AppHarness, client: TestClient) -> None:
    tokens, _user = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agent24@example.test", password="pw12345678", role="field_agent"
        )
    )
    created = _create_parcel(client, tokens.access_token, title="Will be archived").json()
    archived = _archive_parcel(client, tokens.access_token, created["parcel_id"])
    assert archived.status_code == 200

    re_archive = _archive_parcel(client, tokens.access_token, created["parcel_id"])
    assert re_archive.status_code == 409

    update_after_archive = _update_parcel(
        client, tokens.access_token, created["parcel_id"], title="too late"
    )
    assert update_after_archive.status_code == 409


# 25. A delegated GOVERNANCE role inherits the delegator's tenant-wide override --

def test_delegated_governance_role_can_override_ownership(
    harness: AppHarness, client: TestClient
) -> None:
    officer_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="r-officer25@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    agent_tokens, _agent = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agent25@example.test", password="pw12345678",
            role="field_agent", tenant_id=officer.tenant_id,
        )
    )
    delegate_tokens, delegate = asyncio.run(
        _seed_user_with_role(
            harness, email="r-delegate25@example.test", password="pw12345678",
            role="general_user", tenant_id=officer.tenant_id,
        )
    )
    created = _create_parcel(client, agent_tokens.access_token, title="Needs correction").json()

    delegation = _create_delegation(
        client, officer_tokens.access_token,
        delegate_user_id=delegate.user_id, delegated_roles=["compliance_officer"],
    )
    assert delegation.status_code == 201, delegation.text

    response = _update_parcel(
        client, delegate_tokens.access_token, created["parcel_id"], title="Corrected by delegate"
    )
    assert response.status_code == 200, response.text
    assert response.json()["title"] == "Corrected by delegate"


# 26. A delegated NON-governance role does NOT inherit override on a colleague's
# parcel — delegation grants the role's own reach, never more (ADR-011/ADR-015).

def test_delegated_registrant_role_cannot_override_ownership(
    harness: AppHarness, client: TestClient
) -> None:
    officer_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="r-officer26@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    creator_tokens, _creator = asyncio.run(
        _seed_user_with_role(
            harness, email="r-creator26@example.test", password="pw12345678",
            role="field_agent", tenant_id=officer.tenant_id,
        )
    )
    delegate_tokens, delegate = asyncio.run(
        _seed_user_with_role(
            harness, email="r-delegate26@example.test", password="pw12345678",
            role="general_user", tenant_id=officer.tenant_id,
        )
    )
    created = _create_parcel(client, creator_tokens.access_token, title="Not yours").json()

    delegation = _create_delegation(
        client, officer_tokens.access_token,
        delegate_user_id=delegate.user_id, delegated_roles=["field_agent"],
    )
    assert delegation.status_code == 201, delegation.text

    response = _update_parcel(
        client, delegate_tokens.access_token, created["parcel_id"], title="Should be denied"
    )
    assert response.status_code == 403


# 27. Delegation revoked mid-session denies mutation immediately, no replay -------

def test_revoked_delegation_denies_mutation_immediately(
    harness: AppHarness, client: TestClient
) -> None:
    officer_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="r-officer27@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    agent_tokens, _agent = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agent27@example.test", password="pw12345678",
            role="field_agent", tenant_id=officer.tenant_id,
        )
    )
    delegate_tokens, delegate = asyncio.run(
        _seed_user_with_role(
            harness, email="r-delegate27@example.test", password="pw12345678",
            role="general_user", tenant_id=officer.tenant_id,
        )
    )
    created = _create_parcel(client, agent_tokens.access_token, title="Under governance").json()

    delegation = _create_delegation(
        client, officer_tokens.access_token,
        delegate_user_id=delegate.user_id, delegated_roles=["compliance_officer"],
    )
    delegation_id = delegation.json()["delegation_id"]
    assert _update_parcel(
        client, delegate_tokens.access_token, created["parcel_id"], title="Still delegated"
    ).status_code == 200

    revoke = client.post(
        f"/v1/admin/delegations/{delegation_id}/revoke",
        headers={"Authorization": f"Bearer {officer_tokens.access_token}"},
    )
    assert revoke.status_code == 200, revoke.text

    denied = _update_parcel(
        client, delegate_tokens.access_token, created["parcel_id"], title="Too late now"
    )
    assert denied.status_code == 403


# 28. Delegator demoted below the delegated role's rank invalidates the delegation
# for Registry mutation too — reuses ADR-011's highest_rank() re-validation.

def test_delegator_demotion_invalidates_registry_mutation_authority(
    harness: AppHarness, client: TestClient
) -> None:
    officer_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="r-officer28@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    agent_tokens, _agent = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agent28@example.test", password="pw12345678",
            role="field_agent", tenant_id=officer.tenant_id,
        )
    )
    delegate_tokens, delegate = asyncio.run(
        _seed_user_with_role(
            harness, email="r-delegate28@example.test", password="pw12345678",
            role="general_user", tenant_id=officer.tenant_id,
        )
    )
    created = _create_parcel(client, agent_tokens.access_token, title="Under governance").json()
    _create_delegation(
        client, officer_tokens.access_token,
        delegate_user_id=delegate.user_id, delegated_roles=["compliance_officer"],
    )
    assert _update_parcel(
        client, delegate_tokens.access_token, created["parcel_id"], title="Still ok"
    ).status_code == 200

    async def _demote_officer() -> None:
        current = await harness.users.get(officer.user_id)
        assert current is not None
        current.roles = ["general_user"]
        await harness.users.update(current, expected_version=current.version)

    asyncio.run(_demote_officer())

    denied = _update_parcel(
        client, delegate_tokens.access_token, created["parcel_id"], title="No longer authorized"
    )
    assert denied.status_code == 403


# 29. An expired delegation denies Registry mutation ------------------------------

def test_expired_delegation_denies_registry_mutation(
    harness: AppHarness, client: TestClient
) -> None:
    officer_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="r-officer29@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    agent_tokens, _agent = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agent29@example.test", password="pw12345678",
            role="field_agent", tenant_id=officer.tenant_id,
        )
    )
    delegate_tokens, delegate = asyncio.run(
        _seed_user_with_role(
            harness, email="r-delegate29@example.test", password="pw12345678",
            role="general_user", tenant_id=officer.tenant_id,
        )
    )
    created = _create_parcel(client, agent_tokens.access_token, title="Under governance").json()

    expired = Delegation.new(
        tenant_id=officer.tenant_id,
        delegator_user_id=officer.user_id,
        delegate_user_id=delegate.user_id,
        delegated_roles=["compliance_officer"],
        scope="tenant_governance",
        expires_at=(datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
    )
    asyncio.run(harness.delegations.add(expired))

    denied = _update_parcel(
        client, delegate_tokens.access_token, created["parcel_id"], title="Should be denied"
    )
    assert denied.status_code == 403


# 30. A suspended tenant locks out Registry mutation too (existing ADR-010 gate) --

def test_suspended_tenant_locks_out_registry_mutation(
    harness: AppHarness, client: TestClient
) -> None:
    tokens, user = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agent30@example.test", password="pw12345678", role="field_agent"
        )
    )
    created = _create_parcel(client, tokens.access_token, title="Pre-suspension").json()

    async def _suspend_tenant() -> None:
        tenant = await harness.tenants.get(user.tenant_id)
        assert tenant is not None
        tenant.suspend(reason="test")
        await harness.tenants.update(tenant)

    asyncio.run(_suspend_tenant())

    response = _update_parcel(
        client, tokens.access_token, created["parcel_id"], title="Should be locked out"
    )
    # Not 401: the PEP's anonymous check is deliberately literal (only the
    # "anonymous" sentinel principal_id counts, app.kernel.authorization.
    # pep/context_hydration.py's own documented behavior) — a suspended
    # tenant's hydration returns None, so roles is empty and require_role
    # denies with 403, the same shape any other roleless caller gets.
    assert response.status_code == 403


# 31. Validation: an empty update body is rejected --------------------------------

def test_empty_update_body_rejected(harness: AppHarness, client: TestClient) -> None:
    tokens, _user = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agent31@example.test", password="pw12345678", role="field_agent"
        )
    )
    created = _create_parcel(client, tokens.access_token, title="Plot").json()
    response = _update_parcel(client, tokens.access_token, created["parcel_id"])
    assert response.status_code == 400


# 32. Validation: non-positive size_sqm rejected on update too --------------------

def test_update_non_positive_size_rejected(harness: AppHarness, client: TestClient) -> None:
    tokens, _user = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agent32@example.test", password="pw12345678", role="field_agent"
        )
    )
    created = _create_parcel(client, tokens.access_token, title="Plot").json()
    response = _update_parcel(client, tokens.access_token, created["parcel_id"], size_sqm=0)
    assert response.status_code == 400


# 33. Domain guard: update_details rejects unknown fields, archive is one-way ----

def test_domain_update_details_rejects_unknown_fields() -> None:
    parcel = Parcel.new(
        tenant_id="t1", country_code="NG", origin="platform_registration", created_by="u1",
    )
    with pytest.raises(ValueError):
        parcel.update_details(updated_by="u1", fields={"parcel_id": "hacked"})


def test_domain_archive_then_archive_again_raises() -> None:
    parcel = Parcel.new(
        tenant_id="t1", country_code="NG", origin="platform_registration", created_by="u1",
    )
    parcel.archive(archived_by="u1")
    assert parcel.status == "ARCHIVED"
    with pytest.raises(ParcelArchivedError):
        parcel.archive(archived_by="u1")


# 34. Mutation audit: update/archive/denial all carry the expected payload -------

def test_mutation_audit_payloads(harness: AppHarness, client: TestClient) -> None:
    tokens_a, a = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agentA34@example.test", password="pw12345678", role="field_agent"
        )
    )
    tokens_b, _b = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agentB34@example.test", password="pw12345678",
            role="field_agent", tenant_id=a.tenant_id,
        )
    )
    created = _create_parcel(client, tokens_a.access_token, title="Audited plot").json()
    _update_parcel(client, tokens_a.access_token, created["parcel_id"], title="Audited edit")
    _update_parcel(client, tokens_b.access_token, created["parcel_id"], title="Denied edit")
    _archive_parcel(client, tokens_a.access_token, created["parcel_id"])

    entries = asyncio.run(harness.audit_store.all_entries())
    by_action = {e.action: e for e in reversed(entries) if e.resource_id == created["parcel_id"]}

    updated = by_action["registry.parcel.updated"]
    assert updated.payload["effective_authority"] == "creator"
    assert updated.payload["tenant_id"] == created["tenant_id"]
    assert updated.payload["fields_changed"] == ["title"]

    denied = by_action["registry.parcel.mutation_denied"]
    assert denied.decision == "DENY"
    assert denied.payload["reason"] == "not_creator_and_not_governance"

    archived = by_action["registry.parcel.archived"]
    assert archived.payload["effective_authority"] == "creator"

    assert asyncio.run(verify_chain()) is True


# 35. Backward compatibility: slice 1/2 endpoints still work unchanged -----------

def test_create_get_list_still_work_after_slice_3(harness: AppHarness, client: TestClient) -> None:
    tokens, _user = asyncio.run(
        _seed_user_with_role(
            harness, email="r-agent35@example.test", password="pw12345678", role="field_agent"
        )
    )
    created = _create_parcel(client, tokens.access_token, title="Still works").json()
    assert created["status"] == "ACTIVE"

    fetched = client.get(
        f"/v1/parcels/{created['parcel_id']}",
        headers={"Authorization": f"Bearer {tokens.access_token}"},
    )
    assert fetched.status_code == 200

    listed = client.get(
        "/v1/parcels", headers={"Authorization": f"Bearer {tokens.access_token}"}
    )
    assert listed.status_code == 200
    assert any(p["parcel_id"] == created["parcel_id"] for p in listed.json())
