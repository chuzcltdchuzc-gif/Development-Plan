"""ParcelService — Registry context's parcel use-cases (B3 slice 1,
docs/adr/ADR-013).

Only create/get/list in this slice. No mutation commands, no ownership
transfer, no geometry, no atomic numbering — those are later slices. Every
check here reuses an existing mechanism (CountryCode validation from
Identity, the kernel audit() function, the same tenant-scope pattern
AdminService already established) — never a new, divergent one.
"""
from __future__ import annotations

from fastapi import HTTPException, status

from app.contexts.identity.domain.value_objects import CountryCode
from app.contexts.registry.domain.parcel import Parcel
from app.contexts.registry.ports import ParcelRepository
from app.kernel.audit import audit
from app.kernel.context import ExecutionContext

DEFAULT_COUNTRY = "NG"


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _in_scope(ctx: ExecutionContext, resource_tenant_id: str) -> bool:
    """Mirrors the identical helper in app.contexts.identity.application.
    admin_service — duplicated locally rather than imported, since that
    one is a private, context-internal symbol (see docs/adr/ADR-013's
    "known, small, deliberate duplication" section: promote to the kernel
    if a third context ever needs it, not before)."""
    return resource_tenant_id == ctx.tenant_id or ctx.has_any_role("super_admin")


def _parcel_view(parcel: Parcel) -> dict:
    return {
        "parcel_id": parcel.parcel_id,
        "tenant_id": parcel.tenant_id,
        "country_code": parcel.country_code,
        "origin": parcel.origin,
        "created_by": parcel.created_by,
        "status": parcel.status,
        "parcel_number": parcel.parcel_number,
        "title": parcel.title,
        "address": parcel.address,
        "state": parcel.state,
        "lga": parcel.lga,
        "ward": parcel.ward,
        "community": parcel.community,
        "property_type": parcel.property_type,
        "size_sqm": parcel.size_sqm,
        "ownership_type": parcel.ownership_type,
        "current_owner_name": parcel.current_owner_name,
        "current_owner_contact": parcel.current_owner_contact,
        "created_at": parcel.created_at,
        "updated_at": parcel.updated_at,
        "archived_at": parcel.archived_at,
    }


class ParcelService:
    def __init__(self, *, parcels: ParcelRepository) -> None:
        self.parcels = parcels

    async def create_parcel(
        self,
        *,
        ctx: ExecutionContext,
        country_code: str | None = None,
        title: str | None = None,
        address: str | None = None,
        state: str | None = None,
        lga: str | None = None,
        ward: str | None = None,
        community: str | None = None,
        property_type: str | None = None,
        size_sqm: float | None = None,
        ownership_type: str | None = None,
        current_owner_name: str | None = None,
        current_owner_contact: str | None = None,
    ) -> dict:
        if not ctx.tenant_id:
            # Structurally unreachable — require_role already restricts
            # this endpoint to authenticated registrant roles, which
            # hydration only grants with a resolved tenant_id (ADR-010).
            # Fail closed anyway rather than register into "None".
            raise _bad_request("caller has no tenant to register a parcel within")

        resolved_country = (country_code or ctx.country or DEFAULT_COUNTRY).upper()
        try:
            resolved_country = CountryCode(resolved_country).value
        except ValueError as exc:
            raise _bad_request(str(exc)) from exc

        if size_sqm is not None and size_sqm <= 0:
            raise _bad_request("size_sqm must be positive")

        parcel = Parcel.new(
            tenant_id=ctx.tenant_id,
            country_code=resolved_country,
            origin="platform_registration",
            created_by=ctx.principal_id,
            title=title,
            address=address,
            state=state,
            lga=lga,
            ward=ward,
            community=community,
            property_type=property_type,
            size_sqm=size_sqm,
            ownership_type=ownership_type,
            current_owner_name=current_owner_name,
            current_owner_contact=current_owner_contact,
        )
        parcel = await self.parcels.add(parcel)
        await audit(
            "registry.parcel.created",
            resource_type="parcel",
            resource_id=parcel.parcel_id,
            decision="PERMIT",
            payload={"tenant_id": parcel.tenant_id, "origin": parcel.origin},
        )
        return _parcel_view(parcel)

    async def get_parcel(self, *, ctx: ExecutionContext, parcel_id: str) -> dict:
        parcel = await self.parcels.get(parcel_id)
        # RLS already makes a cross-tenant row invisible at the database
        # layer (parcels_tenant_isolation) — this explicit check is the
        # second, independent layer, not a substitute for it. Same
        # super_admin-aware shape as every other _in_scope check in this
        # codebase (ADR-011/ADR-013).
        if not parcel or not _in_scope(ctx, parcel.tenant_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="parcel not found")
        return _parcel_view(parcel)

    async def list_parcels(self, *, ctx: ExecutionContext) -> list[dict]:
        if not ctx.tenant_id:
            return []
        parcels = await self.parcels.list_for_tenant(ctx.tenant_id)
        return [_parcel_view(p) for p in parcels]
