"""Evidence HTTP API — /v1/parcels/{parcel_id}/evidence (B5 IMVP-5, the
first real Evidence HTTP surface). Covers authorization, tenant isolation,
file policy, and failure semantics at the HTTP layer; hash/storage/
integrity/rollback mechanics themselves are already proven directly
against EvidenceService in tests/test_evidence_upload.py and are not
re-derived here — this file proves the *router* wires them correctly
(auth, parcel-authorization, request validation, response shape), the
same division of labor test_b3_registry.py already documents for
Registry.
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from app.contexts.evidence.application.evidence_service import EvidenceIntegrityError
from app.contexts.evidence.dependencies import get_storage_port
from app.contexts.identity.domain.tenant import Tenant
from app.contexts.identity.domain.user import User
from app.contexts.identity.ports import IdentityProviderTokens
from tests.app_factory import AppHarness, build_test_app
from tests.fakes.storage import InMemoryStoragePort
from tests.support.non_adjudication import scan_response_text


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
        identity_subject=subject, email=email, full_name="Seed User", country="NG",
        tenant_id=tenant_id,
    )
    user.roles = [role]
    user = await harness.users.add(user)
    if tenant_id is None:
        await harness.tenants.add(Tenant.new(name="Seed Tenant", tenant_id=user.tenant_id))
    idp_tokens = await harness.identity_provider.authenticate(email=email, password=password)
    return idp_tokens, user


def _create_parcel(client: TestClient, token: str) -> str:
    response = client.post(
        "/v1/parcels",
        json={"address": "12 Green Estate Rd", "state": "Imo", "lga": "Owerri",
              "size_sqm": 500, "property_type": "residential", "current_owner_name": "A Owner"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201, response.text
    return response.json()["parcel_id"]


def _upload(
    client: TestClient, token: str | None, parcel_id: str, *,
    content: bytes = b"%PDF-1.4 fake survey plan content",
    content_type: str = "application/pdf",
    filename: str = "survey.pdf",
    evidence_type: str = "SURVEY_PLAN",
    basis: str = "submitted by registrant as supporting survey documentation",
) -> Response:
    headers = {"Content-Type": content_type}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    return client.post(
        f"/v1/parcels/{parcel_id}/evidence",
        params={"filename": filename, "evidence_type": evidence_type, "basis": basis},
        content=content,
        headers=headers,
    )


def _list(client: TestClient, token: str | None, parcel_id: str) -> Response:
    headers = {"Authorization": f"Bearer {token}"} if token is not None else {}
    return client.get(f"/v1/parcels/{parcel_id}/evidence", headers=headers)


# --- 1. Authorized upload succeeds, reaches HASHED, associates correctly ------


def test_authorized_upload_succeeds_and_reaches_hashed(
    harness: AppHarness, client: TestClient
) -> None:
    tokens, user = asyncio.run(
        _seed_user_with_role(
            harness, email="agent1@example.test", password="pw12345678", role="field_agent"
        )
    )
    parcel_id = _create_parcel(client, tokens.access_token)

    response = _upload(client, tokens.access_token, parcel_id)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "HASHED"
    assert body["sha256"] is not None and len(body["sha256"]) == 64
    assert body["parcel_id"] == parcel_id
    assert body["uploaded_by"] == user.user_id  # server-derived, never client-supplied
    assert body["filename"] == "survey.pdf"
    assert body["evidence_type"] == "SURVEY_PLAN"
    # storage-internal / audit-internal fields are not exposed
    assert "storage_key" not in body
    assert "tenant_id" not in body
    assert "audit_ref" not in body


def test_list_returns_uploaded_evidence_in_deterministic_order(
    harness: AppHarness, client: TestClient
) -> None:
    tokens, _ = asyncio.run(
        _seed_user_with_role(
            harness, email="agent2@example.test", password="pw12345678", role="field_agent"
        )
    )
    parcel_id = _create_parcel(client, tokens.access_token)
    first = _upload(client, tokens.access_token, parcel_id, filename="a.pdf")
    second = _upload(client, tokens.access_token, parcel_id, filename="b.pdf")

    response = _list(client, tokens.access_token, parcel_id)

    assert response.status_code == 200
    body = response.json()
    assert [e["evidence_id"] for e in body] == [
        second.json()["evidence_id"], first.json()["evidence_id"]
    ]  # newest first, matching InMemoryEvidenceRepository/PostgresEvidenceRepository ordering


# --- 2. Auth denial -----------------------------------------------------------


def test_upload_missing_auth_denied(client: TestClient) -> None:
    response = _upload(client, None, "does-not-matter")
    assert response.status_code == 401


def test_upload_invalid_auth_denied(client: TestClient) -> None:
    response = _upload(client, "not-a-real-token", "does-not-matter")
    assert response.status_code == 401


def test_list_missing_auth_denied(client: TestClient) -> None:
    response = _list(client, None, "does-not-matter")
    assert response.status_code == 401


def test_upload_unauthorized_role_denied(harness: AppHarness, client: TestClient) -> None:
    """general_user holds no PARCEL_REGISTRANT_ROLES — denied at the
    router's coarse role gate before any parcel/service logic runs."""
    tokens, _ = asyncio.run(
        _seed_user_with_role(
            harness, email="plain@example.test", password="pw12345678", role="general_user"
        )
    )
    response = _upload(client, tokens.access_token, "does-not-matter")
    assert response.status_code == 403


