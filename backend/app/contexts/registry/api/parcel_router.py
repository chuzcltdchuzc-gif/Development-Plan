"""Registry API router — /v1/parcels/* (B3 slice 1, docs/adr/ADR-013;
mutation routes added B3 slice 3, docs/adr/ADR-015).

Routers are composition only: parse + validate via DTOs, call
ParcelService, shape the response. No business logic lives here — in
particular, the ownership-or-governance mutation check lives in
ParcelService, not here, so it applies uniformly regardless of which
endpoint (or a future one) calls it. ParcelService is built fresh per
request (Depends(get_parcel_service)) — same reasoning as
app.contexts.identity.dependencies for AuthService/AdminService: never a
fixed instance shared across concurrent requests.

PATCH/archive are gated by the identical coarse `require_role(
*PARCEL_REGISTRANT_ROLES)` the create endpoint already uses — holding a
registrant role is necessary to reach these endpoints at all, but is no
longer sufficient on its own; ParcelService's fine-grained,
resource-aware check decides the actual permit/deny (ADR-015).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.contexts.registry.api.dtos import CreateParcelRequest, UpdateParcelRequest
from app.contexts.registry.application.parcel_service import ParcelService
from app.contexts.registry.dependencies import get_parcel_service
from app.contexts.registry.domain.value_objects import PARCEL_REGISTRANT_ROLES
from app.kernel.authorization.pep import require_auth, require_role
from app.kernel.context import ExecutionContext

router = APIRouter(prefix="/v1/parcels", tags=["registry"])


@router.post("", status_code=201)
async def create_parcel(
    body: CreateParcelRequest,
    ctx: ExecutionContext = Depends(require_role(*PARCEL_REGISTRANT_ROLES)),
    parcel_service: ParcelService = Depends(get_parcel_service),
) -> dict:
    return await parcel_service.create_parcel(ctx=ctx, **body.model_dump())


@router.patch("/{parcel_id}")
async def update_parcel(
    parcel_id: str,
    body: UpdateParcelRequest,
    ctx: ExecutionContext = Depends(require_role(*PARCEL_REGISTRANT_ROLES)),
    parcel_service: ParcelService = Depends(get_parcel_service),
) -> dict:
    return await parcel_service.update_parcel(
        ctx=ctx, parcel_id=parcel_id, fields=body.model_dump(exclude_unset=True)
    )


@router.post("/{parcel_id}/archive")
async def archive_parcel(
    parcel_id: str,
    ctx: ExecutionContext = Depends(require_role(*PARCEL_REGISTRANT_ROLES)),
    parcel_service: ParcelService = Depends(get_parcel_service),
) -> dict:
    return await parcel_service.archive_parcel(ctx=ctx, parcel_id=parcel_id)


@router.get("")
async def list_parcels(
    ctx: ExecutionContext = Depends(require_auth),
    parcel_service: ParcelService = Depends(get_parcel_service),
) -> list[dict]:
    return await parcel_service.list_parcels(ctx=ctx)


@router.get("/{parcel_id}")
async def get_parcel(
    parcel_id: str,
    ctx: ExecutionContext = Depends(require_auth),
    parcel_service: ParcelService = Depends(get_parcel_service),
) -> dict:
    return await parcel_service.get_parcel(ctx=ctx, parcel_id=parcel_id)
