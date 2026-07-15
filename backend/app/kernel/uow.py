"""Request-scoped Unit of Work — one fresh AsyncSession per request, with
the Postgres RLS session variables set before any query runs.

`SET LOCAL var = :value` does not accept a bind parameter — confirmed
against a live Postgres (`syntax error at or near "$1"`), since SET is not
a regular parameterized statement. `set_config(name, value, is_local)` is
the parameterizable equivalent and is what this module actually uses, with
`is_local=true` (transaction-scoped, not session/connection-scoped — a
connection-scoped setting would leak into whatever unrelated request later
reuses the same pooled physical connection, a real cross-request RLS-bypass
risk, not just a style choice).

Anonymous requests (register/login — no tenant established yet) and
super_admin both get the cross-tenant `app.is_super_admin` flag rather than
a tenant scope: registration is *creating* a new tenant boundary, so there
is no pre-existing one to scope to (see the Phase 3/5 commits for the full
reasoning); super_admin is explicitly allowed cross-tenant access by the
RLS policies themselves (migrations/versions/0001_identity_and_audit.py).
Every other authenticated request is scoped strictly to its own tenant.

Deliberately does NOT bind this session as the audit store (unlike an
earlier version of this module): `app.kernel.audit`'s `audit()` always
writes through the eager, independently-committing store instead (see
app.kernel.audit_postgres.EagerPostgresAuditStore, configured once at
startup) — confirmed against a live Postgres that binding the per-request
session caused a second bug on top of the one it fixed: audit()'s own
commit ends the transaction `is_local=true` was scoped to, silently
clearing the RLS bypass/tenant-scope for everything the same request does
afterward. `audit_log`'s RLS policies don't need either variable anyway
(migrations/versions/0001 grants SELECT/INSERT on it unconditionally), so
there's no reason for audit() to share the main session's transaction.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.kernel.authorization.pep import current_context_dep
from app.kernel.context import ExecutionContext

_session_factory: async_sessionmaker[AsyncSession] | None = None


def configure_uow(session_factory: async_sessionmaker[AsyncSession]) -> None:
    global _session_factory
    _session_factory = session_factory


async def get_db_session(
    ctx: ExecutionContext = Depends(current_context_dep),
) -> AsyncGenerator[AsyncSession, None]:
    if _session_factory is None:
        raise RuntimeError("Unit of Work not configured — call configure_uow() at startup")

    async with _session_factory() as session:
        if ctx.is_anonymous or ctx.has_any_role("super_admin"):
            await session.execute(text("SELECT set_config('app.is_super_admin', 'true', true)"))
        else:
            await session.execute(
                text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
                {"tenant_id": ctx.tenant_id or ""},
            )
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
