"""Evidence Actor Attribution HTTP API —
`/v1/evidence/{evidence_id}/attributions` and
`/v1/evidence/attributions/{attribution_id}/corrections` (GD-012, as
amended by GD-013).

Mirrors `test_evidence_api.py`'s own division of labor: authorization,
tenant isolation, request validation, and response shape are proven at the
HTTP layer here; the application-service's own authorization/validation/
lineage/audit-staging logic is already proven directly against
`EvidenceActorAttributionService` in `test_evidence_actor_attribution_service.py`
and is not re-derived here. Real-transaction properties (one shared
session, commit-before-response, forced-commit-failure, concurrent
corrections, and the SQLSTATE/constraint-name-gated 409 translation) can
only be proven against a real PostgreSQL database and are covered in
`tests/live/test_evidence_attribution_http_live.py` — not here.
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy.exc import IntegrityError as SAIntegrityError

from app.contexts.evidence.api.attribution_dtos import (
    ActorReferenceKind,
    ActorType,
    AttributionRole,
    CorrectAttributionRequest,
)
from app.contexts.evidence.api.attribution_router import (
    _integrity_diagnostics,
    _is_supersedes_once_violation,
    correct_evidence_attribution,
)
from app.contexts.evidence.domain.evidence_record import EvidenceRecord
from app.contexts.identity.domain.tenant import Tenant
from app.contexts.identity.domain.user import User
from app.contexts.identity.ports import IdentityProviderTokens
from app.kernel.context import ExecutionContext
from tests.app_factory import AppHarness, build_test_app
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


async def _seed_evidence(
    harness: AppHarness, *, tenant_id: str, parcel_id: str, uploaded_by: str
) -> str:
    record = EvidenceRecord.new(
        tenant_id=tenant_id, parcel_id=parcel_id, uploaded_by=uploaded_by,
        filename="plan.pdf", mime_type="application/pdf", size_bytes=1024,
        storage_key=f"evidence/{tenant_id}/{parcel_id}/abc",
        basis="submitted by registrant", evidence_type="SURVEY_PLAN",
    )
    record = await harness.evidence.add(record)
    return record.evidence_id


def _record_body(**overrides: object) -> dict:
    body: dict[str, object] = {
        "attribution_role": "ORIGINATED_BY",
        "actor_reference_kind": "EXTERNAL_NAMED",
        "actor_type": "INDIVIDUAL",
        "actor_name": "A Named Surveyor",
        "basis": "named by the uploader from the document's own title block",
    }
    body.update(overrides)
    return body


def _record(
    client: TestClient, token: str | None, evidence_id: str, **overrides: object
) -> Response:
    headers = {"Authorization": f"Bearer {token}"} if token is not None else {}
    return client.post(
        f"/v1/evidence/{evidence_id}/attributions", json=_record_body(**overrides), headers=headers
    )


def _durability_snapshot(harness: AppHarness) -> tuple[int, int]:
    """(total attribution-row count, total staged-audit-event count) across
    the whole harness — used to prove a rejected mutation (GD-014
    obligation 7) leaves both counts unchanged. `evidence_attributions` is
    the same `InMemoryEvidenceActorAttributionRepository`
    `record_attribution`/`correct_attribution` write through on success;
    `attribution_audit_session.added` is the same fake session's `.add()`
    log that `audit_staged()` writes through on success (see
    `tests.app_factory`'s own docstring for why this, not
    `InMemoryAuditStore`, is the correct observable for this specific
    staged-audit path)."""
    return (
        len(harness.evidence_attributions._by_id),  # noqa: SLF001
        len(harness.attribution_audit_session.added),
    )


def _assert_durability_unchanged(harness: AppHarness, before: tuple[int, int]) -> None:
    after = _durability_snapshot(harness)
    attrs_before, audits_before = before
    attrs_after, audits_after = after
    assert attrs_after == attrs_before, (
        "a rejected mutation must not leave an unauthorized attribution row durable "
        f"(before={attrs_before}, after={attrs_after})"
    )
    assert audits_after == audits_before, (
        "a rejected mutation must not stage a successful-mutation audit event "
        f"(before={audits_before}, after={audits_after})"
    )


def _body_excluding_request_echo(response: Response) -> dict:
    """RFC-7807's `instance` field echoes the request path back to the
    caller — including whatever id they themselves supplied — so it
    legitimately differs between a nonexistent-id request and a
    cross-tenant-id request without disclosing anything the caller didn't
    already know (their own chosen id). Excluded here so the comparison
    isolates the property that actually matters: identical status, error
    type/title, and detail regardless of which condition occurred."""
    body = response.json()
    body.pop("instance", None)
    return body


def _correct(
    client: TestClient, token: str | None, attribution_id: str, **overrides: object
) -> Response:
    headers = {"Authorization": f"Bearer {token}"} if token is not None else {}
    return client.post(
        f"/v1/evidence/attributions/{attribution_id}/corrections",
        json=_record_body(basis="a better-informed correction", **overrides),
        headers=headers,
    )


async def _setup_evidence(
    harness: AppHarness, client: TestClient, *, email: str, role: str = "field_agent"
) -> tuple[str, str]:
    """Returns (token, evidence_id) for a freshly seeded user/parcel/evidence."""
    tokens, user = await _seed_user_with_role(
        harness, email=email, password="pw12345678", role=role
    )
    parcel_id = _create_parcel(client, tokens.access_token)
    evidence_id = await _seed_evidence(
        harness, tenant_id=user.tenant_id, parcel_id=parcel_id, uploaded_by=user.user_id
    )
    return tokens.access_token, evidence_id


# --- 0. Exact route inventory --------------------------------------------------


def test_exactly_two_attribution_operations_exist(harness: AppHarness) -> None:
    # `app.routes` wraps each include_router() call in an opaque
    # `_IncludedRouter` in this FastAPI version rather than flattening
    # paths directly — the generated OpenAPI schema (what
    # test_openapi_security_metadata.py's own fictional-endpoint guard
    # already uses) is the reliable way to enumerate the actual API
    # surface.
    schema = harness.app.openapi()
    attribution_paths = {
        path: tuple(sorted(methods.keys()))
        for path, methods in schema["paths"].items()
        if path.startswith("/v1/evidence/") or path.startswith("/v1/evidence{")
    }
    attribution_paths = {
        path: methods for path, methods in attribution_paths.items() if "attributions" in path
    }
    assert attribution_paths == {
        "/v1/evidence/{evidence_id}/attributions": ("post",),
        "/v1/evidence/attributions/{attribution_id}/corrections": ("post",),
    }


# --- 1. Successful record and correction ---------------------------------------


def test_successful_record_returns_201_and_minimal_response(
    harness: AppHarness, client: TestClient
) -> None:
    token, evidence_id = asyncio.run(
        _setup_evidence(harness, client, email="record1@example.test")
    )

    response = _record(client, token, evidence_id)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["evidence_id"] == evidence_id
    assert body["attribution_role"] == "ORIGINATED_BY"
    assert body["actor_name"] == "A Named Surveyor"
    assert body["is_active"] is True
    # response minimization (GD-012 §6.3)
    assert "tenant_id" not in body
    assert "audit_ref" not in body


def test_successful_correction_supersedes_the_active_head(
    harness: AppHarness, client: TestClient
) -> None:
    token, evidence_id = asyncio.run(
        _setup_evidence(harness, client, email="record2@example.test")
    )
    original = _record(client, token, evidence_id).json()

    response = _correct(client, token, original["attribution_id"], actor_name="Corrected Name")

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["supersedes_id"] == original["attribution_id"]
    assert body["actor_name"] == "Corrected Name"
    assert body["is_active"] is True
    assert "tenant_id" not in body
    assert "audit_ref" not in body


# --- 2. Authentication and authorization ---------------------------------------


def test_record_missing_auth_denied_before_service_runs(
    harness: AppHarness, client: TestClient
) -> None:
    before = _durability_snapshot(harness)
    response = _record(client, None, "does-not-matter")
    assert response.status_code == 401
    _assert_durability_unchanged(harness, before)


def test_correct_missing_auth_denied_before_service_runs(
    harness: AppHarness, client: TestClient
) -> None:
    before = _durability_snapshot(harness)
    response = _correct(client, None, "does-not-matter")
    assert response.status_code == 401
    _assert_durability_unchanged(harness, before)


def test_record_unauthorized_role_denied_before_service_runs(
    harness: AppHarness, client: TestClient
) -> None:
    """general_user holds no PARCEL_REGISTRANT_ROLES — denied at the
    router's coarse role gate before any parcel/service logic runs."""
    tokens, _ = asyncio.run(
        _seed_user_with_role(
            harness, email="plain@example.test", password="pw12345678", role="general_user"
        )
    )
    before = _durability_snapshot(harness)
    response = _record(client, tokens.access_token, "does-not-matter")
    assert response.status_code == 403
    _assert_durability_unchanged(harness, before)


