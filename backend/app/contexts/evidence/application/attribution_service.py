"""EvidenceActorAttributionService — the ADR-028 application-service
foundation for recording and correcting Evidence actor attribution
(docs/adr/ADR-028-evidence-actor-and-commissioning-provenance.md).

No HTTP endpoint exists yet — GD-008/ADR-028 authorize architecture and
this internal foundation only (ADR-028 "Approval Gate": acceptance
authorizes the domain model, migration shape, and repository port, never
implementation of an API surface). These methods exist as the real
orchestration seam a future endpoint would call into, the identical
posture app.contexts.evidence.application.evidence_service.record_upload
had before B5.3 added the real upload path.

Authorization reuses EvidenceService's existing creator-or-governance
shape unchanged (`_can_mutate` below is a deliberate, small duplication of
EvidenceService._can_mutate, mirroring the same "a third occurrence is the
trigger to promote this into the kernel" reasoning ADR-013/ADR-026 already
established) — attribution itself is never treated as an authorization
input (ADR-028 "Tenant isolation" §3: attribution never grants
authorization), and no new authorization mechanism is introduced.
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, status

from app.contexts.evidence.domain.attribution import (
    INTERNAL_PRINCIPAL,
    EvidenceActorAttribution,
)
from app.contexts.evidence.domain.evidence_record import EvidenceRecord
from app.contexts.evidence.ports import (
    EvidenceActorAttributionRepository,
    EvidenceRepository,
    ParcelAuthorityInfo,
    ParcelExistencePort,
    PrincipalTenantPort,
)
from app.contexts.identity.domain.value_objects import GOVERNANCE_ROLES
from app.kernel.audit import audit
from app.kernel.context import ExecutionContext

# A defensive bound on lineage-walking (see _resolve_active_head below) —
# not a business rule. Cycles are already structurally impossible (a
# supersedes_id FK must reference an already-existing row, and rows are
# never UPDATEd after insert), so this exists only to fail loudly, rather
# than hang, in the face of a genuine data-integrity anomaly.
_MAX_LINEAGE_WALK = 10_000


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="evidence record not found")


def _not_found_attribution() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="evidence attribution not found"
    )


def _in_scope(ctx: ExecutionContext, resource_tenant_id: str) -> bool:
    """Mirrors app.contexts.evidence.application.evidence_service._in_scope
    exactly — see that module's own docstring for why this is a known,
    small, deliberate duplication rather than a shared import."""
    return resource_tenant_id == ctx.tenant_id or ctx.has_any_role("super_admin")


def _can_mutate(ctx: ExecutionContext, authority: ParcelAuthorityInfo) -> bool:
    """Mirrors EvidenceService._can_mutate exactly — the same creator-or-
    governance-role authorization gate IMVP-5 already established for
    recording evidence against a parcel, reused here by extension for
    recording attribution against that same evidence, never invented
    fresh and never derived from anything attribution-specific."""
    return authority.created_by == ctx.principal_id or ctx.has_any_role(*GOVERNANCE_ROLES)


def _attribution_view(attribution: EvidenceActorAttribution, *, is_active: bool) -> dict:
    return {
        "attribution_id": attribution.id,
        "tenant_id": attribution.tenant_id,
        "evidence_id": attribution.evidence_id,
        "attribution_role": attribution.attribution_role,
        "actor_reference_kind": attribution.actor_reference_kind,
        "actor_principal_id": attribution.actor_principal_id,
        "actor_name": attribution.actor_name,
        "actor_organization_name": attribution.actor_organization_name,
        "actor_type": attribution.actor_type,
        "basis": attribution.basis,
        "review_method": attribution.review_method,
        "recorded_by": attribution.recorded_by,
        "recorded_at": attribution.recorded_at,
        "audit_ref": attribution.audit_ref,
        "supersedes_id": attribution.supersedes_id,
        "is_active": is_active,
    }


class EvidenceActorAttributionService:
    def __init__(
        self,
        *,
        attributions: EvidenceActorAttributionRepository,
        evidence: EvidenceRepository,
        parcel_existence: ParcelExistencePort,
        principal_tenant: PrincipalTenantPort,
    ) -> None:
        self.attributions = attributions
        self.evidence = evidence
        self.parcel_existence = parcel_existence
        self.principal_tenant = principal_tenant

    async def _load_evidence_in_scope(
        self, *, ctx: ExecutionContext, evidence_id: str
    ) -> EvidenceRecord:
        record = await self.evidence.get(evidence_id)
        if not record or not _in_scope(ctx, record.tenant_id):
            raise _not_found()
        return record

    async def _authorize_mutation(self, *, ctx: ExecutionContext, record: EvidenceRecord) -> None:
        """The same creator-or-governance-role gate EvidenceService.
        upload_evidence already applies against the Evidence's own parcel
        — attribution never introduces its own authorization path
        (ADR-028 "Tenant isolation" §3)."""
        authority = await self.parcel_existence.get_parcel_authority(parcel_id=record.parcel_id)
        if authority is None or not _in_scope(ctx, authority.tenant_id):
            raise _not_found()
        if not _can_mutate(ctx, authority):
            raise _forbidden(
                "only the evidence's parcel creator or a governance role may record or "
                "correct actor attribution for it"
            )

    async def _verify_actor_reference(
        self, *, ctx: ExecutionContext, actor_reference_kind: str, actor_principal_id: str | None
    ) -> None:
        """ADR-028 "Tenant isolation" §2: actor_principal_id may reference
        only a principal within the SAME tenant as the Evidence being
        attributed — never a cross-tenant live reference. A cross-tenant
        or nonexistent principal is a client input error (400), not an
        authorization failure, since the caller themselves is already
        authorized at this point; the problem is the referenced actor."""
        if actor_reference_kind != INTERNAL_PRINCIPAL:
            return
        if not actor_principal_id:
            return  # domain-layer validation already rejects this; defensive no-op here
        actor_tenant_id = await self.principal_tenant.get_tenant_id(actor_principal_id)
        if actor_tenant_id is None:
            raise _bad_request(f"actor_principal_id {actor_principal_id!r} does not exist")
        if actor_tenant_id != ctx.tenant_id:
            raise _bad_request(
                "actor_principal_id must reference a principal in the same tenant as the "
                "Evidence being attributed — a cross-tenant actor must be recorded as a "
                "free-text snapshot (EXTERNAL_NAMED/HISTORICAL_ASSERTED), never a live "
                "internal reference"
            )

    async def _resolve_active_head(self, attribution_id: str) -> EvidenceActorAttribution:
        """Walks a lineage forward from any id in it to its current,
        not-yet-superseded head (ADR-028: "a later correction must
        supersede the currently active row in the lineage, never the
        original"). Bounded defensively — see _MAX_LINEAGE_WALK above —
        against a genuine data-integrity anomaly; ordinary use never
        approaches that bound."""
        current = await self.attributions.get(attribution_id)
        if current is None:
            raise _not_found_attribution()
        for _ in range(_MAX_LINEAGE_WALK):
            successor = await self.attributions.get_successor(current.id)
            if successor is None:
                return current
            current = successor
        raise RuntimeError(
            f"attribution lineage starting at {attribution_id!r} did not terminate within "
            f"{_MAX_LINEAGE_WALK} hops — likely a data-integrity anomaly, not normal usage"
        )

    async def record_attribution(
        self,
        *,
        ctx: ExecutionContext,
        evidence_id: str,
        attribution_role: str,
        actor_reference_kind: str,
        actor_type: str,
        basis: str,
        actor_principal_id: str | None = None,
        actor_name: str | None = None,
        actor_organization_name: str | None = None,
        review_method: str | None = None,
    ) -> dict:
        if not ctx.tenant_id:
            raise _bad_request("caller has no tenant to record attribution within")

        record = await self._load_evidence_in_scope(ctx=ctx, evidence_id=evidence_id)
        await self._authorize_mutation(ctx=ctx, record=record)
        await self._verify_actor_reference(
            ctx=ctx,
            actor_reference_kind=actor_reference_kind,
            actor_principal_id=actor_principal_id,
        )

        audit_id = uuid.uuid4().hex
        try:
            attribution = EvidenceActorAttribution.new(
                tenant_id=record.tenant_id,
                evidence_id=record.evidence_id,
                attribution_role=attribution_role,
                actor_reference_kind=actor_reference_kind,
                actor_type=actor_type,
                basis=basis,
                recorded_by=ctx.principal_id,
                actor_principal_id=actor_principal_id,
                actor_name=actor_name,
                actor_organization_name=actor_organization_name,
                review_method=review_method,
                audit_ref=audit_id,
            )
        except ValueError as exc:
            raise _bad_request(str(exc)) from exc

        attribution = await self.attributions.record(attribution)
        await audit(
            "evidence.actor_attribution.recorded",
            entry_id=audit_id,
            resource_type="evidence_actor_attribution",
            resource_id=attribution.id,
            decision="PERMIT",
            payload={
                "tenant_id": attribution.tenant_id,
                "evidence_id": attribution.evidence_id,
                "attribution_role": attribution.attribution_role,
                "actor_reference_kind": attribution.actor_reference_kind,
            },
        )
        return _attribution_view(attribution, is_active=True)

    async def correct_attribution(
        self,
        *,
        ctx: ExecutionContext,
        attribution_id: str,
        attribution_role: str,
        actor_reference_kind: str,
        actor_type: str,
        basis: str,
        actor_principal_id: str | None = None,
        actor_name: str | None = None,
        actor_organization_name: str | None = None,
        review_method: str | None = None,
    ) -> dict:
        if not ctx.tenant_id:
            raise _bad_request("caller has no tenant to correct attribution within")

        head = await self._resolve_active_head(attribution_id)
        if not _in_scope(ctx, head.tenant_id):
            raise _not_found_attribution()
        record = await self._load_evidence_in_scope(ctx=ctx, evidence_id=head.evidence_id)
        await self._authorize_mutation(ctx=ctx, record=record)
        await self._verify_actor_reference(
            ctx=ctx,
            actor_reference_kind=actor_reference_kind,
            actor_principal_id=actor_principal_id,
        )

        audit_id = uuid.uuid4().hex
        try:
            correction = EvidenceActorAttribution.new(
                tenant_id=head.tenant_id,
                evidence_id=head.evidence_id,
                attribution_role=attribution_role,
                actor_reference_kind=actor_reference_kind,
                actor_type=actor_type,
                basis=basis,
                recorded_by=ctx.principal_id,
                actor_principal_id=actor_principal_id,
                actor_name=actor_name,
                actor_organization_name=actor_organization_name,
                review_method=review_method,
                audit_ref=audit_id,
                supersedes_id=head.id,
            )
        except ValueError as exc:
            raise _bad_request(str(exc)) from exc

        correction = await self.attributions.record(correction)
        await audit(
            "evidence.actor_attribution.corrected",
            entry_id=audit_id,
            resource_type="evidence_actor_attribution",
            resource_id=correction.id,
            decision="PERMIT",
            payload={
                "tenant_id": correction.tenant_id,
                "evidence_id": correction.evidence_id,
                "attribution_role": correction.attribution_role,
                "supersedes_id": correction.supersedes_id,
            },
        )
        return _attribution_view(correction, is_active=True)

    async def list_attributions_for_evidence(
        self, *, ctx: ExecutionContext, evidence_id: str
    ) -> list[dict]:
        """Read-only, tenant-scoped, no creator restriction — mirrors
        EvidenceService.list_evidence_for_parcel's own read-open posture.
        Returns every row (full lineage history), each carrying whether it
        is currently the active head of its own lineage."""
        await self._load_evidence_in_scope(ctx=ctx, evidence_id=evidence_id)
        rows = await self.attributions.list_for_evidence(evidence_id)
        superseded_ids = {row.supersedes_id for row in rows if row.supersedes_id}
        return [
            _attribution_view(row, is_active=row.id not in superseded_ids)
            for row in rows
            if _in_scope(ctx, row.tenant_id)
        ]
