"""Live-Postgres fault-injection rehearsal for ADR-023's "Same Unit of
Work" claim (Phase 8 acceptance, Condition 2).

Deliberately NOT part of the hermetic `pytest -q` suite that CI runs —
every other test in this repo goes through tests/app_factory.py, which
overrides every repository with an in-memory fake and never touches
app.kernel.uow.get_db_session at all (confirmed by reading it). That
suite proves the *domain*/*application* logic; it cannot prove anything
about the real Postgres session/commit/rollback path, because it never
exercises it.

This module does. It:
  1. creates a throwaway database on the Postgres instance addressed by
     LIVE_ROLLBACK_ADMIN_URL (the schema-owning role),
  2. runs the real Alembic migration chain against it (also functions as
     a live-migration rehearsal for 0011_registry_ownership_status_history),
  3. drives app.kernel.uow.get_db_session directly — the actual
     generator FastAPI calls per-request, not a substitute — through the
     same parcel-insert + ownership-history + status-history sequence
     ParcelService.create_parcel uses, via the real PostgresParcelRepository
     and PostgresParcelHistoryRepository,
  4. throws a genuine (non-HTTPException) fault into that generator
     *before* any audit() call and before session.commit(), forcing the
     real `except Exception: await session.rollback(); raise` branch,
  5. opens a fresh session and asserts nothing from step 3 persisted,
     including in audit_log,
  6. proves the session factory/connection pool is not poisoned by
     successfully completing one more real write afterward,
  7. drops the throwaway database.

Skipped unless LIVE_ROLLBACK_ADMIN_URL is set (a superuser/schema-owning
asyncpg URL, e.g. postgresql+asyncpg://landvault:<pw>@localhost:5432/postgres)
— never runs by default, so it cannot break the hermetic suite or CI (which
has no Postgres service).

Known limitation this test does NOT cover (see Phase 8 Acceptance Package):
app.kernel.audit's audit() commits eagerly and independently of the main
request session (app.kernel.uow's own docstring explains why — RLS
`is_local=true` scoping). A fault injected *after* an audit() call but
before the main session's commit could leave an audit_log entry
referencing a parcel/history row that never persisted. This test injects
its fault *before* the first audit() call specifically to isolate and
prove the parcel+history atomicity guarantee; it does not claim the
audit-store/main-session pairing is itself transactional, because it
isn't, by deliberate, pre-existing, documented design.
"""
from __future__ import annotations

import os
import subprocess
import sys
import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

import app.contexts.identity.adapters.orm  # noqa: F401 — registers identity_users/tenants with Base.metadata
from app.contexts.registry.adapters.orm import (
    ParcelOwnershipHistoryRecord,
    ParcelRecord,
    ParcelStatusHistoryRecord,
)
from app.contexts.registry.adapters.postgres_repositories import (
    PostgresParcelHistoryRepository,
    PostgresParcelRepository,
)
from app.contexts.registry.domain.history import OwnershipAssertion, StatusAssertion
from app.contexts.registry.domain.parcel import Parcel
from app.kernel import uow
from app.kernel.audit_orm import AuditLogRecord
from app.kernel.context import ExecutionContext

ADMIN_URL = os.environ.get("LIVE_ROLLBACK_ADMIN_URL")

pytestmark = pytest.mark.skipif(
    not ADMIN_URL,
    reason="live rollback rehearsal — set LIVE_ROLLBACK_ADMIN_URL to run against a real Postgres",
)


def _db_name() -> str:
    return f"landvault_live_rollback_{uuid.uuid4().hex[:12]}"


def _with_db(url: str, db_name: str) -> str:
    base, _, _ = url.rpartition("/")
    return f"{base}/{db_name}"


class _Fault(Exception):
    """Distinguishable from any exception the application itself raises."""


