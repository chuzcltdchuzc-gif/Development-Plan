"""Live-Postgres concurrency rehearsal for the GD-016 / ADR-031 bootstrap
mechanism — GD-016 §11 tests 35-38, 45.

Deliberately NOT part of the hermetic `pytest -q` suite CI runs. Skipped
unless LIVE_IDENTITY_BOOTSTRAP_ADMIN_URL is set, following the same
throwaway-database-per-test pattern as
tests/live/test_identity_bootstrap_live.py and
tests/live/test_transactional_audit_concurrency_live.py.

Race A/Race B (tests 37/38) are demonstrated via guaranteed sequential
ordering rather than relying on real-time scheduler luck for which side
reaches the EXCLUSIVE lock first -- the same "deliberately controlling the
interleaving instead of hoping for it" method GD-009 §14 explicitly
permits as an alternative to an asyncio.gather race. Test 36 (true
concurrent contention) instead launches both sides via a real
`asyncio.gather` against the real server and asserts the invariant that
must hold under either valid resulting order, rather than asserting which
specific order occurred.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import uuid

import pytest
import sqlalchemy as sa
from fastapi import HTTPException
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.contexts.identity.application.bootstrap_service import bootstrap_first_tenant
from app.contexts.identity.authorization.bootstrap_policies import register_bootstrap_policies
from app.kernel.audit import (
    configure_audit_store,
    configure_eager_fallback,
    reset_audit_store,
    verify_chain,
)
from app.kernel.audit_postgres import EagerPostgresAuditStore, PostgresAuditStore
from app.kernel.authorization.policies import reset_policies
from app.kernel.context import ExecutionContext, reset_context, set_context

ADMIN_URL = os.environ.get("LIVE_IDENTITY_BOOTSTRAP_ADMIN_URL")

pytestmark = pytest.mark.skipif(
    not ADMIN_URL,
    reason=(
        "GD-016 / ADR-031 bootstrap concurrency rehearsal -- set "
        "LIVE_IDENTITY_BOOTSTRAP_ADMIN_URL to run against a real Postgres"
    ),
)


def _db_name() -> str:
    return f"landvault_live_bootstrap_conc_{uuid.uuid4().hex[:12]}"


def _with_db(url: str, db_name: str) -> str:
    base, _, _ = url.rpartition("/")
    return f"{base}/{db_name}"


async def _create_throwaway_db(admin_url: str, db_name: str) -> None:
    admin_engine: AsyncEngine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        async with admin_engine.connect() as conn:
            await conn.execute(sa.text(f'CREATE DATABASE "{db_name}"'))
    finally:
        await admin_engine.dispose()


async def _drop_throwaway_db(admin_url: str, db_name: str) -> None:
    admin_engine: AsyncEngine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        async with admin_engine.connect() as conn:
            await conn.execute(
                sa.text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :db AND pid <> pg_backend_pid()"
                ),
                {"db": db_name},
            )
            await conn.execute(sa.text(f'DROP DATABASE IF EXISTS "{db_name}"'))
    finally:
        await admin_engine.dispose()


def _run_migrations(db_url: str) -> None:
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    migration_env = dict(os.environ, MIGRATIONS_DATABASE_URL=db_url)
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=backend_dir,
        env=migration_env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"alembic upgrade head failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )


async def _app_session_factory(db_url: str) -> async_sessionmaker[AsyncSession]:
    app_password = os.environ["POSTGRES_APP_PASSWORD"]
    app_db_url = (
        make_url(db_url)
        .set(username="landvault_app", password=app_password)
        .render_as_string(hide_password=False)
    )
    return async_sessionmaker(create_async_engine(app_db_url), expire_on_commit=False)


async def _tenants_count(db_url: str) -> int:
    engine = create_async_engine(db_url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(sa.text("SELECT count(*) FROM tenants"))
            return result.scalar_one()
    finally:
        await engine.dispose()


async def _insert_ordinary_tenant(app_session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Stands in for register_local's ordinary tenant-creating INSERT --
    the exact same `landvault_app`-role, RLS-governed statement shape,
    without requiring the full AuthService/IdentityProvider stack."""
    async with app_session_factory() as session:
        await session.execute(sa.text("SELECT set_config('app.is_super_admin', 'true', true)"))
        await session.execute(
            sa.text("INSERT INTO tenants (id, name, status) VALUES (:id, :name, 'ACTIVE')"),
            {"id": f"ordinary-{uuid.uuid4().hex[:8]}", "name": "Ordinary Tenant"},
        )
        await session.commit()


def _ctx(subject: str) -> ExecutionContext:
    return ExecutionContext(principal_id=subject, tenant_id=None, roles=())


async def _attempt_bootstrap(
    app_session_factory: async_sessionmaker[AsyncSession], subject: str, role: str, tenant_name: str
):
    ctx = _ctx(subject)
    token = set_context(ctx)
    try:
        return await bootstrap_first_tenant(
            session_factory=app_session_factory,
            subject=subject,
            email=f"{subject}@live-bootstrap-conc-test.invalid",
            full_name="Live Test Founder",
            country="NG",
            tenant_name=tenant_name,
            requested_role=role,
        )
    finally:
        reset_context(token)


async def _setup(db_url: str) -> async_sessionmaker[AsyncSession]:
    _run_migrations(db_url)
    app_session_factory = await _app_session_factory(db_url)
    configure_eager_fallback(EagerPostgresAuditStore(app_session_factory))
    reset_policies()
    register_bootstrap_policies()
    return app_session_factory


# ---- Test 35: bootstrap vs. bootstrap -> exactly one success --------------