def test_record_non_creator_registrant_in_same_tenant_denied(
    harness: AppHarness, client: TestClient
) -> None:
    creator_tokens, creator = asyncio.run(
        _seed_user_with_role(
            harness, email="creator@example.test", password="pw12345678", role="field_agent"
        )
    )
    parcel_id = _create_parcel(client, creator_tokens.access_token)
    evidence_id = asyncio.run(
        _seed_evidence(
            harness, tenant_id=creator.tenant_id, parcel_id=parcel_id, uploaded_by=creator.user_id
        )
    )
    colleague_tokens, _ = asyncio.run(
        _seed_user_with_role(
            harness, email="colleague@example.test", password="pw12345678",
            role="field_agent", tenant_id=creator.tenant_id,
        )
    )

    before = _durability_snapshot(harness)
    response = _record(client, colleague_tokens.access_token, evidence_id)

    assert response.status_code == 403
    _assert_durability_unchanged(harness, before)


def test_governance_role_can_record_against_any_evidence_in_tenant(
    harness: AppHarness, client: TestClient
) -> None:
    creator_tokens, creator = asyncio.run(
        _seed_user_with_role(
            harness, email="creator2@example.test", password="pw12345678", role="field_agent"
        )
    )
    parcel_id = _create_parcel(client, creator_tokens.access_token)
    evidence_id = asyncio.run(
        _seed_evidence(
            harness, tenant_id=creator.tenant_id, parcel_id=parcel_id, uploaded_by=creator.user_id
        )
    )
    officer_tokens, _ = asyncio.run(
        _seed_user_with_role(
            harness, email="officer@example.test", password="pw12345678",
            role="compliance_officer", tenant_id=creator.tenant_id,
        )
    )

    response = _record(client, officer_tokens.access_token, evidence_id)

    assert response.status_code == 201, response.text