@pytest.mark.asyncio
async def test_parcel_and_history_roll_back_together_on_live_postgres() -> None:
    assert ADMIN_URL is not None  # guaranteed by pytestmark skipif above
    admin_engine: AsyncEngine = create_async_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    db_name = _db_name()

    try:
        async with admin_engine.connect() as conn:
            await conn.execute(sa.text(f'CREATE DATABASE "{db_name}"'))
    finally:
        await admin_engine.dispose()

    db_url = _with_db(ADMIN_URL, db_name)

    try:
        # --- Step 1: real migration chain, including 0011 (ADR-023) ---
        # Run as a subprocess (not alembic.command.upgrade in-process) —
        # alembic's async env.py calls asyncio.run() internally, which
        # cannot be nested inside this already-running pytest-asyncio loop.
        # A subprocess is also exactly how CI and a human operator actually
        # invoke migrations, so this doubles as a live-migration rehearsal
        # of the real command, not a special in-process shortcut.
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

        owning_engine: AsyncEngine = create_async_engine(db_url)
        tenant_id = f"tenant-{uuid.uuid4().hex[:8]}"
        user_id = uuid.uuid4()
        try:
            async with owning_engine.begin() as conn:
                await conn.execute(
                    sa.text(
                        "INSERT INTO tenants (id, name, status) VALUES (:id, :name, 'ACTIVE')"
                    ),
                    {"id": tenant_id, "name": "Live Rollback Test Tenant"},
                )
                await conn.execute(
                    sa.text(
                        "INSERT INTO identity_users "
                        "(id, keycloak_subject, email, full_name, country, tenant_id, roles) "
                        "VALUES (:id, :sub, :email, 'Live Rollback Test User', "
                        "'NG', :tenant_id, '[]')"
                    ),
                    {
                        "id": user_id,
                        "sub": f"kc-{user_id}",
                        "email": f"{user_id}@live-rollback-test.invalid",
                        "tenant_id": tenant_id,
                    },
                )
        finally:
            await owning_engine.dispose()

        # DATABASE_URL (least-privilege landvault_app role) — the one the
        # running app actually uses, matching production wiring exactly.
        app_password = os.environ["POSTGRES_APP_PASSWORD"]
        app_db_url = (
            make_url(db_url)
            .set(username="landvault_app", password=app_password)
            .render_as_string(hide_password=False)
        )

        session_factory = async_sessionmaker(
            create_async_engine(app_db_url), expire_on_commit=False
        )
        uow.configure_uow(session_factory)

        ctx = ExecutionContext(principal_id=str(user_id), tenant_id=tenant_id, roles=())

        # --- Steps 2-4: real UoW, real repos, fault before commit ---
        agen = uow.get_db_session(ctx=ctx)
        session = await anext(agen)

        parcels_repo = PostgresParcelRepository(session)
        history_repo = PostgresParcelHistoryRepository(session)

        parcel = Parcel.new(
            tenant_id=tenant_id,
            country_code="NG",
            origin="platform_registration",
            created_by=str(user_id),
            title="Live rollback rehearsal parcel",
        )
        parcel_id = parcel.parcel_id
        parcel.allocate_parcel_number("LV-NG-999999")
        parcel = await parcels_repo.add(parcel)

        ownership_audit_id = uuid.uuid4().hex
        await history_repo.record_ownership(
            OwnershipAssertion.new(
                tenant_id=tenant_id,
                parcel_id=parcel.parcel_id,
                asserted_holder_ref="Live Rollback Holder (000-000-0000)",
                basis="initial registration",
                recorded_by=str(user_id),
                audit_ref=ownership_audit_id,
            )
        )
        status_audit_id = uuid.uuid4().hex
        await history_repo.record_status(
            StatusAssertion.new(
                tenant_id=tenant_id,
                parcel_id=parcel.parcel_id,
                asserted_status=parcel.status,
                basis="initial registration",
                recorded_by=str(user_id),
                audit_ref=status_audit_id,
            )
        )

        # Deliberately BEFORE any audit() call and before session.commit() —
        # isolates the parcel+history atomicity claim from the separately
        # documented (see module docstring) independent-commit audit store.
        with pytest.raises(_Fault):
            await agen.athrow(_Fault("simulated downstream failure before commit"))

        # --- Step 5: verify nothing persisted, on a FRESH session ---
        verify_engine = create_async_engine(db_url)
        try:
            async with verify_engine.connect() as conn:
                parcel_rows = (
                    await conn.execute(
                        sa.select(ParcelRecord).where(ParcelRecord.id == uuid.UUID(parcel_id))
                    )
                ).all()
                assert parcel_rows == [], "parcel mutation must not persist after rollback"

                ownership_rows = (
                    await conn.execute(
                        sa.select(ParcelOwnershipHistoryRecord).where(
                            ParcelOwnershipHistoryRecord.parcel_id == uuid.UUID(parcel_id)
                        )
                    )
                ).all()
                assert ownership_rows == [], "ownership-history row must not persist after rollback"

                status_rows = (
                    await conn.execute(
                        sa.select(ParcelStatusHistoryRecord).where(
                            ParcelStatusHistoryRecord.parcel_id == uuid.UUID(parcel_id)
                        )
                    )
                ).all()
                assert status_rows == [], "status-history row must not persist after rollback"

                audit_rows = (
                    await conn.execute(
                        sa.select(AuditLogRecord).where(
                            AuditLogRecord.resource_id == parcel_id
                        )
                    )
                ).all()
                assert audit_rows == [], (
                    "no orphan audit_log entry may reference the rolled-back parcel — "
                    "the fault fires before any audit() call is reached"
                )
        finally:
            await verify_engine.dispose()

        # --- Step 6: database/connection pool still usable afterward ---
        agen2 = uow.get_db_session(ctx=ctx)
        session2 = await anext(agen2)
        parcels_repo2 = PostgresParcelRepository(session2)
        second_parcel = Parcel.new(
            tenant_id=tenant_id,
            country_code="NG",
            origin="platform_registration",
            created_by=str(user_id),
            title="Post-rollback health-check parcel",
        )
        second_parcel.allocate_parcel_number("LV-NG-999998")
        await parcels_repo2.add(second_parcel)
        with pytest.raises(StopAsyncIteration):
            await anext(agen2)  # drives the generator to its normal commit path

        verify_engine2 = create_async_engine(db_url)
        try:
            async with verify_engine2.connect() as conn:
                rows = (
                    await conn.execute(
                        sa.select(ParcelRecord).where(
                            ParcelRecord.id == uuid.UUID(second_parcel.parcel_id)
                        )
                    )
                ).all()
                assert len(rows) == 1, (
                    "database must remain usable for a normal write after the rollback"
                )
        finally:
            await verify_engine2.dispose()

    finally:
        # --- Step 7: teardown ---
        admin_engine = create_async_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
        try:
            async with admin_engine.connect() as conn:
                await conn.execute(
                    sa.text(
                        f'SELECT pg_terminate_backend(pid) FROM pg_stat_activity '
                        f"WHERE datname = '{db_name}' AND pid <> pg_backend_pid()"
                    )
                )
                await conn.execute(sa.text(f'DROP DATABASE IF EXISTS "{db_name}"'))
        finally:
            await admin_engine.dispose()
