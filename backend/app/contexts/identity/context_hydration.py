"""Builds the PEP's context-hydrator callback (app.kernel.authorization.pep.
ContextHydrator) from the Identity UserRepository — the one place a
verified token's `sub` claim is turned into authorization attributes.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.contexts.identity.adapters.postgres_repositories import PostgresUserRepository
from app.contexts.identity.domain.user import User
from app.contexts.identity.ports import UserRepository


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


def build_context_hydrator(users: UserRepository) -> Callable[[str], Awaitable[dict | None]]:
    """For tests: `users` is already scoped appropriately (an in-memory
    fake has no RLS to worry about)."""

    async def _hydrate(keycloak_subject: str) -> dict | None:
        return _attrs_for(await users.get_by_keycloak_subject(keycloak_subject))

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
    identity_users tenant-isolation RLS policy (migrations/versions/
    0001_identity_and_audit.py). This is safe: the query is fixed at the
    call site (not influenced by request input beyond the already-verified
    subject), read-only, and rolled back immediately — it cannot leak or
    mutate another tenant's data, only resolve which tenant this principal
    belongs to.
    """

    async def _hydrate(keycloak_subject: str) -> dict | None:
        async with session_factory() as session:
            await session.execute(text("SET LOCAL app.is_super_admin = 'true'"))
            repo = PostgresUserRepository(session)
            user = await repo.get_by_keycloak_subject(keycloak_subject)
            await session.rollback()  # read-only; never persist from here
        return _attrs_for(user)

    return _hydrate
