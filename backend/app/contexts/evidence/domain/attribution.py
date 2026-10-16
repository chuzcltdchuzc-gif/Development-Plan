"""EvidenceActorAttribution — the ADR-028 value object recording one
attribution claim (ORIGINATED_BY/REVIEWED_BY/COMMISSIONED_BY) against an
EvidenceRecord (docs/adr/ADR-028-evidence-actor-and-commissioning-provenance.md).

Pure value object — no I/O, no persistence concerns, matching
app.contexts.registry.domain.history.OwnershipAssertion's own shape
exactly. Constructed by EvidenceActorAttributionService, persisted through
EvidenceActorAttributionRepository. Not part of the EvidenceRecord
aggregate's own mutable state — EvidenceRecord gains no new field,
mutator, or invariant from this module (ADR-028 "Relationship to the
frozen baseline": extended, not amended).

Each field records an assertion about who is claimed to have originated,
reviewed, or commissioned a piece of evidence — never a determination of
land ownership, document ownership, copyright, licensing authority, or
legal/professional verification (LV-000 v1.8 Article IV; ADR-028
"Origination provenance", "Professional review", "Commissioning
provenance"). This module enforces ADR-028's structural invariants at
construction time, the same domain-layer-plus-database dual enforcement
every prior aggregate/value-object in this codebase uses.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

ORIGINATED_BY = "ORIGINATED_BY"
REVIEWED_BY = "REVIEWED_BY"
COMMISSIONED_BY = "COMMISSIONED_BY"

# ADR-028 "Future attribution roles" — a starting, deliberately small set.
# Unlike EVIDENCE_TYPES, extending this is NOT always a mechanical
# non-event: some future roles (Rights Holder, Licensor) carry legal/
# commercial weight these three deliberately do not, and per ADR-028 must
# not be added without their own governance review even though this
# column mechanically supports additive enum growth.
ATTRIBUTION_ROLES: frozenset[str] = frozenset({ORIGINATED_BY, REVIEWED_BY, COMMISSIONED_BY})

INTERNAL_PRINCIPAL = "INTERNAL_PRINCIPAL"
EXTERNAL_NAMED = "EXTERNAL_NAMED"
HISTORICAL_ASSERTED = "HISTORICAL_ASSERTED"
UNKNOWN_REFERENCE = "UNKNOWN"

# ADR-028 "Actor-state representation" — answers exactly one question (how
# is this actor identified), deliberately kept separate from basis
# (assertion source, free text), confidence (not modeled, by design), and
# professional verification (not modeled, by design).
ACTOR_REFERENCE_KINDS: frozenset[str] = frozenset(
    {INTERNAL_PRINCIPAL, EXTERNAL_NAMED, HISTORICAL_ASSERTED, UNKNOWN_REFERENCE}
)

ACTOR_TYPE_INDIVIDUAL = "INDIVIDUAL"
ACTOR_TYPE_ORGANIZATION = "ORGANIZATION"
ACTOR_TYPE_UNKNOWN = "UNKNOWN"

# Orthogonal to actor_reference_kind (ADR-028: "what kind of actor this
# is... the two dimensions vary independently").
ACTOR_TYPES: frozenset[str] = frozenset(
    {ACTOR_TYPE_INDIVIDUAL, ACTOR_TYPE_ORGANIZATION, ACTOR_TYPE_UNKNOWN}
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class AttributionValidationError(ValueError):
    """Raised when an attribution claim's fields are internally
    inconsistent with ADR-028's actor-representation and snapshot rules —
    e.g. an INTERNAL_PRINCIPAL claim missing its required snapshot, or an
    EXTERNAL_NAMED claim carrying a principal reference it must not
    have."""


@dataclass(frozen=True)
class EvidenceActorAttribution:
    id: str
    tenant_id: str
    evidence_id: str
    attribution_role: str
    actor_reference_kind: str
    actor_principal_id: str | None
    actor_name: str | None
    actor_organization_name: str | None
    actor_type: str
    basis: str
    review_method: str | None
    recorded_by: str
    audit_ref: str | None
    supersedes_id: str | None = None
    recorded_at: str = field(default_factory=_now_iso)

    @classmethod
    def new(
        cls,
        *,
        tenant_id: str,
        evidence_id: str,
        attribution_role: str,
        actor_reference_kind: str,
        actor_type: str,
        basis: str,
        recorded_by: str,
        actor_principal_id: str | None = None,
        actor_name: str | None = None,
        actor_organization_name: str | None = None,
        review_method: str | None = None,
        audit_ref: str | None = None,
        supersedes_id: str | None = None,
    ) -> EvidenceActorAttribution:
        if attribution_role not in ATTRIBUTION_ROLES:
            raise AttributionValidationError(f"unknown attribution_role: {attribution_role!r}")
        if actor_reference_kind not in ACTOR_REFERENCE_KINDS:
            raise AttributionValidationError(
                f"unknown actor_reference_kind: {actor_reference_kind!r}"
            )
        if actor_type not in ACTOR_TYPES:
            raise AttributionValidationError(f"unknown actor_type: {actor_type!r}")
        if not basis or not basis.strip():
            # ADR-028: "we don't know, and here is why" is itself a
            # recordable fact this field exists to carry — NEVER optional,
            # including for an UNKNOWN actor.
            raise AttributionValidationError("basis is required, including for an unknown actor")
        if review_method and attribution_role != REVIEWED_BY:
            raise AttributionValidationError(
                "review_method is meaningful only when attribution_role is REVIEWED_BY"
            )

        # ADR-028 "Actor-state representation" + "Immutable snapshot
        # requirement": each kind has a fixed, structurally-checked shape.
        if actor_reference_kind == INTERNAL_PRINCIPAL:
            if not actor_principal_id:
                raise AttributionValidationError(
                    "INTERNAL_PRINCIPAL requires actor_principal_id"
                )
            if not actor_name:
                raise AttributionValidationError(
                    "INTERNAL_PRINCIPAL requires an immutable actor_name snapshot — an internal "
                    "reference adds precision, it never substitutes for the snapshot"
                )
        elif actor_reference_kind in (EXTERNAL_NAMED, HISTORICAL_ASSERTED):
            if actor_principal_id:
                raise AttributionValidationError(
                    f"{actor_reference_kind} must not carry a live internal principal reference"
                )
            if not actor_name and not actor_organization_name:
                raise AttributionValidationError(
                    f"{actor_reference_kind} requires actor_name or actor_organization_name"
                )
        else:  # UNKNOWN_REFERENCE
            if actor_principal_id or actor_name or actor_organization_name:
                raise AttributionValidationError(
                    "UNKNOWN must not carry actor_principal_id, actor_name, or "
                    "actor_organization_name — no identity may be fabricated for an unknown actor"
                )

        new_id = str(uuid.uuid4())
        if supersedes_id == new_id:
            # Structurally unreachable (new_id is freshly generated above,
            # never knowable in advance by a caller), kept as a defensive,
            # cheap check mirroring this codebase's habit of enforcing an
            # invariant at every layer it can reach, not only the one
            # layer that happens to make it impossible today.
            raise AttributionValidationError("an attribution may not supersede itself")

        return cls(
            id=new_id,
            tenant_id=tenant_id,
            evidence_id=evidence_id,
            attribution_role=attribution_role,
            actor_reference_kind=actor_reference_kind,
            actor_principal_id=actor_principal_id,
            actor_name=actor_name,
            actor_organization_name=actor_organization_name,
            actor_type=actor_type,
            basis=basis,
            review_method=review_method,
            recorded_by=recorded_by,
            audit_ref=audit_ref,
            supersedes_id=supersedes_id,
        )
