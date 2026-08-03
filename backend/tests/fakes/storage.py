"""In-memory fake for StoragePort (B5 Slice B5.1, app.contexts.evidence.ports)
— implements the exact same protocol a real Supabase Storage / Cloudflare R2
adapter would, so future Evidence application-service tests can exercise real
upload/seal business logic without live cloud infrastructure or credentials.

Real adapters are not implemented yet (see app.contexts.evidence.ports'
module docstring) — this fake is, for now, the only StoragePort
implementation in this codebase, and it enforces the one guarantee that
actually matters for testing "sealed evidence cannot be altered"
(docs/EXECUTION_PLAN.md Phase-3 gate text): once a key is sealed via
put_immutable, no further put/put_immutable against that key succeeds,
regardless of caller. It does not model real cloud latency, partial
failure, or eventual consistency — those are exactly the properties a live
rehearsal against real infrastructure (not this fake) must prove, per
docs/ENGINEERING_RULES.md rule 7.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.contexts.evidence.ports import (
    StorageImmutabilityViolationError,
    StorageObjectNotFoundError,
    WormGrade,
)


@dataclass(frozen=True)
class _StoredObject:
    data: bytes
    content_type: str | None
    sealed: bool
    retention_until: datetime | None


class InMemoryStoragePort:
    def __init__(self, *, worm_grade: WormGrade = "governance") -> None:
        self._objects: dict[str, _StoredObject] = {}
        self._grade: WormGrade = worm_grade

    async def put(self, key: str, data: bytes, *, content_type: str | None = None) -> None:
        existing = self._objects.get(key)
        if existing is not None and existing.sealed:
            raise StorageImmutabilityViolationError(key)
        self._objects[key] = _StoredObject(
            data=data, content_type=content_type, sealed=False, retention_until=None
        )

    async def get(self, key: str) -> bytes:
        obj = self._objects.get(key)
        if obj is None:
            raise StorageObjectNotFoundError(key)
        return obj.data

    async def list_keys(self, prefix: str) -> list[str]:
        return sorted(k for k in self._objects if k.startswith(prefix))

    async def put_immutable(
        self,
        key: str,
        data: bytes,
        *,
        retention_until: datetime,
        content_type: str | None = None,
    ) -> None:
        existing = self._objects.get(key)
        if existing is not None and existing.sealed:
            raise StorageImmutabilityViolationError(key)
        self._objects[key] = _StoredObject(
            data=data, content_type=content_type, sealed=True, retention_until=retention_until
        )

    def worm_grade(self) -> WormGrade:
        return self._grade

    def is_sealed(self, key: str) -> bool:
        """Test-only introspection, not part of StoragePort itself — lets a
        test assert seal state without relying on exception timing."""
        obj = self._objects.get(key)
        return obj is not None and obj.sealed
