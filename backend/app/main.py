"""Application entrypoint — FastAPI app factory.

B0 kernel (fail-closed config, structured logging, RFC-7807 errors, health
checks) plus B1 Identity & Authorization: PDP/PEP, request-scoped
Unit-of-Work, and the /v1/auth, /v1/admin routes, wired against real
Postgres adapters (verified against live infrastructure — see CLAUDE.md for
what that verification covered).

IMVP-3 (ADR-025): the PEP's token verifier now trusts Supabase Auth, the
production identity provider — not Keycloak. `KeycloakIdentityProvider` is
still wired below purely to keep the historical /v1/auth/register|login|
refresh endpoints working (a separate, deferred disposition question); it
plays no role in verifying tokens presented to protected routes any more.
"""
from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.contexts.evidence.adapters.supabase_storage import SupabaseStorageAdapter
from app.contexts.evidence.api import evidence_router
from app.contexts.evidence.dependencies import get_storage_port
from app.contexts.evidence.ports import StoragePort
from app.contexts.identity.adapters.keycloak import KeycloakIdentityProvider
from app.contexts.identity.adapters.supabase import SupabaseJWKSProvider, supabase_issuer
from app.contexts.identity.api import admin_router, auth_router
from app.contexts.identity.context_hydration import build_production_context_hydrator
from app.contexts.identity.dependencies import configure_identity_provider
from app.contexts.registry.api import parcel_router
from app.contexts.registry.dependencies import get_geometry_port
from app.contexts.registry.ports import GeometryPort
from app.contexts.spatial.adapters.geometry_port_adapter import RealGeometryAdapter
from app.contexts.spatial.adapters.postgres_repositories import PostgresParcelGeometryRepository
from app.contexts.spatial.api import spatial_router
from app.kernel.audit import configure_eager_fallback
from app.kernel.audit_postgres import EagerPostgresAuditStore
from app.kernel.authorization.pep import configure_pep
from app.kernel.config import get_settings
from app.kernel.db import build_session_factory
from app.kernel.errors import register_error_handlers
from app.kernel.health import build_health_router
from app.kernel.logging import configure_logging
from app.kernel.security.http_hardening import configure_security
from app.kernel.security.jwt import JwtVerifier
from app.kernel.uow import configure_uow, get_db_session


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    configure_security(app, rate_limit_enabled=True)
    register_error_handlers(app)

    engine = create_async_engine(str(settings.database_url))
    app.include_router(build_health_router(engine))

    session_factory = build_session_factory(engine)
    configure_uow(session_factory)
    configure_eager_fallback(EagerPostgresAuditStore(session_factory))

    # Production token verification trusts Supabase Auth (ADR-025), not
    # Keycloak — this is the actual gate protected routes go through.
    jwks = SupabaseJWKSProvider(project_url=settings.supabase_project_url)
    verifier = JwtVerifier(
        jwks=jwks,
        issuer=supabase_issuer(settings.supabase_project_url),
        audience=settings.supabase_jwt_audience,
        algorithms=[settings.supabase_jwt_algorithm],
    )
    configure_pep(verifier, build_production_context_hydrator(session_factory))

    # Historical only (see module docstring): still backs
    # /v1/auth/register|login|refresh, which do not sit behind the PEP
    # verifier above and are not part of the Supabase-authenticated path.
    identity_provider = KeycloakIdentityProvider(
        realm_url=settings.keycloak_realm_url,
        client_id=settings.keycloak_client_id,
        client_secret=settings.keycloak_client_secret,
        admin_token_url=settings.keycloak_admin_token_url,
        admin_api_url=settings.keycloak_admin_api_url,
    )
    configure_identity_provider(identity_provider)

    app.include_router(auth_router.router)
    app.include_router(admin_router.router)
    app.include_router(parcel_router.router)
    app.include_router(spatial_router.router)
    app.include_router(evidence_router.router)

    # Composition-root-only wiring (docs/adr/ADR-019/ADR-022): connects
    # Registry's GeometryPort to Spatial's real adapter via
    # dependency_overrides, so neither app.contexts.registry nor
    # app.contexts.spatial imports the other directly. Registry's own
    # get_geometry_port (app/contexts/registry/dependencies.py) is never
    # edited for this — only this file, and tests/app_factory.py, are
    # allowed to know about both bounded contexts at once.
    def _get_real_geometry_port(
        session: AsyncSession = Depends(get_db_session),
    ) -> GeometryPort:
        return RealGeometryAdapter(PostgresParcelGeometryRepository(session))

    app.dependency_overrides[get_geometry_port] = _get_real_geometry_port

    # IMVP-5: the real Supabase Storage adapter, wired the identical way
    # GeometryPort's real adapter is above — Evidence's own get_storage_port
    # (app/contexts/evidence/dependencies.py) never learns a concrete
    # adapter exists; only this composition root does.
    def _get_real_storage_port() -> StoragePort:
        return SupabaseStorageAdapter(
            project_url=settings.supabase_project_url,
            service_role_key=settings.supabase_service_role_key,
            bucket=settings.supabase_evidence_bucket,
        )

    app.dependency_overrides[get_storage_port] = _get_real_storage_port

    return app


app = create_app()
