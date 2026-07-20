"""ParcelService — Registry context's parcel use-cases (B3 slices 1-3,
docs/adr/ADR-013, docs/adr/ADR-014, docs/adr/ADR-015).

create/get/list/update/archive, plus atomic parcel-number allocation as an
integral part of creation. No ownership transfer, no geometry — those are
later slices. Every check here reuses an existing mechanism (CountryCode
validation from Identity, the kernel audit() function, the same
tenant-scope pattern AdminService already established, GOVERNANCE_ROLES
from Identity's role hierarchy) — never a new, divergent one.
"""
from __future__ import annotations

from fastapi import HTTPException, status

from app.contexts.identity.domain.value_objects import GOVERNANCE_ROLES, CountryCode
from app.contexts.registry.domain.parcel import Parcel, ParcelArchivedError
from app.contexts.registry.ports import ParcelNumberAllocator, ParcelRepository
from app.kernel.audit import audit
from app.kernel.context import ExecutionContext

DEFAULT_COUNTRY = "NG"


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="parcel not found")


def _in_scope(ctx: ExecutionContext, resource_tenant_id: str) -> bool:
    """Mirrors the identical helper in app.contexts.identity.application.
    admin_service — duplicated locally rather than imported, since that
    one is a private, context-internal symbol (see docs/adr/ADR-013's
    "known, small, deliberate duplication" section: promote to the kernel
    if a third context ever needs it, not before)."""
    return resource_tenant_id == ctx.tenant_id or ctx.has_any_role("super_admin")


def _can_mutate(ctx: ExecutionContext, parcel: Parcel) -> bool:
    """B3 slice 3 (docs/adr/ADR-015) — the fix for the confirmed ADR-005
    defect (any create-tier role could mutate any parcel in their tenant).
    Two independent grants, either sufficient on its own: the parcel's
    creator (ownership is a fact about who registered THIS resource, never
    delegable as a role is), or a currently-effective GOVERNANCE_ROLES
    member (direct or delegated — ctx.roles is already the union of both,
    ADR-011; a delegated governance role gets exactly the delegator's own
    reach, capped by highest_rank() at delegation time, no new check
    needed here). Called only after _in_scope has already confirmed tenant
    scope; super_admin's cross-tenant reach comes from that check, not
    this one — this one just confirms super_admin is also a GOVERNANCE_
    ROLES member so the override actually applies once in scope."""
    return parcel.created_by == ctx.principal_id or ctx.has_any_role(*GOVERNANCE_ROLES)


def _effective_authority(ctx: ExecutionContext, parcel: Parcel) -> str:
    """Audit-facing description of *why* a mutation was permitted — never
    used for the authorization decision itself (that's _can_mutate)."""
    if parcel.created_by == ctx.principal_id:
        return "creator"
    granted = sorted(set(ctx.roles) & GOVERNANCE_ROLES)
    return f"governance:{','.join(granted)}" if granted else "unknown"


