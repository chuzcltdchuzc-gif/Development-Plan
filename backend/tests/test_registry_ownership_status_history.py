"""B3 — Registry Ownership and Status History (docs/adr/ADR-023).

Full test matrix per ADR-023's own "Test matrix" section. Real business
logic against in-memory fakes throughout, same as the rest of the B1/B2/B3
suite — RLS, the append-only database triggers, and real transactional
rollback are DB-level guarantees with no equivalent in an in-memory fake;
they are rehearsed live against Postgres separately (migration 0011's own
docstring, and the implementation report), not here. This file proves the
application-layer behavior ADR-023 decided: which mutations write which
rows, when they don't, supersedes_id chaining, and audit_ref resolution.
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.kernel.audit import verify_chain
from tests.app_factory import AppHarness, build_test_app


@pytest.fixture
def harness() -> AppHarness:
    return build_test_app()


@pytest.fixture
def client(harness: AppHarness) -> TestClient:
    return TestClient(harness.app)


async def _seed_field_agent(harness: AppHarness, *, email: str) -> str:
    from app.contexts.identity.domain.tenant import Tenant
    from app.contexts.identity.domain.user import User

    subject = await harness.identity_provider.create_user(
        email=email, password="pw12345678", full_name="History Test User"
    )
    user = User.new(
        keycloak_subject=subject, email=email, full_name="History Test User", country="NG",
    )
    user.roles = ["field_agent"]
    user = await harness.users.add(user)
    await harness.tenants.add(Tenant.new(name="History Test Tenant", tenant_id=user.tenant_id))
    tokens = await harness.identity_provider.authenticate(email=email, password="pw12345678")
    return tokens.access_token


def _create(client: TestClient, token: str, **body: object) -> dict:
    response = client.post(
        "/v1/parcels", json=body, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201, response.text
    return response.json()


def _update(client: TestClient, token: str, parcel_id: str, **body: object) -> dict:
    response = client.patch(
        f"/v1/parcels/{parcel_id}", json=body, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200, response.text
    return response.json()


def _archive(client: TestClient, token: str, parcel_id: str) -> dict:
    response = client.post(
        f"/v1/parcels/{parcel_id}/archive", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200, response.text
    return response.json()


# 1a. Creating a parcel WITH an owner reference writes exactly one ownership
# row and one status row (the initial ACTIVE assertion). ----------------------

def test_create_with_owner_writes_one_ownership_and_one_status_row(
    harness: AppHarness, client: TestClient
) -> None:
    token = asyncio.run(_seed_field_agent(harness, email="h-owner1@example.test"))
    created = _create(
        client, token, title="Plot", current_owner_name="Jane Doe",
        current_owner_contact="+234-800-000-0001",
    )

    ownership = asyncio.run(harness.parcel_history.all_ownership_for(created["parcel_id"]))
    status = asyncio.run(harness.parcel_history.all_status_for(created["parcel_id"]))

    assert len(ownership) == 1
    assert ownership[0].asserted_holder_ref == "Jane Doe (+234-800-000-0001)"
    assert ownership[0].basis == "initial registration"
    assert ownership[0].supersedes_id is None

    assert len(status) == 1
    assert status[0].asserted_status == "ACTIVE"
    assert status[0].basis == "initial registration"
    assert status[0].supersedes_id is None


# 1b. Creating a parcel with NO owner reference writes zero ownership rows,
# but still writes the initial status row. ------------------------------------

def test_create_without_owner_writes_zero_ownership_rows(
    harness: AppHarness, client: TestClient
) -> None:
    token = asyncio.run(_seed_field_agent(harness, email="h-owner2@example.test"))
    created = _create(client, token, title="No owner yet")

    ownership = asyncio.run(harness.parcel_history.all_ownership_for(created["parcel_id"]))
    status = asyncio.run(harness.parcel_history.all_status_for(created["parcel_id"]))

    assert ownership == []
    assert len(status) == 1
    assert status[0].asserted_status == "ACTIVE"


# 2a. update_parcel changing owner fields writes exactly one NEW ownership
# row, supersedes_id pointing at the prior one. --------------------------------

def test_update_changing_owner_writes_new_ownership_row_with_supersedes(
    harness: AppHarness, client: TestClient
) -> None:
    token = asyncio.run(_seed_field_agent(harness, email="h-owner3@example.test"))
    created = _create(
        client, token, title="Plot", current_owner_name="Original Owner",
    )
    first = asyncio.run(harness.parcel_history.all_ownership_for(created["parcel_id"]))
    assert len(first) == 1

    _update(client, token, created["parcel_id"], current_owner_name="New Owner")

    ownership = asyncio.run(harness.parcel_history.all_ownership_for(created["parcel_id"]))
    assert len(ownership) == 2
    newest = next(a for a in ownership if a.id != first[0].id)
    assert newest.asserted_holder_ref == "New Owner"
    assert newest.basis == "registrant declaration via update_parcel"
    assert newest.supersedes_id == first[0].id


# 2b. update_parcel changing only unrelated fields writes zero new ownership
# rows. -------------------------------------------------------------------------

def test_update_unrelated_field_writes_zero_ownership_rows(
    harness: AppHarness, client: TestClient
) -> None:
    token = asyncio.run(_seed_field_agent(harness, email="h-owner4@example.test"))
    created = _create(client, token, title="Plot", current_owner_name="Stays The Same")
    before = asyncio.run(harness.parcel_history.all_ownership_for(created["parcel_id"]))
    assert len(before) == 1

    _update(client, token, created["parcel_id"], address="123 New Address")

    after = asyncio.run(harness.parcel_history.all_ownership_for(created["parcel_id"]))
    assert len(after) == 1
    assert after[0].id == before[0].id


# 3. archive_parcel writes exactly one status row, supersedes_id pointing at
# the initial ACTIVE row. ---------------------------------------------------------

def test_archive_writes_one_status_row_superseding_initial(
    harness: AppHarness, client: TestClient
) -> None:
    token = asyncio.run(_seed_field_agent(harness, email="h-status1@example.test"))
    created = _create(client, token, title="To be archived")
    initial = asyncio.run(harness.parcel_history.all_status_for(created["parcel_id"]))
    assert len(initial) == 1

    _archive(client, token, created["parcel_id"])

    status = asyncio.run(harness.parcel_history.all_status_for(created["parcel_id"]))
    assert len(status) == 2
    archived_row = next(s for s in status if s.id != initial[0].id)
    assert archived_row.asserted_status == "ARCHIVED"
    assert archived_row.basis == "registrant declaration via archive_parcel"
    assert archived_row.supersedes_id == initial[0].id


# 4 & 5. Append-only enforcement (two independent DB layers) and cross-tenant
# RLS isolation on the two new tables are DB-level guarantees with no
# equivalent in an in-memory fake — rehearsed live against Postgres
# separately (same convention as RLS/uniqueness elsewhere in this suite,
# e.g. test_b3_registry.py's own note on real-concurrency testing).


# 6. Every history row's audit_ref resolves to a real AuditEntry, and that
# entry's payload is consistent with the history row it corresponds to. -------

def test_history_audit_ref_resolves_to_a_real_consistent_audit_entry(
    harness: AppHarness, client: TestClient
) -> None:
    token = asyncio.run(_seed_field_agent(harness, email="h-audit1@example.test"))
    created = _create(client, token, title="Plot", current_owner_name="Audited Owner")

    ownership = asyncio.run(harness.parcel_history.all_ownership_for(created["parcel_id"]))[0]
    status = asyncio.run(harness.parcel_history.all_status_for(created["parcel_id"]))[0]
    entries = {e.entry_id: e for e in asyncio.run(harness.audit_store.all_entries())}

    assert ownership.audit_ref in entries
    ownership_entry = entries[ownership.audit_ref]
    assert ownership_entry.action == "registry.parcel_ownership.recorded"
    assert ownership_entry.payload["asserted_holder_ref"] == ownership.asserted_holder_ref

    assert status.audit_ref in entries
    status_entry = entries[status.audit_ref]
    assert status_entry.action == "registry.parcel.created"

    assert asyncio.run(verify_chain()) is True


def test_ownership_changed_audit_ref_resolves(harness: AppHarness, client: TestClient) -> None:
    token = asyncio.run(_seed_field_agent(harness, email="h-audit2@example.test"))
    created = _create(client, token, title="Plot", current_owner_name="First Owner")
    _update(client, token, created["parcel_id"], current_owner_name="Second Owner")

    ownership = asyncio.run(harness.parcel_history.all_ownership_for(created["parcel_id"]))
    changed = next(a for a in ownership if a.asserted_holder_ref == "Second Owner")
    entries = {e.entry_id: e for e in asyncio.run(harness.audit_store.all_entries())}

    assert changed.audit_ref in entries
    assert entries[changed.audit_ref].action == "registry.parcel_ownership.changed"


def test_status_changed_audit_ref_resolves(harness: AppHarness, client: TestClient) -> None:
    token = asyncio.run(_seed_field_agent(harness, email="h-audit3@example.test"))
    created = _create(client, token, title="Plot")
    _archive(client, token, created["parcel_id"])

    status = asyncio.run(harness.parcel_history.all_status_for(created["parcel_id"]))
    archived_row = next(s for s in status if s.asserted_status == "ARCHIVED")
    entries = {e.entry_id: e for e in asyncio.run(harness.audit_store.all_entries())}

    assert archived_row.audit_ref in entries
    assert entries[archived_row.audit_ref].action == "registry.parcel_status.changed"


# 7. Migration 0011 up/down and rollback rehearsal is a live-Postgres
# verification step (no automated migration-test file exists anywhere in
# this codebase — every prior migration was rehearsed the same way, see the
# implementation report), not a pytest test.


# 8. Parcel aggregate regression: current_owner_name/current_owner_contact
# behaviour is completely unchanged — history recording is additive. ---------

def test_parcel_current_owner_reference_behavior_unchanged(
    harness: AppHarness, client: TestClient
) -> None:
    token = asyncio.run(_seed_field_agent(harness, email="h-regress1@example.test"))
    created = _create(client, token, title="Plot", current_owner_name="Reference Only")
    assert created["current_owner_name"] == "Reference Only"

    updated = _update(client, token, created["parcel_id"], current_owner_name="Updated Reference")
    assert updated["current_owner_name"] == "Updated Reference"
    # The aggregate's own reference field is still just a reference — never
    # a list, never history-shaped — exactly ADR-013 invariant #12.
    assert isinstance(updated["current_owner_name"], str)


# 9. Non-adjudication wording check is tracked separately (see
# docs/ENGINEERING_RULES.md #10 and the implementation report) — this test
# matrix does not claim to satisfy it, exactly as ADR-023 itself states.


# Definition of Done / risk register: a failure during history recording
# propagates rather than being silently swallowed — the necessary
# application-layer condition for "no orphan history row" to hold once a
# real database transaction is involved (full transactional proof is a
# live-Postgres verification step, not reproducible against an in-memory
# fake with no real rollback boundary).

def test_history_recording_failure_propagates_not_swallowed(
    harness: AppHarness, client: TestClient
) -> None:
    from app.contexts.registry.dependencies import get_parcel_history_repository

    class _RaisingHistoryRepository:
        async def record_ownership(self, assertion: object) -> object:
            raise RuntimeError("simulated history-write failure")

        async def record_status(self, assertion: object) -> object:
            raise RuntimeError("simulated history-write failure")

        async def latest_ownership(self, parcel_id: str) -> None:
            return None

        async def latest_status(self, parcel_id: str) -> None:
            return None

    token = asyncio.run(_seed_field_agent(harness, email="h-orphan1@example.test"))
    harness.app.dependency_overrides[get_parcel_history_repository] = _RaisingHistoryRepository
    try:
        with pytest.raises(RuntimeError):
            client_local = TestClient(harness.app, raise_server_exceptions=True)
            client_local.post(
                "/v1/parcels",
                json={"title": "Should not orphan"},
                headers={"Authorization": f"Bearer {token}"},
            )
    finally:
        harness.app.dependency_overrides[get_parcel_history_repository] = (
            lambda: harness.parcel_history
        )