# --- 3. Tenant isolation -------------------------------------------------------


def test_rejected_cross_tenant_upload_never_invokes_storage_adapter(
    harness: AppHarness, client: TestClient
) -> None:
    """ADR-027 §10.2/§11: proves the one authorization boundary that
    actually exists (PDP/PEP + EvidenceService's tenant/parcel check) runs
    to completion, and denies, before StoragePort is ever reached — not an
    assertion about Storage RLS, which does not exist during the pilot
    (SupabaseStorageAdapter has no tenant check of its own; see
    tests/test_supabase_storage_adapter.py). InMemoryStoragePort's
    list_keys("") returns every object ever written, so an empty result
    after a denied request is direct evidence Storage was never called."""
    owner_tokens, _ = asyncio.run(
        _seed_user_with_role(
            harness, email="storage-owner@example.test", password="pw12345678", role="field_agent"
        )
    )
    parcel_id = _create_parcel(client, owner_tokens.access_token)
    other_tokens, _ = asyncio.run(
        _seed_user_with_role(
            harness, email="storage-other@example.test", password="pw12345678", role="field_agent"
        )
    )

    response = _upload(client, other_tokens.access_token, parcel_id)

    assert response.status_code == 404
    assert asyncio.run(harness.storage.list_keys("")) == []


def test_cross_tenant_upload_denied(harness: AppHarness, client: TestClient) -> None:
    owner_tokens, _ = asyncio.run(
        _seed_user_with_role(
            harness, email="owner@example.test", password="pw12345678", role="field_agent"
        )
    )
    parcel_id = _create_parcel(client, owner_tokens.access_token)
    other_tokens, _ = asyncio.run(
        _seed_user_with_role(
            harness, email="other@example.test", password="pw12345678", role="field_agent"
        )
    )

    response = _upload(client, other_tokens.access_token, parcel_id)

    assert response.status_code == 404  # the parcel itself is invisible, not merely forbidden


def test_cross_tenant_list_denied(harness: AppHarness, client: TestClient) -> None:
    owner_tokens, _ = asyncio.run(
        _seed_user_with_role(
            harness, email="owner2@example.test", password="pw12345678", role="field_agent"
        )
    )
    parcel_id = _create_parcel(client, owner_tokens.access_token)
    other_tokens, _ = asyncio.run(
        _seed_user_with_role(
            harness, email="other2@example.test", password="pw12345678", role="field_agent"
        )
    )

    response = _list(client, other_tokens.access_token, parcel_id)

    assert response.status_code == 404


def test_non_creator_registrant_in_same_tenant_denied(
    harness: AppHarness, client: TestClient
) -> None:
    """Same tenant, same registrant role, but not the parcel's creator and
    no governance role — the fine-grained creator-or-governance check
    (mirroring ADR-015/ADR-022) denies, distinct from the coarse role gate
    above."""
    creator_tokens, creator = asyncio.run(
        _seed_user_with_role(
            harness, email="creator@example.test", password="pw12345678", role="field_agent"
        )
    )
    parcel_id = _create_parcel(client, creator_tokens.access_token)
    colleague_tokens, _ = asyncio.run(
        _seed_user_with_role(
            harness, email="colleague@example.test", password="pw12345678",
            role="field_agent", tenant_id=creator.tenant_id,
        )
    )

    response = _upload(client, colleague_tokens.access_token, parcel_id)

    assert response.status_code == 403


