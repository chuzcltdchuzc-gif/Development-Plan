"""Tenant aggregate (B2 slice 3 — docs/adr/ADR-010).

Promotes `tenant_id` from an unstructured string into a first-class
aggregate with its own lifecycle. `Tenant.tenant_id` deliberately keeps the
exact same string identity that `User.tenant_id` and `Invitation.tenant_id`
already use — this is a backward-compatible extension (a new FK target),
not a remapping of any existing id.

Lifecycle: ACTIVE <-> SUSPENDED -> ARCHIVED (one-way out of ARCHIVED, same
"archive is terminal" convention as the Registry aggregate, ADR-005).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

STATUS_ACTIVE = "ACTIVE"
STATUS_SUSPENDED = "SUSPENDED"
STATUS_ARCHIVED = "ARCHIVED"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class Tenant:
    tenant_id: str
    name: str
    owner_user_id: str | None = None
    status: str = STATUS_ACTIVE
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    suspended_at: str | None = None
    suspension_reason: str | None = None
    archived_at: str | None = None

    @classmethod
    def new(
        cls, *, name: str, owner_user_id: str | None = None, tenant_id: str | None = None
    ) -> Tenant:
        return cls(
            tenant_id=tenant_id or str(uuid.uuid4()),
            name=name.strip(),
            owner_user_id=owner_user_id,
        )

    def is_active(self) -> bool:
        return self.status == STATUS_ACTIVE

    def suspend(self, *, reason: str) -> None:
        if self.status == STATUS_ARCHIVED:
            raise ValueError("cannot suspend an archived tenant")
        self.status = STATUS_SUSPENDED
        self.suspension_reason = reason
        self.suspended_at = _now_iso()
        self.updated_at = _now_iso()

    def reactivate(self) -> None:
        if self.status == STATUS_ARCHIVED:
            raise ValueError("cannot reactivate an archived tenant")
        self.status = STATUS_ACTIVE
        self.suspension_reason = None
        self.suspended_at = None
        self.updated_at = _now_iso()

    def archive(self) -> None:
        self.status = STATUS_ARCHIVED
        self.archived_at = _now_iso()
        self.updated_at = _now_iso()
