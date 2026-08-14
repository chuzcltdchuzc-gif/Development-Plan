"""Engineering Rules #10 — non-adjudication automated check.

LV-000 v1.8 Article IV §4: "The platform shall carry an automated check that fails the build on
ownership-adjudication wording in API responses and user-facing text." Implements exactly and only
`docs/PHASE-9_IMPLEMENTATION_PLAN.md` (approved plan) — two independent scanning layers (static
source, real API response content), both sharing the single blocklist in
`tests/support/non_adjudication.py`. Test functions below map directly to the plan's §11 test
matrix; each test's docstring cites the matrix item(s) it satisfies.

Nothing here touches ADR-023, the Parcel aggregate, authorization, or any B1-B4 behaviour — every
non-scanner assertion exercises endpoints exactly as the rest of the Registry suite already does
(`tests/app_factory.py`'s in-memory-fake harness).
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.app_factory import AppHarness, build_test_app
from tests.support.non_adjudication import (
    collect_static_sites,
    find_violations,
    scan_response_text,
    scan_static_sources,
)

APP_ROOT = Path(__file__).resolve().parent.parent / "app"


# ---------------------------------------------------------------------------
# Item 1 — static scan of real source finds no adjudication wording today.
# ---------------------------------------------------------------------------


def test_static_source_scan_finds_no_adjudication_wording() -> None:
    hits = scan_static_sources(APP_ROOT)
    detail = "; ".join(
        f"{site.file}:{site.line} ({site.kind}) matched {violations}" for site, violations in hits
    )
    assert hits == [], f"adjudication wording found in developer-authored source: {detail}"


# ---------------------------------------------------------------------------
# Items 2, 3, 6 — real Registry endpoints, real (including "Owner"-containing)
# caller-submitted data, no adjudicating wording in any response.
# ---------------------------------------------------------------------------


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
        email=email, password="pw12345678", full_name="Non-Adjudication Test User"
    )
    user = User.new(
        keycloak_subject=subject,
        email=email,
        full_name="Non-Adjudication Test User",
        country="NG",
    )
    user.roles = ["field_agent"]
    user = await harness.users.add(user)
    await harness.tenants.add(
        Tenant.new(name="Non-Adjudication Test Tenant", tenant_id=user.tenant_id)
    )
    tokens = await harness.identity_provider.authenticate(email=email, password="pw12345678")
    return tokens.access_token


def test_real_registry_endpoints_emit_no_adjudication_wording(
    harness: AppHarness, client: TestClient
) -> None:
    """Items 2, 3: create/get/update/archive against real endpoints — no response contains
    blocklisted wording. Item 6: `current_owner_name` deliberately contains the word "Owner" as
    ordinary caller-submitted data ("Ade Owens", "Owner's Court Estate Holdings") — this must NOT
    be flagged, since the scan targets developer-authored prose, never echoed user data."""
    token = asyncio.run(_seed_field_agent(harness, email="nonadj-1@example.test"))
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/v1/parcels",
        json={
            "title": "Non-adjudication check parcel",
            "current_owner_name": "Ade Owens",
            "current_owner_contact": "+234-000-0000",
        },
        headers=headers,
    )
    assert create_response.status_code == 201, create_response.text
    parcel = create_response.json()
    assert scan_response_text(parcel) == []

    get_response = client.get(f"/v1/parcels/{parcel['parcel_id']}", headers=headers)
    assert get_response.status_code == 200, get_response.text
    assert scan_response_text(get_response.json()) == []

    update_response = client.patch(
        f"/v1/parcels/{parcel['parcel_id']}",
        json={"current_owner_name": "Owner's Court Estate Holdings"},
        headers=headers,
    )
    assert update_response.status_code == 200, update_response.text
    assert scan_response_text(update_response.json()) == []

    archive_response = client.post(f"/v1/parcels/{parcel['parcel_id']}/archive", headers=headers)
    assert archive_response.status_code == 200, archive_response.text
    assert scan_response_text(archive_response.json()) == []

    list_response = client.get("/v1/parcels", headers=headers)
    assert list_response.status_code == 200, list_response.text
    assert scan_response_text(list_response.json()) == []


# ---------------------------------------------------------------------------
# Item 7 — existing legitimate error messages are not misclassified.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "existing_detail_text",
    [
        "only the parcel's creator or a governance role may modify it",
        "parcel not found",
        "no fields to update",
        "size_sqm must be positive",
        "geometry_reference failed validation",
        "caller has no tenant to register a parcel within",
    ],
)
def test_existing_error_messages_are_not_misclassified(existing_detail_text: str) -> None:
    assert find_violations(existing_detail_text) == []


# ---------------------------------------------------------------------------
# Item 4 — static scanner actually detects an injected violation.
# ---------------------------------------------------------------------------


def test_static_scanner_detects_injected_adjudication_wording(tmp_path: Path) -> None:
    """Proves the static-scan pipeline (AST extraction + phrase match) can actually detect a
    violation, not merely find none because none exists. Writes a synthetic file mimicking a
    router under a temporary `api/` directory — never touches real source."""
    poisoned_api_dir = tmp_path / "api"
    poisoned_api_dir.mkdir()
    poisoned_file = poisoned_api_dir / "adversarial_router.py"
    poisoned_file.write_text(
        "from fastapi import HTTPException\n"
        "\n"
        "def confirm(parcel_id: str) -> None:\n"
        "    raise HTTPException(\n"
        '        status_code=200, detail="This is the confirmed owner of the parcel"\n'
        "    )\n",
        encoding="utf-8",
    )

    hits = scan_static_sources(tmp_path)

    assert len(hits) == 1
    site, violations = hits[0]
    assert site.kind == "http_exception_detail"
    assert "confirmed owner" in violations


# ---------------------------------------------------------------------------
# Item 5 — response-content scanner actually detects an injected violation.
# ---------------------------------------------------------------------------


def test_response_scan_detects_injected_adjudication_wording() -> None:
    """Proves the response-content scan pipeline (JSON flatten + phrase match) can actually
    detect a violation in a synthetic payload — a test double for what a compromised endpoint
    would return, never a real response."""
    poisoned_payload = {
        "parcel_id": "test-parcel",
        "note": "LandVault confirms ownership of this parcel.",
    }

    violations = scan_response_text(poisoned_payload)

    assert "confirms ownership" in violations
    assert "landvault confirms ownership" in violations


# ---------------------------------------------------------------------------
# Item 8 — ADR-021 spatial classification vocabulary is not misclassified.
# ---------------------------------------------------------------------------


def test_blocklist_does_not_flag_spatial_conflict_classification_vocabulary() -> None:
    """ADR-021's six-category spatial classification vocabulary ("confirmed conflict" — a
    geometric finding, never an ownership determination, per that ADR's own §5) must not be
    misclassified as ownership-adjudication wording, in either scanning layer. No spatial
    conflict-detection code exists yet (B4 Slice 3 remains unauthorized, unrelated to and not
    advanced by this test) — this exercises the blocklist design directly against that future
    vocabulary so the boundary is proven before that code is ever written."""
    spatial_response_payload = {
        "classification": "confirmed conflict",
        "detail": (
            "two geometries overlap; this finding is evidence for a governance investigation, "
            "never an automated determination"
        ),
    }
    assert scan_response_text(spatial_response_payload) == []

    for phrase in (
        "confirmed conflict",
        "no conflict",
        "boundary overlap",
        "duplicate",
        "near duplicate",
        "suspicious pattern",
    ):
        assert find_violations(phrase) == []


# ---------------------------------------------------------------------------
# Internal (non-`api/`) docstrings are out of scope by design.
# ---------------------------------------------------------------------------


def test_internal_non_api_docstrings_are_not_scanned(tmp_path: Path) -> None:
    """Internal application/domain-layer docstrings discuss adjudication as a concept
    extensively (e.g. the real `app/contexts/registry/domain/history.py` module docstring) but
    are never returned to an API caller — only `api/`-directory docstrings are OpenAPI-exposed
    and therefore in scope (`docs/PHASE-9_IMPLEMENTATION_PLAN.md` §6.2). `HTTPException detail=`
    and `description=` are still scanned regardless of directory (checked by the other tests
    above) — only bare docstrings are directory-scoped."""
    internal_dir = tmp_path / "application"
    internal_dir.mkdir()
    internal_file = internal_dir / "service.py"
    internal_file.write_text(
        '"""This module never claims to have determined the true owner of anything — it only '
        'records assertions."""\n'
        "\n"
        "def noop() -> None:\n"
        "    pass\n",
        encoding="utf-8",
    )

    sites = collect_static_sites(tmp_path)

    assert sites == []
