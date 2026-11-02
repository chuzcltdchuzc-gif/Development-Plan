"""SpatialService — Spatial Intelligence context's use-cases (B4 Slice 1,
docs/adr/ADR-018, docs/adr/ADR-019; authorization and real validation
added B4 Slice 2, docs/adr/ADR-022, docs/adr/ADR-018 §"Validation gates
persistence").

submit_geometry/get_active_geometry only. No overlap detection, no
duplicate-geometry detection, no adjacency, no spatial search, no GIS
computation of any kind — those remain later ADRs' job.

Authorization is ADR-022's creator-or-governance model, mirroring
docs/adr/ADR-015's identical shape for Registry exactly: `_can_mutate`,
`_effective_authority`, and `_delegated_roles` below are the same
functions as `app.contexts.registry.application.parcel_service`'s, with
`Parcel` swapped for `ParcelAuthorityInfo` (the minimal cross-context view
`ParcelExistencePort` now returns, ADR-022 §8) since Spatial must not
import Registry's `Parcel` domain object directly (docs/adr/ADR-018
bounded-context isolation). Evaluation order (ADR-022 §5, and this slice's
own authorization brief): tenant scope -> creator-or-governance ->
archived-parcel check -> validation -> persistence -> audit -> response.
Never reordered.
"""
from __future__ import annotations

from fastapi import HTTPException, status

from app.contexts.identity.domain.value_objects import GOVERNANCE_ROLES
from app.contexts.spatial.domain.geometry_validation import InvalidGeometryError
from app.contexts.spatial.domain.parcel_geometry import ParcelGeometry
from app.contexts.spatial.ports import (
    ParcelAuthorityInfo,
    ParcelExistencePort,
    ParcelGeometryRepository,
)
from app.kernel.audit import audit
from app.kernel.context import ExecutionContext

# The one Parcel status (docs/adr/ADR-013) Spatial's authorization model
# must react to (ADR-022 §8) — read only, via ParcelAuthorityInfo, never
# by importing Registry's own STATUS_ARCHIVED constant or Parcel domain
# object (bounded-context isolation, docs/adr/ADR-018).
_PARCEL_STATUS_ARCHIVED = "ARCHIVED"


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _in_scope(ctx: ExecutionContext, resource_tenant_id: str) -> bool:
    """Mirrors the identical helper in app.contexts.registry.application.
    parcel_service (itself mirroring app.contexts.identity.application.
    admin_service) — duplicated locally rather than imported, since it is
    a private, context-internal symbol (see docs/adr/ADR-013's "known,
    small, deliberate duplication" section: promote to the kernel if a
    fourth context needs it, not before)."""
    return resource_tenant_id == ctx.tenant_id or ctx.has_any_role("super_admin")


def _can_mutate(ctx: ExecutionContext, authority: ParcelAuthorityInfo) -> bool:
    """ADR-022 §§2-3 — two independent grants, either sufficient: the
    *parcel's* creator (`Parcel.created_by`, read via ParcelAuthorityInfo,
    never a second Spatial-local "geometry ownership" concept), or a
    currently-effective GOVERNANCE_ROLES member (direct or delegated —
    ctx.roles is already the union of both, ADR-011). Called only after
    _in_scope has already confirmed tenant scope."""
    return authority.created_by == ctx.principal_id or ctx.has_any_role(*GOVERNANCE_ROLES)


def _effective_authority(ctx: ExecutionContext, authority: ParcelAuthorityInfo) -> str:
    """Audit-facing description of *why* a mutation was permitted — never
    used for the authorization decision itself (that's _can_mutate)."""
    if authority.created_by == ctx.principal_id:
        return "creator"
    granted = sorted(set(ctx.roles) & GOVERNANCE_ROLES)
    return f"governance:{','.join(granted)}" if granted else "unknown"


def _delegated_roles(ctx: ExecutionContext) -> list[str]:
    """Populated by app.contexts.identity.context_hydration when any
    currently-effective delegation contributed roles to this request
    (docs/adr/ADR-015) — read-only here, never recomputed."""
    return list(ctx.attributes.get("delegated_roles") or [])


def _geometry_view(geometry: ParcelGeometry) -> dict:
    return {
        "geometry_id": geometry.geometry_id,
        "tenant_id": geometry.tenant_id,
        "parcel_id": geometry.parcel_id,
        "boundary": geometry.boundary,
        "srid": geometry.srid,
        "status": geometry.status,
        "created_by": geometry.created_by,
        "created_at": geometry.created_at,
        "superseded_at": geometry.superseded_at,
    }


class SpatialService:
    def __init__(
        self,
        *,
        geometries: ParcelGeometryRepository,
        parcel_existence: ParcelExistencePort,
    ) -> None:
        self.geometries = geometries
        self.parcel_existence = parcel_existence

    async def _load_authority_in_scope(
        self, *, ctx: ExecutionContext, parcel_id: str
    ) -> ParcelAuthorityInfo:
        authority = await self.parcel_existence.get_parcel_authority(parcel_id=parcel_id)
        if authority is None or not _in_scope(ctx, authority.tenant_id):
            raise _not_found("parcel not found")
        return authority

    async def _authorize_mutation(
        self, *, ctx: ExecutionContext, parcel_id: str, authority: ParcelAuthorityInfo
    ) -> None:
        if _can_mutate(ctx, authority):
            return
        await audit(
            "spatial.parcel_geometry.mutation_denied",
            resource_type="parcel_geometry",
            resource_id=parcel_id,
            decision="DENY",
            payload={
                "tenant_id": authority.tenant_id,
                "reason": "not_creator_and_not_governance",
                "delegated_roles": _delegated_roles(ctx),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="only the parcel's creator or a governance role may submit its geometry",
        )

    async def submit_geometry(
        self, *, ctx: ExecutionContext, parcel_id: str, boundary: str
    ) -> dict:
        authority = await self._load_authority_in_scope(ctx=ctx, parcel_id=parcel_id)
        await self._authorize_mutation(ctx=ctx, parcel_id=parcel_id, authority=authority)

        if authority.status == _PARCEL_STATUS_ARCHIVED:
            raise _conflict("cannot submit geometry for an archived parcel")

        try:
            geometry = ParcelGeometry.new(
                tenant_id=authority.tenant_id,
                parcel_id=parcel_id,
                boundary=boundary,
                created_by=ctx.principal_id,
            )
        except InvalidGeometryError as exc:
            raise _bad_request(str(exc)) from exc

        existing = await self.geometries.get_active_for_parcel(parcel_id)
        if existing is not None:
            existing.supersede()
            await self.geometries.update(existing)

        geometry = await self.geometries.add(geometry)
        await audit(
            "spatial.parcel_geometry.created",
            resource_type="parcel_geometry",
            resource_id=geometry.geometry_id,
            decision="PERMIT",
            payload={
                "tenant_id": geometry.tenant_id,
                "parcel_id": geometry.parcel_id,
                "effective_authority": _effective_authority(ctx, authority),
                "delegated_roles": _delegated_roles(ctx),
                "superseded_geometry_id": existing.geometry_id if existing else None,
            },
        )
        return _geometry_view(geometry)

    async def get_active_geometry(self, *, ctx: ExecutionContext, parcel_id: str) -> dict:
        # Tenant scope only — reading is not a mutation (ADR-022 §6), so
        # creator/governance/archived checks do not apply here.
        await self._load_authority_in_scope(ctx=ctx, parcel_id=parcel_id)
        geometry = await self.geometries.get_active_for_parcel(parcel_id)
        if geometry is None:
            raise _not_found("no active geometry for this parcel")
        return _geometry_view(geometry)
