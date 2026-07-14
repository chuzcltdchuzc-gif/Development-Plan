"""User aggregate — Identity context's canonical authority on who a
principal is. Authentication adapters (Keycloak) verify credentials; this
aggregate owns roles, status, and tenant/country/org scope.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.contexts.identity.domain.value_objects import ALL_ROLES, AccountStatus, Role


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class User:
    """User aggregate root. `keycloak_subject` is the IdP's stable `sub`
    claim — the join point between our data and the IdP's (docs/adr/ADR-004
    consequence: this join must exist since we no longer issue tokens)."""

    user_id: str
    keycloak_subject: str
    email: str
    full_name: str
    country: str
    tenant_id: str
    roles: list[str] = field(default_factory=lambda: [Role.GENERAL_USER.value])
    account_status: str = AccountStatus.ACTIVE.value
    organization_id: str | None = None
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    last_login_at: str | None = None
    suspension_reason: str | None = None
    version: int = 1

    @classmethod
    def new(
        cls,
        *,
        keycloak_subject: str,
        email: str,
        full_name: str,
        country: str,
        tenant_id: str | None = None,
        organization_id: str | None = None,
    ) -> User:
        return cls(
            user_id="usr_" + uuid.uuid4().hex,
            keycloak_subject=keycloak_subject,
            email=email.strip().lower(),
            full_name=full_name.strip(),
            country=country.upper(),
            tenant_id=tenant_id or "ten_" + uuid.uuid4().hex,
            organization_id=organization_id,
        )

    def can_authenticate(self) -> bool:
        return self.account_status == AccountStatus.ACTIVE.value

    def mark_logged_in(self) -> None:
        self.last_login_at = _now_iso()
        self.updated_at = self.last_login_at

    def suspend(self, *, reason: str) -> None:
        self.account_status = AccountStatus.SUSPENDED.value
        self.suspension_reason = reason
        self.updated_at = _now_iso()

    def activate(self) -> None:
        self.account_status = AccountStatus.ACTIVE.value
        self.suspension_reason = None
        self.updated_at = _now_iso()

    def assign_role(self, role: str) -> None:
        """Grant `role`. Callers MUST perform the hierarchy check
        (app.contexts.identity.application.admin_service) before calling
        this — the aggregate only enforces that the role name is valid."""
        if role not in ALL_ROLES:
            raise ValueError(f"unknown role: {role}")
        if role not in self.roles:
            self.roles.append(role)
        self.updated_at = _now_iso()

    def public_view(self) -> dict:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "full_name": self.full_name,
            "country": self.country,
            "tenant_id": self.tenant_id,
            "organization_id": self.organization_id,
            "roles": list(self.roles),
            "account_status": self.account_status,
            "created_at": self.created_at,
            "last_login_at": self.last_login_at,
        }
