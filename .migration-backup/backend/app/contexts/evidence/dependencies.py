"""FastAPI dependency providers for the Evidence context (B5 Slices B5.2/B5.3).

Same shape as app.contexts.registry.dependencies: EvidenceService is built
fresh per request from the request-scoped Unit-of-Work session
(app.kernel.uow.get_db_session) — never a fixed instance shared across
concurrent requests. No router includes this wiring yet (no upload HTTP
endpoint exists in this slice); this module exists so the DI chain is
provably correct end-to-end ahead of that router, the same "seam before
consumer" discipline app.contexts.registry.adapters.geometry.
PlaceholderGeometryAdapter already demonstrated.

get_storage_port() has no real adapter to return: Supabase Storage and
Cloudflare R2 adapters are explicitly out of scope for B5.1/B5.2/B5.3 (both
need a new external dependency — docs/ENGINEERING_RULES.md rule 5 — and
live credentials this programme does not yet have). Returning the
in-memory test fake here would be actively wrong — a hermetic test double
silently substituted into a real request path is exactly the kind of
"looks wired, isn't real" defect docs/adr/ADR-007-audit-trail-evidence-model.md's
own founding motivation exists to prevent. This provider therefore raises
loudly, by design, if ever actually resolved outside a test — the fail-closed
discipline docs/ENGINEERING_RULES.md rule 2 already requires for missing
security-relevant configuration, applied here to a missing storage backend."""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.evidence.adapters.postgres_repositories import PostgresEvidenceRepository
from app.contexts.evidence.application.evidence_service import EvidenceService
from app.contexts.evidence.ports import EvidenceRepository, StoragePort
from app.kernel.uow import get_db_session


def get_evidence_repository(
    session: AsyncSession = Depends(get_db_session),
) -> EvidenceRepository:
    return PostgresEvidenceRepository(session)


def get_storage_port() -> StoragePort:
    raise NotImplementedError(
        "No StoragePort adapter is configured. Supabase Storage / Cloudflare R2 adapters "
        "are not yet implemented (require docs/ENGINEERING_RULES.md rule 5 dependency "
        "approval and live credentials) — see docs/PHASE-B5_IMPLEMENTATION_PLAN.md Slices "
        "B5.7/B5.8. Tests must override this provider with a fake, never rely on it."
    )


def get_evidence_service(
    evidence: EvidenceRepository = Depends(get_evidence_repository),
    storage: StoragePort = Depends(get_storage_port),
) -> EvidenceService:
    return EvidenceService(evidence=evidence, storage=storage)
