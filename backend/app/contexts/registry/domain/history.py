"""Ownership and status assertion value objects (B3, docs/adr/ADR-023).

Pure value objects — no I/O, no persistence concerns. Constructed by
ParcelService, persisted through ParcelHistoryRepository. Neither is part
of the Parcel aggregate's own mutable state (ADR-023 "Domain layer") —
Parcel.update_details()/archive() continue to know nothing about history
recording, exactly as today.

Each field records an *assertion* — who asserted what, on what basis, when
— never a determination of who owns the parcel (LV-000 v1.8 Article IV).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class OwnershipAssertion:
    id: str
    tenant_id: str
    parcel_id: str
    asserted_holder_ref: str | None
    basis: str
    recorded_by: str
    audit_ref: str | None
    supersedes_id: str | None = None
    recorded_at: str = field(default_factory=_now_iso)

    @classmethod
    def new(
        cls,
        *,
        tenant_id: str,
        parcel_id: str,
        asserted_holder_ref: str | None,
        basis: str,
        recorded_by: str,
        audit_ref: str | None,
        supersedes_id: str | None = None,
    ) -> OwnershipAssertion:
        return cls(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            parcel_id=parcel_id,
            asserted_holder_ref=asserted_holder_ref,
            basis=basis,
            recorded_by=recorded_by,
            audit_ref=audit_ref,
            supersedes_id=supersedes_id,
        )


@dataclass(frozen=True)
class StatusAssertion:
    id: str
    tenant_id: str
    parcel_id: str
    asserted_status: str
    basis: str
    recorded_by: str
    audit_ref: str | None
    supersedes_id: str | None = None
    recorded_at: str = field(default_factory=_now_iso)

    @classmethod
    def new(
        cls,
        *,
        tenant_id: str,
        parcel_id: str,
        asserted_status: str,
        basis: str,
        recorded_by: str,
        audit_ref: str | None,
        supersedes_id: str | None = None,
    ) -> StatusAssertion:
        return cls(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            parcel_id=parcel_id,
            asserted_status=asserted_status,
            basis=basis,
            recorded_by=recorded_by,
            audit_ref=audit_ref,
            supersedes_id=supersedes_id,
        )
