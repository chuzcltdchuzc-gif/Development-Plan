"""Live-Postgres audit-chain concurrency rehearsal for GD-009 Batch 1
(docs/GD-009-audit-transaction-semantics-implementation-authorization-and-
adr-007-regularisation.md §11, §15; docs/adr/ADR-030-audit-chain-
concurrency-ordering-and-linearization.md; docs/GD-010-audit-dag-verifier-
implementation-authorization.md; docs/GD-011-gd009-batch1-resumption-
authorization.md).

**This is the mandatory gate GD-009 §11/§15 requires before Batch 1's
concurrency behavior may be treated as proven.** Unlike the module this
replaces (a prototype predating ADR-030/GD-010, preserved as reference
evidence only on `feat/gd009-batch1-transactional-audit` — see
docs/GD-011-...md §14/§17/§18 for why it is not reused directly), the
success criterion here is NOT "no two committed rows may share a
`prev_hash`". Under the accepted DAG architecture, two legitimate
concurrent writers observing the same predecessor is an expected, valid
outcome — the required proof is that the resulting graph is DAG-valid
(`app.kernel.audit.verify_chain()` returns `True`), not that no branching
occurred.

Deliberately NOT part of the hermetic `pytest -q` suite CI runs — see
tests/live/test_registry_history_rollback_live.py's own docstring for why.
Skipped unless LIVE_TRANSACTIONAL_AUDIT_ADMIN_URL is set.

**Method — "controlled barrier" interleaving, not a hope-it-races
asyncio.gather.** GD-009 §14 explicitly permits "deliberately controlling
barriers to produce a known interleaving" as an alternative to relying on
scheduler luck. Two (or more) separate AsyncSession objects are driven
sequentially in Python code, each left OPEN (flushed, not committed) until
explicitly committed — from PostgreSQL's own point of view this
reproduces the exact "both readers see the same last-committed state
before either writer commits" interleaving deterministically, every run.

Proves, against a real Postgres:

  Case A — transactional vs. transactional: two concurrent
  `audit_staged()` calls, each on its own session, each reaching "flushed,
  not yet committed" before either commits — legitimate DAG topology,
  `verify_chain()` must return `True`.

  Case B — transactional vs. eager-independent: one `audit_staged()` call
  left uncommitted while a representative eager/independent `audit()`
  call (the existing, unmodified path) commits in between — same
  requirement.

  Case C — repeated execution: Case A run N times in a fresh throwaway
  database each time, to rule out one lucky/unlucky interleaving being
  mistaken for the general case.

  Negative controls, proving the verifier still rejects genuine defects
  (constructed via deliberately corrupted synthetic rows, inserted
  directly — GD-010 §9's own established technique for cycle/defect
  fixtures that cannot be cryptographically self-consistent by
  construction):

  D — a dangling predecessor (a row whose `prev_hash` matches no existing
      row and is not `GENESIS_HASH`) — `verify_chain()` must return `False`.

  E — a tampered hash (a row whose stored `hash` does not match
      `recompute_hash()`) — `verify_chain()` must return `False`.

  F — a cycle (two rows whose `prev_hash` values reference each other) —
      `verify_chain()` must return `False`, and must terminate (not hang).
"""
from __future__ import annotations

import os
import subprocess
import sys
import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.kernel import uow
from app.kernel.audit import (
    GENESIS_HASH,
    audit,
    configure_audit_store,
    configure_eager_fallback,
    reset_audit_store,
    verify_chain,
)
from app.kernel.audit_orm import AuditLogRecord
from app.kernel.audit_postgres import EagerPostgresAuditStore, PostgresAuditStore, audit_staged
from app.kernel.context import ExecutionContext, set_context

ADMIN_URL = os.environ.get("LIVE_TRANSACTIONAL_AUDIT_ADMIN_URL")

pytestmark = pytest.mark.skipif(
    not ADMIN_URL,
    reason=(
        "GD-009 Batch 1 audit-chain concurrency rehearsal — set "
        "LIVE_TRANSACTIONAL_AUDIT_ADMIN_URL to run against a real Postgres"
    ),
)


def _db_name() -> str:
    return f"landvault_live_txaudit_conc_{uuid.uuid4().hex[:12]}"


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