def test_governance_role_can_upload_to_any_parcel_in_tenant(
    harness: AppHarness, client: TestClient
) -> None:
    creator_tokens, creator = asyncio.run(
        _seed_user_with_role(
            harness, email="creator2@example.test", password="pw12345678", role="field_agent"
        )
    )
    parcel_id = _create_parcel(client, creator_tokens.access_token)
    officer_tokens, _ = asyncio.run(
        _seed_user_with_role(
            harness, email="officer@example.test", password="pw12345678",
            role="compliance_officer", tenant_id=creator.tenant_id,
        )
    )

    response = _upload(client, officer_tokens.access_token, parcel_id)

    assert response.status_code == 201, response.text


# --- 4. File policy -------------------------------------------------------------


def test_unsupported_mime_type_rejected(harness: AppHarness, client: TestClient) -> None:
    tokens, _ = asyncio.run(
        _seed_user_with_role(
            harness, email="mime@example.test", password="pw12345678", role="field_agent"
        )
    )
    parcel_id = _create_parcel(client, tokens.access_token)

    response = _upload(client, tokens.access_token, parcel_id, content_type="application/zip")

    assert response.status_code == 400


def test_oversized_upload_rejected(harness: AppHarness, client: TestClient) -> None:
    tokens, _ = asyncio.run(
        _seed_user_with_role(
            harness, email="big@example.test", password="pw12345678", role="field_agent"
        )
    )
    parcel_id = _create_parcel(client, tokens.access_token)

    oversized = b"0" * (10 * 1024 * 1024 + 1)
    response = _upload(client, tokens.access_token, parcel_id, content=oversized)

    assert response.status_code == 413


def test_empty_upload_rejected(harness: AppHarness, client: TestClient) -> None:
    """A truly zero-length body is indistinguishable, on the wire, from no
    body at all — FastAPI's own required `Body(...)` parameter rejects it
    with 422 before the handler (or EvidenceService's own "uploaded content
    is empty" 400 guard) ever runs. Both layers agree the request is
    rejected; only the status code differs by which layer caught it."""
    tokens, _ = asyncio.run(
        _seed_user_with_role(
            harness, email="empty@example.test", password="pw12345678", role="field_agent"
        )
    )
    parcel_id = _create_parcel(client, tokens.access_token)

    response = _upload(client, tokens.access_token, parcel_id, content=b"")

    assert response.status_code == 422


def test_malformed_parcel_id_denied_not_500(harness: AppHarness, client: TestClient) -> None:
    tokens, _ = asyncio.run(
        _seed_user_with_role(
            harness, email="malformed@example.test", password="pw12345678", role="field_agent"
        )
    )
    response = _upload(client, tokens.access_token, "not-a-real-parcel-id")
    assert response.status_code == 404


# --- 5. Failure/integrity semantics — no falsely-successful record -----------


def test_storage_failure_yields_error_not_falsely_successful_record(
    harness: AppHarness, client: TestClient
) -> None:
    tokens, _ = asyncio.run(
        _seed_user_with_role(
            harness, email="storagefail@example.test", password="pw12345678", role="field_agent"
        )
    )
    parcel_id = _create_parcel(client, tokens.access_token)
    harness.storage.fail_next_put = RuntimeError("simulated storage outage")

    # An unhandled exception propagates through TestClient rather than
    # becoming a response object — the same convention
    # test_registry_ownership_status_history.py's own fault-injection test
    # already establishes for this test suite.
    with pytest.raises(RuntimeError, match="simulated storage outage"):
        _upload(client, tokens.access_token, parcel_id)

    list_response = _list(client, tokens.access_token, parcel_id)
    assert list_response.json() == []  # no record was ever created


