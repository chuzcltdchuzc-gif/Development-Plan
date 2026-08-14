"""Delegation aggregate — delegated administration within a tenant (B2
slice 4, docs/adr/ADR-011).

Delegation is derived authority, never independent authority: a delegate
never has more effective authority than their delegator currently holds.
`delegation_is_effective()` is the single resolution function used by both
the hot per-request context-hydration path (app.contexts.identity.
context_hydration) and the admin-facing list/get/revoke/extend endpoints
(app.contexts.identity.application.admin_service) — one function, not two
divergent checks, so "is this delegation currently granting anything" can
never disagree between what a request actually gets and what an admin
sees when they look at it.

No `delegated_permissions` field: this platform's authorization model is
role-based (ADR-004/ADR-009), not permission-based — there is no PDP
concept to bind a fine-grained permission to, so adding the field would be
a decorative, unenforced placeholder. `scope` is a descriptive label only
(see docs/adr/ADR-011 for why it isn't independently enforced in this
slice) — delegated_roles + the hierarchy ceiling is what actually carries
and limits authority.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.contexts.identity.domain.tenant import Tenant
from app.contexts.identity.domain.user import User
from app.contexts.identity.domain.value_objects import highest_rank

STATUS_ACTIVE = "ACTIVE"
STATUS_REVOKED = "REVOKED"

VALID_SCOPES: frozenset[str] = frozenset(
    {"tenant_governance", "role_assignment", "invitation_management"}
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class Delegation:
    delegation_id: str
    tenant_id: str
    delegator_user_id: str
    delegate_user_id: str
    delegated_roles: list[str]
    scope: str
    status: str = STATUS_ACTIVE
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    expires_at: str | None = None
    revoked_at: str | None = None
    revoked_by: str | None = None

    @classmethod
    def new(
        cls,
        *,
        tenant_id: str,
        delegator_user_id: str,
        delegate_user_id: str,
        delegated_roles: list[str],
        scope: str,
        expires_at: str | None = None,
    ) -> Delegation:
        return cls(
            delegation_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            delegator_user_id=delegator_user_id,
            delegate_user_id=delegate_user_id,
            delegated_roles=list(delegated_roles),
            scope=scope,
            expires_at=expires_at,
        )

    def revoke(self, *, revoked_by: str) -> None:
        self.status = STATUS_REVOKED
        self.revoked_at = _now_iso()
        self.revoked_by = revoked_by
        self.updated_at = _now_iso()

    def extend(self, *, new_expires_at: str | None) -> None:
        self.expires_at = new_expires_at
        self.updated_at = _now_iso()


def delegation_is_effective(
    delegation: Delegation, *, delegator: User | None, tenant: Tenant | None, now: datetime
) -> tuple[bool, str | None]:
    """Fail closed on every branch: any unresolved input (missing
    delegator, missing tenant) or stale condition (expired, revoked,
    delegator no longer eligible or ranked highly enough, tenant not
    active) returns `(False, reason)`. Never raises — a delegation that
    can't be resolved simply doesn't grant anything; it never denies the
    rest of the request the way a raised exception would."""
    if delegation.status != STATUS_ACTIVE:
        return False, "revoked"
    if delegation.expires_at and datetime.fromisoformat(delegation.expires_at) <= now:
        return False, "expired"
    if not delegator or not delegator.can_authenticate():
        return False, "delegator_inactive"
    if delegator.tenant_id != delegation.tenant_id:
        # Currently unreachable (nothing mutates User.tenant_id after
        # creation, same as the equivalent guard in AuthService.
        # accept_invitation) — kept as a forward-compatible guard.
        return False, "tenant_mismatch"
    if not tenant or not tenant.is_active():
        return False, "tenant_suspended"
    if highest_rank(delegation.delegated_roles) > highest_rank(delegator.roles):
        return False, "authority_lost"
    return True, None