async def _seed_tenant_and_user(db_url: str) -> tuple[str, uuid.UUID]:
    tenant_id = f"tenant-{uuid.uuid4().hex[:8]}"
    user_id = uuid.uuid4()
    owning_engine: AsyncEngine = create_async_engine(db_url)
    try:
        async with owning_engine.begin() as conn:
            await conn.execute(
                sa.text("INSERT INTO tenants (id, name, status) VALUES (:id, :name, 'ACTIVE')"),
                {"id": tenant_id, "name": "Live TxAudit Concurrency Tenant"},
            )
            await conn.execute(
                sa.text(
                    "INSERT INTO identity_users "
                    "(id, identity_subject, email, full_name, country, tenant_id, roles) "
                    "VALUES (:id, :sub, :email, 'Live TxAudit Test User', 'NG', "
                    ":tenant_id, '[]'::jsonb)"
                ),
                {
                    "id": user_id,
                    "sub": f"kc-{user_id}",
                    "email": f"{user_id}@live-txaudit-test.invalid",
                    "tenant_id": tenant_id,
                },
            )
    finally:
        await owning_engine.dispose()
    return tenant_id, user_id


async def _chain_rows(db_url: str) -> list[AuditLogRecord]:
    # An ORM AsyncSession, not a raw Core Connection — Connection.execute()
    # against an ORM-mapped-class select does not perform entity hydration.
    verify_engine = create_async_engine(db_url)
    verify_sessionmaker = async_sessionmaker(verify_engine, expire_on_commit=False)
    try:
        async with verify_sessionmaker() as session:
            result = await session.execute(
                sa.select(AuditLogRecord).order_by(AuditLogRecord.created_at.asc())
            )
            return list(result.scalars().all())
    finally:
        await verify_engine.dispose()


async def _verify_chain_against(db_url: str) -> bool:
    """Runs the real, merged, DAG-aware verify_chain() against `db_url`'s
    actual audit_log table, using the same PostgresAuditStore/AuditStore
    resolution production uses — the actual governance-mandated proof,
    not a reimplementation of its logic."""
    session_factory = async_sessionmaker(create_async_engine(db_url), expire_on_commit=False)
    async with session_factory() as session:
        token = configure_audit_store(PostgresAuditStore(session))
        try:
            return await verify_chain()
        finally:
            reset_audit_store(token)


def _assert_dag_valid(result: bool, rows: list[AuditLogRecord], *, context: str) -> None:
    """The actual pass/fail assertion GD-009 §11/§15 requires under the
    accepted DAG architecture (ADR-030/GD-010/GD-011): the resulting graph
    must verify valid. A duplicate prev_hash among the rows is explicitly
    NOT a failure signal here — it is the expected shape of a legitimate
    concurrent fork; only `verify_chain()` returning `False` (a genuine
    hash/referential/cyclic defect) is."""
    assert result is True, (
        f"({context}): verify_chain() returned False against a real, legitimately "
        f"concurrent-written audit history — this DAG-aware verifier must accept a "
        f"shared-predecessor fork as valid, not misclassify it as corruption. Rows: "
        + "; ".join(
            f"[hash={r.hash[:12]}.. prev={r.prev_hash[:12]}.. action={r.action} "
            f"created_at={r.created_at.isoformat()}]"
            for r in rows
        )
    )


async def _case_a_transactional_vs_transactional(
    session_factory: async_sessionmaker[AsyncSession], ctx: ExecutionContext
) -> tuple[str, str]:
    """Two concurrent transaction-coupled audit_staged() calls, each on its
    own session, each flushed (not committed) before either commits —
    returns (prev_hash_a, prev_hash_b) as actually staged."""
    set_context(ctx)
    session_a = session_factory()
    session_b = session_factory()
    try:
        entry_a = await audit_staged(
            session_a,
            "registry.parcel.created",
            resource_type="parcel",
            resource_id=f"case-a-parcel-a-{uuid.uuid4().hex[:8]}",
            decision="PERMIT",
            payload={"case": "A", "side": "a"},
        )
        # session_a is now flushed (visible within its own transaction) but
        # NOT committed — session_b's own last_hash() read, through its own,
        # separate transaction, cannot see session_a's uncommitted row
        # (READ COMMITTED).
        entry_b = await audit_staged(
            session_b,
            "registry.parcel.created",
            resource_type="parcel",
            resource_id=f"case-a-parcel-b-{uuid.uuid4().hex[:8]}",
            decision="PERMIT",
            payload={"case": "A", "side": "b"},
        )
        await session_a.commit()
        await session_b.commit()
    finally:
        await session_a.close()
        await session_b.close()
    return entry_a.prev_hash, entry_b.prev_hash


