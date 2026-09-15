"""EvidenceActorAttributionService — application-layer use cases (docs/adr/
ADR-028-evidence-actor-and-commissioning-provenance.md).

No HTTP surface exists yet, so these tests exercise the service directly
against ExecutionContext and in-memory fakes — the identical pattern
tests/test_evidence_service.py already uses for EvidenceService. Tenant
isolation, authorization reuse, attribution ≠ authorization, historical/
multi-actor support, and append-only correction/lineage are proven here;
RLS, the append-only trigger, and the one-successor-per-row constraint are
DB-level guarantees rehearsed live separately (tests/live/
test_evidence_actor_attribution_live.py), the identical split ADR-023 and
ADR-026 already established for their own history/aggregate tables.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.contexts.evidence.application.attribution_service import (
    EvidenceActorAttributionService,
)
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
)
from app.contexts.evidence.domain.evidence_record import EvidenceRecord
from app.contexts.evidence.ports import ParcelAuthorityInfo
from app.kernel.audit import configure_audit_store
from app.kernel.context import ExecutionContext
from tests.fakes.audit_store import InMemoryAuditStore
from tests.fakes.evidence import (
    InMemoryEvidenceActorAttributionRepository,
    InMemoryEvidenceRepository,
    StaticPrincipalTenantPort,
)


class _StaticParcelExistence:
    def __init__(self, parcels: dict[str, ParcelAuthorityInfo]) -> None:
        self._parcels = parcels

    async def get_parcel_authority(self, *, parcel_id: str) -> ParcelAuthorityInfo | None:
        return self._parcels.get(parcel_id)


@pytest.fixture
def audit_store() -> InMemoryAuditStore:
    store = InMemoryAuditStore()
    configure_audit_store(store)
    return store


@pytest.fixture
def evidence_repo() -> InMemoryEvidenceRepository:
    return InMemoryEvidenceRepository()


@pytest.fixture
def attribution_repo() -> InMemoryEvidenceActorAttributionRepository:
    return InMemoryEvidenceActorAttributionRepository()


@pytest.fixture
def parcel_existence() -> _StaticParcelExistence:
    return _StaticParcelExistence(
        {
            "par_1": ParcelAuthorityInfo(tenant_id="ten_1", created_by="usr_1"),
            "par_2": ParcelAuthorityInfo(tenant_id="ten_2", created_by="usr_9"),
        }
    )


@pytest.fixture
def principal_tenant() -> StaticPrincipalTenantPort:
    return StaticPrincipalTenantPort(
        {
            "usr_1": "ten_1",  # same tenant as par_1 — a legitimate internal reference
            "usr_9": "ten_2",  # a different tenant — must never be live-referenceable from ten_1
        }
    )


@pytest.fixture
def service(
    attribution_repo: InMemoryEvidenceActorAttributionRepository,
    evidence_repo: InMemoryEvidenceRepository,
    parcel_existence: _StaticParcelExistence,
    principal_tenant: StaticPrincipalTenantPort,
) -> EvidenceActorAttributionService:
    return EvidenceActorAttributionService(
        attributions=attribution_repo,
        evidence=evidence_repo,
        parcel_existence=parcel_existence,
        principal_tenant=principal_tenant,
    )


def _ctx(
    *, tenant_id: str = "ten_1", principal_id: str = "usr_1", roles: tuple[str, ...] = ()
) -> ExecutionContext:
    return ExecutionContext(principal_id=principal_id, tenant_id=tenant_id, roles=roles)


async def _seed_evidence(
    evidence_repo: InMemoryEvidenceRepository, *, tenant_id: str = "ten_1", parcel_id: str = "par_1"
) -> EvidenceRecord:
    record = EvidenceRecord.new(
        tenant_id=tenant_id,
        parcel_id=parcel_id,
        uploaded_by="usr_1",
        filename="plan.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        storage_key="evidence/ten_1/par_1/abc",
        basis="submitted by registrant",
        evidence_type="SURVEY_PLAN",
    )
    return await evidence_repo.add(record)


# -- Historical Evidence acceptance test (the four-actor worked example) ----


async def test_historical_evidence_records_four_independent_facts(
    service: EvidenceActorAttributionService,
    evidence_repo: InMemoryEvidenceRepository,
    audit_store: InMemoryAuditStore,
) -> None:
    """User A uploaded a 1998 survey plan created by Surveyor B, commissioned
    by Client/Organisation C, later reviewed by Professional D — all four
    facts coexist without semantic collision (ADR-028 "Worked example")."""
    record = await _seed_evidence(evidence_repo)
    ctx = _ctx()

    originated = await service.record_attribution(
        ctx=ctx,
        evidence_id=record.evidence_id,
        attribution_role=ORIGINATED_BY,
        actor_reference_kind=HISTORICAL_ASSERTED,
        actor_type=ACTOR_TYPE_INDIVIDUAL,
        actor_name="Surveyor B",
        basis="named in the plan's own title block; not independently confirmed",
    )
    commissioned = await service.record_attribution(
        ctx=ctx,
        evidence_id=record.evidence_id,
        attribution_role=COMMISSIONED_BY,
        actor_reference_kind=HISTORICAL_ASSERTED,
        actor_type=ACTOR_TYPE_ORGANIZATION,
        actor_organization_name="Client Organisation C",
        basis="named in the historical commissioning correspondence",
    )
    reviewed = await service.record_attribution(
        ctx=ctx,
        evidence_id=record.evidence_id,
        attribution_role=REVIEWED_BY,
        actor_reference_kind=INTERNAL_PRINCIPAL,
        actor_type=ACTOR_TYPE_INDIVIDUAL,
        actor_principal_id="usr_1",
        actor_name="Professional D",
        basis="performed a desk review of the scanned plan",
        review_method="desk review",
    )

    assert record.uploaded_by == "usr_1"  # User A — unchanged, untouched by attribution
    assert originated["actor_name"] == "Surveyor B"
    assert originated["attribution_role"] == ORIGINATED_BY
    assert commissioned["actor_organization_name"] == "Client Organisation C"
    assert reviewed["actor_principal_id"] == "usr_1"
    assert reviewed["review_method"] == "desk review"

    all_rows = await service.list_attributions_for_evidence(ctx=ctx, evidence_id=record.evidence_id)
    assert len(all_rows) == 3
    assert all(row["is_active"] for row in all_rows)


# -- Multi-actor tests --------------------------------------------------------


async def test_two_originators_joint_authorship(
    service: EvidenceActorAttributionService,
    evidence_repo: InMemoryEvidenceRepository,
    audit_store: InMemoryAuditStore,
) -> None:
    record = await _seed_evidence(evidence_repo)
    ctx = _ctx()

    first = await service.record_attribution(
        ctx=ctx, evidence_id=record.evidence_id, attribution_role=ORIGINATED_BY,
        actor_reference_kind=EXTERNAL_NAMED, actor_type=ACTOR_TYPE_INDIVIDUAL,
        actor_name="Field crew member", basis="named by uploader",
    )
    second = await service.record_attribution(
        ctx=ctx, evidence_id=record.evidence_id, attribution_role=ORIGINATED_BY,
        actor_reference_kind=INTERNAL_PRINCIPAL, actor_type=ACTOR_TYPE_INDIVIDUAL,
        actor_principal_id="usr_1", actor_name="Responsible Surveyor",
        basis="the licensed surveyor of record",
    )
    assert first["attribution_id"] != second["attribution_id"]

    rows = await service.list_attributions_for_evidence(ctx=ctx, evidence_id=record.evidence_id)
    assert {r["attribution_role"] for r in rows} == {ORIGINATED_BY}
    assert len(rows) == 2


async def test_unknown_originator_does_not_force_false_precision(
    service: EvidenceActorAttributionService,
    evidence_repo: InMemoryEvidenceRepository,
    audit_store: InMemoryAuditStore,
) -> None:
    record = await _seed_evidence(evidence_repo)
    ctx = _ctx()

    result = await service.record_attribution(
        ctx=ctx, evidence_id=record.evidence_id, attribution_role=ORIGINATED_BY,
        actor_reference_kind=UNKNOWN_REFERENCE, actor_type=ACTOR_TYPE_UNKNOWN,
        basis="originator could not be determined from the historical document",
    )
    assert result["actor_name"] is None
    assert result["actor_principal_id"] is None


# -- Correction / lineage tests ----------------------------------------------


async def test_correction_supersedes_without_modifying_unrelated_attributions(
    service: EvidenceActorAttributionService,
    evidence_repo: InMemoryEvidenceRepository,
    audit_store: InMemoryAuditStore,
) -> None:
    record = await _seed_evidence(evidence_repo)
    ctx = _ctx()

    unrelated = await service.record_attribution(
        ctx=ctx, evidence_id=record.evidence_id, attribution_role=COMMISSIONED_BY,
        actor_reference_kind=EXTERNAL_NAMED, actor_type=ACTOR_TYPE_ORGANIZATION,
        actor_organization_name="Client C", basis="named by uploader",
    )
    original = await service.record_attribution(
        ctx=ctx, evidence_id=record.evidence_id, attribution_role=ORIGINATED_BY,
        actor_reference_kind=EXTERNAL_NAMED, actor_type=ACTOR_TYPE_INDIVIDUAL,
        actor_name="Wrong Name", basis="initial, mistaken assertion",
    )
    corrected = await service.correct_attribution(
        ctx=ctx, attribution_id=original["attribution_id"], attribution_role=ORIGINATED_BY,
        actor_reference_kind=EXTERNAL_NAMED, actor_type=ACTOR_TYPE_INDIVIDUAL,
        actor_name="Correct Name", basis="corrected after review of the original document",
    )

    assert corrected["supersedes_id"] == original["attribution_id"]

    rows = await service.list_attributions_for_evidence(ctx=ctx, evidence_id=record.evidence_id)
    by_id = {r["attribution_id"]: r for r in rows}
    assert by_id[original["attribution_id"]]["is_active"] is False
    assert by_id[corrected["attribution_id"]]["is_active"] is True
    assert by_id[unrelated["attribution_id"]]["is_active"] is True  # untouched
    assert by_id[unrelated["attribution_id"]]["actor_organization_name"] == "Client C"


async def test_correction_of_a_stale_reference_resolves_to_current_head(
    service: EvidenceActorAttributionService,
    evidence_repo: InMemoryEvidenceRepository,
    audit_store: InMemoryAuditStore,
) -> None:
    """ADR-028: 'a later correction must supersede the currently active
    row in the lineage, never the original' — even when the caller passes
    the id of the ORIGINAL (already-superseded) row."""
    record = await _seed_evidence(evidence_repo)
    ctx = _ctx()

    original = await service.record_attribution(
        ctx=ctx, evidence_id=record.evidence_id, attribution_role=ORIGINATED_BY,
        actor_reference_kind=EXTERNAL_NAMED, actor_type=ACTOR_TYPE_INDIVIDUAL,
        actor_name="First guess", basis="initial",
    )
    first_correction = await service.correct_attribution(
        ctx=ctx, attribution_id=original["attribution_id"], attribution_role=ORIGINATED_BY,
        actor_reference_kind=EXTERNAL_NAMED, actor_type=ACTOR_TYPE_INDIVIDUAL,
        actor_name="Second guess", basis="revised",
    )
    # Caller passes the ORIGINAL id again, not the first correction's id.
    second_correction = await service.correct_attribution(
        ctx=ctx, attribution_id=original["attribution_id"], attribution_role=ORIGINATED_BY,
        actor_reference_kind=EXTERNAL_NAMED, actor_type=ACTOR_TYPE_INDIVIDUAL,
        actor_name="Final answer", basis="fully confirmed",
    )

    assert second_correction["supersedes_id"] == first_correction["attribution_id"]
    assert second_correction["supersedes_id"] != original["attribution_id"]

    rows = await service.list_attributions_for_evidence(ctx=ctx, evidence_id=record.evidence_id)
    active = [r for r in rows if r["is_active"]]
    assert len(active) == 1
    assert active[0]["actor_name"] == "Final answer"


# -- Authorization: attribution ≠ authorization, and negative tests ---------


async def test_unauthorized_caller_cannot_record_attribution(
    service: EvidenceActorAttributionService,
    evidence_repo: InMemoryEvidenceRepository,
    attribution_repo: InMemoryEvidenceActorAttributionRepository,
) -> None:
    record = await _seed_evidence(evidence_repo)
    stranger = _ctx(principal_id="usr_stranger", roles=())

    with pytest.raises(HTTPException) as exc_info:
        await service.record_attribution(
            ctx=stranger, evidence_id=record.evidence_id, attribution_role=ORIGINATED_BY,
            actor_reference_kind=EXTERNAL_NAMED, actor_type=ACTOR_TYPE_INDIVIDUAL,
            actor_name="Anyone", basis="attempted by a non-creator, non-governance caller",
        )
    assert exc_info.value.status_code == 403
    assert await attribution_repo.list_for_evidence(record.evidence_id) == []


async def test_unauthorized_caller_cannot_correct_attribution(
    service: EvidenceActorAttributionService,
    evidence_repo: InMemoryEvidenceRepository,
    audit_store: InMemoryAuditStore,
) -> None:
    record = await _seed_evidence(evidence_repo)
    owner_ctx = _ctx()
    original = await service.record_attribution(
        ctx=owner_ctx, evidence_id=record.evidence_id, attribution_role=ORIGINATED_BY,
        actor_reference_kind=EXTERNAL_NAMED, actor_type=ACTOR_TYPE_INDIVIDUAL,
        actor_name="Someone", basis="named by uploader",
    )

    stranger = _ctx(principal_id="usr_stranger", roles=())
    with pytest.raises(HTTPException) as exc_info:
        await service.correct_attribution(
            ctx=stranger, attribution_id=original["attribution_id"],
            attribution_role=ORIGINATED_BY, actor_reference_kind=EXTERNAL_NAMED,
            actor_type=ACTOR_TYPE_INDIVIDUAL, actor_name="Hijacked", basis="unauthorized attempt",
        )
    assert exc_info.value.status_code == 403


async def test_denied_operation_creates_no_audit_event_representing_success(
    service: EvidenceActorAttributionService,
    evidence_repo: InMemoryEvidenceRepository,
    audit_store: InMemoryAuditStore,
) -> None:
    record = await _seed_evidence(evidence_repo)
    stranger = _ctx(principal_id="usr_stranger", roles=())

    with pytest.raises(HTTPException):
        await service.record_attribution(
            ctx=stranger, evidence_id=record.evidence_id, attribution_role=ORIGINATED_BY,
            actor_reference_kind=EXTERNAL_NAMED, actor_type=ACTOR_TYPE_INDIVIDUAL,
            actor_name="Anyone", basis="denied",
        )
    entries = await audit_store.all_entries()
    assert not any(e.action == "evidence.actor_attribution.recorded" for e in entries)


async def test_being_named_as_originator_grants_no_access(
    service: EvidenceActorAttributionService,
    evidence_repo: InMemoryEvidenceRepository,
    audit_store: InMemoryAuditStore,
) -> None:
    """ADR-028 'Tenant isolation' §3: attribution never grants
    authorization. usr_2 is named as ORIGINATED_BY but is not the
    parcel's creator and holds no governance role — usr_2 still cannot
    correct or newly record attribution on this evidence merely by being
    named on an existing row."""
    record = await _seed_evidence(evidence_repo)
    owner_ctx = _ctx()
    named_actor_ctx = _ctx(principal_id="usr_2", roles=())

    original = await service.record_attribution(
        ctx=owner_ctx, evidence_id=record.evidence_id, attribution_role=ORIGINATED_BY,
        actor_reference_kind=EXTERNAL_NAMED, actor_type=ACTOR_TYPE_INDIVIDUAL,
        actor_name="Named Actor", basis="named by the creator",
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.correct_attribution(
            ctx=named_actor_ctx, attribution_id=original["attribution_id"],
            attribution_role=ORIGINATED_BY, actor_reference_kind=EXTERNAL_NAMED,
            actor_type=ACTOR_TYPE_INDIVIDUAL, actor_name="Self-correction attempt",
            basis="the named actor tries to act on their own attribution",
        )
    assert exc_info.value.status_code == 403


# -- Cross-tenant negative tests ----------------------------------------------


async def test_cross_tenant_actor_cannot_be_linked_via_live_internal_reference(
    service: EvidenceActorAttributionService, evidence_repo: InMemoryEvidenceRepository
) -> None:
    """usr_9 belongs to ten_2; the evidence belongs to ten_1. A live
    INTERNAL_PRINCIPAL reference to usr_9 must be rejected — only a
    free-text snapshot may represent a cross-tenant actor."""
    record = await _seed_evidence(evidence_repo, tenant_id="ten_1", parcel_id="par_1")
    ctx = _ctx(tenant_id="ten_1", principal_id="usr_1")

    with pytest.raises(HTTPException) as exc_info:
        await service.record_attribution(
            ctx=ctx, evidence_id=record.evidence_id, attribution_role=ORIGINATED_BY,
            actor_reference_kind=INTERNAL_PRINCIPAL, actor_type=ACTOR_TYPE_INDIVIDUAL,
            actor_principal_id="usr_9", actor_name="Cross-tenant Surveyor",
            basis="attempted cross-tenant live reference",
        )
    assert exc_info.value.status_code == 400
    assert "same tenant" in exc_info.value.detail


async def test_cross_tenant_actor_via_snapshot_grants_no_disclosure_or_access(
    service: EvidenceActorAttributionService,
    evidence_repo: InMemoryEvidenceRepository,
    audit_store: InMemoryAuditStore,
) -> None:
    record = await _seed_evidence(evidence_repo, tenant_id="ten_1", parcel_id="par_1")
    ctx = _ctx(tenant_id="ten_1", principal_id="usr_1")

    result = await service.record_attribution(
        ctx=ctx, evidence_id=record.evidence_id, attribution_role=ORIGINATED_BY,
        actor_reference_kind=EXTERNAL_NAMED, actor_type=ACTOR_TYPE_INDIVIDUAL,
        actor_name="A surveyor known to belong to another tenant, by name only",
        basis="named as a free-text snapshot, not a live reference",
    )
    assert result["actor_principal_id"] is None  # no live cross-tenant identity link created

    # The other tenant's own caller still cannot read ten_1's evidence or
    # its attributions merely because a name happens to be associated
    # with their tenant in the real world — no such access path exists.
    other_tenant_ctx = _ctx(tenant_id="ten_2", principal_id="usr_9")
    with pytest.raises(HTTPException) as exc_info:
        await service.list_attributions_for_evidence(
            ctx=other_tenant_ctx, evidence_id=record.evidence_id
        )
    assert exc_info.value.status_code == 404


async def test_nonexistent_internal_principal_rejected() -> None:
    from tests.fakes.evidence import (
        InMemoryEvidenceActorAttributionRepository as _AttrRepo,
    )
    from tests.fakes.evidence import (
        InMemoryEvidenceRepository as _EvRepo,
    )
    from tests.fakes.evidence import (
        StaticPrincipalTenantPort as _PT,
    )

    ev_repo = _EvRepo()
    record = await _seed_evidence(ev_repo)
    svc = EvidenceActorAttributionService(
        attributions=_AttrRepo(),
        evidence=ev_repo,
        parcel_existence=_StaticParcelExistence({"par_1": ParcelAuthorityInfo("ten_1", "usr_1")}),
        principal_tenant=_PT({}),  # no principals known at all
    )
    with pytest.raises(HTTPException) as exc_info:
        await svc.record_attribution(
            ctx=_ctx(), evidence_id=record.evidence_id, attribution_role=ORIGINATED_BY,
            actor_reference_kind=INTERNAL_PRINCIPAL, actor_type=ACTOR_TYPE_INDIVIDUAL,
            actor_principal_id="usr_ghost", actor_name="Ghost",
            basis="references a principal that does not exist",
        )
    assert exc_info.value.status_code == 400
