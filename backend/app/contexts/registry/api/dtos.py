"""Registry API request/response shapes (B3 slice 1)."""
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