def test_read_back_hash_mismatch_yields_error_not_hashed_record(
    harness: AppHarness, client: TestClient
) -> None:
    class _CorruptingStoragePort(InMemoryStoragePort):
        async def get(self, key: str) -> bytes:
            data = await super().get(key)
            return data + b"\x00"

    tokens, _ = asyncio.run(
        _seed_user_with_role(
            harness, email="corrupt@example.test", password="pw12345678", role="field_agent"
        )
    )
    parcel_id = _create_parcel(client, tokens.access_token)
    harness.app.dependency_overrides[get_storage_port] = lambda: _CorruptingStoragePort()

    with pytest.raises(EvidenceIntegrityError):
        _upload(client, tokens.access_token, parcel_id)

    list_response = _list(client, tokens.access_token, parcel_id)
    body = list_response.json()
    assert len(body) == 1
    assert body[0]["status"] == "RECEIVED"  # never advanced to HASHED
    assert body[0]["sha256"] is None


def test_failed_upload_writes_no_successful_audit_event(
    harness: AppHarness, client: TestClient
) -> None:
    tokens, _ = asyncio.run(
        _seed_user_with_role(
            harness, email="auditfail@example.test", password="pw12345678", role="field_agent"
        )
    )
    parcel_id = _create_parcel(client, tokens.access_token)
    harness.storage.fail_next_put = RuntimeError("simulated storage outage")

    with pytest.raises(RuntimeError, match="simulated storage outage"):
        _upload(client, tokens.access_token, parcel_id)

    entries = asyncio.run(harness.audit_store.all_entries())
    assert not any(e.action == "evidence.uploaded" for e in entries)


def test_successful_upload_writes_expected_audit_entries(
    harness: AppHarness, client: TestClient
) -> None:
    tokens, user = asyncio.run(
        _seed_user_with_role(
            harness, email="auditok@example.test", password="pw12345678", role="field_agent"
        )
    )
    parcel_id = _create_parcel(client, tokens.access_token)

    _upload(client, tokens.access_token, parcel_id)

    entries = asyncio.run(harness.audit_store.all_entries())
    actions = [e.action for e in entries if e.resource_type == "evidence_record"]
    assert "evidence.uploaded" in actions
    assert "evidence.hashed" in actions
    uploaded = next(e for e in entries if e.action == "evidence.uploaded")
    assert uploaded.payload["parcel_id"] == parcel_id
    assert "Bearer" not in str(uploaded.payload)  # no token/secret ever enters the audit payload


def test_evidence_responses_emit_no_adjudication_wording(
    harness: AppHarness, client: TestClient
) -> None:
    """Engineering Rule #10 (LV-000 v1.8 Article IV §4), extended to
    Evidence's real HTTP surface for the first time (B5.0b's own deferred
    follow-up — Rule #10 previously only covered Registry, since Evidence
    had no HTTP surface to scan). RECEIVED/HASHED are storage-integrity
    states; this proves neither the upload nor the list response ever
    implies a legal/ownership determination."""
    tokens, _ = asyncio.run(
        _seed_user_with_role(
            harness, email="nonadj@example.test", password="pw12345678", role="field_agent"
        )
    )
    parcel_id = _create_parcel(client, tokens.access_token)

    upload_response = _upload(client, tokens.access_token, parcel_id)
    assert upload_response.status_code == 201, upload_response.text
    assert scan_response_text(upload_response.json()) == []

    list_response = _list(client, tokens.access_token, parcel_id)
    assert list_response.status_code == 200
    assert scan_response_text(list_response.json()) == []


def test_worm_sealing_never_invoked_by_upload(harness: AppHarness, client: TestClient) -> None:
    """IMVP-5 never calls seal()/put_immutable — proven here by spying on
    the storage fake, not merely by inspecting the router's code."""
    calls = {"put_immutable": 0}
    real_put_immutable = InMemoryStoragePort.put_immutable

    async def spying_put_immutable(
        self: InMemoryStoragePort, *args: object, **kwargs: object
    ) -> None:
        calls["put_immutable"] += 1
        await real_put_immutable(self, *args, **kwargs)  # type: ignore[arg-type]

    InMemoryStoragePort.put_immutable = spying_put_immutable  # type: ignore[method-assign]
    try:
        tokens, _ = asyncio.run(
            _seed_user_with_role(
                harness, email="worm@example.test", password="pw12345678", role="field_agent"
            )
        )
        parcel_id = _create_parcel(client, tokens.access_token)
        response = _upload(client, tokens.access_token, parcel_id)
        assert response.status_code == 201, response.text
    finally:
        InMemoryStoragePort.put_immutable = real_put_immutable  # type: ignore[method-assign]

    assert calls["put_immutable"] == 0
