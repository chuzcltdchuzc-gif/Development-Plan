"""Live-Postgres atomicity rehearsal for GD-009 Batch 1's transaction-coupled
successful-mutation audit path (docs/adr/ADR-029, docs/GD-009-audit-
transaction-semantics-implementation-authorization-and-adr-007-
regularisation.md §8/§15 items 1-4, resumed under docs/GD-011-gd009-batch1-
resumption-authorization.md).

Deliberately NOT part of the hermetic `pytest -q` suite CI runs — see
tests/live/test_evidence_upload_rollback_live.py's own docstring for why:
the hermetic suite (tests/test_evidence_actor_attribution_service.py)
proves authorization/validation/business logic against in-memory fakes; it
cannot prove real transactional atomicity, because it never touches a real
database session's own commit/rollback boundary.

This module drives `app.kernel.uow.get_db_session` directly (the real
production per-request session factory), builds a real
`EvidenceActorAttributionService` against `PostgresEvidenceActorAttribution
Repository`/`PostgresEvidenceRepository`/`PostgresParcelExistenceAdapter`/
`PostgresPrincipalTenantAdapter`, and proves, against a real, throwaway
Postgres database (created and dropped within this test run):

  A. COMMIT TOGETHER — a successful `record_attribution()` call, followed
     by the generator's own normal commit, leaves BOTH the attribution row
     and its staged `evidence.actor_attribution.recorded` audit row durable,
     and `app.kernel.audit.verify_chain()` (the real, merged, DAG-aware
     verifier) returns `True` against the resulting real database.

  B. ROLLBACK TOGETHER — a fault injected after `record_attribution()`
     stages both rows but before the request's own final commit (mirroring
     tests/live/test_evidence_upload_rollback_live.py's own `agen.athrow`
     technique) leaves NEITHER row durable.

  C. AUDIT-STAGE FAILURE BLOCKS THE MUTATION — a controlled fault injected
     into `PostgresAuditStore.append_staged` itself (after the attribution
     row has already been staged) still prevents the attribution row from
     becoming durable, because both share the same session/transaction and
     neither this test nor the application code issues an intermediate
     commit. The fault is injected via patching, but the assertion is made
     entirely against real, independently-queried database state — not
     against whether the patched function was called.

  D. DENIAL/FAILURE INDEPENDENCE — a representative denial-shaped
     `app.kernel.audit.audit()` call (the unmodified, eager, independent
     path every non-migrated call site still uses) remains durable even
     when the surrounding business transaction is rolled back — proving
     GD-009 §9's regression guard directly, not merely asserted.

Skipped unless LIVE_TRANSACTIONAL_AUDIT_ADMIN_URL is set (a superuser/
schema-owning asyncpg URL) — never runs by default, so it cannot break the
hermetic suite or CI (which has no Postgres service).
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

import app.contexts.identity.adapters.orm  # noqa: F401 — registers identity_users/tenants
import app.contexts.registry.adapters.orm  # noqa: F401 — registers parcels
from app.contexts.evidence.adapters.orm import EvidenceRecordModel  # noqa: F401 — registers table
from app.contexts.evidence.adapters.postgres_repositories import (
    PostgresEvidenceActorAttributionRepository,
    PostgresEvidenceRepository,
    PostgresParcelExistenceAdapter,
    PostgresPrincipalTenantAdapter,
)
from app.contexts.evidence.application.attribution_service import (
    EvidenceActorAttributionService,
)
from app.contexts.evidence.domain.attribution import (
    ACTOR_TYPE_INDIVIDUAL,
    EXTERNAL_NAMED,
    ORIGINATED_BY,
)
from app.kernel import uow
from app.kernel.audit import audit, configure_eager_fallback, verify_chain
from app.kernel.audit_orm import AuditLogRecord
from app.kernel.audit_postgres import EagerPostgresAuditStore, PostgresAuditStore
from app.kernel.context import ExecutionContext

ADMIN_URL = os.environ.get("LIVE_TRANSACTIONAL_AUDIT_ADMIN_URL")

pytestmark = pytest.mark.skipif(
    not ADMIN_URL,
    reason=(
        "live GD-009 Batch 1 atomicity rehearsal — set "
        "LIVE_TRANSACTIONAL_AUDIT_ADMIN_URL to run against a real Postgres"
    ),
)


class _Fault(Exception):
    """Distinguishable from any exception the application itself raises."""


def _db_name() -> str:
    return f"landvault_live_batch1_audit_{uuid.uuid4().hex[:12]}"


def _with_db(url: str, db_name: str) -> str:
    base, _, _ = url.rpartition("/")
    return f"{base}/{db_name}"


async def _seed_fixture_rows(engine: AsyncEngine) -> dict[str, str]:
    """Mirrors tests/live/test_evidence_actor_attribution_live.py's own
    `_seed_fixture_rows` exactly — the minimum parent rows an attribution
    row's foreign keys require."""
    tenant_id = f"tenant-{uuid.uuid4().hex[:8]}"
    user_id = uuid.uuid4()
    parcel_id = uuid.uuid4()
    evidence_id = uuid.uuid4()

    async with engine.begin() as conn:
        await conn.execute(
            sa.text("INSERT INTO tenants (id, name, status) VALUES (:id, :name, 'ACTIVE')"),
            {"id": tenant_id, "name": "Live Batch1 Audit Test Tenant"},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO identity_users "
                "(id, identity_subject, email, full_name, country, tenant_id, roles) "
                "VALUES (:id, :sub, :email, 'Live Test User', 'NG', :tenant_id, '[]'::jsonb)"
            ),
            {
                "id": user_id,
                "sub": f"sub-{uuid.uuid4().hex[:8]}",
                "email": f"{uuid.uuid4().hex[:8]}@example.test",
                "tenant_id": tenant_id,
            },
        )
        await conn.execute(
            sa.text(
                "INSERT INTO parcels "
                "(id, tenant_id, country_code, origin, parcel_number, title, status, "
                " created_by) "
                "VALUES (:id, :tenant_id, 'NG', 'field_survey', :pnum, 'Live Test Parcel', "
                " 'ACTIVE', :created_by)"
            ),
            {
                "id": parcel_id,
                "tenant_id": tenant_id,
                "pnum": f"LP-{uuid.uuid4().hex[:8]}",
                "created_by": user_id,
            },
        )
        await conn.execute(
            sa.text(
                "INSERT INTO evidence_records "
                "(id, tenant_id, parcel_id, uploaded_by, filename, mime_type, size_bytes, "
                " storage_key, basis, evidence_type, status) "
                "VALUES (:id, :tenant_id, :parcel_id, :uploaded_by, 'plan.pdf', "
                " 'application/pdf', 1024, :storage_key, 'submitted by registrant', "
                " 'SURVEY_PLAN', 'RECEIVED')"
            ),
            {
                "id": evidence_id,
                "tenant_id": tenant_id,
                "parcel_id": parcel_id,
                "uploaded_by": user_id,
                "storage_key": f"evidence/{tenant_id}/{parcel_id}/abc",
            },
        )
    return {
        "tenant_id": tenant_id,
        "user_id": str(user_id),
        "parcel_id": str(parcel_id),
        "evidence_id": str(evidence_id),
    }


