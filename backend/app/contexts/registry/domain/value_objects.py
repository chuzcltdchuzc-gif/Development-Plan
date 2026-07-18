"""Registry value objects.

`PARCEL_REGISTRANT_ROLES` references Identity's existing `Role` enum
values directly — no new role is introduced, no role string is
duplicated as a literal. Adding a role to this set is a Registry-scoped
decision about who may register parcels; it is not a change to Identity's
frozen role set (ADR-004/ADR-009).
"""
from __future__ import annotations

from app.contexts.identity.domain.value_objects import Role

PARCEL_REGISTRANT_ROLES: frozenset[str] = frozenset(
    {
        Role.FIELD_AGENT.value,
        Role.LICENSED_SURVEYOR.value,
        Role.SURVEYOR_PARTNER.value,
        Role.SURVEYOR_GENERAL.value,
        Role.COMPLIANCE_OFFICER.value,
        Role.SUPER_ADMIN.value,
    }
)
