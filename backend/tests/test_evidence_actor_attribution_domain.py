"""EvidenceActorAttribution — domain-layer validation (docs/adr/
ADR-028-evidence-actor-and-commissioning-provenance.md).

Pure value-object tests, no repository, no service, no DB — mirrors
tests/test_evidence_domain.py's own split from tests/test_evidence_service.py.
"""
from __future__ import annotations

import pytest

from app.contexts.evidence.domain.attribution import (
    ACTOR_TYPE_INDIVIDUAL,
    ACTOR_TYPE_ORGANIZATION,
    ACTOR_TYPE_UNKNOWN,
    COMMISSIONED_BY,
    EXTERNAL_NAMED,
    HISTORICAL_ASSERTED,
    INTERNAL_PRINCIPAL,
    ORIGINATED_BY,
    REVIEWED_BY,
    UNKNOWN_REFERENCE,
    AttributionValidationError,
    EvidenceActorAttribution,
)

_COMMON = dict(
    tenant_id="ten_1",
    evidence_id="ev_1",
    basis="asserted by uploader",
    recorded_by="usr_1",
)


def test_internal_principal_requires_principal_id_and_name_snapshot() -> None:
    attribution = EvidenceActorAttribution.new(
        attribution_role=ORIGINATED_BY,
        actor_reference_kind=INTERNAL_PRINCIPAL,
        actor_type=ACTOR_TYPE_INDIVIDUAL,
        actor_principal_id="usr_2",
        actor_name="Jane Surveyor",
        **_COMMON,
    )
    assert attribution.actor_principal_id == "usr_2"
    assert attribution.actor_name == "Jane Surveyor"


def test_internal_principal_without_principal_id_rejected() -> None:
    with pytest.raises(AttributionValidationError, match="requires actor_principal_id"):
        EvidenceActorAttribution.new(
            attribution_role=ORIGINATED_BY,
            actor_reference_kind=INTERNAL_PRINCIPAL,
            actor_type=ACTOR_TYPE_INDIVIDUAL,
            actor_name="Jane Surveyor",
            **_COMMON,
        )


def test_internal_principal_without_snapshot_rejected() -> None:
    """ADR-028 "Immutable snapshot requirement": an internal reference
    never substitutes for the snapshot."""
    with pytest.raises(AttributionValidationError, match="immutable actor_name snapshot"):
        EvidenceActorAttribution.new(
            attribution_role=ORIGINATED_BY,
            actor_reference_kind=INTERNAL_PRINCIPAL,
            actor_type=ACTOR_TYPE_INDIVIDUAL,
            actor_principal_id="usr_2",
            **_COMMON,
        )


def test_external_named_rejects_live_principal_reference() -> None:
    with pytest.raises(AttributionValidationError, match="must not carry a live internal"):
        EvidenceActorAttribution.new(
            attribution_role=COMMISSIONED_BY,
            actor_reference_kind=EXTERNAL_NAMED,
            actor_type=ACTOR_TYPE_ORGANIZATION,
            actor_principal_id="usr_2",
            actor_organization_name="Ministry of Lands",
            **_COMMON,
        )


def test_external_named_requires_a_name() -> None:
    with pytest.raises(AttributionValidationError, match="requires actor_name"):
        EvidenceActorAttribution.new(
            attribution_role=COMMISSIONED_BY,
            actor_reference_kind=EXTERNAL_NAMED,
            actor_type=ACTOR_TYPE_ORGANIZATION,
            **_COMMON,
        )


def test_historical_asserted_accepts_organization_only() -> None:
    """A historical plan where only the practice name survives — the
    architecture must not force false precision."""
    attribution = EvidenceActorAttribution.new(
        attribution_role=ORIGINATED_BY,
        actor_reference_kind=HISTORICAL_ASSERTED,
        actor_type=ACTOR_TYPE_ORGANIZATION,
        actor_organization_name="ABC Surveying Practice",
        basis="only the practice name appears on the historical document",
        tenant_id="ten_1",
        evidence_id="ev_1",
        recorded_by="usr_1",
    )
    assert attribution.actor_name is None
    assert attribution.actor_organization_name == "ABC Surveying Practice"


