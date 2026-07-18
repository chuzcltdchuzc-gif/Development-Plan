"""Builds the PEP's context-hydrator callback (app.kernel.authorization.pep.
ContextHydrator) from the Identity UserRepository/TenantRepository/
DelegationRepository — the one place a verified token's `sub` claim is
turned into authorization attributes.

Fail-closed on a suspended *user*, a suspended/archived *tenant* (B2 slice
3, docs/adr/ADR-010), and now on delegated roles that are no longer
currently effective (B2 slice 4, docs/adr/ADR-011): the first two return
None entirely — "no authorization attributes" — while an ineffective
delegation simply isn't added to the role set (the principal's own direct
roles, if any, are unaffected). This runs on every authenticated request
(this hydrator is called per-request, not just at login), so a tenant
suspended, a delegator demoted, or a delegation revoked after its
delegate already holds a valid access token all take effect immediately —
no caching layer exists anywhere in this pipeline to make that untrue.

Precision matters here: an empty-attrs result does NOT make `require_auth`
-only routes (e.g. `/v1/auth/me`) start returning 401 for that same
already-issued token. `ExecutionContext.is_anonymous` only checks the
literal "anonymous" sentinel principal_id; the PEP's fallback
(`attrs.get("principal_id", subject)`) still yields the raw IdP subject
when attrs is empty, so such a request is technically "authenticated,"
just powerless. That's existing, documented B1 behavior
(app.kernel.authorization.pep's own docstring: "a valid Keycloak session
with no local account yet ... roles is empty and the PDP default-denies
almost everything anyway") — this module extends the SAME fallback to
tenant suspension rather than introducing a new one, and delegation
resolution folds into the SAME single hydration call rather than becoming
a separate pipeline stage or a second authorization path.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.contexts.identity.adapters.postgres_repositories import (
    PostgresDelegationRepository,
    PostgresTenantRepository,
    PostgresUserRepository,
)
from app.contexts.identity.domain.delegation import delegation_is_effective
from app.contexts.identity.domain.tenant import Tenant
from app.contexts.identity.domain.user import User
from app.contexts.identity.ports import DelegationRepository, TenantRepository, UserRepository


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


async def _resolve_delegated_roles(
    *, users: UserRepository, delegations: DelegationRepository, user: User, tenant: Tenant
) -> set[str]:
    """Union of every currently-effective delegation's roles for `user` as
    delegate. Resolved fresh on every call — see module docstring on why
    that's what gives revocation/authority-loss immediate effect without
    any extra machinery."""
    active = await delegations.list_active_for_delegate(tenant.tenant_id, user.user_id)
    if not active:
        return set()
    granted: set[str] = set()
    now = datetime.now(UTC)
    for delegation in active:
        delegator = await users.get(delegation.delegator_user_id)
        effective, _reason = delegation_is_effective(
            delegation, delegator=delegator, tenant=tenant, now=now
        )
        if effective:
            granted.update(delegation.delegated_roles)
    return granted


def build_context_hydrator(
    users: UserRepository,
    tenants: TenantRepository | None = None,
    delegations: DelegationRepository | None = None,
) -> Callable[[str], Awaitable[dict | None]]:
    """For tests: repositories are already scoped appropriately (an
    in-memory fake has no RLS to worry about). `tenants`/`delegations` are
    optional so existing tests that don't care about tenant lifecycle or
    delegation don't need to thread them through."""

    async def _hydrate(keycloak_subject: str) -> dict | None:
        user = await users.get_by_keycloak_subject(keycloak_subject)
        if user is None or not user.can_authenticate():
            return None
        tenant: Tenant | None = None
        if tenants is not None:
            tenant = await tenants.get(user.tenant_id)
            if tenant is None or not tenant.is_active():
                return None
        attrs = _attrs_for(user)
        if attrs is not None and delegations is not None and tenant is not None:
            delegated = await _resolve_delegated_roles(
                users=users, delegations=delegations, user=user, tenant=tenant
            )
            if delegated:
                attrs["roles"] = list(set(attrs["roles"]) | delegated)
        return attrs

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
    identity_users/tenants/identity_delegations tenant-isolation RLS
    policies (migrations/versions/0001, 0005, 0006). This is safe: the
    query is fixed at the call site (not influenced by request input
    beyond the already-verified subject), read-only, and rolled back
    immediately — it cannot leak or mutate another tenant's data, only
    resolve which tenant this principal belongs to, whether that tenant is
    still active, and which delegated roles (if any) currently apply.
    """

    async def _hydrate(keycloak_subject: str) -> dict | None:
        async with session_factory() as session:
            await session.execute(text("SET LOCAL app.is_super_admin = 'true'"))
            users = PostgresUserRepository(session)
            user = await users.get_by_keycloak_subject(keycloak_subject)
            if user is None or not user.can_authenticate():
                await session.rollback()
                return None
            tenant = await PostgresTenantRepository(session).get(user.tenant_id)
            if tenant is None or not tenant.is_active():
                await session.rollback()
                return None
            delegated = await _resolve_delegated_roles(
                users=users,
                delegations=PostgresDelegationRepository(session),
                user=user,
                tenant=tenant,
            )
            await session.rollback()  # read-only; never persist from here
        attrs = _attrs_for(user)
        if attrs is not None and delegated:
            attrs["roles"] = list(set(attrs["roles"]) | delegated)
        return attrs

    return _hydrate
