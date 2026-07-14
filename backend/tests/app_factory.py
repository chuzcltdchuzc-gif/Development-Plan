"""Builds a fully-wired FastAPI app for acceptance tests — real kernel +
Identity application logic, with Keycloak and Postgres swapped for
in-memory fakes at the port boundary (app.contexts.identity.ports). This is
the same wiring shape app.main uses in production, just with adapters
substituted (docs/adr/ADR-002: ports & adapters).
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, FastAPI, HTTPException, status

from app.contexts.identity.api import admin_router, auth_router
from app.contexts.identity.application.admin_service import AdminService
from app.contexts.identity.application.auth_service import AuthService
from app.contexts.identity.context_hydration import build_context_hydrator
from app.kernel.audit import configure_audit_store
from app.kernel.authorization.pep import configure_pep, current_context_dep, require_role
from app.kernel.context import ExecutionContext
from app.kernel.errors import register_error_handlers
from app.kernel.security.http_hardening import configure_security
from app.kernel.security.jwt import JwtVerifier
from tests.fakes.audit_store import InMemoryAuditStore
from tests.fakes.identity import (
    FakeIdentityProvider,
    InMemorySessionRepository,
    InMemoryUserRepository,
)
from tests.fakes.jwks import FakeKeycloak


@dataclass
class AppHarness:
    app: FastAPI
    keycloak: FakeKeycloak
    users: InMemoryUserRepository
    sessions: InMemorySessionRepository
    identity_provider: FakeIdentityProvider
    audit_store: InMemoryAuditStore


def build_test_app(*, rate_limit_enabled: bool = True) -> AppHarness:
    keycloak = FakeKeycloak()
    users = InMemoryUserRepository()
    sessions = InMemorySessionRepository()
    identity_provider = FakeIdentityProvider(keycloak)
    audit_store = InMemoryAuditStore()

    configure_audit_store(audit_store)

    verifier = JwtVerifier(jwks=keycloak, issuer=keycloak.issuer, audience=keycloak.audience)
    configure_pep(verifier, build_context_hydrator(users))

    auth_service = AuthService(users=users, sessions=sessions, identity_provider=identity_provider)
    admin_service = AdminService(users=users)
    auth_router.configure_router(auth_service)
    admin_router.configure_router(admin_service)

    app = FastAPI(title="landvault-api-test")
    register_error_handlers(app)
    configure_security(app, rate_limit_enabled=rate_limit_enabled)
    app.include_router(auth_router.router)
    app.include_router(admin_router.router)

    @app.get("/v1/test/protected")
    async def protected_route(ctx: ExecutionContext = Depends(current_context_dep)) -> dict:
        if ctx.is_anonymous:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
            )
        return {"principal_id": ctx.principal_id}

    @app.get("/v1/test/governance-only")
    async def governance_only_route(
        ctx: ExecutionContext = Depends(
            require_role("super_admin", "surveyor_general", "compliance_officer")
        ),
    ) -> dict:
        return {"principal_id": ctx.principal_id}

    return AppHarness(
        app=app,
        keycloak=keycloak,
        users=users,
        sessions=sessions,
        identity_provider=identity_provider,
        audit_store=audit_store,
    )
