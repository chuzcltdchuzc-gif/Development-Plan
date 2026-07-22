"""In-memory fake for the Registry ports — implements the exact same
protocol as the real Postgres adapter (app.contexts.registry.adapters),
so application-service tests exercise real business logic without a live
database.
"""
from __future__ import annotations

from copy import deepcopy

from app.contexts.registry.domain.parcel import Parcel


class InMemoryParcelRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, Parcel] = {}

    async def add(self, parcel: Parcel) -> Parcel:
        self._by_id[parcel.parcel_id] = deepcopy(parcel)
        return deepcopy(parcel)

    async def get(self, parcel_id: str) -> Parcel | None:
        parcel = self._by_id.get(parcel_id)
        return deepcopy(parcel) if parcel else None

    async def list_for_tenant(self, tenant_id: str) -> list[Parcel]:
        return sorted(
            (deepcopy(p) for p in self._by_id.values() if p.tenant_id == tenant_id),
            key=lambda p: p.created_at,
            reverse=True,
        )

    async def update(self, parcel: Parcel) -> Parcel:
        self._by_id[parcel.parcel_id] = deepcopy(parcel)
        return deepcopy(parcel)


class InMemoryParcelNumberAllocator:
    """Mirrors PostgresParcelNumberAllocator's per-country_code, 1-based
    counter and formatting exactly, for deterministic unit tests. NOT a
    substitute for the real concurrency proof — asyncio's cooperative
    scheduling means a plain dict increment here (no `await` between read
    and write) can never exercise the row-locking behavior the real
    adapter depends on; that is verified live, against real Postgres, with
    genuinely concurrent connections (docs/adr/ADR-014's completion
    report)."""

    def __init__(self) -> None:
        self._counters: dict[str, int] = {}

    async def allocate(self, *, country_code: str) -> str:
        next_value = self._counters.get(country_code, 0) + 1
        self._counters[country_code] = next_value
        return f"LV-{country_code}-{next_value:06d}"


class FakeGeometryPort:
    """Configurable in-memory GeometryPort (B3 slice 4, docs/adr/ADR-016;
    signature amended B4, docs/adr/ADR-019). Defaults to always-valid,
    matching production's PlaceholderGeometryAdapter; tests can construct
    with `always_valid=False` to prove ParcelService actually consults the
    port's answer rather than merely wiring it decoratively. `calls`
    records every reference the port was asked about (geometry_reference
    only, matching the pre-amendment recording shape — tenant_id/parcel_id
    are accepted per the amended signature but deliberately not recorded,
    so no existing test assertion needed to change), so a test can also
    assert the port was (or wasn't) invoked."""

    def __init__(self, *, always_valid: bool = True) -> None:
        self.always_valid = always_valid
        self.calls: list[str] = []

    async def reference_is_valid(
        self, *, geometry_reference: str, tenant_id: str, parcel_id: str
    ) -> bool:
        self.calls.append(geometry_reference)
        return self.always_valid