# --- 3. Request validation -------------------------------------------------------


def test_invalid_actor_reference_combination_rejected(
    harness: AppHarness, client: TestClient
) -> None:
    token, evidence_id = asyncio.run(
        _setup_evidence(harness, client, email="invalidref@example.test")
    )

    before = _durability_snapshot(harness)
    response = _record(
        client, token, evidence_id,
        actor_reference_kind="INTERNAL_PRINCIPAL", actor_principal_id=None,
    )

    assert response.status_code == 400
    _assert_durability_unchanged(harness, before)


def test_invalid_enum_value_rejected(harness: AppHarness, client: TestClient) -> None:
    token, evidence_id = asyncio.run(
        _setup_evidence(harness, client, email="invalidenum@example.test")
    )

    before = _durability_snapshot(harness)
    response = _record(client, token, evidence_id, attribution_role="NOT_A_REAL_ROLE")

    assert response.status_code == 422
    _assert_durability_unchanged(harness, before)


def test_self_supersession_rejected(harness: AppHarness, client: TestClient) -> None:
    """The domain layer's own defensive check (EvidenceActorAttribution.new)
    — supersedes_id can never equal a freshly-generated id in practice, but
    review_method-on-a-non-REVIEWED_BY-role is a reachable analogue of the
    same "invalid combination" validation class and is exercised here as
    the router-level proof that domain ValueErrors surface as 400."""
    token, evidence_id = asyncio.run(
        _setup_evidence(harness, client, email="selfsuper@example.test")
    )

    before = _durability_snapshot(harness)
    response = _record(
        client, token, evidence_id, attribution_role="ORIGINATED_BY", review_method="desk review"
    )

    assert response.status_code == 400
    _assert_durability_unchanged(harness, before)


# --- 4. Not-found: byte-identical nonexistent vs. cross-tenant -----------------


