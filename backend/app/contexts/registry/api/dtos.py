"""Registry API request/response shapes (B3 slices 1 and 3)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CreateParcelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    country_code: str | None = None
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


class UpdateParcelRequest(BaseModel):
    """B3 slice 3 (docs/adr/ADR-015). Every field is genuinely optional —
    the router calls `model_dump(exclude_unset=True)`, so only fields the
    caller actually sent are passed to ParcelService.update_parcel,
    letting a client both omit a field (leave unchanged) and explicitly
    send `null` (clear it), which CreateParcelRequest's shape can't
    distinguish and doesn't need to. Matches Parcel.UPDATABLE_FIELDS
    exactly — extra="forbid" rejects any other field name at the API
    boundary, before the domain-level allow-list is ever consulted."""

    model_config = ConfigDict(extra="forbid")

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
