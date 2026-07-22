"""B4 slice 1 — Spatial Domain Foundation (docs/adr/ADR-018, docs/adr/ADR-019).

Covers: the ParcelGeometry aggregate's domain invariants (structural
validation gates persistence, append-only ACTIVE/SUPERSEDED lifecycle),
the Spatial bounded context's own authorization boundary (coarse
PARCEL_REGISTRANT_ROLES gate + parcel-existence/tenant-scope check via
ParcelExistencePort — NOT yet a full creator-or-governance model, that is
ADR-022's job), and audit integration. No overlap detection, no real
geometry validation beyond structural well-formedness, no GIS computation
of any kind — those are ADR-020/021's job. Real business logic
throughout; Keycloak and Postgres are swapped for in-memory fakes at the
port boundary, same as the rest of the B1/B2/B3/B4 suite. RLS and the
database-level "one ACTIVE geometry per parcel" constraint are verified
live against real Postgres separately (see the completion report), not
here — in-memory fakes have no RLS/constraints to exercise.
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from app.contexts.identity.domain.tenant import Tenant
from app.contexts.identity.domain.user import User
from app.contexts.identity.ports import IdentityProviderTokens
from app.contexts.spatial.domain.parcel_geometry import (
    InvalidGeometryError,
    ParcelGeometry,
    ParcelGeometryAlreadySupersededError,
)
from app.kernel.audit import verify_chain
from tests.app_factory import AppHarness, build_test_app

VALID_POLYGON = "POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))"
OTHER_POLYGON = "POLYGON((2 2, 2 3, 3 3, 3 2, 2 2))"


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


def _submit_geometry(
    client: TestClient, access_token: str, parcel_id: str, boundary: str
) -> Response:
    return client.put(
        f"/v1/spatial/parcels/{parcel_id}/geometry",
        json={"boundary": boundary},
        headers={"Authorization": f"Bearer {access_token}"},
    )


def _get_active_geometry(client: TestClient, access_token: str, parcel_id: str) -> Response:
    return client.get(
        f"/v1/spatial/parcels/{parcel_id}/geometry",
        headers={"Authorization": f"Bearer {access_token}"},
    )


# 1. A registrant can submit geometry for their own parcel -----------------------

def test_registrant_can_submit_geometry_for_own_parcel(
    harness: AppHarness, client: TestClient
) -> None:
    tokens, _user = asyncio.run(
        _seed_user_with_role(
            harness, email="s-agent1@example.test", password="pw12345678", role="field_agent"
        )
    )
    parcel = _create_parcel(client, tokens.access_token, title="Needs geometry").json()

    response = _submit_geometry(client, tokens.access_token, parcel["parcel_id"], VALID_POLYGON)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "ACTIVE"
    assert body["boundary"] == VALID_POLYGON
    assert body["parcel_id"] == parcel["parcel_id"]
    assert body["tenant_id"] == parcel["tenant_id"]
    assert body["srid"] == 4326


# 2. The active geometry can be read back -----------------------------------------

def test_get_active_geometry(harness: AppHarness, client: TestClient) -> None:
    tokens, _user = asyncio.run(
        _seed_user_with_role(
            harness, email="s-agent2@example.test", password="pw12345678", role="field_agent"
        )
    )
    parcel = _create_parcel(client, tokens.access_token, title="Plot").json()
    _submit_geometry(client, tokens.access_token, parcel["parcel_id"], VALID_POLYGON)

    response = _get_active_geometry(client, tokens.access_token, parcel["parcel_id"])
    assert response.status_code == 200, response.text
    assert response.json()["boundary"] == VALID_POLYGON


# 3. Submitting new geometry supersedes the prior ACTIVE one (append-only) -------

def test_second_submission_supersedes_the_first(harness: AppHarness, client: TestClient) -> None:
    tokens, _user = asyncio.run(
        _seed_user_with_role(
            harness, email="s-agent3@example.test", password="pw12345678", role="field_agent"
        )
    )
    parcel = _create_parcel(client, tokens.access_token, title="Plot").json()
    first = _submit_geometry(client, tokens.access_token, parcel["parcel_id"], VALID_POLYGON).json()
    second = _submit_geometry(
        client, tokens.access_token, parcel["parcel_id"], OTHER_POLYGON
    ).json()

    assert first["geometry_id"] != second["geometry_id"]
    assert second["status"] == "ACTIVE"
    assert second["boundary"] == OTHER_POLYGON

    superseded = asyncio.run(harness.parcel_geometries.get(first["geometry_id"]))
    assert superseded is not None
    assert superseded.status == "SUPERSEDED"
    assert superseded.superseded_at is not None
    # The original row's boundary is untouched — a correction never edits
    # in place, it only ever adds a new row and flips the old one's status.
    assert superseded.boundary == VALID_POLYGON

    active = asyncio.run(harness.parcel_geometries.get_active_for_parcel(parcel["parcel_id"]))
    assert active is not None
    assert active.geometry_id == second["geometry_id"]


# 4. A non-existent parcel_id 404s -------------------------------------------------

def test_nonexistent_parcel_404s(harness: AppHarness, client: TestClient) -> None:
    tokens, _user = asyncio.run(
        _seed_user_with_role(
            harness, email="s-agent4@example.test", password="pw12345678", role="field_agent"
        )
    )
    response = _submit_geometry(
        client, tokens.access_token, "00000000-0000-0000-0000-000000000000", VALID_POLYGON
    )
    assert response.status_code == 404
    response_get = _get_active_geometry(
        client, tokens.access_token, "00000000-0000-0000-0000-000000000000"
    )
    assert response_get.status_code == 404


# 5. A cross-tenant parcel_id 404s (existence not revealed across tenants) -------

def test_cross_tenant_parcel_404s(harness: AppHarness, client: TestClient) -> None:
    tokens_a, _a = asyncio.run(
        _seed_user_with_role(
            harness, email="s-agentA5@example.test", password="pw12345678", role="field_agent"
        )
    )
    tokens_b, _b = asyncio.run(
        _seed_user_with_role(
            harness, email="s-agentB5@example.test", password="pw12345678", role="field_agent"
        )
    )
    parcel = _create_parcel(client, tokens_a.access_token, title="A's plot").json()

    response = _submit_geometry(client, tokens_b.access_token, parcel["parcel_id"], VALID_POLYGON)
    assert response.status_code == 404


# 5b. super_admin retains cross-tenant reach (matches RLS/_in_scope bypass) ------

def test_super_admin_can_submit_geometry_cross_tenant(
    harness: AppHarness, client: TestClient
) -> None:
    tokens_agent, _agent = asyncio.run(
        _seed_user_with_role(
            harness, email="s-agent5b@example.test", password="pw12345678", role="field_agent"
        )
    )
    tokens_admin, _admin = asyncio.run(
        _seed_user_with_role(
            harness, email="s-root5b@example.test", password="pw12345678", role="super_admin"
        )
    )
    parcel = _create_parcel(client, tokens_agent.access_token, title="Agent's plot").json()

    response = _submit_geometry(
        client, tokens_admin.access_token, parcel["parcel_id"], VALID_POLYGON
    )
    assert response.status_code == 201, response.text


# 6. A malformed boundary is rejected (structural validation only) --------------

def test_malformed_boundary_rejected(harness: AppHarness, client: TestClient) -> None:
    tokens, _user = asyncio.run(
        _seed_user_with_role(
            harness, email="s-agent6@example.test", password="pw12345678", role="field_agent"
        )
    )
    parcel = _create_parcel(client, tokens.access_token, title="Plot").json()

    response = _submit_geometry(client, tokens.access_token, parcel["parcel_id"], "not a polygon")
    assert response.status_code == 400


# 7. A non-registrant role is denied (coarse role gate, same as Registry) -------

def test_non_registrant_denied(harness: AppHarness, client: TestClient) -> None:
    tokens_agent, _agent = asyncio.run(
        _seed_user_with_role(
            harness, email="s-agent7@example.test", password="pw12345678", role="field_agent"
        )
    )
    parcel = _create_parcel(client, tokens_agent.access_token, title="Plot").json()

    tokens_plain, _plain = asyncio.run(
        _seed_user_with_role(
            harness, email="s-plain7@example.test", password="pw12345678", role="general_user"
        )
    )
    response = _submit_geometry(
        client, tokens_plain.access_token, parcel["parcel_id"], VALID_POLYGON
    )
    assert response.status_code == 403


# 8. Anonymous is denied ------------------------------------------------------------

def test_anonymous_denied(client: TestClient) -> None:
    assert client.put(
        "/v1/spatial/parcels/00000000-0000-0000-0000-000000000000/geometry",
        json={"boundary": VALID_POLYGON},
    ).status_code == 401
    assert client.get(
        "/v1/spatial/parcels/00000000-0000-0000-0000-000000000000/geometry"
    ).status_code == 401


# 9. Submission is audited and the hash chain verifies ---------------------------

def test_geometry_submission_audited(harness: AppHarness, client: TestClient) -> None:
    tokens, _user = asyncio.run(
        _seed_user_with_role(
            harness, email="s-agent9@example.test", password="pw12345678", role="field_agent"
        )
    )
    parcel = _create_parcel(client, tokens.access_token, title="Plot").json()
    created = _submit_geometry(
        client, tokens.access_token, parcel["parcel_id"], VALID_POLYGON
    ).json()

    entries = asyncio.run(harness.audit_store.all_entries())
    creation_entries = [e for e in entries if e.action == "spatial.parcel_geometry.created"]
    assert any(e.resource_id == created["geometry_id"] for e in creation_entries)
    assert asyncio.run(verify_chain()) is True


# 10. Domain guard: ParcelGeometry.new() rejects malformed WKT --------------------

def test_domain_new_rejects_malformed_boundary() -> None:
    with pytest.raises(InvalidGeometryError):
        ParcelGeometry.new(
            tenant_id="t1", parcel_id="p1", boundary="garbage", created_by="u1"
        )


# 11. Domain guard: supersede() cannot be called twice ---------------------------

def test_domain_supersede_twice_raises() -> None:
    geometry = ParcelGeometry.new(
        tenant_id="t1", parcel_id="p1", boundary=VALID_POLYGON, created_by="u1"
    )
    geometry.supersede()
    assert geometry.status == "SUPERSEDED"
    with pytest.raises(ParcelGeometryAlreadySupersededError):
        geometry.supersede()


# 12. Backward compatibility: Registry endpoints unaffected by Spatial's presence

def test_registry_endpoints_still_work(harness: AppHarness, client: TestClient) -> None:
    tokens, _user = asyncio.run(
        _seed_user_with_role(
            harness, email="s-agent12@example.test", password="pw12345678", role="field_agent"
        )
    )
    created = _create_parcel(client, tokens.access_token, title="Still works").json()
    assert created["status"] == "ACTIVE"
    fetched = client.get(
        f"/v1/parcels/{created['parcel_id']}",
        headers={"Authorization": f"Bearer {tokens.access_token}"},
    )
    assert fetched.status_code == 200
