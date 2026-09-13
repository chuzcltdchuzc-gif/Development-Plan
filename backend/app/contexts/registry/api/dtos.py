"""Registry API request/response shapes (B3 slices 1, 3, and 4)."""
from __future__ import annotations

from enum import StrEnum

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


class SetGeometryReferenceRequest(BaseModel):
    """B3 slice 4 (docs/adr/ADR-016). `geometry_reference: null` clears
    the association; a non-null value is validated (structurally only —
    Registry never interprets its content) via the injected GeometryPort
    before being stored."""

    model_config = ConfigDict(extra="forbid")

    geometry_reference: str | None = None


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


class ParcelStatus(StrEnum):
    """The two values `app.contexts.registry.domain.parcel.Parcel.status`
    can ever hold (STATUS_ACTIVE/STATUS_ARCHIVED) — one-way, no third
    value, no code path constructs anything else (ADR-013)."""

    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class Parcel(BaseModel):
    """Response shape for every Registry endpoint that returns a parcel.
    Mirrors `parcel_service._parcel_view` field-for-field — that function,
    not this model, is the source of truth; this only makes its existing
    shape visible to OpenAPI (OpenAPI Source-of-Truth Hardening)."""

    parcel_id: str
    tenant_id: str
    country_code: str
    origin: str
    created_by: str
    status: ParcelStatus
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
    created_at: str
    updated_at: str
    archived_at: str | None = None
    geometry_reference: str | None = None