async def _case_b_transactional_vs_eager(
    session_factory: async_sessionmaker[AsyncSession], ctx: ExecutionContext
) -> tuple[str, str]:
    """One audit_staged() call left uncommitted while a representative
    eager/independent audit() call (unmodified path) commits in between."""
    set_context(ctx)
    session_a = session_factory()
    try:
        entry_staged = await audit_staged(
            session_a,
            "registry.parcel.created",
            resource_type="parcel",
            resource_id=f"case-b-staged-{uuid.uuid4().hex[:8]}",
            decision="PERMIT",
            payload={"case": "B", "side": "staged"},
        )
        entry_eager = await audit(
            "authz.deny",
            resource_type="role_gate",
            decision="DENY",
            payload={"case": "B", "side": "eager"},
        )
        await session_a.commit()
    finally:
        await session_a.close()
    return entry_staged.prev_hash, entry_eager.prev_hash


@pytest.mark.asyncio
async def test_case_a_and_case_b_dag_validity_on_live_postgres() -> None:
    assert ADMIN_URL is not None  # guaranteed by pytestmark skipif above
    db_name = _db_name()
    await _create_throwaway_db(ADMIN_URL, db_name)
    db_url = _with_db(ADMIN_URL, db_name)
    try:
        _run_migrations(db_url)
        tenant_id, user_id = await _seed_tenant_and_user(db_url)
        ctx = ExecutionContext(principal_id=str(user_id), tenant_id=tenant_id, roles=())
        session_factory = await _app_session_factory(db_url)
        uow.configure_uow(session_factory)
        configure_eager_fallback(EagerPostgresAuditStore(session_factory))

        prev_a, prev_b = await _case_a_transactional_vs_transactional(session_factory, ctx)
        prev_staged, prev_eager = await _case_b_transactional_vs_eager(session_factory, ctx)

        rows = await _chain_rows(db_url)
        assert len(rows) == 4, f"expected exactly 4 committed audit rows, got {len(rows)}: {rows}"

        print(f"\n[Case A] prev_hash seen by A: {prev_a}")
        print(f"[Case A] prev_hash seen by B: {prev_b}")
        same = prev_a == prev_b
        print(f"[Case A] A and B saw the SAME prev_hash (a legitimate fork, if so): {same}")
        print(f"[Case B] prev_hash seen by staged call:  {prev_staged}")
        print(f"[Case B] prev_hash seen by eager call:   {prev_eager}")
        for row in rows:
            print(
                f"  committed row: hash={row.hash[:16]}.. prev_hash={row.prev_hash[:16]}.. "
                f"action={row.action} created_at={row.created_at.isoformat()}"
            )

        result = await _verify_chain_against(db_url)
        _assert_dag_valid(result, rows, context="Case A/B, single interleaving")
    finally:
        await _drop_throwaway_db(ADMIN_URL, db_name)


@pytest.mark.asyncio
async def test_case_c_repeated_dag_validity_on_live_postgres() -> None:
    """Case C — repeat Case A's controlled-barrier interleaving in N fresh
    throwaway databases, to rule out one run's result being an artifact of
    a single lucky/unlucky interleaving rather than the general case."""
    assert ADMIN_URL is not None  # guaranteed by pytestmark skipif above
    iterations = int(os.environ.get("LIVE_TRANSACTIONAL_AUDIT_CONCURRENCY_ITERATIONS", "5"))
    valid_results: list[bool] = []
    forked_count = 0
    for i in range(iterations):
        db_name = _db_name()
        await _create_throwaway_db(ADMIN_URL, db_name)
        db_url = _with_db(ADMIN_URL, db_name)
        try:
            _run_migrations(db_url)
            tenant_id, user_id = await _seed_tenant_and_user(db_url)
            ctx = ExecutionContext(principal_id=str(user_id), tenant_id=tenant_id, roles=())
            session_factory = await _app_session_factory(db_url)
            uow.configure_uow(session_factory)
            configure_eager_fallback(EagerPostgresAuditStore(session_factory))

            prev_a, prev_b = await _case_a_transactional_vs_transactional(session_factory, ctx)
            rows = await _chain_rows(db_url)
            forked = prev_a == prev_b and len(rows) == 2
            forked_count += int(forked)
            result = await _verify_chain_against(db_url)
            valid_results.append(result)
            print(
                f"[Case C] iteration {i + 1}/{iterations}: fork={forked} "
                f"verify_chain={result} (prev_a={prev_a[:12]}.., prev_b={prev_b[:12]}..)"
            )
        finally:
            await _drop_throwaway_db(ADMIN_URL, db_name)

    print(f"[Case C] {forked_count}/{iterations} iterations produced a legitimate fork")
    assert all(valid_results), (
        f"({forked_count}/{iterations} iterations forked; legitimate forks are expected and "
        f"must still verify valid): verify_chain() returned False for at least one iteration — "
        f"results: {valid_results}"
    )


