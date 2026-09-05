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
SERVICE_ROLE_KEY = "test-service-role-key-do-not-log-me"
BUCKET = "evidence"


def _adapter(transport: httpx.MockTransport) -> SupabaseStorageAdapter:
    return SupabaseStorageAdapter(
        project_url=PROJECT_URL,
        service_role_key=SERVICE_ROLE_KEY,
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
    assert request.headers["authorization"] == f"Bearer {SERVICE_ROLE_KEY}"
    assert request.headers["content-type"] == "application/pdf"
    assert request.headers["x-upsert"] == "true"
    assert request.content == b"hello"


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
        assert request.headers["authorization"] == f"Bearer {SERVICE_ROLE_KEY}"
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


async def test_put_immutable_fails_closed_not_implemented() -> None:
    from datetime import UTC, datetime

    adapter = _adapter(httpx.MockTransport(lambda r: httpx.Response(200)))
    with pytest.raises(NotImplementedError, match="no WORM"):
        await adapter.put_immutable("key", b"data", retention_until=datetime.now(UTC))


def test_worm_grade_fails_closed_not_implemented() -> None:
    adapter = _adapter(httpx.MockTransport(lambda r: httpx.Response(200)))
    with pytest.raises(NotImplementedError, match="no WORM grade"):
        adapter.worm_grade()
