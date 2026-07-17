"""Builds the PEP's context-hydrator callback (app.kernel.authorization.pep.
ContextHydrator) from the Identity UserRepository/TenantRepository — the
one place a verified token's `sub` claim is turned into authorization
attributes.

Fail-closed on both a suspended *user* (the original check) and a
suspended/archived *tenant* (B2 slice 3, docs/adr/ADR-010): either one
returns None here, which the PEP treats as "no authorization attributes" —
roles/tenant_id come back empty. This runs on every authenticated request
(this hydrator is called per-request, not just at login), so a tenant
suspended after its members already hold valid access tokens loses
effective authorization immediately on any `require_role`-gated or PDP-
checked route, not only on their next login.

Precision matters here: an empty-attrs result does NOT make `require_auth`
-only routes (e.g. `/v1/auth/me`) start returning 401 for that same
already-issued token. `ExecutionContext.is_anonymous` only checks the
literal "anonymous" sentinel principal_id; the PEP's fallback
(`attrs.get("principal_id", subject)`) still yields the raw IdP subject
when attrs is empty, so such a request is technically "authenticated,"
just powerless. That's existing, documented B1 behavior
(app.kernel.authorization.pep's own docstring: "a valid Keycloak session
with no local account yet ... roles is empty and the PDP default-denies
almost everything anyway") — this module extends the SAME fallback to a
second cause (tenant suspended) rather than introducing a new one, and
does not change that documented ADR-009 contract.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.contexts.identity.adapters.postgres_repositories import (
    PostgresTenantRepository,
    PostgresUserRepository,
)
from app.contexts.identity.domain.user import User
from app.contexts.identity.ports import TenantRepository, UserRepository


def _attrs_for(user: User | None) -> dict | None:
    if user is None or not user.can_authenticate():
        return None
    return {
        # Our own internal id — NOT the raw Keycloak subject — is what the
        # rest of the system compares against (owner checks, self-checks,
        # role-assignment target ids). See docs/adr/ADR-004 point 5.
        "principal_id": user.user_id,
        "email": user.email,
        "country": user.country,
        "tenant_id": user.tenant_id,
        "organization_id": user.organization_id,
        "roles": list(user.roles),
    }


def build_context_hydrator(
    users: UserRepository, tenants: TenantRepository | None = None
) -> Callable[[str], Awaitable[dict | None]]:
    """For tests: `users`/`tenants` are already scoped appropriately (an
    in-memory fake has no RLS to worry about). `tenants` is optional so
    existing tests that don't care about tenant lifecycle don't need to
    thread one through."""

    async def _hydrate(keycloak_subject: str) -> dict | None:
        user = await users.get_by_keycloak_subject(keycloak_subject)
        if user is None or not user.can_authenticate():
            return None
        if tenants is not None:
            tenant = await tenants.get(user.tenant_id)
            if tenant is None or not tenant.is_active():
                return None
        return _attrs_for(user)

    return _hydrate


def build_production_context_hydrator(
    session_factory: async_sessionmaker[AsyncSession],
) -> Callable[[str], Awaitable[dict | None]]:
    """Production hydrator: opens its own short-lived read transaction per
    call (there is no per-request session to reuse at this point in the
    request lifecycle — this runs inside the PEP dependency, before any
    route-level session dependency exists).

    This lookup is keyed on the IdP subject alone — we don't yet know the
    caller's tenant, which is the whole point of the lookup — so it must
    run with `app.is_super_admin` set for this one query, bypassing the
    identity_users/tenants tenant-isolation RLS policies (migrations/
    versions/0001_identity_and_audit.py, 0005_tenants.py). This is safe:
    the query is fixed at the call site (not influenced by request input
    beyond the already-verified subject), read-only, and rolled back
    immediately — it cannot leak or mutate another tenant's data, only
    resolve which tenant this principal belongs to and whether that tenant
    is still active.
    """

    async def _hydrate(keycloak_subject: str) -> dict | None:
        async with session_factory() as session:
            await session.execute(text("SET LOCAL app.is_super_admin = 'true'"))
            repo = PostgresUserRepository(session)
            user = await repo.get_by_keycloak_subject(keycloak_subject)
            if user is None or not user.can_authenticate():
                await session.rollback()
                return None
            tenant = await PostgresTenantRepository(session).get(user.tenant_id)
            await session.rollback()  # read-only; never persist from here
        if tenant is None or not tenant.is_active():
            return None
        return _attrs_for(user)

    return _hydrate