def _delegated_roles(ctx: ExecutionContext) -> list[str]:
    """Populated by app.contexts.identity.context_hydration when any
    currently-effective delegation contributed roles to this request
    (docs/adr/ADR-015) — read-only here, never recomputed."""
    return list(ctx.attributes.get("delegated_roles") or [])


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
    def __init__(self, *, parcels: ParcelRepository, allocator: ParcelNumberAllocator) -> None:
        self.parcels = parcels
        self.allocator = allocator

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

        # Allocation happens in the SAME Unit-of-Work transaction as the
        # insert below (both self.allocator and self.parcels are built
        # from the same per-request AsyncSession — see
        # app.contexts.registry.dependencies) — so a failure anywhere in
        # this method rolls back the counter increment along with
        # everything else (docs/adr/ADR-014's transaction model). Goes
        # through Parcel's own guard method (ADR-013), not a raw field
        # assignment, so "never reassigned" is still enforced here too.
        parcel_number = await self.allocator.allocate(country_code=resolved_country)
        parcel.allocate_parcel_number(parcel_number)

        parcel = await self.parcels.add(parcel)
        await audit(
            "registry.parcel.created",
            resource_type="parcel",
            resource_id=parcel.parcel_id,
            decision="PERMIT",
            payload={
                "tenant_id": parcel.tenant_id,
                "origin": parcel.origin,
                "parcel_number": parcel.parcel_number,
            },
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
            raise _not_found()
        return _parcel_view(parcel)

    async def list_parcels(self, *, ctx: ExecutionContext) -> list[dict]:
        if not ctx.tenant_id:
            return []
        parcels = await self.parcels.list_for_tenant(ctx.tenant_id)
        return [_parcel_view(p) for p in parcels]

    async def _load_in_scope(self, *, ctx: ExecutionContext, parcel_id: str) -> Parcel:
        """Shared by update_parcel/archive_parcel: 404s exactly like
        get_parcel for a missing or out-of-tenant-scope parcel (existence
        is not revealed cross-tenant, ADR-013) — evaluated before the
        ownership/governance check, so a cross-tenant caller never learns
        whether they'd have passed it (ADR-015)."""
        parcel = await self.parcels.get(parcel_id)
        if not parcel or not _in_scope(ctx, parcel.tenant_id):
            raise _not_found()
        return parcel

    async def _authorize_mutation(self, *, ctx: ExecutionContext, parcel: Parcel) -> None:
        if _can_mutate(ctx, parcel):
            return
        await audit(
            "registry.parcel.mutation_denied",
            resource_type="parcel",
            resource_id=parcel.parcel_id,
            decision="DENY",
            payload={
                "tenant_id": parcel.tenant_id,
                "reason": "not_creator_and_not_governance",
                "delegated_roles": _delegated_roles(ctx),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="only the parcel's creator or a governance role may modify it",
        )

    async def update_parcel(
        self, *, ctx: ExecutionContext, parcel_id: str, fields: dict[str, object]
    ) -> dict:
        if not fields:
            raise _bad_request("no fields to update")
        size_sqm = fields.get("size_sqm")
        if size_sqm is not None and size_sqm <= 0:  # type: ignore[operator]
            raise _bad_request("size_sqm must be positive")

        parcel = await self._load_in_scope(ctx=ctx, parcel_id=parcel_id)
        await self._authorize_mutation(ctx=ctx, parcel=parcel)

        try:
            parcel.update_details(updated_by=ctx.principal_id, fields=fields)
        except ParcelArchivedError as exc:
            raise _conflict(str(exc)) from exc

        parcel = await self.parcels.update(parcel)
        await audit(
            "registry.parcel.updated",
            resource_type="parcel",
            resource_id=parcel.parcel_id,
            decision="PERMIT",
            payload={
                "tenant_id": parcel.tenant_id,
                "effective_authority": _effective_authority(ctx, parcel),
                "delegated_roles": _delegated_roles(ctx),
                "fields_changed": sorted(fields),
            },
        )
        return _parcel_view(parcel)

    async def archive_parcel(self, *, ctx: ExecutionContext, parcel_id: str) -> dict:
        parcel = await self._load_in_scope(ctx=ctx, parcel_id=parcel_id)
        await self._authorize_mutation(ctx=ctx, parcel=parcel)

        try:
            parcel.archive(archived_by=ctx.principal_id)
        except ParcelArchivedError as exc:
            raise _conflict(str(exc)) from exc

        parcel = await self.parcels.update(parcel)
        await audit(
            "registry.parcel.archived",
            resource_type="parcel",
            resource_id=parcel.parcel_id,
            decision="PERMIT",
            payload={
                "tenant_id": parcel.tenant_id,
                "effective_authority": _effective_authority(ctx, parcel),
                "delegated_roles": _delegated_roles(ctx),
            },
        )
        return _parcel_view(parcel)