@pytest.mark.asyncio
async def test_dangling_predecessor_rejected_on_live_postgres() -> None:
    """Negative control D: a row whose prev_hash matches no existing row
    and is not GENESIS_HASH must be rejected by the real, merged
    verify_chain() against a real database."""
    assert ADMIN_URL is not None
    db_name = _db_name()
    await _create_throwaway_db(ADMIN_URL, db_name)
    db_url = _with_db(ADMIN_URL, db_name)
    try:
        _run_migrations(db_url)
        session_factory = async_sessionmaker(create_async_engine(db_url), expire_on_commit=False)
        async with session_factory() as session:
            session.add(
                AuditLogRecord(
                    id=uuid.uuid4(),
                    action="test.dangling",
                    resource_type="test",
                    resource_id=None,
                    decision=None,
                    principal_id="usr_test",
                    payload={},
                    prev_hash="ab" * 32,  # matches no existing row; not GENESIS_HASH
                    hash="cd" * 32,
                    created_at=sa.func.now(),
                )
            )
            await session.commit()

        result = await _verify_chain_against(db_url)
        assert result is False, "a dangling predecessor must make verify_chain() return False"
    finally:
        await _drop_throwaway_db(ADMIN_URL, db_name)


@pytest.mark.asyncio
async def test_tampered_hash_rejected_on_live_postgres() -> None:
    """Negative control E: a row whose stored hash does not match its own
    recomputed hash must be rejected."""
    assert ADMIN_URL is not None
    db_name = _db_name()
    await _create_throwaway_db(ADMIN_URL, db_name)
    db_url = _with_db(ADMIN_URL, db_name)
    try:
        _run_migrations(db_url)
        session_factory = async_sessionmaker(create_async_engine(db_url), expire_on_commit=False)
        async with session_factory() as session:
            session.add(
                AuditLogRecord(
                    id=uuid.uuid4(),
                    action="test.tampered",
                    resource_type="test",
                    resource_id=None,
                    decision=None,
                    principal_id="usr_test",
                    payload={},
                    prev_hash=GENESIS_HASH,
                    hash="ff" * 32,  # deliberately unrelated to the content above
                    created_at=sa.func.now(),
                )
            )
            await session.commit()

        result = await _verify_chain_against(db_url)
        assert result is False, "a tampered/incorrect stored hash must make verify_chain() False"
    finally:
        await _drop_throwaway_db(ADMIN_URL, db_name)


@pytest.mark.asyncio
async def test_cycle_rejected_without_hanging_on_live_postgres() -> None:
    """Negative control F: two rows whose prev_hash values reference each
    other. A cryptographically self-consistent cycle is infeasible by
    construction (GD-010 §9) — this deliberately corrupted synthetic
    fixture (both rows' stored hash is fabricated, not recomputed) proves
    the verifier terminates safely and rejects the cycle, without asserting
    that cycle-detection specifically (as opposed to hash-validity) is what
    fires first, exactly as GD-010 §9's "Validation order" clause permits."""
    assert ADMIN_URL is not None
    db_name = _db_name()
    await _create_throwaway_db(ADMIN_URL, db_name)
    db_url = _with_db(ADMIN_URL, db_name)
    try:
        _run_migrations(db_url)
        hash_a, hash_b = "11" * 32, "22" * 32
        session_factory = async_sessionmaker(create_async_engine(db_url), expire_on_commit=False)
        async with session_factory() as session:
            session.add(
                AuditLogRecord(
                    id=uuid.uuid4(),
                    action="test.cycle.a",
                    resource_type="test",
                    resource_id=None,
                    decision=None,
                    principal_id="usr_test",
                    payload={},
                    prev_hash=hash_b,
                    hash=hash_a,
                    created_at=sa.func.now(),
                )
            )
            session.add(
                AuditLogRecord(
                    id=uuid.uuid4(),
                    action="test.cycle.b",
                    resource_type="test",
                    resource_id=None,
                    decision=None,
                    principal_id="usr_test",
                    payload={},
                    prev_hash=hash_a,
                    hash=hash_b,
                    created_at=sa.func.now(),
                )
            )
            await session.commit()

        result = await _verify_chain_against(db_url)
        assert result is False, "a two-node cycle must make verify_chain() return False"
    finally:
        await _drop_throwaway_db(ADMIN_URL, db_name)
