"""In-memory AuditStore — implements the same protocol as the real
Postgres-backed store (app.contexts.identity.adapters... audit table).
"""
from __future__ import annotations

from app.kernel.audit import GENESIS_HASH, AuditEntry


class InMemoryAuditStore:
    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    async def append(self, entry: AuditEntry) -> None:
        self._entries.append(entry)

    async def last_hash(self) -> str:
        return self._entries[-1].hash if self._entries else GENESIS_HASH

    async def all_entries(self) -> list[AuditEntry]:
        return list(self._entries)