@pytest.mark.asyncio
async def test_bootstrap_vs_bootstrap_yields_exactly_one_success() -> None:
    assert ADMIN_URL is not None
    db_name = _db_name()
    await _create_throwaway_db(ADMIN_URL, db_name)
    db_url = _with_db(ADMIN_URL, db_name)
    try:
        app_session_factory = await _setup(db_url)
        try:
            results = await asyncio.gather(
                _attempt_bootstrap(
                    app_session_factory, "live-35a", "compliance_officer", "Tenant A"
                ),
                _attempt_bootstrap(
                    app_session_factory, "live-35b", "surveyor_general", "Tenant B"
                ),
                return_exceptions=True,
            )
            successes = [r for r in results if not isinstance(r, Exception)]
            failures = [r for r in results if isinstance(r, Exception)]
            assert len(successes) == 1, f"expected exactly one success, got: {results}"
            assert len(failures) == 1
            assert isinstance(failures[0], HTTPException)
            assert await _tenants_count(db_url) == 1
        finally:
            reset_policies()
    finally:
        await _drop_throwaway_db(ADMIN_URL, db_name)


# ---- Test 36: bootstrap vs. ordinary tenant-creator -- serialized ---------


@pytest.mark.asyncio
async def test_bootstrap_vs_ordinary_tenant_creator_serialized_consistently() -> None:
    assert ADMIN_URL is not None
    db_name = _db_name()
    await _create_throwaway_db(ADMIN_URL, db_name)
    db_url = _with_db(ADMIN_URL, db_name)
    try:
        app_session_factory = await _setup(db_url)
        try:
            results = await asyncio.gather(
                _attempt_bootstrap(
                    app_session_factory, "live-36", "compliance_officer", "Concurrent Tenant"
                ),
                _insert_ordinary_tenant(app_session_factory),
                return_exceptions=True,
            )
            bootstrap_result, ordinary_result = results
            final_count = await _tenants_count(db_url)
            if isinstance(bootstrap_result, Exception):
                # Race B shape: the ordinary creator won the lock first --
                # bootstrap correctly denies on a non-empty platform, and
                # exactly the ordinary tenant exists.
                assert isinstance(bootstrap_result, HTTPException)
                assert not isinstance(ordinary_result, Exception)
                assert final_count == 1
            else:
                # Race A shape: bootstrap won the lock first and does not
                # permanently block the ordinary creator, which proceeds
                # once bootstrap's transaction ends.
                assert not isinstance(ordinary_result, Exception)
                assert final_count == 2
        finally:
            reset_policies()
    finally:
        await _drop_throwaway_db(ADMIN_URL, db_name)


# ---- Test 37: Race A -- bootstrap obtains the lock first -------------------


@pytest.mark.asyncio
async def test_race_a_bootstrap_does_not_permanently_block_later_creation() -> None:
    assert ADMIN_URL is not None
    db_name = _db_name()
    await _create_throwaway_db(ADMIN_URL, db_name)
    db_url = _with_db(ADMIN_URL, db_name)
    try:
        app_session_factory = await _setup(db_url)
        try:
            result = await _attempt_bootstrap(
                app_session_factory, "live-37", "compliance_officer", "Race A Tenant"
            )
            assert result.tenant_id is not None
            # A later, ordinary tenant-creator proceeds normally once
            # bootstrap's transaction has already ended -- bootstrap does
            # not permanently prohibit later legitimate tenant creation.
            await _insert_ordinary_tenant(app_session_factory)
            assert await _tenants_count(db_url) == 2
        finally:
            reset_policies()
    finally:
        await _drop_throwaway_db(ADMIN_URL, db_name)


# ---- Test 38: Race B -- another tenant creator commits first --------------


@pytest.mark.asyncio
async def test_race_b_bootstrap_denies_on_nonempty_platform() -> None:
    assert ADMIN_URL is not None
    db_name = _db_name()
    await _create_throwaway_db(ADMIN_URL, db_name)
    db_url = _with_db(ADMIN_URL, db_name)
    try:
        app_session_factory = await _setup(db_url)
        try:
            await _insert_ordinary_tenant(app_session_factory)
            assert await _tenants_count(db_url) == 1

            with pytest.raises(HTTPException):
                await _attempt_bootstrap(
                    app_session_factory, "live-38", "compliance_officer", "Race B Tenant"
                )
            # fail-closed, no mutation -- still exactly the one ordinary tenant
            assert await _tenants_count(db_url) == 1
        finally:
            reset_policies()
    finally:
        await _drop_throwaway_db(ADMIN_URL, db_name)


# ---- Test 45: verify_chain() remains valid after bootstrap audit entries --


@pytest.mark.asyncio
async def test_audit_dag_remains_valid_after_concurrent_bootstrap_attempts() -> None:
    assert ADMIN_URL is not None
    db_name = _db_name()
    await _create_throwaway_db(ADMIN_URL, db_name)
    db_url = _with_db(ADMIN_URL, db_name)
    try:
        app_session_factory = await _setup(db_url)
        try:
            await asyncio.gather(
                _attempt_bootstrap(
                    app_session_factory, "live-45a", "compliance_officer", "Tenant A"
                ),
                _attempt_bootstrap(
                    app_session_factory, "live-45b", "surveyor_general", "Tenant B"
                ),
                return_exceptions=True,
            )
        finally:
            reset_policies()

        session_factory = async_sessionmaker(create_async_engine(db_url), expire_on_commit=False)
        async with session_factory() as session:
            token = configure_audit_store(PostgresAuditStore(session))
            try:
                result = await verify_chain()
            finally:
                reset_audit_store(token)
        assert result is True
    finally:
        await _drop_throwaway_db(ADMIN_URL, db_name)
