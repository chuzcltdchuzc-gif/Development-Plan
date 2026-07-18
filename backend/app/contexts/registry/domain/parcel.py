"""Parcel aggregate — the canonical, single authoritative representation of
a land parcel (B3 slice 1, docs/adr/ADR-013).

`parcel_id` is immutable identity, set once at construction. `parcel_number`
is a separate concept: reserved here as a guarded field for Slice 2's real
atomic allocator to populate — `allocate_parcel_number()` exists now,
unused by any Slice 1 code path, so the invariant "once allocated, never
reassigned" is a domain rule from day one, not a retrofit once the
allocator lands.

Ownership is modeled as a *current reference* only
(`current_owner_name`/`current_owner_contact`) — deliberately distinct from
an ownership *history*, which is a later slice's responsibility and must
never be conflated with "who owns it now" (ADR-013 invariant #12).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

STATUS_ACTIVE = "ACTIVE"
STATUS_ARCHIVED = "ARCHIVED"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class ParcelArchivedError(Exception):
    """Raised when a mutation is attempted against an archived parcel
    (ADR-013 invariant #6: archived parcels cannot be modified)."""


@dataclass
class Parcel:
    parcel_id: str
    tenant_id: str
    country_code: str
    origin: str
    created_by: str
    status: str = STATUS_ACTIVE
    parcel_number: str | None = None
    title: str | None = None
    address: str | None = None
    state: str | None = None
    lga: str | None = None
    ward: str | None = None
    community: str | None = None
    property_type: str | None = None
    size_sqm: float | None = None
    ownership_type: str | None = None
    current_owner_name: str | None = None
    current_owner_contact: str | None = None
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    updated_by: str | None = None
    archived_at: str | None = None

    @classmethod
    def new(
        cls,
        *,
        tenant_id: str,
        country_code: str,
        origin: str,
        created_by: str,
        title: str | None = None,
        address: str | None = None,
        state: str | None = None,
        lga: str | None = None,
        ward: str | None = None,
        community: str | None = None,
        property_type: str | None = None,
        size_sqm: float | None = None,
        ownership_type: str | None = None,
        current_owner_name: str | None = None,
        current_owner_contact: str | None = None,
    ) -> Parcel:
        return cls(
            parcel_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            country_code=country_code,
            origin=origin,
            created_by=created_by,
            title=title,
            address=address,
            state=state,
            lga=lga,
            ward=ward,
            community=community,
            property_type=property_type,
            size_sqm=size_sqm,
            ownership_type=ownership_type,
            current_owner_name=current_owner_name,
            current_owner_contact=current_owner_contact,
        )

    def is_archived(self) -> bool:
        return self.status == STATUS_ARCHIVED

    def _ensure_mutable(self) -> None:
        """Every mutator on this aggregate must call this first — the one
        guard every future mutation command (Slice 3+) inherits, so
        "archived parcels cannot be modified" is enforced structurally,
        not re-implemented per command."""
        if self.is_archived():
            raise ParcelArchivedError("cannot modify an archived parcel")

    def allocate_parcel_number(self, parcel_number: str) -> None:
        """Reserved for Slice 2's real atomic allocator — not called by any
        Slice 1 code path. Guards the invariant "parcel number, once
        allocated, can never be reassigned" (ADR-013 #2)."""
        self._ensure_mutable()
        if self.parcel_number is not None:
            raise ValueError("parcel_number already allocated; cannot be reassigned")
        self.parcel_number = parcel_number
        self.updated_at = _now_iso()
