"""In-memory fake for the Evidence ports — implements the exact same
protocol as PostgresEvidenceRepository (app.contexts.evidence.adapters), so
application-service tests exercise real business logic without a live
database.
"""
from __future__ import annotations

from copy import deepcopy

from app.contexts.evidence.domain.evidence_record import EvidenceRecord


class InMemoryEvidenceRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, EvidenceRecord] = {}
        # One-shot failure injection (B5 Slice B5.3 test matrix — "repository
        # failure"), same shape as InMemoryStoragePort's — set, consumed by
        # the next matching call, then cleared.
        self.fail_next_add: BaseException | None = None
        self.fail_next_mark_hashed: BaseException | None = None

    async def add(self, record: EvidenceRecord) -> EvidenceRecord:
        if self.fail_next_add is not None:
            exc, self.fail_next_add = self.fail_next_add, None
            raise exc
        self._by_id[record.evidence_id] = deepcopy(record)
        return deepcopy(record)

    async def get(self, evidence_id: str) -> EvidenceRecord | None:
        record = self._by_id.get(evidence_id)
        return deepcopy(record) if record else None

    async def list_for_parcel(self, parcel_id: str) -> list[EvidenceRecord]:
        return sorted(
            (deepcopy(r) for r in self._by_id.values() if r.parcel_id == parcel_id),
            key=lambda r: r.created_at,
            reverse=True,
        )

    async def mark_hashed(self, record: EvidenceRecord) -> EvidenceRecord:
        if self.fail_next_mark_hashed is not None:
            exc, self.fail_next_mark_hashed = self.fail_next_mark_hashed, None
            raise exc
        if record.evidence_id not in self._by_id:
            raise ValueError(f"evidence record {record.evidence_id} not found")
        self._by_id[record.evidence_id] = deepcopy(record)
        return deepcopy(record)

    async def seal(self, record: EvidenceRecord) -> EvidenceRecord:
        if record.evidence_id not in self._by_id:
            raise ValueError(f"evidence record {record.evidence_id} not found")
        self._by_id[record.evidence_id] = deepcopy(record)
        return deepcopy(record)

    async def set_legal_hold(self, record: EvidenceRecord) -> EvidenceRecord:
        if record.evidence_id not in self._by_id:
            raise ValueError(f"evidence record {record.evidence_id} not found")
        self._by_id[record.evidence_id] = deepcopy(record)
        return deepcopy(record)
