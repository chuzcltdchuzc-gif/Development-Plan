"""FastAPI dependency providers for the Evidence context (B5 Slice B5.2).

Same shape as app.contexts.registry.dependencies: EvidenceService is built
fresh per request from the request-scoped Unit-of-Work session
(app.kernel.uow.get_db_session) — never a fixed instance shared across
concurrent requests. No router includes this wiring yet (no upload endpoint
exists in this slice — B5.3); this module exists so the DI chain is
provably correct end-to-end ahead of that router, the same "seam before
consumer" discipline app.contexts.registry.adapters.geometry.
PlaceholderGeometryAdapter already demonstrated.
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.evidence.adapters.postgres_repositories import PostgresEvidenceRepository
from app.contexts.evidence.application.evidence_service import EvidenceService
from app.contexts.evidence.ports import EvidenceRepository
from app.kernel.uow import get_db_session


def get_evidence_repository(
    session: AsyncSession = Depends(get_db_session),
) -> EvidenceRepository:
    return PostgresEvidenceRepository(session)


def get_evidence_service(
    evidence: EvidenceRepository = Depends(get_evidence_repository),
) -> EvidenceService:
    return EvidenceService(evidence=evidence)
