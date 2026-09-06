"""Real Supabase Storage adapter for StoragePort (B5 IMVP-5,
docs/adr/ADR-025-supabase-platform-baseline.md E3 — "Supabase Storage
becomes the primary adapter" for ordinary, non-WORM evidence).

Uses `httpx` directly against Supabase Storage's REST API — the identical
pattern app.contexts.identity.adapters.supabase.SupabaseJWKSProvider
already uses for Supabase Auth's REST API — not a dedicated Supabase SDK.
No new dependency was introduced for this adapter (Engineering Rule 5):
`httpx` is already pinned in pyproject.toml.

Security model — governed by docs/adr/
ADR-027-supabase-storage-authorization-and-tenant-isolation.md (Accepted),
not by ADR-025 E2, which describes Postgres RLS only and was never a
decision about Storage's own trust model. Stated plainly, per that ADR's
own §10.0: this backend authenticates to Storage as *itself*, using a
server-side-only service-role key — it never forwards a caller's own
Supabase JWT to Storage. FastAPI's existing PDP/PEP (require_auth/
require_role, unchanged) is the *sole* tenant-authorization boundary for
Evidence Storage, decided entirely before this adapter is ever called
(app.contexts.evidence.application.evidence_service's own
_load_parcel_authority_in_scope/_can_mutate checks). The private bucket's
Storage policies (infra/supabase/evidence_bucket.sql) grant nothing to
`anon`/`authenticated` and so are bypassed entirely by this adapter's
service-role key — **there is no second, independent enforcement layer
here**, unlike Postgres, where RLS is a same-connection backstop behind
the PDP/PEP decision. This adapter performs no tenant validation of its
own, by design; a key naming one tenant and a key naming another are
handled identically (see test_adapter_accepts_any_key_without_tenant_check
in tests/test_supabase_storage_adapter.py). This asymmetry is an accepted,
named, self-expiring pilot exception under ADR-027 §10.1 — bounded to a
single Evidence-storage tenant, all access through FastAPI, no
browser/client-direct Storage path — not a claim of parity with Postgres's
two-layer model, and not a new architecture decision made by this file.

This adapter provides ordinary (non-WORM) storage only. `put_immutable`/
`worm_grade` fail closed (`NotImplementedError`) — Supabase Storage has no
Object-Lock/WORM primitive; pretending otherwise would be exactly the
"fake WORM at the storage layer" defect ADR-007's own founding motivation
exists to prevent. Cloudflare R2 (WORM-grade sealing) remains a separate,
unbuilt adapter, out of scope until B5.4 — ADR-027 does not authorize it.
"""
from __future__ import annotations

from datetime import datetime

import httpx

from app.contexts.evidence.ports import StorageObjectNotFoundError, WormGrade


class SupabaseStorageAdapter:
    def __init__(
        self,
        *,
        project_url: str,
        service_role_key: str,
        bucket: str,
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._object_base = f"{project_url.rstrip('/')}/storage/v1/object"
        self._bucket = bucket
        self._timeout = timeout_seconds
        # Test-only seam (tests/test_supabase_storage_adapter.py uses
        # httpx.MockTransport — already part of the pinned httpx package,
        # no new dependency): production never passes this, so
        # httpx.AsyncClient's own real transport is always used there,
        # identical to every call site below before this parameter existed.
        self._transport = transport
        # Never logged, never included in any exception message below —
        # only ever sent as this adapter's own outbound Authorization
        # header, exactly like SupabaseJWKSProvider's own httpx usage.
        self._headers = {"Authorization": f"Bearer {service_role_key}"}

    def _object_url(self, key: str) -> str:
        return f"{self._object_base}/{self._bucket}/{key}"

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self._timeout, transport=self._transport)

    async def put(self, key: str, data: bytes, *, content_type: str | None = None) -> None:
        """Write (or overwrite) `key`. This adapter never seals anything
        (see module docstring), so the "was this key already sealed"
        branch StoragePort's own docstring describes can never trigger
        here — there is no code path on this adapter that ever marks a
        key sealed."""
        headers = {
            **self._headers,
            "Content-Type": content_type or "application/octet-stream",
            "x-upsert": "true",
        }
        async with self._client() as client:
            response = await client.post(self._object_url(key), headers=headers, content=data)
        response.raise_for_status()

    async def get(self, key: str) -> bytes:
        async with self._client() as client:
            response = await client.get(self._object_url(key), headers=self._headers)
        if response.status_code == 404:
            raise StorageObjectNotFoundError(key)
        response.raise_for_status()
        return response.content

    async def list_keys(self, prefix: str) -> list[str]:
        folder, _, leaf_prefix = prefix.rpartition("/")
        async with self._client() as client:
            response = await client.post(
                f"{self._object_base}/list/{self._bucket}",
                headers={**self._headers, "Content-Type": "application/json"},
                json={"prefix": folder},
            )
        response.raise_for_status()
        names = sorted(
            f"{folder}/{item['name']}" if folder else item["name"]
            for item in response.json()
            if item.get("name", "").startswith(leaf_prefix)
        )
        return names

    async def put_immutable(
        self,
        key: str,
        data: bytes,
        *,
        retention_until: datetime,
        content_type: str | None = None,
    ) -> None:
        raise NotImplementedError(
            "SupabaseStorageAdapter provides no WORM/immutable-retention guarantee "
            "(ADR-025 E3 — Supabase Storage is the ordinary-evidence adapter only; "
            "Cloudflare R2 is the WORM-grade adapter, not yet implemented, B5.4)."
        )

    def worm_grade(self) -> WormGrade:
        raise NotImplementedError(
            "SupabaseStorageAdapter has no WORM grade — it is not a sealing adapter."
        )


__all__ = ["SupabaseStorageAdapter"]
