"""SupabaseStorageAdapter — request-building/response-parsing/error-
translation contract tests (B5 IMVP-5), using `httpx.MockTransport`
(already part of the pinned `httpx` dependency — no new package). Proves
the adapter builds correct requests and translates responses/errors
without live Supabase Storage credentials or network access.

Does not, and cannot, prove real Supabase Storage's own actual behavior
(auth enforcement, bucket policies, real latency/failure modes) — that is
exactly what Engineering Rule 7's live rehearsal is for, and this
environment has no live Supabase project to rehearse against (see the
IMVP-5 implementation report's "live Supabase integration status").
"""
from __future__ import annotations

import httpx
import pytest

from app.contexts.evidence.adapters.supabase_storage import SupabaseStorageAdapter
from app.contexts.evidence.ports import StorageObjectNotFoundError

PROJECT_URL = "https://test-project.supabase.test"
# Shaped like a modern Supabase secret key (sb_secret_...): an opaque,
# non-JWT string. Deliberately NOT dot-separated, so it must never be sent
# as a Bearer token (see module docstring of supabase_storage.py and
# https://supabase.com/docs/guides/api/api-keys: "send publishable and
# secret keys on the apikey header, not on Authorization: Bearer").
SERVICE_ROLE_KEY = "test-service-role-key-do-not-log-me"
# Shaped like a legacy service_role JWT: three dot-separated segments.
# Not a real signed token — only its *shape* matters to the adapter's
# format-detection logic under test.
LEGACY_JWT_SERVICE_ROLE_KEY = "test-header.test-payload.test-signature"
BUCKET = "evidence"


def _adapter(
    transport: httpx.MockTransport, *, key: str = SERVICE_ROLE_KEY
) -> SupabaseStorageAdapter:
    return SupabaseStorageAdapter(
        project_url=PROJECT_URL,
        service_role_key=key,
        bucket=BUCKET,
        transport=transport,
    )


async def test_put_sends_correct_request_and_upserts() -> None:
    captured: dict[str, httpx.Request] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return httpx.Response(200, json={"Key": f"{BUCKET}/some/key"})

    key = "tenants/t1/parcels/p1/evidence/e1/object"
    adapter = _adapter(httpx.MockTransport(handler))
    await adapter.put(key, b"hello", content_type="application/pdf")

    request = captured["request"]
    assert request.method == "POST"
    assert request.url == f"{PROJECT_URL}/storage/v1/object/{BUCKET}/{key}"
    assert request.headers["apikey"] == SERVICE_ROLE_KEY
    assert request.headers["content-type"] == "application/pdf"
    assert request.headers["x-upsert"] == "true"
    assert request.content == b"hello"


async def test_put_sends_modern_secret_key_only_via_apikey_never_as_bearer() -> None:
    """Supabase's current API-key docs: a non-JWT secret/publishable key
    sent as `Authorization: Bearer` fails the gateway's JWT parsing before
    reaching this project's own routing — the "Invalid Compact JWS" failure
    this fix exists to prevent for real (non-JWT) credentials."""
    captured: dict[str, httpx.Request] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return httpx.Response(200, json={"Key": "x"})

    adapter = _adapter(httpx.MockTransport(handler))
    await adapter.put("key", b"data")

    headers = captured["request"].headers
    assert headers["apikey"] == SERVICE_ROLE_KEY
    assert "authorization" not in headers


async def test_put_sends_legacy_jwt_key_via_both_apikey_and_bearer() -> None:
    """Backward compatibility: Supabase's docs confirm legacy service_role
    JWT keys "remain valid until you disable them" — a JWT-shaped
    credential still gets Authorization: Bearer, alongside apikey."""
    captured: dict[str, httpx.Request] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return httpx.Response(200, json={"Key": "x"})

    adapter = _adapter(httpx.MockTransport(handler), key=LEGACY_JWT_SERVICE_ROLE_KEY)
    await adapter.put("key", b"data")

    headers = captured["request"].headers
    assert headers["apikey"] == LEGACY_JWT_SERVICE_ROLE_KEY
    assert headers["authorization"] == f"Bearer {LEGACY_JWT_SERVICE_ROLE_KEY}"


