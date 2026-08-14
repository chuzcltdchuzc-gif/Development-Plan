"""Parcel aggregate — the canonical, single authoritative representation of
a land parcel (B3 slice 1, docs/adr/ADR-013; mutation commands added B3
slice 3, docs/adr/ADR-015; geometry association added B3 slice 4,
docs/adr/ADR-016).

`parcel_id` is immutable identity, set once at construction. `parcel_number`
is a separate concept, populated by Slice 2's atomic allocator
(docs/adr/ADR-014) — `allocate_parcel_number()` guards the invariant "once
allocated, never reassigned."

Ownership is modeled as a *current reference* only
(`current_owner_name`/`current_owner_contact`) — deliberately distinct from
an ownership *history*, which is a later slice's responsibility and must
never be conflated with "who owns it now" (ADR-013 invariant #12).
`update_details()` may change this reference; it never changes `created_by`
(ADR-015: creator/registrant identity and current ownership are distinct
concepts, and must stay that way for a future ownership-transfer command
to be additive rather than a refactor).

Authorization (who may call `update_details`/`archive`/`set_geometry_reference`
on a given parcel) is entirely the caller's responsibility (ParcelService,
ADR-015) — this aggregate enforces only domain-level invariants: archived
parcels are immutable (`_ensure_mutable`), and only the fields in
`UPDATABLE_FIELDS` may ever change outside of creation/allocation/geometry
association.

`geometry_reference` (ADR-016) is an opaque pointer to a future Spatial
Intelligence context's own geometry data — never a polygon, coordinate
pair, or PostGIS type, and never interpreted here. It is an *association*,
not part of this aggregate's core business invariants (ADR-016's aggregate
boundary), the same "reserved pointer" pattern ADR-013 used for
`parcel_number` before ADR-014 populated it.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

STATUS_ACTIVE = "ACTIVE"
STATUS_ARCHIVED = "ARCHIVED"

# B3 slice 3 (docs/adr/ADR-015): the exhaustive set of fields a mutation
# command may ever touch — registry metadata and the current-ownership
# *reference* (not history, ADR-013 invariant #12). Deliberately excludes
# parcel_id, tenant_id, country_code, origin, created_by, created_at
# (permanently immutable) and status/parcel_number (guarded by their own
# dedicated methods, never by update_details). Living on the aggregate,
# not only in the API DTO, so "which fields can change" is a domain
# invariant even if a second entry point into update_details is ever
# added.
UPDATABLE_FIELDS: frozenset[str] = frozenset(
    {
        "title",
        "address",
        "state",
        "lga",
        "ward",
        "community",
        "property_type",
        "size_sqm",
        "ownership_type",
        "current_owner_name",
        "current_owner_contact",
    }
)


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
    geometry_reference: str | None = None

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

    def update_details(self, *, updated_by: str, fields: dict[str, object]) -> None:
        """B3 slice 3 (docs/adr/ADR-015) — the first real mutation command.
        `fields` must be a subset of UPDATABLE_FIELDS; the caller
        (ParcelService) is responsible for authorization (creator or
        governance role) before this is ever called — this method enforces
        only the domain-level invariants: archived parcels are immutable,
        and only registry-metadata/current-ownership-reference fields may
        ever change here."""
        self._ensure_mutable()
        unknown = set(fields) - UPDATABLE_FIELDS
        if unknown:
            raise ValueError(f"cannot update fields: {sorted(unknown)}")
        for key, value in fields.items():
            setattr(self, key, value)
        self.updated_by = updated_by
        self.updated_at = _now_iso()

    def archive(self, *, archived_by: str) -> None:
        """One-way ACTIVE -> ARCHIVED (ADR-013: status is terminal; no
        restore command exists — see ADR-015). Authorization (creator or
        governance role) is the caller's responsibility, exactly like
        update_details."""
        self._ensure_mutable()
        self.status = STATUS_ARCHIVED
        self.archived_at = _now_iso()
        self.updated_by = archived_by
        self.updated_at = self.archived_at

    def set_geometry_reference(self, *, geometry_reference: str | None, updated_by: str) -> None:
        """B3 slice 4 (docs/adr/ADR-016) — associates (or clears, when
        `geometry_reference` is None) this parcel with an opaque geometry
        reference owned entirely by a future Spatial Intelligence
        capability. Registry never validates or interprets what the
        reference contains beyond what the injected GeometryPort decides
        (ParcelService's responsibility, not this aggregate's) — this
        method only enforces that archived parcels remain immutable, the
        same guard every other mutator uses."""
        self._ensure_mutable()
        self.geometry_reference = geometry_reference
        self.updated_by = updated_by
        self.updated_at = _now_iso()
