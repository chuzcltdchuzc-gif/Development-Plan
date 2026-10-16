"""FastAPI dependency providers for the Spatial context (B4 Slice 1).

Same shape as app.contexts.registry.dependencies: SpatialService is built
fresh per request from the request-scoped Unit-of-Work session
(app.kernel.uow.get_db_session) — never a fixed instance shared across
concurrent requests. get_parcel_geometry_repository and
get_parcel_existence_port both depend on the SAME get_db_session, which
FastAPI resolves once per request and caches — so both share one
AsyncSession/transaction.
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.spatial.adapters.postgres_repositories import (
    PostgresParcelExistenceAdapter,
    PostgresParcelGeometryRepository,
)
from app.contexts.spatial.application.spatial_service import SpatialService
from app.contexts.spatial.ports import ParcelExistencePort, ParcelGeometryRepository
from app.kernel.uow import get_db_session


def get_parcel_geometry_repository(
    session: AsyncSession = Depends(get_db_session),
) -> ParcelGeometryRepository:
    return PostgresParcelGeometryRepository(session)


def get_parcel_existence_port(
    session: AsyncSession = Depends(get_db_session),
) -> ParcelExistencePort:
    return PostgresParcelExistenceAdapter(session)


def get_spatial_service(
    geometries: ParcelGeometryRepository = Depends(get_parcel_geometry_repository),
    parcel_existence: ParcelExistencePort = Depends(get_parcel_existence_port),
) -> SpatialService:
    return SpatialService(geometries=geometries, parcel_existence=parcel_existence)