async def test_put_default_content_type_when_none_given() -> None:
    captured: dict[str, httpx.Request] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return httpx.Response(200, json={"Key": "x"})

    adapter = _adapter(httpx.MockTransport(handler))
    await adapter.put("key", b"data")

    assert captured["request"].headers["content-type"] == "application/octet-stream"


async def test_put_raises_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"message": "not authorized"})

    adapter = _adapter(httpx.MockTransport(handler))
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await adapter.put("key", b"data")
    assert SERVICE_ROLE_KEY not in str(exc_info.value)


async def test_get_returns_bytes() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.headers["apikey"] == SERVICE_ROLE_KEY
        return httpx.Response(200, content=b"the stored bytes")

    adapter = _adapter(httpx.MockTransport(handler))
    result = await adapter.get("tenants/t1/parcels/p1/evidence/e1/object")

    assert result == b"the stored bytes"


async def test_get_missing_object_raises_not_found() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "not_found"})

    adapter = _adapter(httpx.MockTransport(handler))
    with pytest.raises(StorageObjectNotFoundError):
        await adapter.get("missing-key")


async def test_get_raises_on_server_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "internal"})

    adapter = _adapter(httpx.MockTransport(handler))
    with pytest.raises(httpx.HTTPStatusError):
        await adapter.get("key")


async def test_list_keys_filters_by_prefix_and_sorts() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert "/storage/v1/object/list/" in str(request.url)
        return httpx.Response(
            200,
            json=[
                {"name": "e2-object"},
                {"name": "e1-object"},
                {"name": "unrelated-object"},
            ],
        )

    adapter = _adapter(httpx.MockTransport(handler))
    keys = await adapter.list_keys("tenants/t1/parcels/p1/evidence/e1")

    assert keys == ["tenants/t1/parcels/p1/evidence/e1-object"]


async def test_adapter_accepts_any_key_without_tenant_check() -> None:
    """Documents ADR-027 §10.0/§11 as an executable invariant, not just a
    docstring claim: this adapter performs no tenant authorization of its
    own. A key naming one tenant and a key naming a completely different
    tenant, written through the same service-role-authenticated adapter
    instance, are handled identically — there is no code path here that
    could accept one and deny the other. The one real tenant boundary is
    EvidenceService's, proven in tests/test_evidence_api.py, not this
    adapter's."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"Key": "x"})

    adapter = _adapter(httpx.MockTransport(handler))

    await adapter.put("tenants/tenant-a/parcels/p1/evidence/e1/object", b"data")
    await adapter.put("tenants/tenant-b/parcels/p9/evidence/e9/object", b"data")
    # No further assertion is possible or meaningful — both calls simply
    # succeeding, with no tenant-comparison logic anywhere in the adapter
    # to have denied either one, is the invariant under test.


def test_adapter_never_accepts_a_per_call_caller_token() -> None:
    """ADR-027 §10.1/§3 (Option A): this adapter authenticates to Storage
    only as itself, via one fixed service-role key set at construction —
    it never forwards a caller's own Supabase JWT (that would be Option
    B's dual-enforcement design, not yet built, gated on ADR-027 §10.4/
    §10.5). Asserted structurally so a future change cannot silently add a
    per-call caller-token parameter without this test being touched."""
    import inspect

    init_params = set(inspect.signature(SupabaseStorageAdapter.__init__).parameters)
    assert init_params == {
        "self", "project_url", "service_role_key", "bucket", "timeout_seconds", "transport",
    }
    for method_name in ("put", "get", "list_keys"):
        method_params = set(
            inspect.signature(getattr(SupabaseStorageAdapter, method_name)).parameters
        )
        assert not method_params & {"caller_token", "jwt", "user_token", "access_token"}


async def test_put_immutable_fails_closed_not_implemented() -> None:
    from datetime import UTC, datetime

    adapter = _adapter(httpx.MockTransport(lambda r: httpx.Response(200)))
    with pytest.raises(NotImplementedError, match="no WORM"):
        await adapter.put_immutable("key", b"data", retention_until=datetime.now(UTC))


def test_worm_grade_fails_closed_not_implemented() -> None:
    adapter = _adapter(httpx.MockTransport(lambda r: httpx.Response(200)))
    with pytest.raises(NotImplementedError, match="no WORM grade"):
        adapter.worm_grade()
