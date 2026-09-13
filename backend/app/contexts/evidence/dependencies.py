"""FastAPI dependency providers for the Evidence context (B5 Slices
B5.2/B5.3; upload HTTP endpoint and real StoragePort adapter, IMVP-5).

Same shape as app.contexts.registry.dependencies: EvidenceService is built
fresh per request from the request-scoped Unit-of-Work session
(app.kernel.uow.get_db_session) — never a fixed instance shared across
concurrent requests.

get_storage_port() below has no real adapter to return by default — R2
(Cloudflare, WORM-grade) remains genuinely unimplemented, out of scope
until B5.4. The real Supabase Storage adapter (IMVP-5,
app.contexts.evidence.adapters.supabase_storage.SupabaseStorageAdapter)
is wired over this default via `app.dependency_overrides` in app.main,
the identical override mechanism Registry's own GeometryPort already uses
for RealGeometryAdapter — this module's own default stays a loud failure
so a test or a future router that forgets to wire a real adapter fails
immediately rather than silently writing nowhere."""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.evidence.adapters.postgres_repositories import (
    PostgresEvidenceActorAttributionRepository,
    PostgresEvidenceRepository,
    PostgresParcelExistenceAdapter,
    PostgresPrincipalTenantAdapter,
)
from app.contexts.evidence.application.attribution_service import (
    EvidenceActorAttributionService,
)
from app.contexts.evidence.application.evidence_service import EvidenceService
from app.contexts.evidence.ports import (
    EvidenceActorAttributionRepository,
    EvidenceRepository,
    ParcelExistencePort,
    PrincipalTenantPort,
    StoragePort,
)
from app.kernel.uow import get_db_session


def get_evidence_repository(
    session: AsyncSession = Depends(get_db_session),
) -> EvidenceRepository:
    return PostgresEvidenceRepository(session)


def get_evidence_parcel_existence_port(
    session: AsyncSession = Depends(get_db_session),
) -> ParcelExistencePort:
    return PostgresParcelExistenceAdapter(session)


def get_storage_port() -> StoragePort:
    raise NotImplementedError(
        "No StoragePort adapter is configured. Production wires a real adapter over this "
        "default via app.dependency_overrides in app.main (IMVP-5: SupabaseStorageAdapter). "
        "Cloudflare R2 (WORM-grade) remains genuinely unimplemented, out of scope until B5.4. "
        "Tests must override this provider with a fake, never rely on it."
    )


def get_evidence_service(
    evidence: EvidenceRepository = Depends(get_evidence_repository),
    storage: StoragePort = Depends(get_storage_port),
    parcel_existence: ParcelExistencePort = Depends(get_evidence_parcel_existence_port),
) -> EvidenceService:
    return EvidenceService(evidence=evidence, storage=storage, parcel_existence=parcel_existence)


def get_evidence_actor_attribution_repository(
    session: AsyncSession = Depends(get_db_session),
) -> EvidenceActorAttributionRepository:
    return PostgresEvidenceActorAttributionRepository(session)


def get_principal_tenant_port(
    session: AsyncSession = Depends(get_db_session),
) -> PrincipalTenantPort:
    return PostgresPrincipalTenantAdapter(session)


def get_evidence_actor_attribution_service(
    attributions: EvidenceActorAttributionRepository = Depends(
        get_evidence_actor_attribution_repository
    ),
    evidence: EvidenceRepository = Depends(get_evidence_repository),
    parcel_existence: ParcelExistencePort = Depends(get_evidence_parcel_existence_port),
    principal_tenant: PrincipalTenantPort = Depends(get_principal_tenant_port),
) -> EvidenceActorAttributionService:
    return EvidenceActorAttributionService(
        attributions=attributions,
        evidence=evidence,
        parcel_existence=parcel_existence,
        principal_tenant=principal_tenant,
    )