def test_unknown_actor_requires_no_identity_fields() -> None:
    attribution = EvidenceActorAttribution.new(
        attribution_role=ORIGINATED_BY,
        actor_reference_kind=UNKNOWN_REFERENCE,
        actor_type=ACTOR_TYPE_UNKNOWN,
        tenant_id="ten_1",
        evidence_id="ev_1",
        recorded_by="usr_1",
        basis="originator could not be determined from the historical document",
    )
    assert attribution.actor_principal_id is None
    assert attribution.actor_name is None
    assert attribution.actor_organization_name is None


def test_unknown_actor_with_a_name_rejected() -> None:
    """No identity may be fabricated for an unknown actor."""
    with pytest.raises(AttributionValidationError, match="must not carry"):
        EvidenceActorAttribution.new(
            attribution_role=ORIGINATED_BY,
            actor_reference_kind=UNKNOWN_REFERENCE,
            actor_type=ACTOR_TYPE_UNKNOWN,
            actor_name="Someone",
            **_COMMON,
        )


def test_basis_is_mandatory_even_for_unknown() -> None:
    with pytest.raises(AttributionValidationError, match="basis is required"):
        EvidenceActorAttribution.new(
            attribution_role=ORIGINATED_BY,
            actor_reference_kind=UNKNOWN_REFERENCE,
            actor_type=ACTOR_TYPE_UNKNOWN,
            basis="",
            tenant_id="ten_1",
            evidence_id="ev_1",
            recorded_by="usr_1",
        )


def test_review_method_rejected_outside_reviewed_by() -> None:
    with pytest.raises(AttributionValidationError, match="meaningful only when"):
        EvidenceActorAttribution.new(
            attribution_role=ORIGINATED_BY,
            actor_reference_kind=EXTERNAL_NAMED,
            actor_type=ACTOR_TYPE_INDIVIDUAL,
            actor_name="Surveyor B",
            review_method="desk review",
            **_COMMON,
        )


def test_review_method_permitted_on_reviewed_by() -> None:
    attribution = EvidenceActorAttribution.new(
        attribution_role=REVIEWED_BY,
        actor_reference_kind=EXTERNAL_NAMED,
        actor_type=ACTOR_TYPE_INDIVIDUAL,
        actor_name="Professional D",
        review_method="desk review against the uploaded scan",
        **_COMMON,
    )
    assert attribution.review_method == "desk review against the uploaded scan"


def test_unknown_attribution_role_rejected() -> None:
    with pytest.raises(AttributionValidationError, match="unknown attribution_role"):
        EvidenceActorAttribution.new(
            attribution_role="RIGHTS_HOLDER",
            actor_reference_kind=UNKNOWN_REFERENCE,
            actor_type=ACTOR_TYPE_UNKNOWN,
            **_COMMON,
        )


def test_unknown_actor_reference_kind_rejected() -> None:
    with pytest.raises(AttributionValidationError, match="unknown actor_reference_kind"):
        EvidenceActorAttribution.new(
            attribution_role=ORIGINATED_BY,
            actor_reference_kind="VERIFIED",
            actor_type=ACTOR_TYPE_UNKNOWN,
            **_COMMON,
        )


def test_two_originated_by_rows_are_independent_ids() -> None:
    """Multi-originator support: two independent ORIGINATED_BY claims for
    the same evidence are simply two independent value objects — no
    scalar field forces a collision."""
    first = EvidenceActorAttribution.new(
        attribution_role=ORIGINATED_BY,
        actor_reference_kind=EXTERNAL_NAMED,
        actor_type=ACTOR_TYPE_INDIVIDUAL,
        actor_name="Field crew member 1",
        **_COMMON,
    )
    second = EvidenceActorAttribution.new(
        attribution_role=ORIGINATED_BY,
        actor_reference_kind=INTERNAL_PRINCIPAL,
        actor_type=ACTOR_TYPE_INDIVIDUAL,
        actor_principal_id="usr_3",
        actor_name="Responsible Surveyor",
        **_COMMON,
    )
    assert first.id != second.id
    assert first.evidence_id == second.evidence_id
