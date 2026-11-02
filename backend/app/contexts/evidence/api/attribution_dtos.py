"""Evidence Actor Attribution API request/response shapes (GD-012 §9).

Mirrors `evidence/api/dtos.py`'s own conventions: `StrEnum`s mirroring the
domain module's plain-string constants, kept in sync by a same-file
assertion (the domain layer itself stays framework-free). The response DTO
mirrors `_attribution_view`'s field set exactly, per GD-012 §6.3, omitting
`tenant_id` (implicit in the authenticated session) and `audit_ref`
(audit-internal) — the identical omission `EvidenceResponse` already makes
for the same reasons.

No list/detail response shape exists here — GD-012 §6.2 deliberately
authorizes no such endpoint; ADR-028's personal-data disclosure question for
third-party attribution reads remains open for its own, future, separate
Governance act.
"""
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from app.contexts.evidence.domain.attribution import (
    ACTOR_REFERENCE_KINDS,
    ACTOR_TYPES,
    ATTRIBUTION_ROLES,
)


class AttributionRole(StrEnum):
    ORIGINATED_BY = "ORIGINATED_BY"
    REVIEWED_BY = "REVIEWED_BY"
    COMMISSIONED_BY = "COMMISSIONED_BY"


assert {r.value for r in AttributionRole} == ATTRIBUTION_ROLES, (
    "AttributionRole drifted from the domain"
)


class ActorReferenceKind(StrEnum):
    INTERNAL_PRINCIPAL = "INTERNAL_PRINCIPAL"
    EXTERNAL_NAMED = "EXTERNAL_NAMED"
    HISTORICAL_ASSERTED = "HISTORICAL_ASSERTED"
    UNKNOWN = "UNKNOWN"


assert {k.value for k in ActorReferenceKind} == ACTOR_REFERENCE_KINDS, (
    "ActorReferenceKind drifted from the domain"
)


class ActorType(StrEnum):
    INDIVIDUAL = "INDIVIDUAL"
    ORGANIZATION = "ORGANIZATION"
    UNKNOWN = "UNKNOWN"


assert {t.value for t in ActorType} == ACTOR_TYPES, "ActorType drifted from the domain"


class RecordAttributionRequest(BaseModel):
    """Request body for `POST /v1/evidence/{evidence_id}/attributions`."""

    attribution_role: AttributionRole
    actor_reference_kind: ActorReferenceKind
    actor_type: ActorType
    basis: str
    actor_principal_id: str | None = None
    actor_name: str | None = None
    actor_organization_name: str | None = None
    review_method: str | None = None


class CorrectAttributionRequest(BaseModel):
    """Request body for
    `POST /v1/evidence/attributions/{attribution_id}/corrections`. Carries
    no `evidence_id` — `correct_attribution` resolves it from the
    attribution's own lineage (GD-012 §4)."""

    attribution_role: AttributionRole
    actor_reference_kind: ActorReferenceKind
    actor_type: ActorType
    basis: str
    actor_principal_id: str | None = None
    actor_name: str | None = None
    actor_organization_name: str | None = None
    review_method: str | None = None


class AttributionResponse(BaseModel):
    """Response shape for both attribution endpoints — mirrors
    `_attribution_view`'s field set exactly (GD-012 §6.3), omitting
    `tenant_id` (implicit in the authenticated session) and `audit_ref`
    (audit-internal)."""

    attribution_id: str
    evidence_id: str
    attribution_role: AttributionRole
    actor_reference_kind: ActorReferenceKind
    actor_principal_id: str | None
    actor_name: str | None
    actor_organization_name: str | None
    actor_type: ActorType
    basis: str
    review_method: str | None
    recorded_by: str
    recorded_at: str
    supersedes_id: str | None
    is_active: bool
