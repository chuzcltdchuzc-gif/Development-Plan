"""Live-Postgres rehearsal for B5.3's upload orchestration (docs/adr/
ADR-026-evidence-domain-model.md "Transaction boundaries", docs/adr/
ADR-007-audit-trail-evidence-model.md decision 4).

Deliberately NOT part of the hermetic `pytest -q` suite CI runs — mirrors
tests/live/test_registry_history_rollback_live.py's own structure and
scope exactly, adapted for Evidence. That suite proves the domain/
application logic against in-memory fakes; it cannot prove anything about
the real Postgres session/commit/rollback path, because it never exercises
it (app.kernel.uow.get_db_session is never touched — confirmed by reading
tests/app_factory.py).

This module:
  1. creates a throwaway database on the Postgres instance addressed by
     LIVE_ROLLBACK_ADMIN_URL (the schema-owning role),
  2. runs the real Alembic migration chain against it — this doubles as a
     from-scratch live-migration rehearsal of 0012_evidence_records (no
     schema changed in B5.3 itself; re-running the full chain here confirms
     0012 still applies cleanly on top of everything before it),
  3. seeds a tenant, user, and parcel via raw SQL (the same minimal-seed
     style the Registry live-rollback test already uses),
  4. drives app.kernel.uow.get_db_session directly with a real
     EagerPostgresAuditStore configured (app.main's own production wiring,
     docs/PHASE-B5-SLICE3_ACCEPTANCE_PACKAGE.md) — the real per-request path,
  5. Test A: a full, real EvidenceService.upload_evidence() call against
     PostgresEvidenceRepository — confirms persistence, HASHED status,
     correct sha256, and both audit entries, all via a fresh connection,
  6. Test B: fault-injection before the first audit() call (matching the
     Registry test's own documented boundary — the audit-store/main-session
     pairing is not itself transactional, a pre-existing, documented gap,
     not new to B5.3) — confirms the EvidenceRecord row does not persist,
  7. proves the connection pool is not poisoned by one more real write,
  8. drops the throwaway database.

Skipped unless LIVE_ROLLBACK_ADMIN_URL is set — never runs by default, so
it cannot break the hermetic suite or CI (which has no Postgres service).
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

import app.contexts.identity.adapters.orm  # noqa: F401 — registers identity_users/tenants
import app.contexts.registry.adapters.orm  # noqa: F401 — registers parcels
from app.contexts.evidence.adapters.orm import EvidenceRecordModel
from app.contexts.evidence.adapters.postgres_repositories import PostgresEvidenceRepository
from app.contexts.evidence.application.evidence_service import EvidenceService
from app.contexts.evidence.domain.evidence_record import EvidenceRecord
from app.kernel import uow
from app.kernel.audit import configure_eager_fallback
from app.kernel.audit_orm import AuditLogRecord
from app.kernel.audit_postgres import EagerPostgresAuditStore
from app.kernel.context import ExecutionContext
from tests.fakes.storage import InMemoryStoragePort

ADMIN_URL = os.environ.get("LIVE_ROLLBACK_ADMIN_URL")

pytestmark = pytest.mark.skipif(
    not ADMIN_URL,
    reason="live rollback rehearsal — set LIVE_ROLLBACK_ADMIN_URL to run against a real Postgres",
)


def _db_name() -> str:
    return f"landvault_live_evidence_{uuid.uuid4().hex[:12]}"


def _with_db(url: str, db_name: str) -> str:
    base, _, _ = url.rpartition("/")
    return f"{base}/{db_name}"


class _Fault(Exception):
    """Distinguishable from any exception the application itself raises."""


@pytest.mark.asyncio
async def test_evidence_upload_persists_and_rolls_back_on_live_postgres() -> None:
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
        # --- Step 1: real migration chain, including 0012 (ADR-026) ---
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        migration_env = dict(os.environ, MIGRATIONS_DATABASE_URL=db_url)
        migration_result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=backend_dir,
            env=migration_env,
            capture_output=True,
            text=True,
        )
        assert migration_result.returncode == 0, (
            f"alembic upgrade head failed:\n"
            f"stdout={migration_result.stdout}\nstderr={migration_result.stderr}"
        )

        owning_engine: AsyncEngine = create_async_engine(db_url)
        tenant_id = f"tenant-{uuid.uuid4().hex[:8]}"
        user_id = uuid.uuid4()
        parcel_id = uuid.uuid4()
        try:
            async with owning_engine.begin() as conn:
                await conn.execute(
                    sa.text(
                        "INSERT INTO tenants (id, name, status) VALUES (:id, :name, 'ACTIVE')"
                    ),
                    {"id": tenant_id, "name": "Live Evidence Upload Test Tenant"},
                )
                await conn.execute(
                    sa.text(
                        "INSERT INTO identity_users "
                        "(id, keycloak_subject, email, full_name, country, tenant_id, roles) "
                        "VALUES (:id, :sub, :email, 'Live Evidence Test User', "
                        "'NG', :tenant_id, '[]')"
                    ),
                    {
                        "id": user_id,
                        "sub": f"kc-{user_id}",
                        "email": f"{user_id}@live-evidence-test.invalid",
                        "tenant_id": tenant_id,
                    },
                )
                await conn.execute(
                    sa.text(
                        "INSERT INTO parcels "
                        "(id, tenant_id, country_code, origin, created_by, status, title) "
                        "VALUES (:id, :tenant_id, 'NG', 'platform_registration', :created_by, "
                        "'ACTIVE', 'Live Evidence Test Parcel')"
                    ),
                    {"id": parcel_id, "tenant_id": tenant_id, "created_by": user_id},
                )
        finally:
            await owning_engine.dispose()

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
        # Real production wiring (app.main.create_app) — the same
        # eager-commit Postgres audit store, not a fake, so audit() calls
        # made through EvidenceService actually reach this database.
        configure_eager_fallback(EagerPostgresAuditStore(session_factory))

        ctx = ExecutionContext(principal_id=str(user_id), tenant_id=tenant_id, roles=())
        content = b"live rehearsal evidence content"

        # --- Test A: full, real, successful upload ---------------------
        agen = uow.get_db_session(ctx=ctx)
        session = await anext(agen)
        service = EvidenceService(
            evidence=PostgresEvidenceRepository(session), storage=InMemoryStoragePort()
        )
        result = await service.upload_evidence(
            ctx=ctx,
            parcel_id=str(parcel_id),
            filename="live-rehearsal.pdf",
            mime_type="application/pdf",
            data=content,
            basis="live rehearsal upload",
            evidence_type="OTHER",
        )
        with pytest.raises(StopAsyncIteration):
            await anext(agen)  # drives the generator to its normal commit path

        assert result["status"] == "HASHED"
        assert result["sha256"] == hashlib.sha256(content).hexdigest()

        verify_engine = create_async_engine(db_url)
        try:
            async with verify_engine.connect() as conn:
                rows = (
                    await conn.execute(
                        sa.select(EvidenceRecordModel).where(
                            EvidenceRecordModel.id == uuid.UUID(result["evidence_id"])
                        )
                    )
                ).all()
                assert len(rows) == 1, "evidence row must persist after a successful upload"
                persisted = rows[0]
                assert persisted.status == "HASHED"
                assert persisted.sha256 == hashlib.sha256(content).hexdigest()

                audit_rows = (
                    await conn.execute(
                        sa.select(AuditLogRecord.action).where(
                            AuditLogRecord.resource_id == result["evidence_id"]
                        )
                    )
                ).all()
                actions = sorted(r[0] for r in audit_rows)
                assert actions == ["evidence.hashed", "evidence.uploaded"], (
                    "both audit entries must be durably persisted, real store, not a fake"
                )
        finally:
            await verify_engine.dispose()

        # --- Test B: fault before the first audit() call, before commit --
        agen2 = uow.get_db_session(ctx=ctx)
        session2 = await anext(agen2)
        repo2 = PostgresEvidenceRepository(session2)
        storage2 = InMemoryStoragePort()

        data2 = b"this row must never persist"
        key2 = f"evidence/{tenant_id}/{parcel_id}/rollback-rehearsal"
        await storage2.put(key2, data2)

        doomed_record = EvidenceRecord.new(
            tenant_id=tenant_id,
            parcel_id=str(parcel_id),
            uploaded_by=str(user_id),
            filename="doomed.pdf",
            mime_type="application/pdf",
            size_bytes=len(data2),
            storage_key=key2,
            basis="rollback rehearsal",
            evidence_type="OTHER",
        )
        doomed_record = await repo2.add(doomed_record)  # flush only, not committed
        doomed_id: str = doomed_record.evidence_id

        # Deliberately BEFORE any audit() call and before session.commit()
        # — isolates the row's own atomicity claim from the separately
        # documented (see module docstring) independent-commit audit store,
        # the identical boundary the Registry live-rollback test draws.
        with pytest.raises(_Fault):
            await agen2.athrow(_Fault("simulated downstream failure before commit"))

        verify_engine2 = create_async_engine(db_url)
        try:
            async with verify_engine2.connect() as conn:
                rows = (
                    await conn.execute(
                        sa.select(EvidenceRecordModel).where(
                            EvidenceRecordModel.id == uuid.UUID(doomed_id)
                        )
                    )
                ).all()
                assert rows == [], "evidence row must not persist after rollback"

                doomed_audit_rows = (
                    await conn.execute(
                        sa.select(AuditLogRecord).where(AuditLogRecord.resource_id == doomed_id)
                    )
                ).all()
                assert doomed_audit_rows == [], (
                    "no orphan audit_log entry may reference the rolled-back evidence row"
                )
        finally:
            await verify_engine2.dispose()

        # storage2 still holds the orphaned object — the accepted, named
        # residual risk ADR-026 "Transaction boundaries" documents (storage
        # write precedes the DB row; a failure after that write can leave
        # an object with nothing referencing it). Confirmed, not assumed.
        assert await storage2.list_keys(f"evidence/{tenant_id}/{parcel_id}/") == [key2]

        # --- Step: connection pool still usable after the rollback ------
        agen3 = uow.get_db_session(ctx=ctx)
        session3 = await anext(agen3)
        repo3 = PostgresEvidenceRepository(session3)
        healthcheck_record = EvidenceRecord.new(
            tenant_id=tenant_id,
            parcel_id=str(parcel_id),
            uploaded_by=str(user_id),
            filename="post-rollback-healthcheck.pdf",
            mime_type="application/pdf",
            size_bytes=4,
            storage_key=f"evidence/{tenant_id}/{parcel_id}/healthcheck",
            basis="post-rollback health check",
            evidence_type="OTHER",
        )
        await repo3.add(healthcheck_record)
        with pytest.raises(StopAsyncIteration):
            await anext(agen3)

        verify_engine3 = create_async_engine(db_url)
        try:
            async with verify_engine3.connect() as conn:
                rows = (
                    await conn.execute(
                        sa.select(EvidenceRecordModel).where(
                            EvidenceRecordModel.id == uuid.UUID(healthcheck_record.evidence_id)
                        )
                    )
                ).all()
                assert len(rows) == 1, "database must remain usable for a normal write"
        finally:
            await verify_engine3.dispose()

    finally:
        admin_engine = create_async_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
        try:
            async with admin_engine.connect() as conn:
                await conn.execute(
                    sa.text(
                        f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                        f"WHERE datname = '{db_name}' AND pid <> pg_backend_pid()"
                    )
                )
                await conn.execute(sa.text(f'DROP DATABASE IF EXISTS "{db_name}"'))
        finally:
            await admin_engine.dispose()
