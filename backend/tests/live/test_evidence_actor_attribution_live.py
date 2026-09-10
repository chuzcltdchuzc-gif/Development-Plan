"""Live-Postgres rehearsal for ADR-028's database-level invariants
(migrations/versions/0014_evidence_actor_attributions.py).

Deliberately NOT part of the hermetic `pytest -q` suite that CI runs — see
tests/live/test_registry_history_rollback_live.py's own docstring for why:
the hermetic suite proves domain/application logic against in-memory
fakes; it cannot prove anything about real database constraints, triggers,
or concurrent-transaction behavior, because it never exercises Postgres at
all. This module does, following that same module's exact "throwaway
database, real migration chain via subprocess, drop at the end" pattern.

**Regression history:** the first version of this module proved only
append-only rejection, self-supersession rejection, and one-successor
concurrency. A subsequent Governance-directed red-team tested the
database invariant directly (not merely through the application service)
and found that a single multi-row `INSERT` could persist a two-row
`supersedes_id` cycle — the `UNIQUE (supersedes_id)` constraint does not
catch a mutual pair (the two referenced values differ), and Postgres
checks a `NOT DEFERRABLE` foreign key at end-of-statement, not per-row
within a multi-row statement. Migration 0014 was remediated with two new
`BEFORE INSERT` triggers (cycle rejection via a bounded recursive ancestry
walk; same-tenant `actor_principal_id` enforcement) and a `CHECK`
constraint expressing ADR-028's actor-representation shape. Every case
that red-team found is now a permanent regression test below — most
importantly Case C, the one that actually escaped the original
implementation.

Proves, against a real Postgres:
  1. the append-only trigger rejects UPDATE and DELETE unconditionally,
     including as the schema-owning role (mirroring migration 0011's own
     rehearsal for parcel_ownership_history);
  2. the CHECK (id <> supersedes_id) constraint rejects self-supersession;
  3. the evidence_actor_attributions_reject_cycle trigger rejects a
     sequential two-row cycle attempt, a cycle assembled inside one
     multi-row INSERT statement (Case C — the actual regression), a
     longer (3-row) cycle attempt, and permits ordinary valid linear
     succession;
  4. the UNIQUE (supersedes_id) constraint enforces ADR-028's "one direct
     successor per superseded attribution" invariant under REAL
     concurrent writes — two concurrent transactions each attempting to
     supersede the same row; exactly one must succeed, the other must
     fail with a unique-violation, not silently corrupt state;
  5. the ck_evidence_actor_attributions_actor_shape CHECK rejects every
     actor-representation violation the domain constructor also rejects,
     even when the domain constructor and application service are
     bypassed entirely via direct SQL;
  6. the evidence_actor_attributions_check_same_tenant trigger rejects a
     live actor_principal_id belonging to a different tenant than the
     attribution, even via direct SQL — while a cross-tenant actor
     represented as a free-text snapshot (no live reference) still
     succeeds, exactly as ADR-028 permits.

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
    engine: AsyncEngine,
    *,
    ids: dict[str, str],
    supersedes_id: str | None = None,
    attribution_id: uuid.UUID | None = None,
    actor_reference_kind: str = "EXTERNAL_NAMED",
    actor_principal_id: str | None = None,
    actor_name: str | None = "Test Actor",
    actor_organization_name: str | None = None,
    actor_type: str = "INDIVIDUAL",
    attribution_role: str = "ORIGINATED_BY",
    tenant_id: str | None = None,
) -> str:
    attribution_id = attribution_id or uuid.uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            sa.text(
                "INSERT INTO evidence_actor_attributions "
                "(id, tenant_id, evidence_id, attribution_role, actor_reference_kind, "
                " actor_principal_id, actor_name, actor_organization_name, actor_type, "
                " basis, recorded_by, supersedes_id) "
                "VALUES (:id, :tenant_id, :evidence_id, :attribution_role, "
                " :actor_reference_kind, :actor_principal_id, :actor_name, "
                " :actor_organization_name, :actor_type, 'live rehearsal row', "
                " :recorded_by, :supersedes_id)"
            ),
            {
                "id": attribution_id,
                "tenant_id": tenant_id or ids["tenant_id"],
                "evidence_id": ids["evidence_id"],
                "attribution_role": attribution_role,
                "actor_reference_kind": actor_reference_kind,
                "actor_principal_id": actor_principal_id,
                "actor_name": actor_name,
                "actor_organization_name": actor_organization_name,
                "actor_type": actor_type,
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

            # --- Invariant 2: self-supersession is rejected (Case A).
            # BEFORE ROW triggers fire before CHECK constraints are
            # evaluated, so evidence_actor_attributions_reject_cycle's
            # ancestry walk (which trivially finds NEW.id at depth 1 when
            # supersedes_id = id) is what actually raises here — the
            # CHECK (id <> supersedes_id) constraint remains in the
            # schema as an independent, cheaper guard, but this specific
            # case is caught by the trigger first. Both existing;
            # asserting on whichever fires is the accurate claim. ---
            self_superseding_id = uuid.uuid4()
            with pytest.raises(Exception) as self_supersede_exc:
                await _insert_attribution(
                    owning_engine, ids=ids, attribution_id=self_superseding_id,
                    supersedes_id=str(self_superseding_id), actor_name="Self Superseder",
                )
            assert (
                "ck_evidence_actor_attributions_no_self_supersede" in str(self_supersede_exc.value)
                or "cycle back to" in str(self_supersede_exc.value)
            )

            # --- Invariant 3: cycle rejection (Cases B, C, D, E) ---

            # Case B: sequential two-row cycle attempted via UPDATE — the
            # append-only trigger alone already blocks this (no row can
            # ever be retargeted after insert), proven again here for
            # completeness of the cycle-specific regression suite.
            row_x = await _insert_attribution(owning_engine, ids=ids, actor_name="X")
            row_y = await _insert_attribution(
                owning_engine, ids=ids, supersedes_id=row_x, actor_name="Y"
            )
            with pytest.raises(Exception) as seq_cycle_exc:
                async with owning_engine.begin() as conn:
                    await conn.execute(
                        sa.text(
                            "UPDATE evidence_actor_attributions SET supersedes_id = :y "
                            "WHERE id = :x"
                        ),
                        {"y": row_y, "x": row_x},
                    )
            assert "append-only" in str(seq_cycle_exc.value)

            # Case C: THE regression — a two-row cycle assembled entirely
            # inside one multi-row INSERT statement. This is the exact
            # case that escaped the original implementation; it must now
            # be rejected by evidence_actor_attributions_reject_cycle.
            row_p = uuid.uuid4()
            row_q = uuid.uuid4()
            with pytest.raises(Exception) as multi_row_cycle_exc:
                async with owning_engine.begin() as conn:
                    await conn.execute(
                        sa.text(
                            "INSERT INTO evidence_actor_attributions "
                            "(id, tenant_id, evidence_id, attribution_role, "
                            " actor_reference_kind, actor_name, actor_type, basis, "
                            " recorded_by, supersedes_id) VALUES "
                            "(:p, :tenant_id, :evidence_id, 'ORIGINATED_BY', "
                            " 'EXTERNAL_NAMED', 'P', 'INDIVIDUAL', 'rt', :recorded_by, :q), "
                            "(:q2, :tenant_id, :evidence_id, 'ORIGINATED_BY', "
                            " 'EXTERNAL_NAMED', 'Q', 'INDIVIDUAL', 'rt', :recorded_by, :p2)"
                        ),
                        {
                            "p": row_p, "q": row_q, "p2": row_p, "q2": row_q,
                            "tenant_id": ids["tenant_id"], "evidence_id": ids["evidence_id"],
                            "recorded_by": ids["user_id"],
                        },
                    )
            assert "cycle" in str(multi_row_cycle_exc.value)
            # Confirm neither half of the attempted cycle persisted.
            async with owning_engine.begin() as conn:
                check = await conn.execute(
                    sa.text(
                        "SELECT count(*) AS n FROM evidence_actor_attributions "
                        "WHERE id IN (:p, :q)"
                    ),
                    {"p": row_p, "q": row_q},
                )
                assert check.one().n == 0, "cyclic INSERT must not partially persist"

            # Case D: longer (3-row) cycle attempt via UPDATE rewiring —
            # blocked by append-only regardless of cycle length.
            row_1 = await _insert_attribution(owning_engine, ids=ids, actor_name="1")
            row_2 = await _insert_attribution(
                owning_engine, ids=ids, supersedes_id=row_1, actor_name="2"
            )
            row_3 = await _insert_attribution(
                owning_engine, ids=ids, supersedes_id=row_2, actor_name="3"
            )
            with pytest.raises(Exception) as long_cycle_exc:
                async with owning_engine.begin() as conn:
                    await conn.execute(
                        sa.text(
                            "UPDATE evidence_actor_attributions SET supersedes_id = :three "
                            "WHERE id = :one"
                        ),
                        {"three": row_3, "one": row_1},
                    )
            assert "append-only" in str(long_cycle_exc.value)

            # Case E: valid linear succession must still succeed —
            # cycle rejection must not be overzealous about ordinary,
            # non-cyclic corrections.
            valid_head = await _insert_attribution(owning_engine, ids=ids, actor_name="Valid 1")
            valid_next = await _insert_attribution(
                owning_engine, ids=ids, supersedes_id=valid_head, actor_name="Valid 2"
            )
            assert valid_next

            # --- Invariant 4: UNIQUE (supersedes_id) enforces "one direct
            # successor per superseded attribution" under REAL concurrent
            # writes (Case F) — two concurrent transactions each try to
            # supersede `original_id`; exactly one must succeed. ---
            async def _try_supersede() -> str | None:
                try:
                    return await _insert_attribution(
                        owning_engine, ids=ids, supersedes_id=original_id, actor_name="Racer"
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
                owning_engine, ids=ids, supersedes_id=successes[0], actor_name="After Race"
            )
            assert third_id

            # --- Invariant 5: actor-representation CHECK rejects every
            # domain-layer violation even when the domain constructor and
            # the application service are bypassed entirely. ---
            async def _expect_actor_shape_rejection(**overrides: object) -> None:
                with pytest.raises(IntegrityError) as exc_info:
                    await _insert_attribution(owning_engine, ids=ids, **overrides)  # type: ignore[arg-type]
                assert "ck_evidence_actor_attributions_actor_shape" in str(
                    exc_info.value
                ) or "ck_evidence_actor_attributions_reference_kind_bounded" in str(
                    exc_info.value
                )

            await _expect_actor_shape_rejection(
                actor_reference_kind="INTERNAL_PRINCIPAL", actor_name=None,
                actor_principal_id=ids["user_id"],
            )
            await _expect_actor_shape_rejection(
                actor_reference_kind="INTERNAL_PRINCIPAL", actor_name="X",
                actor_principal_id=None,
            )
            await _expect_actor_shape_rejection(
                actor_reference_kind="EXTERNAL_NAMED", actor_name="X",
                actor_principal_id=ids["user_id"],
            )
            await _expect_actor_shape_rejection(
                actor_reference_kind="UNKNOWN", actor_name="Fabricated",
            )
            await _expect_actor_shape_rejection(
                actor_reference_kind="TOTALLY_MADE_UP",
            )

            # --- Invariant 6: same-tenant enforcement rejects a live
            # cross-tenant actor_principal_id even via direct SQL, while
            # a snapshot-only cross-tenant actor still succeeds. ---
            other_tenant = f"tenant-other-{uuid.uuid4().hex[:8]}"
            other_user = uuid.uuid4()
            async with owning_engine.begin() as conn:
                await conn.execute(
                    sa.text("INSERT INTO tenants (id, name, status) VALUES (:id, :n, 'ACTIVE')"),
                    {"id": other_tenant, "n": "Other Tenant"},
                )
                await conn.execute(
                    sa.text(
                        "INSERT INTO identity_users (id, identity_subject, email, full_name, "
                        "country, tenant_id, roles) VALUES (:id, :sub, :email, 'Other', 'NG', "
                        ":tenant, '[]'::jsonb)"
                    ),
                    {
                        "id": other_user, "sub": f"sub-{uuid.uuid4().hex[:8]}",
                        "email": f"{uuid.uuid4().hex[:8]}@example.test", "tenant": other_tenant,
                    },
                )
            with pytest.raises(Exception) as cross_tenant_exc:
                await _insert_attribution(
                    owning_engine, ids=ids, actor_reference_kind="INTERNAL_PRINCIPAL",
                    actor_principal_id=str(other_user), actor_name="Cross Tenant",
                )
            assert "same tenant" in str(cross_tenant_exc.value)

            snapshot_only = await _insert_attribution(
                owning_engine, ids=ids, actor_reference_kind="HISTORICAL_ASSERTED",
                actor_name="Cross Tenant Actor By Name Only",
            )
            assert snapshot_only
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