@pytest.mark.asyncio
async def test_batch1_attribution_audit_atomicity_on_live_postgres() -> None:
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
        try:
            ids = await _seed_fixture_rows(owning_engine)
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
        # Real production wiring for the (unmodified) eager/independent path
        # — Test D below proves it stays independent of Batch 1's staged path.
        configure_eager_fallback(EagerPostgresAuditStore(session_factory))

        ctx = ExecutionContext(
            principal_id=ids["user_id"], tenant_id=ids["tenant_id"], roles=()
        )

        def _build_service(session: object) -> EvidenceActorAttributionService:
            return EvidenceActorAttributionService(
                attributions=PostgresEvidenceActorAttributionRepository(session),  # type: ignore[arg-type]
                evidence=PostgresEvidenceRepository(session),  # type: ignore[arg-type]
                parcel_existence=PostgresParcelExistenceAdapter(session),  # type: ignore[arg-type]
                principal_tenant=PostgresPrincipalTenantAdapter(session),  # type: ignore[arg-type]
                session=session,  # type: ignore[arg-type]
            )

        # --- Test A: COMMIT TOGETHER -------------------------------------
        agen_a = uow.get_db_session(ctx=ctx)
        session_a = await anext(agen_a)
        service_a = _build_service(session_a)
        result_a = await service_a.record_attribution(
            ctx=ctx,
            evidence_id=ids["evidence_id"],
            attribution_role=ORIGINATED_BY,
            actor_reference_kind=EXTERNAL_NAMED,
            actor_type=ACTOR_TYPE_INDIVIDUAL,
            actor_name="Live Test Surveyor A",
            basis="Test A — commit together",
        )
        with pytest.raises(StopAsyncIteration):
            await anext(agen_a)  # drives the generator to its normal commit path

        # An ORM AsyncSession, not a raw Core Connection — Connection.
        # execute() against an ORM-mapped-class select does not perform
        # entity hydration, so indexing into the result would yield the
        # first mapped COLUMN (id) rather than the AuditLogRecord instance
        # (mirrors tests/live/test_transactional_audit_concurrency_live.py's
        # own _chain_rows helper and its identical documented reasoning).
        verify_engine_a = create_async_engine(db_url)
        verify_sessionmaker_a = async_sessionmaker(verify_engine_a, expire_on_commit=False)
        try:
            async with verify_sessionmaker_a() as verify_session:
                audit_rows = (
                    (
                        await verify_session.execute(
                            sa.select(AuditLogRecord).where(
                                AuditLogRecord.resource_id == result_a["attribution_id"]
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                assert len(audit_rows) == 1, (
                    "Test A: exactly one durable audit row must reference the committed "
                    "attribution row"
                )
                assert audit_rows[0].action == "evidence.actor_attribution.recorded"
        finally:
            await verify_engine_a.dispose()

        # Real, merged, DAG-aware verify_chain() against this real database
        # — proves the staged entry is not merely present, but hash-chain
        # valid, using the same PostgresAuditStore/AuditStore path
        # production uses (app.kernel.audit.get_audit_store()).
        verify_session_factory = async_sessionmaker(
            create_async_engine(app_db_url), expire_on_commit=False
        )
        async with verify_session_factory() as verify_session:
            from app.kernel.audit import configure_audit_store, reset_audit_store

            token = configure_audit_store(PostgresAuditStore(verify_session))
            try:
                assert await verify_chain() is True, (
                    "Test A: verify_chain() must accept the real, committed audit history"
                )
            finally:
                reset_audit_store(token)

        # --- Test B: ROLLBACK TOGETHER ------------------------------------
        agen_b = uow.get_db_session(ctx=ctx)
        session_b = await anext(agen_b)
        service_b = _build_service(session_b)
        result_b = await service_b.record_attribution(
            ctx=ctx,
            evidence_id=ids["evidence_id"],
            attribution_role=ORIGINATED_BY,
            actor_reference_kind=EXTERNAL_NAMED,
            actor_type=ACTOR_TYPE_INDIVIDUAL,
            actor_name="Live Test Surveyor B — must not survive",
            basis="Test B — rollback together",
        )
        doomed_attribution_id = result_b["attribution_id"]
        # Deliberately AFTER both rows are staged (flushed) but BEFORE this
        # request's own commit — mirrors test_evidence_upload_rollback_live.
        # py's identical `agen.athrow` technique.
        with pytest.raises(_Fault):
            await agen_b.athrow(_Fault("simulated downstream failure before commit"))

        verify_engine_b = create_async_engine(db_url)
        try:
            async with verify_engine_b.connect() as conn:
                attribution_rows = (
                    await conn.execute(
                        sa.text(
                            "SELECT id FROM evidence_actor_attributions WHERE id = :id"
                        ),
                        {"id": doomed_attribution_id},
                    )
                ).all()
                assert attribution_rows == [], (
                    "Test B: the attribution row must not persist after rollback"
                )
                audit_rows_b = (
                    await conn.execute(
                        sa.select(AuditLogRecord).where(
                            AuditLogRecord.resource_id == doomed_attribution_id
                        )
                    )
                ).all()
                assert audit_rows_b == [], (
                    "Test B: no orphan audit_log entry may reference the rolled-back "
                    "attribution row — neither survives, together"
                )
        finally:
            await verify_engine_b.dispose()

        # --- Test C: AUDIT-STAGE FAILURE BLOCKS THE MUTATION --------------
        agen_c = uow.get_db_session(ctx=ctx)
        session_c = await anext(agen_c)
        service_c = _build_service(session_c)

        original_append_staged = PostgresAuditStore.append_staged

        async def _failing_append_staged(self: PostgresAuditStore, entry: object) -> None:
            raise _Fault("simulated audit-stage persistence failure")

        PostgresAuditStore.append_staged = _failing_append_staged  # type: ignore[method-assign]
        try:
            with pytest.raises(_Fault):
                await service_c.record_attribution(
                    ctx=ctx,
                    evidence_id=ids["evidence_id"],
                    attribution_role=ORIGINATED_BY,
                    actor_reference_kind=EXTERNAL_NAMED,
                    actor_type=ACTOR_TYPE_INDIVIDUAL,
                    actor_name="Live Test Surveyor C — must not survive",
                    basis="Test C — audit-stage failure blocks mutation",
                )
        finally:
            PostgresAuditStore.append_staged = original_append_staged  # type: ignore[method-assign]

        # The exception propagated out of record_attribution() before this
        # request's own commit ever ran — drive the generator's exception
        # path exactly as production would (the route handler re-raises,
        # get_db_session's `except Exception: await session.rollback()`).
        with pytest.raises(_Fault):
            await agen_c.athrow(_Fault("propagated: audit-stage failure aborts the request"))

        verify_engine_c = create_async_engine(db_url)
        try:
            async with verify_engine_c.connect() as conn:
                attribution_rows_c = (
                    await conn.execute(
                        sa.text(
                            "SELECT id FROM evidence_actor_attributions "
                            "WHERE tenant_id = :tenant_id AND basis LIKE 'Test C%'"
                        ),
                        {"tenant_id": ids["tenant_id"]},
                    )
                ).all()
                assert attribution_rows_c == [], (
                    "Test C: a forced audit-stage failure must prevent the attribution "
                    "row from becoming durable — real database state, not a mock check"
                )
        finally:
            await verify_engine_c.dispose()

        # --- Test D: DENIAL/FAILURE INDEPENDENCE --------------------------
        # session_d is deliberately unused below: audit() always writes
        # through the eager, independently-committing store (configure_
        # eager_fallback above), never through the request's own UoW
        # session — the exact separation this test proves.
        agen_d = uow.get_db_session(ctx=ctx)
        _session_d = await anext(agen_d)
        from app.kernel.context import reset_context, set_context

        token_ctx = set_context(ctx)
        try:
            denial_entry = await audit(
                "identity.refresh.replay_detected",
                resource_type="test_denial",
                decision="DENY",
                payload={"note": "Test D — representative denial/failure audit"},
            )
        finally:
            reset_context(token_ctx)
        with pytest.raises(_Fault):
            await agen_d.athrow(_Fault("simulated downstream failure — business tx rolls back"))

        # ORM AsyncSession, not a raw Core Connection — see the identical
        # reasoning at Test A's own verification block above.
        verify_engine_d = create_async_engine(db_url)
        verify_sessionmaker_d = async_sessionmaker(verify_engine_d, expire_on_commit=False)
        try:
            async with verify_sessionmaker_d() as verify_session:
                denial_rows = (
                    (
                        await verify_session.execute(
                            sa.select(AuditLogRecord).where(
                                AuditLogRecord.action == "identity.refresh.replay_detected",
                                AuditLogRecord.resource_type == "test_denial",
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                assert len(denial_rows) == 1, (
                    "Test D: the denial/failure audit entry must remain independently "
                    "durable even though the surrounding business transaction rolled back"
                )
                assert denial_rows[0].hash == denial_entry.hash
        finally:
            await verify_engine_d.dispose()

    finally:
        admin_engine2: AsyncEngine = create_async_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
        try:
            async with admin_engine2.connect() as conn:
                await conn.execute(
                    sa.text(
                        f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                        f"WHERE datname = '{db_name}' AND pid <> pg_backend_pid()"
                    )
                )
                await conn.execute(sa.text(f'DROP DATABASE IF EXISTS "{db_name}"'))
        finally:
            await admin_engine2.dispose()
