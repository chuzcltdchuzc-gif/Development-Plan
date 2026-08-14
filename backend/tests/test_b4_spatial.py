"""B4 Slice 1 + Slice 2 — Spatial Domain Foundation and Geometry
Validation & Authorization (docs/adr/ADR-018, docs/adr/ADR-019,
docs/adr/ADR-022).

Covers: the ParcelGeometry aggregate's domain invariants (real structural
WKT validation gates persistence, append-only ACTIVE/SUPERSEDED
lifecycle), Spatial's ADR-022 creator-or-governance authorization model
(mirroring Registry's ADR-015 exactly: creator permit, governance permit,
delegated-governance permit, non-creator/non-governance deny — the
ADR-005-shaped regression — archived-parcel unconditional block), and
audit integration (`spatial.parcel_geometry.created`/`.mutation_denied`).
No overlap detection, no self-intersection/topology, no GIS computation
of any kind — those remain later ADRs' job. Real business logic
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
from app.contexts.registry.dependencies import get_geometry_port
from app.contexts.spatial.adapters.geometry_port_adapter import RealGeometryAdapter
from app.contexts.spatial.domain.geometry_validation import (
    InvalidGeometryError,
    validate_wkt_polygon,
)
from app.contexts.spatial.domain.parcel_geometry import (
    ParcelGeometry,
    ParcelGeometryAlreadySupersededError,
)
from app.kernel.audit import verify_chain
from tests.app_factory import AppHarness, build_test_app

VALID_POLYGON = "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"
OTHER_POLYGON = "POLYGON((2 2, 3 2, 3 3, 2 3, 2 2))"


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


def _archive_parcel(client: TestClient, access_token: str, parcel_id: str) -> Response:
    return client.post(
        f"/v1/parcels/{parcel_id}/archive", headers={"Authorization": f"Bearer {access_token}"}
    )


def _set_geometry(
    client: TestClient, access_token: str, parcel_id: str, geometry_reference: str | None
) -> Response:
    return client.put(
        f"/v1/parcels/{parcel_id}/geometry",
        json={"geometry_reference": geometry_reference},
        headers={"Authorization": f"Bearer {access_token}"},
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


# --- B4 Slice 2 (docs/adr/ADR-022) ------------------------------------------------

# 13. A governance role can submit geometry for a colleague's parcel (override) --

def test_governance_role_can_submit_geometry_for_colleagues_parcel(
    harness: AppHarness, client: TestClient
) -> None:
    agent_tokens, agent = asyncio.run(
        _seed_user_with_role(
            harness, email="s-agent13@example.test", password="pw12345678", role="field_agent"
        )
    )
    officer_tokens, _officer = asyncio.run(
        _seed_user_with_role(
            harness, email="s-officer13@example.test", password="pw12345678",
            role="compliance_officer", tenant_id=agent.tenant_id,
        )
    )
    created = _create_parcel(client, agent_tokens.access_token, title="Agent's plot").json()

    response = _submit_geometry(
        client, officer_tokens.access_token, created["parcel_id"], VALID_POLYGON
    )
    assert response.status_code == 201, response.text


# 14. A delegated governance role inherits the same override -----------------------

def test_delegated_governance_role_can_submit_geometry(
    harness: AppHarness, client: TestClient
) -> None:
    officer_tokens, officer = asyncio.run(
        _seed_user_with_role(
            harness, email="s-officer14@example.test", password="pw12345678",
            role="compliance_officer",
        )
    )
    agent_tokens, _agent = asyncio.run(
        _seed_user_with_role(
            harness, email="s-agent14@example.test", password="pw12345678",
            role="field_agent", tenant_id=officer.tenant_id,
        )
    )
    delegate_tokens, delegate = asyncio.run(
        _seed_user_with_role(
            harness, email="s-delegate14@example.test", password="pw12345678",
            role="general_user", tenant_id=officer.tenant_id,
        )
    )
    created = _create_parcel(client, agent_tokens.access_token, title="Needs geometry").json()

    delegation = _create_delegation(
        client, officer_tokens.access_token,
        delegate_user_id=delegate.user_id, delegated_roles=["compliance_officer"],
    )
    assert delegation.status_code == 201, delegation.text

    response = _submit_geometry(
        client, delegate_tokens.access_token, created["parcel_id"], VALID_POLYGON
    )
    assert response.status_code == 201, response.text


# 15. ADR-005-SHAPED REGRESSION: a non-creator holding a registrant role, same
# tenant, cannot submit geometry for a colleague's parcel — the exact historical
# defect ADR-022 exists to prevent for Spatial. Also confirms the denial is
# audited with the same reason string Registry's own ADR-015 audit uses.

def test_non_creator_registrant_denied_adr005_regression(
    harness: AppHarness, client: TestClient
) -> None:
    tokens_a, a = asyncio.run(
        _seed_user_with_role(
            harness, email="s-agentA15@example.test", password="pw12345678", role="field_agent"
        )
    )
    tokens_b, _b = asyncio.run(
        _seed_user_with_role(
            harness, email="s-agentB15@example.test", password="pw12345678",
            role="field_agent", tenant_id=a.tenant_id,
        )
    )
    created = _create_parcel(client, tokens_a.access_token, title="A's plot").json()

    response = _submit_geometry(client, tokens_b.access_token, created["parcel_id"], VALID_POLYGON)
    assert response.status_code == 403

    entries = asyncio.run(harness.audit_store.all_entries())
    denials = [e for e in entries if e.action == "spatial.parcel_geometry.mutation_denied"]
    assert any(
        e.resource_id == created["parcel_id"]
        and e.payload.get("reason") == "not_creator_and_not_governance"
        for e in denials
    )

    # And no geometry was left behind for A's parcel.
    still = _get_active_geometry(client, tokens_a.access_token, created["parcel_id"])
    assert still.status_code == 404


# 16. Archived-parcel geometry mutation is unconditionally blocked — creator,
# governance, and super_admin alike, no override path (ADR-022 §8, mirroring
# ADR-015's identical rule for Registry).

def test_archived_parcel_blocks_geometry_mutation_for_every_role(
    harness: AppHarness, client: TestClient
) -> None:
    agent_tokens, agent = asyncio.run(
        _seed_user_with_role(
            harness, email="s-agent16@example.test", password="pw12345678", role="field_agent"
        )
    )
    officer_tokens, _officer = asyncio.run(
        _seed_user_with_role(
            harness, email="s-officer16@example.test", password="pw12345678",
            role="compliance_officer", tenant_id=agent.tenant_id,
        )
    )
    admin_tokens, _admin = asyncio.run(
        _seed_user_with_role(
            harness, email="s-root16@example.test", password="pw12345678", role="super_admin"
        )
    )
    created = _create_parcel(client, agent_tokens.access_token, title="Will be archived").json()
    archived = _archive_parcel(client, agent_tokens.access_token, created["parcel_id"])
    assert archived.status_code == 200, archived.text

    creator_attempt = _submit_geometry(
        client, agent_tokens.access_token, created["parcel_id"], VALID_POLYGON
    )
    assert creator_attempt.status_code == 409

    governance_attempt = _submit_geometry(
        client, officer_tokens.access_token, created["parcel_id"], VALID_POLYGON
    )
    assert governance_attempt.status_code == 409

    super_admin_attempt = _submit_geometry(
        client, admin_tokens.access_token, created["parcel_id"], VALID_POLYGON
    )
    assert super_admin_attempt.status_code == 409

    # Reading remains permitted on an archived parcel — reading is not a
    # mutation (ADR-022 §6) — but there is no geometry to find yet.
    read = _get_active_geometry(client, agent_tokens.access_token, created["parcel_id"])
    assert read.status_code == 404


# 17. Validator edge cases (pure domain-level, no HTTP) -----------------------------

def test_validator_rejects_empty_boundary() -> None:
    with pytest.raises(InvalidGeometryError):
        validate_wkt_polygon("")


def test_validator_rejects_non_polygon_keyword() -> None:
    with pytest.raises(InvalidGeometryError):
        validate_wkt_polygon("POINT(0 0)")


def test_validator_rejects_unclosed_ring() -> None:
    with pytest.raises(InvalidGeometryError):
        validate_wkt_polygon("POLYGON((0 0, 1 0, 1 1, 0 1))")


def test_validator_rejects_too_few_points() -> None:
    with pytest.raises(InvalidGeometryError):
        validate_wkt_polygon("POLYGON((0 0, 1 1, 0 0))")


def test_validator_rejects_non_numeric_coordinates() -> None:
    with pytest.raises(InvalidGeometryError):
        validate_wkt_polygon("POLYGON((0 0, 1 0, x y, 0 1, 0 0))")


def test_validator_rejects_out_of_range_coordinates() -> None:
    with pytest.raises(InvalidGeometryError):
        validate_wkt_polygon("POLYGON((0 0, 200 0, 200 1, 0 1, 0 0))")


def test_validator_rejects_clockwise_exterior_ring() -> None:
    with pytest.raises(InvalidGeometryError):
        validate_wkt_polygon("POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))")


def test_validator_rejects_unsupported_srid() -> None:
    with pytest.raises(InvalidGeometryError):
        validate_wkt_polygon("SRID=3857;POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))")


def test_validator_accepts_matching_ewkt_srid() -> None:
    assert validate_wkt_polygon(
        "SRID=4326;POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"
    ) == "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"


def test_validator_accepts_valid_polygon_with_hole() -> None:
    # Exterior CCW, interior (hole) CW — OGC Simple Features convention.
    polygon = (
        "POLYGON((0 0, 10 0, 10 10, 0 10, 0 0), (2 2, 2 4, 4 4, 4 2, 2 2))"
    )
    assert validate_wkt_polygon(polygon) == polygon


# 18. Registry<->Spatial GeometryPort integration: a geometry_reference produced
# by Spatial is genuinely honoured by Registry's real GeometryPort adapter, and a
# foreign/unknown reference is genuinely rejected — proving the composition-root
# wiring (app.main's dependency_overrides) is not merely decorative.

def test_registry_accepts_real_spatial_geometry_reference(
    harness: AppHarness, client: TestClient
) -> None:
    tokens, _user = asyncio.run(
        _seed_user_with_role(
            harness, email="s-agent18@example.test", password="pw12345678", role="field_agent"
        )
    )
    parcel = _create_parcel(client, tokens.access_token, title="Real geometry seam").json()
    submitted = _submit_geometry(
        client, tokens.access_token, parcel["parcel_id"], VALID_POLYGON
    ).json()

    real_port = RealGeometryAdapter(harness.parcel_geometries)
    harness.app.dependency_overrides[get_geometry_port] = lambda: real_port
    try:
        accepted = _set_geometry(
            client, tokens.access_token, parcel["parcel_id"], submitted["geometry_id"]
        )
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["geometry_reference"] == submitted["geometry_id"]

        rejected = _set_geometry(
            client, tokens.access_token, parcel["parcel_id"],
            "00000000-0000-0000-0000-000000000000",
        )
        assert rejected.status_code == 400
    finally:
        harness.app.dependency_overrides[get_geometry_port] = lambda: harness.geometry


def test_registry_rejects_geometry_reference_belonging_to_another_parcel(
    harness: AppHarness, client: TestClient
) -> None:
    tokens, _user = asyncio.run(
        _seed_user_with_role(
            harness, email="s-agent18b@example.test", password="pw12345678", role="field_agent"
        )
    )
    parcel_a = _create_parcel(client, tokens.access_token, title="Parcel A").json()
    parcel_b = _create_parcel(client, tokens.access_token, title="Parcel B").json()
    submitted_for_a = _submit_geometry(
        client, tokens.access_token, parcel_a["parcel_id"], VALID_POLYGON
    ).json()

    real_port = RealGeometryAdapter(harness.parcel_geometries)
    harness.app.dependency_overrides[get_geometry_port] = lambda: real_port
    try:
        cross_parcel = _set_geometry(
            client, tokens.access_token, parcel_b["parcel_id"], submitted_for_a["geometry_id"]
        )
        assert cross_parcel.status_code == 400
    finally:
        harness.app.dependency_overrides[get_geometry_port] = lambda: harness.geometry
