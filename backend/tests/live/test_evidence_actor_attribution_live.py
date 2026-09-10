"""Live-Postgres rehearsal for ADR-028's database-level invariants
(migrations/versions/0014_evidence_actor_attributions.py).

Deliberately NOT part of the hermetic `pytest -q` suite that CI runs — see
tests/live/test_registry_history_rollback_live.py's own docstring for why:
the hermetic suite proves domain/application logic against in-memory
fakes; it cannot prove anything about real database constraints, triggers,
or concurrent-transaction behavior, because it never exercises Postgres at
all. This module does, following that same module's exact "throwaway
database, real migration chain via subprocess, drop at the end" pattern.

Proves, against a real Postgres:
  1. the append-only trigger rejects UPDATE and DELETE unconditionally,
     including as the schema-owning role (mirroring migration 0011's own
     rehearsal for parcel_ownership_history);
  2. the CHECK (id <> supersedes_id) constraint rejects self-supersession;
  3. the UNIQUE (supersedes_id) constraint enforces ADR-028's "one direct
     successor per superseded attribution" invariant under REAL
     concurrent writes — two concurrent transactions each attempting to
     supersede the same row; exactly one must succeed, the other must
     fail with a unique-violation, not silently corrupt state.

Skipped unless LIVE_ATTRIBUTION_ADMIN_URL is set (a superuser/schema-
owning asyncpg URL) — never runs by default, so it cannot break the
hermetic suite or CI (which has no Postgres service).
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

ADMIN_URL = os.environ.get("LIVE_ATTRIBUTION_ADMIN_URL")

pytestmark = pytest.mark.skipif(
    not ADMIN_URL,
    reason="live ADR-028 rehearsal — set LIVE_ATTRIBUTION_ADMIN_URL to run against a real Postgres",
)


def _db_name() -> str:
    return f"landvault_live_attribution_{uuid.uuid4().hex[:12]}"


def _with_db(url: str, db_name: str) -> str:
    base, _, _ = url.rpartition("/")
    return f"{base}/{db_name}"


async def _seed_fixture_rows(engine: AsyncEngine) -> dict[str, str]:
    """Inserts the minimum parent rows (tenant, user, parcel, evidence
    record) a real evidence_actor_attributions row's foreign keys require
    — mirrors test_registry_history_rollback_live.py's own seeding style."""
    tenant_id = f"tenant-{uuid.uuid4().hex[:8]}"
    user_id = uuid.uuid4()
    parcel_id = uuid.uuid4()
    evidence_id = uuid.uuid4()

    async with engine.begin() as conn:
        await conn.execute(
            sa.text("INSERT INTO tenants (id, name, status) VALUES (:id, :name, 'ACTIVE')"),
            {"id": tenant_id, "name": "Live Attribution Test Tenant"},
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


async def _insert_attribution(
    engine: AsyncEngine, *, ids: dict[str, str], supersedes_id: str | None = None
) -> str:
    attribution_id = uuid.uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            sa.text(
                "INSERT INTO evidence_actor_attributions "
                "(id, tenant_id, evidence_id, attribution_role, actor_reference_kind, "
                " actor_name, actor_type, basis, recorded_by, supersedes_id) "
                "VALUES (:id, :tenant_id, :evidence_id, 'ORIGINATED_BY', 'EXTERNAL_NAMED', "
                " 'Test Actor', 'INDIVIDUAL', 'live rehearsal row', :recorded_by, "
                " :supersedes_id)"
            ),
            {
                "id": attribution_id,
                "tenant_id": ids["tenant_id"],
                "evidence_id": ids["evidence_id"],
                "recorded_by": ids["user_id"],
                "supersedes_id": supersedes_id,
            },
        )
    return str(attribution_id)


@pytest.mark.asyncio
async def test_adr028_database_invariants_on_live_postgres() -> None:
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
        # --- Step 1: real migration chain, including 0014 (ADR-028) ---
        # Subprocess, not alembic.command.upgrade in-process — alembic's
        # async env.py calls asyncio.run() internally, which cannot nest
        # inside this already-running pytest-asyncio loop (identical
        # constraint test_registry_history_rollback_live.py documents).
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
        try:
            ids = await _seed_fixture_rows(owning_engine)
            original_id = await _insert_attribution(owning_engine, ids=ids)

            # --- Invariant 1: append-only trigger rejects UPDATE/DELETE,
            # even as the schema-owning role, exactly as migration 0011's
            # own trigger already proves for parcel_ownership_history. ---
            with pytest.raises(Exception) as update_exc:
                async with owning_engine.begin() as conn:
                    await conn.execute(
                        sa.text(
                            "UPDATE evidence_actor_attributions SET basis = 'tampered' "
                            "WHERE id = :id"
                        ),
                        {"id": original_id},
                    )
            assert "append-only" in str(update_exc.value)

            with pytest.raises(Exception) as delete_exc:
                async with owning_engine.begin() as conn:
                    await conn.execute(
                        sa.text("DELETE FROM evidence_actor_attributions WHERE id = :id"),
                        {"id": original_id},
                    )
            assert "append-only" in str(delete_exc.value)

            # --- Invariant 2: CHECK (id <> supersedes_id) rejects
            # self-supersession. ---
            self_superseding_id = uuid.uuid4()
            with pytest.raises(IntegrityError) as self_supersede_exc:
                async with owning_engine.begin() as conn:
                    await conn.execute(
                        sa.text(
                            "INSERT INTO evidence_actor_attributions "
                            "(id, tenant_id, evidence_id, attribution_role, "
                            " actor_reference_kind, actor_name, actor_type, basis, "
                            " recorded_by, supersedes_id) "
                            "VALUES (:id, :tenant_id, :evidence_id, 'ORIGINATED_BY', "
                            " 'EXTERNAL_NAMED', 'Self Superseder', 'INDIVIDUAL', "
                            " 'attempted self-supersession', :recorded_by, :id)"
                        ),
                        {
                            "id": self_superseding_id,
                            "tenant_id": ids["tenant_id"],
                            "evidence_id": ids["evidence_id"],
                            "recorded_by": ids["user_id"],
                        },
                    )
            assert "ck_evidence_actor_attributions_no_self_supersede" in str(
                self_supersede_exc.value
            )

            # --- Invariant 3: UNIQUE (supersedes_id) enforces "one direct
            # successor per superseded attribution" under REAL concurrent
            # writes — two concurrent transactions each try to supersede
            # `original_id`; exactly one must succeed. ---
            async def _try_supersede() -> str | None:
                try:
                    return await _insert_attribution(
                        owning_engine, ids=ids, supersedes_id=original_id
                    )
                except IntegrityError:
                    return None

            results = await asyncio.gather(
                _try_supersede(), _try_supersede(), return_exceptions=False
            )
            successes = [r for r in results if r is not None]
            assert len(successes) == 1, (
                f"expected exactly one concurrent correction to succeed, got {successes!r}"
            )

            # Proves the connection pool survives the failed concurrent
            # attempt and one more real write still succeeds afterward
            # (mirrors test_registry_history_rollback_live.py's own
            # "not poisoned" check).
            third_id = await _insert_attribution(
                owning_engine, ids=ids, supersedes_id=successes[0]
            )
            assert third_id
        finally:
            await owning_engine.dispose()
    finally:
        admin_engine = create_async_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
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
