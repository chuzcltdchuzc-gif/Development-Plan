"""FastAPI dependency providers for the Registry context (B3 slices 1-2).

Same shape as app.contexts.identity.dependencies: ParcelService is built
fresh per request from the request-scoped Unit-of-Work session
(app.kernel.uow.get_db_session) — never a fixed instance shared across
concurrent requests. get_parcel_repository and get_parcel_number_allocator
both depend on the SAME get_db_session, which FastAPI resolves once per
request and caches — so both share one AsyncSession/transaction, exactly
the property docs/adr/ADR-014's transaction model relies on.
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.registry.adapters.postgres_repositories import (
    PostgresParcelNumberAllocator,
    PostgresParcelRepository,
)
from app.contexts.registry.application.parcel_service import ParcelService
from app.contexts.registry.ports import ParcelNumberAllocator, ParcelRepository
from app.kernel.uow import get_db_session


def get_parcel_repository(session: AsyncSession = Depends(get_db_session)) -> ParcelRepository:
    return PostgresParcelRepository(session)


def get_parcel_number_allocator(
    session: AsyncSession = Depends(get_db_session),
) -> ParcelNumberAllocator:
    return PostgresParcelNumberAllocator(session)


def get_parcel_service(
    parcels: ParcelRepository = Depends(get_parcel_repository),
    allocator: ParcelNumberAllocator = Depends(get_parcel_number_allocator),
) -> ParcelService:
    return ParcelService(parcels=parcels, allocator=allocator)
