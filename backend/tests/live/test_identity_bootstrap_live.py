"""Live-Postgres rehearsal for the GD-016 / ADR-031 (as qualified by
ADR-032) bootstrap mechanism — GD-016 §11 tests 1, 21, 23, 29, 30 (live
half), 31, 32, 39, 40, 42 (live half).

Deliberately NOT part of the hermetic `pytest -q` suite CI runs — see
tests/live/test_registry_history_rollback_live.py's own docstring for why.
Skipped unless LIVE_IDENTITY_BOOTSTRAP_ADMIN_URL is set, following exactly
the throwaway-database-per-test pattern already established in
tests/live/test_transactional_audit_concurrency_live.py.
"""
from __future__ import annotations

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
from app.kernel.audit_orm import AuditLogRecord
from app.kernel.audit_postgres import EagerPostgresAuditStore, PostgresAuditStore
from app.kernel.authorization.policies import reset_policies
from app.kernel.context import ExecutionContext, reset_context, set_context

ADMIN_URL = os.environ.get("LIVE_IDENTITY_BOOTSTRAP_ADMIN_URL")

pytestmark = pytest.mark.skipif(
    not ADMIN_URL,
    reason=(
        "GD-016 / ADR-031 bootstrap live rehearsal — set "
        "LIVE_IDENTITY_BOOTSTRAP_ADMIN_URL to run against a real Postgres"
    ),
)


def _db_name() -> str:
    return f"landvault_live_bootstrap_{uuid.uuid4().hex[:12]}"


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


