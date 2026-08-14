"""Invitation aggregate — tenant membership provisioning (B2).

A governance-role principal invites a specific email into their own tenant
at a role no higher than their own rank (the same hierarchy rule
AdminService.assign_role enforces for existing users — see
app.contexts.identity.domain.value_objects.highest_rank). The invited
person has no local account yet, so the invitation itself, not a
role-assignment call, is what carries the intended tenant and role.

The token is opaque and only its hash is persisted, exactly like a refresh
token (app.kernel.security.tokens) — a database read alone must not yield
a redeemable invitation.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

STATUS_PENDING = "PENDING"
STATUS_ACCEPTED = "ACCEPTED"
STATUS_REVOKED = "REVOKED"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class Invitation:
    invitation_id: str
    tenant_id: str
    invited_email: str
    role: str
    invited_by: str
    token_hash: str
    expires_at: str
    status: str = STATUS_PENDING
    created_at: str = field(default_factory=_now_iso)
    accepted_at: str | None = None
    revoked_at: str | None = None

    @classmethod
    def new(
        cls,
        *,
        tenant_id: str,
        invited_email: str,
        role: str,
        invited_by: str,
        token_hash: str,
        expires_at: str,
    ) -> Invitation:
        return cls(
            invitation_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            invited_email=invited_email,
            role=role,
            invited_by=invited_by,
            token_hash=token_hash,
            expires_at=expires_at,
        )

    def is_redeemable_at(self, when: datetime) -> bool:
        return self.status == STATUS_PENDING and datetime.fromisoformat(self.expires_at) > when

    def accept(self) -> None:
        self.status = STATUS_ACCEPTED
        self.accepted_at = _now_iso()

    def revoke(self) -> None:
        self.status = STATUS_REVOKED
        self.revoked_at = _now_iso()
