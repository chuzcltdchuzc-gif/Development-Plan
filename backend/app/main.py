"""Application entrypoint — FastAPI app factory.

B0 kernel (fail-closed config, structured logging, RFC-7807 errors, health
checks) plus B1 Identity & Authorization: PDP/PEP, request-scoped
Unit-of-Work, and the /v1/auth, /v1/admin routes, wired against real
Keycloak + Postgres adapters (verified against live infrastructure — see
CLAUDE.md for what that verification covered).
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine

from app.contexts.identity.adapters.keycloak import KeycloakIdentityProvider, KeycloakJWKSProvider
from app.contexts.identity.api import admin_router, auth_router
from app.contexts.identity.context_hydration import build_production_context_hydrator
from app.contexts.identity.dependencies import configure_identity_provider
from app.contexts.registry.api import parcel_router
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
from app.kernel.uow import configure_uow


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

    jwks = KeycloakJWKSProvider(realm_url=settings.keycloak_realm_url)
    verifier = JwtVerifier(
        jwks=jwks, issuer=settings.keycloak_realm_url, audience=settings.jwt_audience
    )
    configure_pep(verifier, build_production_context_hydrator(session_factory))

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

    return app


app = create_app()