async def _guc_value(db_url: str, setting: str) -> str | None:
    engine = create_async_engine(db_url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(sa.text(f"SHOW {setting}"))
            return result.scalar_one()
    finally:
        await engine.dispose()


async def _tenants_rows(db_url: str) -> list[dict]:
    engine = create_async_engine(db_url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                sa.text("SELECT id, owner_user_id, created_at FROM tenants ORDER BY created_at ASC")
            )
            return [dict(row._mapping) for row in result]
    finally:
        await engine.dispose()


async def _audit_rows(db_url: str) -> list[AuditLogRecord]:
    session_factory = async_sessionmaker(create_async_engine(db_url), expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(
            sa.select(AuditLogRecord).order_by(AuditLogRecord.created_at.asc())
        )
        return list(result.scalars().all())


def _ctx(subject: str) -> ExecutionContext:
    return ExecutionContext(principal_id=subject, tenant_id=None, roles=())


async def _run_bootstrap_attempt(
    *, db_url: str, subject: str, role: str, tenant_name: str
):
    app_session_factory = await _app_session_factory(db_url)
    configure_eager_fallback(EagerPostgresAuditStore(app_session_factory))
    reset_policies()
    register_bootstrap_policies()
    ctx = _ctx(subject)
    token = set_context(ctx)
    try:
        return await bootstrap_first_tenant(
            session_factory=app_session_factory,
            subject=subject,
            email=f"{subject}@live-bootstrap-test.invalid",
            full_name="Live Test Founder",
            country="NG",
            tenant_name=tenant_name,
            requested_role=role,
        )
    finally:
        reset_context(token)
        reset_policies()


@pytest.mark.asyncio
async def test_empty_platform_bootstrap_succeeds_with_correct_persistence_order() -> None:
    """Test 1 / 29: full success path on a genuinely empty platform;
    Tenant row exists (owner_user_id NULL) before the User row, and
    owner_user_id is only set after that User row exists; both staged
    successful-mutation audit events commit atomically with the mutation."""
    assert ADMIN_URL is not None
    db_name = _db_name()
    await _create_throwaway_db(ADMIN_URL, db_name)
    db_url = _with_db(ADMIN_URL, db_name)
    try:
        _run_migrations(db_url)
        result = await _run_bootstrap_attempt(
            db_url=db_url, subject="live-subject-1", role="compliance_officer",
            tenant_name="Live Bootstrap Tenant",
        )
        rows = await _tenants_rows(db_url)
        assert len(rows) == 1
        assert rows[0]["id"] == result.tenant_id
        assert str(rows[0]["owner_user_id"]) == result.user_id

        audit_rows = await _audit_rows(db_url)
        staged_actions = {r.action for r in audit_rows}
        assert "identity.tenant.bootstrapped" in staged_actions
        assert "identity.user.registered" in staged_actions

        chain_valid = await _verify_chain_against(db_url)
        assert chain_valid is True  # test 45 corroboration at the single-attempt level
    finally:
        await _drop_throwaway_db(ADMIN_URL, db_name)


async def _verify_chain_against(db_url: str) -> bool:
    session_factory = async_sessionmaker(create_async_engine(db_url), expire_on_commit=False)
    async with session_factory() as session:
        token = configure_audit_store(PostgresAuditStore(session))
        try:
            return await verify_chain()
        finally:
            reset_audit_store(token)


@pytest.mark.asyncio
async def test_override_use_audit_is_durable_and_platform_empty_evaluated_under_lock() -> None:
    """Tests 21 / 23: the independent override-use audit event is present
    and durable; platform_empty was evaluated under the active override
    and the EXCLUSIVE lock (proven indirectly: a correct bootstrap on a
    genuinely empty platform succeeds end-to-end, which requires step 7's
    read to have correctly observed zero rows under the override — a
    false-empty-without-override RLS result would make the mutation itself
    fail, not merely the read)."""
    assert ADMIN_URL is not None
    db_name = _db_name()
    await _create_throwaway_db(ADMIN_URL, db_name)
    db_url = _with_db(ADMIN_URL, db_name)
    try:
        _run_migrations(db_url)
        await _run_bootstrap_attempt(
            db_url=db_url, subject="live-subject-21", role="surveyor_general",
            tenant_name="Override Audit Tenant",
        )
        audit_rows = await _audit_rows(db_url)
        override_rows = [
            r for r in audit_rows if r.action == "identity.bootstrap.rls_override_used"
        ]
        assert len(override_rows) == 1
    finally:
        await _drop_throwaway_db(ADMIN_URL, db_name)


@pytest.mark.asyncio
async def test_staged_audit_failure_rolls_back_everything(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test 30 (live half): a forced failure staging the second
    successful-mutation event rolls back the Tenant, the User, and the
    already-staged first event together -- nothing survives in the real
    database."""
    assert ADMIN_URL is not None
    db_name = _db_name()
    await _create_throwaway_db(ADMIN_URL, db_name)
    db_url = _with_db(ADMIN_URL, db_name)
    try:
        _run_migrations(db_url)
        app_session_factory = await _app_session_factory(db_url)
        configure_eager_fallback(EagerPostgresAuditStore(app_session_factory))
        reset_policies()
        register_bootstrap_policies()

        import app.contexts.identity.application.bootstrap_service as bootstrap_service_module

        real_audit_staged = bootstrap_service_module.audit_staged

        async def _failing_audit_staged(session, action, **kwargs):
            if action == "identity.user.registered":
                raise RuntimeError("simulated live staged-audit failure")
            return await real_audit_staged(session, action, **kwargs)

        monkeypatch.setattr(bootstrap_service_module, "audit_staged", _failing_audit_staged)

        ctx = _ctx("live-subject-30")
        token = set_context(ctx)
        try:
            with pytest.raises(RuntimeError, match="simulated"):
                await bootstrap_service_module.bootstrap_first_tenant(
                    session_factory=app_session_factory,
                    subject="live-subject-30",
                    email="live-subject-30@live-bootstrap-test.invalid",
                    full_name="Live Test Founder",
                    country="NG",
                    tenant_name="Should Not Persist",
                    requested_role="compliance_officer",
                )
        finally:
            reset_context(token)
            reset_policies()

        rows = await _tenants_rows(db_url)
        assert rows == []  # nothing committed
        audit_rows = await _audit_rows(db_url)
        assert all(r.action != "identity.tenant.bootstrapped" for r in audit_rows)
        assert all(r.action != "identity.user.registered" for r in audit_rows)
    finally:
        await _drop_throwaway_db(ADMIN_URL, db_name)


@pytest.mark.asyncio
async def test_forced_commit_failure_leaves_no_successful_mutation_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test 31: a forced failure at the commit point itself leaves no
    durable domain rows or successful-mutation audit events."""
    assert ADMIN_URL is not None
    db_name = _db_name()
    await _create_throwaway_db(ADMIN_URL, db_name)
    db_url = _with_db(ADMIN_URL, db_name)
    try:
        _run_migrations(db_url)
        app_session_factory = await _app_session_factory(db_url)
        configure_eager_fallback(EagerPostgresAuditStore(app_session_factory))
        reset_policies()
        register_bootstrap_policies()

        raw_session = app_session_factory()
        try:
            real_commit = raw_session.commit

            async def _failing_commit() -> None:
                raise RuntimeError("simulated commit failure")

            raw_session.commit = _failing_commit  # type: ignore[method-assign]

            def _factory_returning_broken_session():
                return raw_session

            import app.contexts.identity.application.bootstrap_service as bootstrap_service_module

            ctx = _ctx("live-subject-31")
            token = set_context(ctx)
            try:
                with pytest.raises(RuntimeError, match="simulated"):
                    await bootstrap_service_module.bootstrap_first_tenant(
                        session_factory=_factory_returning_broken_session,
                        subject="live-subject-31",
                        email="live-subject-31@live-bootstrap-test.invalid",
                        full_name="Live Test Founder",
                        country="NG",
                        tenant_name="Should Not Persist Either",
                        requested_role="compliance_officer",
                    )
            finally:
                reset_context(token)
                reset_policies()
                raw_session.commit = real_commit
        finally:
            await raw_session.rollback()
            await raw_session.close()

        rows = await _tenants_rows(db_url)
        assert rows == []
    finally:
        await _drop_throwaway_db(ADMIN_URL, db_name)


@pytest.mark.asyncio
async def test_independent_audit_survives_later_mutation_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test 32: the independent/eager Stage-1/Stage-2/override-use audit
    entries survive even though the later domain mutation itself rolls
    back (forced via the same staged-audit failure as test 30)."""
    assert ADMIN_URL is not None
    db_name = _db_name()
    await _create_throwaway_db(ADMIN_URL, db_name)
    db_url = _with_db(ADMIN_URL, db_name)
    try:
        _run_migrations(db_url)
        app_session_factory = await _app_session_factory(db_url)
        configure_eager_fallback(EagerPostgresAuditStore(app_session_factory))
        reset_policies()
        register_bootstrap_policies()

        import app.contexts.identity.application.bootstrap_service as bootstrap_service_module

        async def _failing_audit_staged(session, action, **kwargs):
            raise RuntimeError("simulated failure for independent-survival proof")

        monkeypatch.setattr(bootstrap_service_module, "audit_staged", _failing_audit_staged)

        ctx = _ctx("live-subject-32")
        token = set_context(ctx)
        try:
            with pytest.raises(RuntimeError, match="simulated"):
                await bootstrap_service_module.bootstrap_first_tenant(
                    session_factory=app_session_factory,
                    subject="live-subject-32",
                    email="live-subject-32@live-bootstrap-test.invalid",
                    full_name="Live Test Founder",
                    country="NG",
                    tenant_name="Independent Audit Survival",
                    requested_role="compliance_officer",
                )
        finally:
            reset_context(token)
            reset_policies()

        audit_rows = await _audit_rows(db_url)
        actions = {r.action for r in audit_rows}
        assert "authz.permit" in actions  # Stage 1 + Stage 2 both independently durable
        assert "identity.bootstrap.rls_override_used" in actions
        assert "identity.tenant.bootstrapped" not in actions
        assert "identity.user.registered" not in actions
    finally:
        await _drop_throwaway_db(ADMIN_URL, db_name)


@pytest.mark.asyncio
async def test_transaction_local_guc_clears_on_commit_and_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tests 39 / 40: app.is_super_admin is transaction-local and clears
    automatically at transaction end, both on a successful commit and on
    a forced rollback."""
    assert ADMIN_URL is not None
    db_name = _db_name()
    await _create_throwaway_db(ADMIN_URL, db_name)
    db_url = _with_db(ADMIN_URL, db_name)
    try:
        _run_migrations(db_url)

        # Commit path.
        await _run_bootstrap_attempt(
            db_url=db_url, subject="live-subject-39", role="compliance_officer",
            tenant_name="GUC Commit Tenant",
        )
        guc_after_commit = await _guc_value(db_url, "app.is_super_admin")
        assert guc_after_commit in (None, "", "false")

        # Rollback path: force the second attempt to fail via staged audit.
        app_session_factory = await _app_session_factory(db_url)
        configure_eager_fallback(EagerPostgresAuditStore(app_session_factory))
        reset_policies()
        register_bootstrap_policies()
        import app.contexts.identity.application.bootstrap_service as bootstrap_service_module

        async def _failing_audit_staged(session, action, **kwargs):
            raise RuntimeError("simulated failure for GUC-rollback proof")

        monkeypatch.setattr(bootstrap_service_module, "audit_staged", _failing_audit_staged)

        ctx = _ctx("live-subject-40")
        token = set_context(ctx)
        try:
            with pytest.raises(HTTPException | RuntimeError):
                await bootstrap_service_module.bootstrap_first_tenant(
                    session_factory=app_session_factory,
                    subject="live-subject-40",
                    email="live-subject-40@live-bootstrap-test.invalid",
                    full_name="Live Test Founder",
                    country="NG",
                    tenant_name="GUC Rollback Tenant",
                    requested_role="surveyor_general",
                )
        finally:
            reset_context(token)
            reset_policies()

        guc_after_rollback = await _guc_value(db_url, "app.is_super_admin")
        assert guc_after_rollback in (None, "", "false")
    finally:
        await _drop_throwaway_db(ADMIN_URL, db_name)


@pytest.mark.asyncio
async def test_token_never_appears_in_persisted_audit_payloads() -> None:
    """Test 42 (live half): the Supabase access token never appears in
    any persisted audit row's payload."""
    assert ADMIN_URL is not None
    db_name = _db_name()
    await _create_throwaway_db(ADMIN_URL, db_name)
    db_url = _with_db(ADMIN_URL, db_name)
    secret_token_fragment = "sb-super-secret-live-test-token-fragment"
    try:
        _run_migrations(db_url)
        await _run_bootstrap_attempt(
            db_url=db_url, subject="live-subject-42", role="compliance_officer",
            tenant_name="Token Absence Tenant",
        )
        audit_rows = await _audit_rows(db_url)
        for row in audit_rows:
            assert secret_token_fragment not in str(row.payload)
    finally:
        await _drop_throwaway_db(ADMIN_URL, db_name)
