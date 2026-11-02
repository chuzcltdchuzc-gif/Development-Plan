"""Bootstrap transactional/domain orchestration — docs/GD-016-adr-031-
initial-supabase-identity-bootstrap-implementation-authorization.md §9
steps 3-10. Implements docs/adr/ADR-031-initial-supabase-identity-
bootstrap-and-first-tenant-provisioning.md as qualified by docs/adr/
ADR-032-bootstrap-pdp-action-ownership-and-explicit-deny-semantics.md.

Owns ONLY the authorized bootstrap transactional/domain orchestration. It
receives an already-verified subject, an already-normalized email, and an
already-bound `ExecutionContext` (read ambiently via
`app.kernel.context.current_context()`, exactly as every other
`enforce()`/`authorize()` caller does) from
`app.contexts.identity.cli.bootstrap_first_tenant` — the sole standalone
composition root. This module never verifies a token, never validates an
email, and never constructs or binds an `ExecutionContext` itself; no
second composition root exists anywhere in this package (GD-016 §3).
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.contexts.identity.adapters.postgres_repositories import (
    PostgresTenantRepository,
    PostgresUserRepository,
)
from app.contexts.identity.authorization.bootstrap_policies import (
    FIRST_TENANT_ACTION,
    PREFLIGHT_ACTION,
)
from app.contexts.identity.domain.tenant import Tenant
from app.contexts.identity.domain.user import User
from app.kernel.audit import audit
from app.kernel.audit_postgres import audit_staged
from app.kernel.authorization.pep import enforce


@dataclass(frozen=True)
class BootstrapResult:
    tenant_id: str
    user_id: str
    role: str


async def bootstrap_first_tenant(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    subject: str,
    email: str,
    full_name: str,
    country: str,
    tenant_name: str,
    requested_role: str,
) -> BootstrapResult:
    """GD-016 §9 steps 3-10, exact and not reordered.

    `enforce()` raises `fastapi.HTTPException` on DENY — an ordinary
    Python exception class outside a FastAPI request context (ADR-031
    §"PDP/PEP treatment") — which the caller (the CLI entrypoint) reports
    to the operator. Both `enforce()` calls independently audit their own
    outcome through the eager audit path the CLI's composition root
    configures before this function is ever called.
    """
    # Step 3: Stage 1 PDP, before any transaction, any GUC, and any lock
    # exist. Raises on DENY -- step 4 is never reached.
    await enforce(
        PREFLIGHT_ACTION,
        resource={"requested_role": requested_role},
        env={"invocation_channel": "bootstrap_cli"},
    )

    # Step 4: only on PERMIT, open the bootstrap transaction on its OWN,
    # dedicated session -- never app.kernel.uow.get_db_session(), which
    # would activate app.is_super_admin eagerly, before this PDP decision
    # ever existed for it (GD-016 §1 finding / §7).
    session = session_factory()
    try:
        # Step 5: activate the transaction-local RLS override.
        await session.execute(text("SELECT set_config('app.is_super_admin', 'true', true)"))

        # Step 6: the override-use audit is independent/eager -- it uses
        # the SEPARATE session the CLI's EagerPostgresAuditStore owns, not
        # this bootstrap-transaction session, so it is not itself "a
        # statement executed by the bootstrap transaction" (GD-016 §7). A
        # failure here fails closed before the privileged read below ever
        # runs; the except/finally below rolls this transaction back.
        await audit(
            "identity.bootstrap.rls_override_used",
            resource_type="tenant",
            payload={
                "pending_action": FIRST_TENANT_ACTION,
                "purpose": "initial-platform bootstrap probe/provisioning",
            },
        )

        # Step 7: the NEXT statement on THIS session must be the EXCLUSIVE
        # lock -- then, under it, the authoritative platform_empty fact.
        await session.execute(text("LOCK TABLE tenants IN EXCLUSIVE MODE"))
        count_result = await session.execute(text("SELECT count(*) FROM tenants"))
        platform_empty = count_result.scalar_one() == 0

        # Step 8: Stage 2 PDP. Raises on DENY -- step 9 is never reached,
        # and the except/finally below rolls this transaction back with no
        # mutation.
        await enforce(
            FIRST_TENANT_ACTION,
            resource={"requested_role": requested_role},
            env={"preflight_permitted": True, "platform_empty": platform_empty},
        )

        # Step 9: only on PERMIT, in exactly this order (GD-016 §9 step 9
        # a-g) -- the same mutual-FK-avoidance sequence ADR-010/
        # register_local already establish, never a deferred-constraint
        # trick. No owner reference is persisted before the row it
        # references exists.
        tenants = PostgresTenantRepository(session)
        users = PostgresUserRepository(session)

        tenant = Tenant.new(name=tenant_name)  # a
        tenant = await tenants.add(tenant)  # b: owner_user_id still None

        user = User.new(
            identity_subject=subject,
            email=email,
            full_name=full_name,
            country=country,
            tenant_id=tenant.tenant_id,
        )  # c
        # d: direct field assignment, never user.assign_role() -- that
        # would APPEND to User.new()'s default [general_user] rather than
        # replace it, leaving both roles present.
        user.roles = [requested_role]
        user = await users.add(user)  # e

        tenant.owner_user_id = user.user_id  # f: only now that User exists
        tenant = await tenants.update(tenant)

        await audit_staged(
            session,
            "identity.tenant.bootstrapped",
            resource_type="tenant",
            resource_id=tenant.tenant_id,
            payload={"via": "bootstrap"},
        )
        await audit_staged(
            session,
            "identity.user.registered",
            resource_type="user",
            resource_id=user.user_id,
            payload={"country": country, "role": requested_role, "via": "bootstrap"},
        )  # g

        # Step 10: commit -- Tenant, User, owner-FK, and both staged
        # audit events together. The EXCLUSIVE lock and the
        # app.is_super_admin GUC are both released automatically at
        # transaction end, regardless of outcome.
        await session.commit()
        return BootstrapResult(
            tenant_id=tenant.tenant_id, user_id=user.user_id, role=requested_role
        )
    except Exception:
        # Deliberately unlike app.kernel.uow.get_db_session(), which
        # commits on a propagating HTTPException: nothing bootstrap's own
        # transaction holds (the lock, the override, the pending mutation)
        # may ever survive a Stage-2 DENY or any other failure here -- the
        # independent/eager audit evidence from steps 3/6/8 lives on a
        # separate session already and is unaffected by this rollback.
        await session.rollback()
        raise
    finally:
        await session.close()
