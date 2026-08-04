"""Spatial API router — /v1/spatial/* (B4 Slice 1, docs/adr/ADR-018;
authorization refined B4 Slice 2, docs/adr/ADR-022).

Routers are composition only: parse + validate via DTOs, call
SpatialService, shape the response — the identical convention Registry's
own routers use. The router-level gate is still the same coarse
`require_role(*PARCEL_REGISTRANT_ROLES)` Registry's own mutation endpoints
use (imported directly, not duplicated — the same cross-context role-set
reuse ADR-013 already established for Registry consuming Identity's
`Role` enum) — it only confirms the caller holds *some* registrant role,
never that they are authorized for *this specific* parcel. The
resource-specific creator-or-governance check (ADR-022) is enforced
entirely inside `SpatialService`, not here — see its own docstring.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.contexts.registry.domain.value_objects import PARCEL_REGISTRANT_ROLES
from app.contexts.spatial.api.dtos import SubmitGeometryRequest
from app.contexts.spatial.application.spatial_service import SpatialService
from app.contexts.spatial.dependencies import get_spatial_service
from app.kernel.authorization.pep import require_auth, require_role
from app.kernel.context import ExecutionContext

router = APIRouter(prefix="/v1/spatial", tags=["spatial"])


@router.put("/parcels/{parcel_id}/geometry", status_code=201)
async def submit_geometry(
    parcel_id: str,
    body: SubmitGeometryRequest,
    ctx: ExecutionContext = Depends(require_role(*PARCEL_REGISTRANT_ROLES)),
    spatial_service: SpatialService = Depends(get_spatial_service),
) -> dict:
    return await spatial_service.submit_geometry(
        ctx=ctx, parcel_id=parcel_id, boundary=body.boundary
    )


@router.get("/parcels/{parcel_id}/geometry")
async def get_active_geometry(
    parcel_id: str,
    ctx: ExecutionContext = Depends(require_auth),
    spatial_service: SpatialService = Depends(get_spatial_service),
) -> dict:
    return await spatial_service.get_active_geometry(ctx=ctx, parcel_id=parcel_id)
