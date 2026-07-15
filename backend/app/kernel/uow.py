"""Request-scoped Unit of Work — one fresh AsyncSession per request, with
the Postgres RLS session variables set before any query runs.

`SET LOCAL var = :value` does not accept a bind parameter — confirmed
against a live Postgres (`syntax error at or near "$1"`), since SET is not
a regular parameterized statement. `set_config(name, value, is_local)` is
the parameterizable equivalent and is what this module actually uses.

Anonymous requests (register/login — no tenant established yet) and
super_admin both get the cross-tenant `app.is_super_admin` flag rather than
a tenant scope: registration is *creating* a new tenant boundary, so there
is no pre-existing one to scope to (see the Phase 3/5 commits for the full
reasoning); super_admin is explicitly allowed cross-tenant access by the
RLS policies themselves (migrations/versions/0001_identity_and_audit.py).
Every other authenticated request is scoped strictly to its own tenant.
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
