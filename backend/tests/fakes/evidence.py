"""In-memory fake for the Evidence ports — implements the exact same
protocol as PostgresEvidenceRepository (app.contexts.evidence.adapters), so
application-service tests exercise real business logic without a live
database.
"""
from __future__ import annotations

from copy import deepcopy

from app.contexts.evidence.domain.evidence_record import EvidenceRecord
from app.contexts.evidence.ports import ParcelAuthorityInfo
from tests.fakes.registry import InMemoryParcelRepository


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


class FakeEvidenceParcelExistencePort:
    """Wraps the SAME InMemoryParcelRepository instance the test harness
    gives to Registry — mirrors tests.fakes.spatial.FakeParcelExistencePort
    exactly, so a test can create a real parcel via Registry's own
    endpoints and immediately upload/list Evidence against that exact
    parcel_id."""

    def __init__(self, parcels: InMemoryParcelRepository) -> None:
        self._parcels = parcels

    async def get_parcel_authority(self, *, parcel_id: str) -> ParcelAuthorityInfo | None:
        parcel = await self._parcels.get(parcel_id)
        if parcel is None:
            return None
        return ParcelAuthorityInfo(tenant_id=parcel.tenant_id, created_by=parcel.created_by)