def test_record_against_nonexistent_evidence_404(harness: AppHarness, client: TestClient) -> None:
    tokens, _ = asyncio.run(
        _seed_user_with_role(
            harness, email="nf1@example.test", password="pw12345678", role="field_agent"
        )
    )
    before = _durability_snapshot(harness)
    response = _record(client, tokens.access_token, "00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    _assert_durability_unchanged(harness, before)


def test_record_against_nonexistent_and_cross_tenant_evidence_are_byte_identical(
    harness: AppHarness, client: TestClient
) -> None:
    owner_tokens, owner = asyncio.run(
        _seed_user_with_role(
            harness, email="ownerev@example.test", password="pw12345678", role="field_agent"
        )
    )
    parcel_id = _create_parcel(client, owner_tokens.access_token)
    evidence_id = asyncio.run(
        _seed_evidence(
            harness, tenant_id=owner.tenant_id, parcel_id=parcel_id, uploaded_by=owner.user_id
        )
    )
    other_tokens, _ = asyncio.run(
        _seed_user_with_role(
            harness, email="otherev@example.test", password="pw12345678", role="field_agent"
        )
    )

    before = _durability_snapshot(harness)
    nonexistent = _record(client, other_tokens.access_token, "00000000-0000-0000-0000-000000000000")
    cross_tenant = _record(client, other_tokens.access_token, evidence_id)

    assert nonexistent.status_code == cross_tenant.status_code == 404
    assert nonexistent.headers["content-type"] == cross_tenant.headers["content-type"]
    assert _body_excluding_request_echo(nonexistent) == _body_excluding_request_echo(cross_tenant)
    _assert_durability_unchanged(harness, before)


def test_correct_against_nonexistent_and_cross_tenant_attribution_are_byte_identical(
    harness: AppHarness, client: TestClient
) -> None:
    owner_token, evidence_id = asyncio.run(
        _setup_evidence(harness, client, email="ownerattr@example.test")
    )
    original = _record(client, owner_token, evidence_id).json()
    other_tokens, _ = asyncio.run(
        _seed_user_with_role(
            harness, email="otherattr@example.test", password="pw12345678", role="field_agent"
        )
    )

    before = _durability_snapshot(harness)
    nonexistent = _correct(
        client, other_tokens.access_token, "00000000-0000-0000-0000-000000000000"
    )
    cross_tenant = _correct(client, other_tokens.access_token, original["attribution_id"])

    assert nonexistent.status_code == cross_tenant.status_code == 404
    assert nonexistent.headers["content-type"] == cross_tenant.headers["content-type"]
    assert _body_excluding_request_echo(nonexistent) == _body_excluding_request_echo(cross_tenant)
    _assert_durability_unchanged(harness, before)


# --- 5. Actor-principal existence-oracle remediation (GD-012 §6.4) -------------


def test_actor_principal_oracle_byte_identical_over_http(
    harness: AppHarness, client: TestClient
) -> None:
    token, evidence_id = asyncio.run(
        _setup_evidence(harness, client, email="oracle2@example.test")
    )
    other_tokens, other_user = asyncio.run(
        _seed_user_with_role(
            harness, email="oracle2-other@example.test", password="pw12345678", role="field_agent"
        )
    )

    before = _durability_snapshot(harness)
    nonexistent = _record(
        client, token, evidence_id,
        actor_reference_kind="INTERNAL_PRINCIPAL",
        actor_principal_id="00000000-0000-0000-0000-000000000000",
        actor_name="Nonexistent",
    )
    cross_tenant = _record(
        client, token, evidence_id,
        actor_reference_kind="INTERNAL_PRINCIPAL",
        actor_principal_id=other_user.user_id,
        actor_name="Cross-tenant",
    )

    assert nonexistent.status_code == cross_tenant.status_code == 400
    assert nonexistent.json() == cross_tenant.json()
    _assert_durability_unchanged(harness, before)


# --- 6. Non-adjudication wording ------------------------------------------------


def test_attribution_responses_emit_no_adjudication_wording(
    harness: AppHarness, client: TestClient
) -> None:
    token, evidence_id = asyncio.run(
        _setup_evidence(harness, client, email="nonadj@example.test")
    )

    response = _record(client, token, evidence_id)
    assert response.status_code == 201, response.text
    assert scan_response_text(response.json()) == []

    correction = _correct(client, token, response.json()["attribution_id"])
    assert correction.status_code == 201, correction.text
    assert scan_response_text(correction.json()) == []


# --- 7. Dual-diagnostic 409 predicate (unit-level, hermetic) -------------------


class _FakeDriverExc:
    def __init__(self, sqlstate: str | None, constraint_name: str | None) -> None:
        self.sqlstate = sqlstate
        self.constraint_name = constraint_name


class _FakeOrig:
    def __init__(self, cause: object) -> None:
        self.__cause__ = cause


class _FakeIntegrityError(Exception):
    def __init__(self, orig: object) -> None:
        super().__init__("fake integrity error")
        self.orig = orig


def test_supersedes_once_violation_detected_by_dual_diagnostic() -> None:
    exc = _FakeIntegrityError(
        _FakeOrig(_FakeDriverExc("23505", "uq_evidence_actor_attributions_supersedes_once"))
    )
    assert _integrity_diagnostics(exc) == (  # type: ignore[arg-type]
        "23505", "uq_evidence_actor_attributions_supersedes_once"
    )
    assert _is_supersedes_once_violation(exc) is True  # type: ignore[arg-type]


def test_check_constraint_violation_not_matched_despite_same_exception_class() -> None:
    """Same SQLSTATE class (23) as the unique violation, different code and
    constraint name — must not be translated to 409 (GD-013 §4)."""
    exc = _FakeIntegrityError(
        _FakeOrig(_FakeDriverExc("23514", "ck_evidence_actor_attributions_no_self_supersede"))
    )
    assert _is_supersedes_once_violation(exc) is False  # type: ignore[arg-type]


def test_matching_constraint_name_but_wrong_sqlstate_not_matched() -> None:
    exc = _FakeIntegrityError(
        _FakeOrig(_FakeDriverExc("23503", "uq_evidence_actor_attributions_supersedes_once"))
    )
    assert _is_supersedes_once_violation(exc) is False  # type: ignore[arg-type]


def test_matching_sqlstate_but_wrong_constraint_name_not_matched() -> None:
    exc = _FakeIntegrityError(_FakeOrig(_FakeDriverExc("23505", "uq_something_else")))
    assert _is_supersedes_once_violation(exc) is False  # type: ignore[arg-type]


def test_missing_diagnostics_do_not_crash_and_do_not_match() -> None:
    exc = _FakeIntegrityError(orig=None)
    assert _integrity_diagnostics(exc) == (None, None)  # type: ignore[arg-type]
    assert _is_supersedes_once_violation(exc) is False  # type: ignore[arg-type]


# --- 8. Rollback-failure propagation (GD-014 §5.4 / obligation 5) --------------


def _real_supersedes_once_integrity_error() -> SAIntegrityError:
    """Builds an actual `sqlalchemy.exc.IntegrityError` instance (so the
    router's own `except IntegrityError` clause catches it, unlike the
    plain-Exception `_FakeIntegrityError` above, which is only ever
    inspected directly by the predicate functions) carrying the exact
    dual-diagnostic pair `_is_supersedes_once_violation` requires — mirrors
    `tests/live/test_evidence_attribution_http_live.py::
    test_unrelated_unique_violation_not_translated_to_409`'s own
    fake-driver-exception shape."""

    class _FakeDriverExc:
        sqlstate = "23505"
        constraint_name = "uq_evidence_actor_attributions_supersedes_once"

    class _FakeOrig:
        __cause__ = _FakeDriverExc()

    exc = SAIntegrityError("stmt", {}, Exception("orig"))
    exc.orig = _FakeOrig()  # type: ignore[assignment]
    return exc


class _RollbackFailingSession:
    """A fake `service.session` whose `rollback()` itself raises — GD-014
    §5.4 requires that this failure propagate as-is, never be swallowed
    behind a misleading HTTP 409."""

    def __init__(self) -> None:
        self.rollback_called = False

    async def rollback(self) -> None:
        self.rollback_called = True
        raise RuntimeError("GD-014 obligation 5 proof: simulated rollback failure")


class _SupersedesOnceRaisingService:
    """Fake `EvidenceActorAttributionService` stand-in whose
    `correct_attribution` raises the exact exception the router's
    GD-013/GD-014 translation branch is authorized to catch — isolating
    the router's own rollback-failure handling (attribution_router.py)
    from the real service/repository stack, which obligation 5 does not
    concern."""

    def __init__(self, session: object) -> None:
        self.session = session

    async def correct_attribution(self, **_kwargs: object) -> dict:
        raise _real_supersedes_once_integrity_error()


def test_rollback_failure_propagates_and_is_not_masked_as_409() -> None:
    """GD-014 §5.4 / obligation 5 (hermetic): once the dual-diagnostic
    `IntegrityError` branch is entered and `service.session.rollback()`
    itself raises, that exception must propagate unmodified — not be
    caught and replaced with `HTTPException(409)`, which would misleadingly
    imply the session's own state had been verified clean. Calls the
    router's `correct_evidence_attribution` coroutine directly (an ordinary
    async function, not routed through FastAPI's DI here) so the proof
    isolates exactly the router's own except-clause behavior, per GD-014
    §5.4's own required-proof wording."""
    session = _RollbackFailingSession()
    service = _SupersedesOnceRaisingService(session)
    ctx = ExecutionContext(principal_id="does-not-matter", tenant_id="does-not-matter")
    body = CorrectAttributionRequest(
        attribution_role=AttributionRole.ORIGINATED_BY,
        actor_reference_kind=ActorReferenceKind.EXTERNAL_NAMED,
        actor_type=ActorType.INDIVIDUAL,
        basis="GD-014 obligation 5 proof",
    )

    async def _invoke() -> None:
        await correct_evidence_attribution(
            attribution_id="does-not-matter",
            body=body,
            ctx=ctx,
            service=service,  # type: ignore[arg-type]
        )

    with pytest.raises(RuntimeError, match="simulated rollback failure"):
        asyncio.run(_invoke())

    assert session.rollback_called is True, (
        "the rollback branch must actually have been reached for this proof to be meaningful"
    )
