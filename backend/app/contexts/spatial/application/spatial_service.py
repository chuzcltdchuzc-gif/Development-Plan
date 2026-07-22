"""SpatialService — Spatial Intelligence context's use-cases (B4 Slice 1,
docs/adr/ADR-018, docs/adr/ADR-019).

submit_geometry/get_active_geometry only. No overlap detection, no
duplicate-geometry detection, no adjacency, no spatial search, no GIS
computation of any kind — those are ADR-020/021's job. This slice's
GeometryPort is still `PlaceholderGeometryAdapter` (Registry's own
dependency, unconnected to this service) — this service does not
implement, call, or otherwise wire the real GeometryPort adapter; that is
explicitly ADR-020's responsibility, not this slice's.

Authorization here is deliberately coarse and narrow, not a full "Spatial
Authorization Model" (that is ADR-022's job, not yet written): the router
gates on the same `PARCEL_REGISTRANT_ROLES` role check Registry's own
mutation endpoints use, and this service additionally confirms the
referenced parcel is in the caller's tenant scope via `_in_scope` — the
identical two-independent-layers pattern every prior context in this
codebase uses (RLS as one layer, an explicit application-level tenant
check as the other, ADR-011/013): `ParcelExistencePort`'s real adapter
already benefits from `parcels`' own RLS policy (a read-only, FK-following
query through the same request-scoped session), but RLS alone is not
something Spatial's own tests can exercise against an in-memory fake, so
the explicit `_in_scope` check here is not redundant — it is the layer
that is actually verified by this slice's test suite, exactly as
`app.contexts.registry.application.parcel_service._in_scope` is for
Registry. It does *not* yet check "is this caller specifically the
parcel's creator or a governance role" — that finer-grained,
resource-aware rule is exactly what ADR-022 is reserved to design,
mirroring ADR-015's model once it exists.
"""
from __future__ import annotations

from fastapi import HTTPException, status

from app.contexts.spatial.domain.parcel_geometry import InvalidGeometryError, ParcelGeometry
from app.contexts.spatial.ports import ParcelExistencePort, ParcelGeometryRepository
from app.kernel.audit import audit
from app.kernel.context import ExecutionContext


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _in_scope(ctx: ExecutionContext, resource_tenant_id: str) -> bool:
    """Mirrors the identical helper in app.contexts.registry.application.
    parcel_service (itself mirroring app.contexts.identity.application.
    admin_service) — duplicated locally rather than imported, since it is
    a private, context-internal symbol (see docs/adr/ADR-013's "known,
    small, deliberate duplication" section: promote to the kernel if a
    fourth context needs it, not before)."""
    return resource_tenant_id == ctx.tenant_id or ctx.has_any_role("super_admin")


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

    async def submit_geometry(
        self, *, ctx: ExecutionContext, parcel_id: str, boundary: str
    ) -> dict:
        parcel_tenant_id = await self.parcel_existence.get_tenant_id(parcel_id=parcel_id)
        if parcel_tenant_id is None or not _in_scope(ctx, parcel_tenant_id):
            raise _not_found("parcel not found")

        existing = await self.geometries.get_active_for_parcel(parcel_id)
        if existing is not None:
            existing.supersede()
            await self.geometries.update(existing)

        try:
            geometry = ParcelGeometry.new(
                tenant_id=parcel_tenant_id,
                parcel_id=parcel_id,
                boundary=boundary,
                created_by=ctx.principal_id,
            )
        except InvalidGeometryError as exc:
            raise _bad_request(str(exc)) from exc

        geometry = await self.geometries.add(geometry)
        await audit(
            "spatial.parcel_geometry.created",
            resource_type="parcel_geometry",
            resource_id=geometry.geometry_id,
            decision="PERMIT",
            payload={
                "tenant_id": geometry.tenant_id,
                "parcel_id": geometry.parcel_id,
                "superseded_geometry_id": existing.geometry_id if existing else None,
            },
        )
        return _geometry_view(geometry)

    async def get_active_geometry(self, *, ctx: ExecutionContext, parcel_id: str) -> dict:
        parcel_tenant_id = await self.parcel_existence.get_tenant_id(parcel_id=parcel_id)
        if parcel_tenant_id is None or not _in_scope(ctx, parcel_tenant_id):
            raise _not_found("parcel not found")
        geometry = await self.geometries.get_active_for_parcel(parcel_id)
        if geometry is None:
            raise _not_found("no active geometry for this parcel")
        return _geometry_view(geometry)
