"""Identity value objects — the canonical role set, ranked for hierarchy
checks, plus Email/CountryCode.

Roles are the set recovered from the Base44/Emergent audits
(docs/adr/ADR-005). No role may be invented ad hoc; a new role is an ADR
amendment, not a string literal added somewhere in application code.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_ISO_3166_RE = re.compile(r"^[A-Z]{2}$")


@dataclass(frozen=True)
class Email:
    value: str

    def __post_init__(self) -> None:
        if not _EMAIL_RE.match(self.value):
            raise ValueError(f"invalid email: {self.value!r}")

    @classmethod
    def parse(cls, raw: str) -> Email:
        return cls((raw or "").strip().lower())

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class CountryCode:
    """ISO 3166-1 alpha-2 country code (e.g. 'NG')."""

    value: str

    def __post_init__(self) -> None:
        if not _ISO_3166_RE.match(self.value):
            raise ValueError(f"invalid country code: {self.value!r}")

    def __str__(self) -> str:
        return self.value


class Role(StrEnum):
    GENERAL_USER = "general_user"
    FIELD_AGENT = "field_agent"
    COMMUNITY_VALIDATOR = "community_validator"
    GOVERNMENT_OBSERVER = "government_observer"
    SURVEYOR = "surveyor"
    SURVEYOR_PARTNER = "surveyor_partner"
    LICENSED_SURVEYOR = "licensed_surveyor"
    COMPLIANCE_OFFICER = "compliance_officer"
    SURVEYOR_GENERAL = "surveyor_general"
    SUPER_ADMIN = "super_admin"


ALL_ROLES: frozenset[str] = frozenset(r.value for r in Role)

# Named ABAC attributes, applied per resource by later bounded contexts.
GOVERNANCE_ROLES: frozenset[str] = frozenset(
    {Role.SUPER_ADMIN.value, Role.SURVEYOR_GENERAL.value, Role.COMPLIANCE_OFFICER.value}
)
SURVEY_ROLES: frozenset[str] = frozenset(
    {Role.LICENSED_SURVEYOR.value, Role.SURVEYOR_PARTNER.value, Role.SURVEYOR.value}
)
COMMUNITY_ROLES: frozenset[str] = frozenset({Role.COMMUNITY_VALIDATOR.value})
OBSERVER_ROLES: frozenset[str] = frozenset({Role.GOVERNMENT_OBSERVER.value})
FIELD_ROLES: frozenset[str] = frozenset({Role.FIELD_AGENT.value})

# ---- Role hierarchy (docs/adr/ADR-004 point 4: a principal can never grant
# a role ranked higher than their own, nor elevate themselves). Rank is used
# only for the *assignment* hierarchy check, never for authorization
# decisions in general — those go through the PDP.
ROLE_RANK: dict[str, int] = {
    Role.GENERAL_USER.value: 0,
    Role.FIELD_AGENT.value: 10,
    Role.COMMUNITY_VALIDATOR.value: 10,
    Role.GOVERNMENT_OBSERVER.value: 10,
    Role.SURVEYOR.value: 20,
    Role.SURVEYOR_PARTNER.value: 20,
    Role.LICENSED_SURVEYOR.value: 30,
    Role.COMPLIANCE_OFFICER.value: 40,
    Role.SURVEYOR_GENERAL.value: 40,
    Role.SUPER_ADMIN.value: 100,
}


def highest_rank(roles: frozenset[str] | tuple[str, ...] | list[str]) -> int:
    if not roles:
        return -1
    return max(ROLE_RANK.get(role, 0) for role in roles)


class AccountStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"


CAN_AUTHENTICATE_STATUSES: frozenset[str] = frozenset({AccountStatus.ACTIVE.value})
