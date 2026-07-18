"""FastAPI dependency providers for the Registry context (B3 slice 1).

Same shape as app.contexts.identity.dependencies: ParcelService is built
fresh per request from the request-scoped Unit-of-Work session
(app.kernel.uow.get_db_session) — never a fixed instance shared across
concurrent requests.
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.registry.adapters.postgres_repositories import PostgresParcelRepository
from app.contexts.registry.application.parcel_service import ParcelService
from app.contexts.registry.ports import ParcelRepository
from app.kernel.uow import get_db_session


def get_parcel_repository(session: AsyncSession = Depends(get_db_session)) -> ParcelRepository:
    return PostgresParcelRepository(session)


def get_parcel_service(
    parcels: ParcelRepository = Depends(get_parcel_repository),
) -> ParcelService:
    return ParcelService(parcels=parcels)
