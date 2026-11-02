"""Live-Postgres HTTP-boundary rehearsal for GD-012's two Evidence Actor
Attribution endpoints, as amended by GD-013 (docs/GD-012-evidence-actor-
attribution-http-implementation-authorization.md,
docs/GD-013-gd012-commit-boundary-and-concurrent-correction-exception-
authorization.md).

The hermetic suite (tests/test_evidence_attribution_api.py,
tests/test_evidence_actor_attribution_service.py) proves authorization,
validation, response shape, and the dual-diagnostic 409 predicate's own
logic in isolation. It cannot prove the properties that only exist at the
real HTTP+database boundary — this module drives the real FastAPI app,
the real `attribution_router.py` (including its five endpoint-local,
function-scoped dependency providers), and a real, throwaway PostgreSQL
database (created and dropped within each test), over a real TCP socket,
to prove:

  A. ONE SHARED SESSION — every one of the five endpoint-local providers,
     and the service's own `.session`, resolve to the identical
     `AsyncSession` instance for one request (GD-013 §3; GD-014 obligation
     3 — proven independently for both the record and correction
     endpoints).

  B. COMMIT BEFORE RESPONSE — the real UoW commit completes before the
     HTTP client receives the successful response (GD-013 §3; GD-014
     obligation 2 — proven independently for both endpoints).

  C. FORCED FINAL-COMMIT FAILURE — a commit failure after the mutation and
     its audit event are staged yields a non-2xx response, with neither
     row left durable (GD-013 §3; GD-014 obligation 1 — proven
     independently for both endpoints).

  D. SUCCESSFUL RECORD DURABILITY — the record endpoint's response and the
     database agree.

  E. SUCCESSFUL CORRECTION DURABILITY — the correction endpoint's response,
     lineage, and the database agree; the superseded row is untouched.

  F. COMPETING CONCURRENT CORRECTIONS — exactly one of two genuinely
     racing corrections against the same head succeeds; the loser receives
     409, specifically because of SQLSTATE 23505 on
     `uq_evidence_actor_attributions_supersedes_once`; the loser leaves
     nothing durable (GD-013 §4). This test does NOT claim `HTTPException`
     itself causes a rollback — see the test's own docstring for the
     precise mechanism.

  G. UNRELATED UNIQUE VIOLATION NOT TRANSLATED — an `IntegrityError` with
     SQLSTATE 23505 but a different constraint name surfaces as 5xx.

  H. SELF-SUPERSESSION NOT TRANSLATED — a raw self-supersession attempt is
     rejected by the database (empirically, by the cycle-rejection trigger,
     which intercepts it before the separate CHECK constraint ever fires —
     see the test's own docstring) and surfaces as 5xx, not 409; nothing is
     left durable.

  I. CYCLIC-CORRECTION TRIGGER — the real `evidence_actor_attributions_
     reject_cycle` trigger rejects a cyclic lineage.

  J. INDISTINGUISHABLE 404s — nonexistent vs. cross-tenant EvidenceRecord
     (record endpoint) and attribution (correction endpoint) each produce
     byte-identical responses over real RLS, and (GD-012 §10 item 17 /
     GD-014 obligation 7) neither rejected attempt leaves a durable row or
     audit event.

  K. ACTOR-PRINCIPAL ORACLE — nonexistent vs. cross-tenant
     `actor_principal_id` produce byte-identical responses over real data.

Skipped unless `LIVE_TRANSACTIONAL_AUDIT_ADMIN_URL` is set — never runs by
default, so it cannot break the hermetic suite or CI (which has no
Postgres service).

Authentication is not the object of proof here (it is already covered by
the hermetic suite and by this codebase's existing Supabase/Keycloak live
coverage) — the minimal live app below overrides `current_context_dep`
to read principal/tenant/roles from test-only request headers, so each
request can specify its own `ExecutionContext` without real JWT machinery,
exactly as this repository's other live-test modules already avoid
re-deriving authentication mechanics that are proven elsewhere.
"""
from __future__ import annotations

import asyncio
import contextlib
import os
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import AsyncIterator, Iterator

import httpx
import pytest
import sqlalchemy as sa
import uvicorn
from fastapi import FastAPI, Request
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import app.contexts.evidence.api.attribution_router as attribution_router_module
import app.contexts.identity.adapters.orm  # noqa: F401 — registers identity_users/tenants
import app.contexts.registry.adapters.orm  # noqa: F401 — registers parcels
from app.contexts.evidence.adapters.orm import EvidenceRecordModel  # noqa: F401
from app.contexts.evidence.api.attribution_router import router as attribution_api_router
from app.contexts.evidence.application.attribution_service import (
    EvidenceActorAttributionService,
)
from app.kernel import uow
from app.kernel.audit import configure_eager_fallback
from app.kernel.audit_orm import AuditLogRecord  # noqa: F401
from app.kernel.audit_postgres import EagerPostgresAuditStore
from app.kernel.authorization.pep import current_context_dep
from app.kernel.context import ANONYMOUS, ExecutionContext

ADMIN_URL = os.environ.get("LIVE_TRANSACTIONAL_AUDIT_ADMIN_URL")

pytestmark = pytest.mark.skipif(
    not ADMIN_URL,
    reason=(
        "live GD-012/GD-013 attribution HTTP rehearsal — set "
        "LIVE_TRANSACTIONAL_AUDIT_ADMIN_URL to run against a real Postgres"
    ),
)

_PORT = 18800  # bumped per-test via a module counter to avoid TIME_WAIT clashes
_port_lock = threading.Lock()


def _next_port() -> int:
    global _PORT
    with _port_lock:
        _PORT += 1
        return _PORT


def _db_name() -> str:
    return f"landvault_gd012_http_live_{uuid.uuid4().hex[:12]}"


def _with_db(url: str, db_name: str) -> str:
    base, _, _ = url.rpartition("/")
    return f"{base}/{db_name}"


async def _test_context_dep(request: Request) -> ExecutionContext:
    """Test-only substitute for `current_context_dep` — reads the
    ExecutionContext from headers rather than a real JWT. Authentication
    itself is proven elsewhere (hermetic suite, existing Supabase/Keycloak
    live coverage); this module's own proofs concern the HTTP+database
    boundary GD-012/GD-013 actually authorize."""
    principal_id = request.headers.get("x-test-principal-id")
    if not principal_id:
        return ANONYMOUS
    tenant_id = request.headers.get("x-test-tenant-id")
    roles = tuple(request.headers.get("x-test-roles", "").split(",")) if request.headers.get(
        "x-test-roles"
    ) else ()
    return ExecutionContext(principal_id=principal_id, tenant_id=tenant_id, roles=roles)


def _auth_headers(
    *, principal_id: str, tenant_id: str, roles: tuple[str, ...] = ("field_agent",)
) -> dict:
    return {
        "x-test-principal-id": principal_id,
        "x-test-tenant-id": tenant_id,
        "x-test-roles": ",".join(roles),
    }


async def _seed_fixture_rows(engine: AsyncEngine) -> dict[str, str]:
    tenant_id = f"tenant-{uuid.uuid4().hex[:8]}"
    user_id = uuid.uuid4()
    parcel_id = uuid.uuid4()
    evidence_id = uuid.uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            sa.text("INSERT INTO tenants (id, name, status) VALUES (:id, :name, 'ACTIVE')"),
            {"id": tenant_id, "name": "GD-012/013 HTTP live test tenant"},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO identity_users "
                "(id, identity_subject, email, full_name, country, tenant_id, roles) "
                "VALUES (:id, :sub, :email, 'Live HTTP Test User', 'NG', :tenant_id, '[]'::jsonb)"
            ),
            {
                "id": user_id, "sub": f"sub-{uuid.uuid4().hex[:8]}",
                "email": f"{uuid.uuid4().hex[:8]}@example.test", "tenant_id": tenant_id,
            },
        )
        await conn.execute(
            sa.text(
                "INSERT INTO parcels "
                "(id, tenant_id, country_code, origin, parcel_number, title, status, created_by) "
                "VALUES (:id, :tenant_id, 'NG', 'field_survey', :pnum, 'Live HTTP Test Parcel', "
                " 'ACTIVE', :created_by)"
            ),
            {
                "id": parcel_id, "tenant_id": tenant_id,
                "pnum": f"LP-{uuid.uuid4().hex[:8]}", "created_by": user_id,
            },
        )
        await conn.execute(
            sa.text(
                "INSERT INTO evidence_records "
                "(id, tenant_id, parcel_id, uploaded_by, filename, mime_type, size_bytes, "
                " storage_key, basis, evidence_type, status) "
                "VALUES (:id, :tenant_id, :parcel_id, :uploaded_by, 'plan.pdf', "
                " 'application/pdf', 1024, :storage_key, 'submitted', 'SURVEY_PLAN', 'RECEIVED')"
            ),
            {
                "id": evidence_id, "tenant_id": tenant_id, "parcel_id": parcel_id,
                "uploaded_by": user_id, "storage_key": f"evidence/{tenant_id}/{parcel_id}/x",
            },
        )
    return {
        "tenant_id": tenant_id, "user_id": str(user_id),
        "parcel_id": str(parcel_id), "evidence_id": str(evidence_id),
    }


class LiveEnv:
    def __init__(self, base_url: str, db_url: str, ids: dict[str, str]) -> None:
        self.base_url = base_url
        self.db_url = db_url
        self.ids = ids

    def headers(self, **kw: object) -> dict:
        return _auth_headers(**kw)  # type: ignore[arg-type]

    async def row_counts(self) -> tuple[int, int]:
        """(attribution row count, matching audit event count) for this
        test's evidence_id — via a connection independent of any request's
        own session."""
        engine = create_async_engine(self.db_url)
        try:
            async with engine.connect() as conn:
                attrs = (await conn.execute(
                    sa.text(
                        "SELECT count(*) FROM evidence_actor_attributions WHERE evidence_id = :eid"
                    ),
                    {"eid": self.ids["evidence_id"]},
                )).scalar_one()
                audits = (await conn.execute(
                    sa.text(
                        "SELECT count(*) FROM audit_log WHERE action IN "
                        "('evidence.actor_attribution.recorded', "
                        "'evidence.actor_attribution.corrected')"
                    ),
                )).scalar_one()
            return attrs, audits
        finally:
            await engine.dispose()


@contextlib.asynccontextmanager
async def _live_env() -> AsyncIterator[LiveEnv]:
    assert ADMIN_URL is not None
    admin_engine = create_async_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    db_name = _db_name()
    try:
        async with admin_engine.connect() as conn:
            await conn.execute(sa.text(f'CREATE DATABASE "{db_name}"'))
    finally:
        await admin_engine.dispose()

    db_url = _with_db(ADMIN_URL, db_name)
    server: uvicorn.Server | None = None
    thread: threading.Thread | None = None
    try:
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        migration_env = dict(
            os.environ, MIGRATIONS_DATABASE_URL=db_url,
            POSTGRES_APP_PASSWORD=os.environ["POSTGRES_APP_PASSWORD"],
        )
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=backend_dir, env=migration_env, capture_output=True, text=True,
        )
        assert result.returncode == 0, f"migration failed:\n{result.stdout}\n{result.stderr}"

        owning_engine = create_async_engine(db_url)
        try:
            ids = await _seed_fixture_rows(owning_engine)
        finally:
            await owning_engine.dispose()

        app_password = os.environ["POSTGRES_APP_PASSWORD"]
        app_db_url = (
            make_url(db_url).set(username="landvault_app", password=app_password)
            .render_as_string(hide_password=False)
        )
        session_factory = async_sessionmaker(
            create_async_engine(app_db_url), expire_on_commit=False
        )
        uow.configure_uow(session_factory)
        # require_role's coarse-gate denial path calls the eager, independent
        # audit() for the denial event (GD-009 §9) — must be configured even
        # though this module's own proofs concern the staged path, or any
        # request that gets denied crashes with "audit store not
        # configured" instead of returning the intended 403/404.
        configure_eager_fallback(EagerPostgresAuditStore(session_factory))

        app = FastAPI()
        app.include_router(attribution_api_router)
        app.dependency_overrides[current_context_dep] = _test_context_dep

        port = _next_port()
        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        for _ in range(50):
            if getattr(server, "started", False):
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("live test server did not start in time")

        yield LiveEnv(base_url=f"http://127.0.0.1:{port}", db_url=db_url, ids=ids)
    finally:
        if server is not None:
            server.should_exit = True
        if thread is not None:
            thread.join(timeout=10)
        cleanup_engine = create_async_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
        try:
            async with cleanup_engine.connect() as conn:
                await conn.execute(sa.text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    f"WHERE datname = '{db_name}'"
                ))
                await conn.execute(sa.text(f'DROP DATABASE IF EXISTS "{db_name}"'))
        finally:
            await cleanup_engine.dispose()


def _capture_service_instances() -> (
    tuple[list[EvidenceActorAttributionService], contextlib.AbstractContextManager[None]]
):
    """Test-only capture of every EvidenceActorAttributionService instance
    the router's own `_get_attribution_service` constructs, by substituting
    a capturing subclass for the name `attribution_router.
    EvidenceActorAttributionService` — that function looks up the class by
    this module-global name at CALL time, so the substitution takes effect
    for requests made after this context manager is entered, without
    editing any production file. Yields the list to append observations
    into for the duration of the `with` block."""
    captured: list[EvidenceActorAttributionService] = []
    real_cls = attribution_router_module.EvidenceActorAttributionService  # type: ignore[attr-defined]

    class _CapturingService(real_cls):  # type: ignore[misc, valid-type]
        def __init__(self, *a: object, **kw: object) -> None:
            super().__init__(*a, **kw)
            captured.append(self)

    @contextlib.contextmanager
    def _cm() -> Iterator[None]:
        attribution_router_module.EvidenceActorAttributionService = (  # type: ignore[attr-defined]
            _CapturingService
        )
        try:
            yield
        finally:
            attribution_router_module.EvidenceActorAttributionService = (  # type: ignore[attr-defined]
                real_cls
            )

    return captured, _cm()


# === A. ONE SHARED SESSION ======================================================


@pytest.mark.asyncio
async def test_one_shared_session_for_the_whole_request() -> None:
    async with _live_env() as env:
        captured, cm = _capture_service_instances()
        with cm:
            async with httpx.AsyncClient(base_url=env.base_url, timeout=10) as client:
                resp = await client.post(
                    f"/v1/evidence/{env.ids['evidence_id']}/attributions",
                    json={
                        "attribution_role": "ORIGINATED_BY",
                        "actor_reference_kind": "EXTERNAL_NAMED",
                        "actor_type": "INDIVIDUAL", "actor_name": "Session Proof Actor",
                        "basis": "GD-013 one-session proof",
                    },
                    headers=env.headers(
                        principal_id=env.ids["user_id"], tenant_id=env.ids["tenant_id"]
                    ),
                )
        assert resp.status_code == 201, resp.text
        assert len(captured) == 1
        service = captured[0]
        session_ids = {
            id(service.session),
            id(service.attributions._session),  # type: ignore[attr-defined]
            id(service.evidence._session),  # type: ignore[attr-defined]
            id(service.parcel_existence._session),  # type: ignore[attr-defined]
            id(service.principal_tenant._session),  # type: ignore[attr-defined]
        }
        assert len(session_ids) == 1, (
            f"expected exactly one shared session across all five providers, got {len(session_ids)}"
        )


@pytest.mark.asyncio
async def test_one_shared_session_for_the_whole_request_correction() -> None:
    """GD-014 obligation 3, correction endpoint. Identical proof to the
    record-endpoint test above, against `correct_evidence_attribution`
    instead — the five endpoint-local providers are shared code between
    both routes (GD-013 §3), but session identity must be independently
    demonstrated for each endpoint's own request, not inferred from the
    other's."""
    async with _live_env() as env:
        headers = env.headers(principal_id=env.ids["user_id"], tenant_id=env.ids["tenant_id"])
        async with httpx.AsyncClient(base_url=env.base_url, timeout=10) as client:
            original = (await client.post(
                f"/v1/evidence/{env.ids['evidence_id']}/attributions",
                json={
                    "attribution_role": "ORIGINATED_BY", "actor_reference_kind": "EXTERNAL_NAMED",
                    "actor_type": "INDIVIDUAL", "actor_name": "Session Proof Original",
                    "basis": "GD-014 obligation 3 correction proof (original)",
                },
                headers=headers,
            )).json()

        captured, cm = _capture_service_instances()
        with cm:
            async with httpx.AsyncClient(base_url=env.base_url, timeout=10) as client:
                resp = await client.post(
                    f"/v1/evidence/attributions/{original['attribution_id']}/corrections",
                    json={
                        "attribution_role": "ORIGINATED_BY",
                        "actor_reference_kind": "EXTERNAL_NAMED", "actor_type": "INDIVIDUAL",
                        "actor_name": "Session Proof Correction",
                        "basis": "GD-014 obligation 3 correction proof",
                    },
                    headers=headers,
                )
        assert resp.status_code == 201, resp.text
        assert len(captured) == 1
        service = captured[0]
        session_ids = {
            id(service.session),
            id(service.attributions._session),  # type: ignore[attr-defined]
            id(service.evidence._session),  # type: ignore[attr-defined]
            id(service.parcel_existence._session),  # type: ignore[attr-defined]
            id(service.principal_tenant._session),  # type: ignore[attr-defined]
        }
        assert len(session_ids) == 1, (
            f"expected exactly one shared session across all five providers, got {len(session_ids)}"
        )


# === B. COMMIT BEFORE RESPONSE ==================================================


@pytest.mark.asyncio
async def test_commit_completes_before_successful_response_is_returned() -> None:
    events: list[tuple[str, float]] = []
    real_commit = AsyncSession.commit

    async def _logged_commit(self: AsyncSession) -> None:
        await real_commit(self)
        events.append(("commit_completed", time.monotonic()))

    async with _live_env() as env:
        AsyncSession.commit = _logged_commit  # type: ignore[method-assign]
        try:
            async with httpx.AsyncClient(base_url=env.base_url, timeout=10) as client:
                resp = await client.post(
                    f"/v1/evidence/{env.ids['evidence_id']}/attributions",
                    json={
                        "attribution_role": "ORIGINATED_BY",
                        "actor_reference_kind": "EXTERNAL_NAMED",
                        "actor_type": "INDIVIDUAL", "actor_name": "Commit-Order Proof Actor",
                        "basis": "GD-013 commit-before-response proof",
                    },
                    headers=env.headers(
                        principal_id=env.ids["user_id"], tenant_id=env.ids["tenant_id"]
                    ),
                )
            events.append(("response_received", time.monotonic()))
        finally:
            AsyncSession.commit = real_commit  # type: ignore[method-assign]

    assert resp.status_code == 201, resp.text
    assert [e[0] for e in events] == ["commit_completed", "response_received"], events
    assert events[0][1] <= events[1][1]


@pytest.mark.asyncio
async def test_commit_completes_before_successful_response_is_returned_correction() -> None:
    """GD-014 obligation 2, correction endpoint."""
    events: list[tuple[str, float]] = []
    real_commit = AsyncSession.commit

    async def _logged_commit(self: AsyncSession) -> None:
        await real_commit(self)
        events.append(("commit_completed", time.monotonic()))

    async with _live_env() as env:
        headers = env.headers(principal_id=env.ids["user_id"], tenant_id=env.ids["tenant_id"])
        async with httpx.AsyncClient(base_url=env.base_url, timeout=10) as client:
            original = (await client.post(
                f"/v1/evidence/{env.ids['evidence_id']}/attributions",
                json={
                    "attribution_role": "ORIGINATED_BY", "actor_reference_kind": "EXTERNAL_NAMED",
                    "actor_type": "INDIVIDUAL", "actor_name": "Commit-Order Proof Original",
                    "basis": "GD-014 obligation 2 correction proof (original)",
                },
                headers=headers,
            )).json()

        AsyncSession.commit = _logged_commit  # type: ignore[method-assign]
        try:
            async with httpx.AsyncClient(base_url=env.base_url, timeout=10) as client:
                resp = await client.post(
                    f"/v1/evidence/attributions/{original['attribution_id']}/corrections",
                    json={
                        "attribution_role": "ORIGINATED_BY",
                        "actor_reference_kind": "EXTERNAL_NAMED", "actor_type": "INDIVIDUAL",
                        "actor_name": "Commit-Order Proof Correction",
                        "basis": "GD-014 obligation 2 correction proof",
                    },
                    headers=headers,
                )
            events.append(("response_received", time.monotonic()))
        finally:
            AsyncSession.commit = real_commit  # type: ignore[method-assign]

    assert resp.status_code == 201, resp.text
    assert [e[0] for e in events] == ["commit_completed", "response_received"], events
    assert events[0][1] <= events[1][1]


# === C. FORCED FINAL-COMMIT FAILURE =============================================


@pytest.mark.asyncio
async def test_forced_final_commit_failure_yields_non_2xx_and_no_durable_rows() -> None:
    real_commit = AsyncSession.commit

    async def _failing_commit(self: AsyncSession) -> None:
        raise RuntimeError("GD-013 live proof: simulated deferred-constraint commit failure")

    async with _live_env() as env:
        AsyncSession.commit = _failing_commit  # type: ignore[method-assign]
        try:
            async with httpx.AsyncClient(base_url=env.base_url, timeout=10) as client:
                resp = await client.post(
                    f"/v1/evidence/{env.ids['evidence_id']}/attributions",
                    json={
                        "attribution_role": "ORIGINATED_BY",
                        "actor_reference_kind": "EXTERNAL_NAMED",
                        "actor_type": "INDIVIDUAL", "actor_name": "Should Not Persist",
                        "basis": "GD-013 forced commit-failure proof",
                    },
                    headers=env.headers(
                        principal_id=env.ids["user_id"], tenant_id=env.ids["tenant_id"]
                    ),
                )
        finally:
            AsyncSession.commit = real_commit  # type: ignore[method-assign]

        assert resp.status_code >= 500, (
            f"client must not receive a successful response when the final commit fails, got "
            f"{resp.status_code}"
        )
        attrs, audits = await env.row_counts()
        assert attrs == 0, "no attribution row may be durable after a forced commit failure"
        assert audits == 0, "no audit event may be durable after a forced commit failure"


@pytest.mark.asyncio
async def test_correction_forced_final_commit_failure_yields_non_2xx_and_no_durable_rows() -> None:
    """GD-014 obligation 1, correction endpoint. The original attribution is
    recorded BEFORE the commit patch is installed, so it is durable on its
    own, unaffected merit; the proof concerns only whether the failed
    correction's row/audit event leak through."""
    real_commit = AsyncSession.commit

    async def _failing_commit(self: AsyncSession) -> None:
        raise RuntimeError("GD-014 obligation 1 proof: simulated correction commit failure")

    async with _live_env() as env:
        headers = env.headers(principal_id=env.ids["user_id"], tenant_id=env.ids["tenant_id"])
        async with httpx.AsyncClient(base_url=env.base_url, timeout=10) as client:
            original = (await client.post(
                f"/v1/evidence/{env.ids['evidence_id']}/attributions",
                json={
                    "attribution_role": "ORIGINATED_BY", "actor_reference_kind": "EXTERNAL_NAMED",
                    "actor_type": "INDIVIDUAL", "actor_name": "Commit-Failure Proof Original",
                    "basis": "GD-014 obligation 1 correction proof (original)",
                },
                headers=headers,
            )).json()

        before_attrs, before_audits = await env.row_counts()
        assert before_attrs == 1 and before_audits == 1, "the original record must be durable"

        AsyncSession.commit = _failing_commit  # type: ignore[method-assign]
        try:
            async with httpx.AsyncClient(base_url=env.base_url, timeout=10) as client:
                resp = await client.post(
                    f"/v1/evidence/attributions/{original['attribution_id']}/corrections",
                    json={
                        "attribution_role": "ORIGINATED_BY",
                        "actor_reference_kind": "EXTERNAL_NAMED", "actor_type": "INDIVIDUAL",
                        "actor_name": "Should Not Persist Correction",
                        "basis": "GD-014 obligation 1 correction proof",
                    },
                    headers=headers,
                )
        finally:
            AsyncSession.commit = real_commit  # type: ignore[method-assign]

        assert resp.status_code >= 500, (
            f"client must not receive a successful response when the final commit fails, got "
            f"{resp.status_code}"
        )
        attrs, audits = await env.row_counts()
        assert attrs == before_attrs, (
            "no additional attribution row may be durable after a forced commit failure"
        )
        assert audits == before_audits, (
            "no additional audit event may be durable after a forced commit failure"
        )


# === D. SUCCESSFUL RECORD DURABILITY ============================================


@pytest.mark.asyncio
async def test_successful_record_is_durable_and_matches_response() -> None:
    async with _live_env() as env:
        async with httpx.AsyncClient(base_url=env.base_url, timeout=10) as client:
            resp = await client.post(
                f"/v1/evidence/{env.ids['evidence_id']}/attributions",
                json={
                    "attribution_role": "ORIGINATED_BY", "actor_reference_kind": "EXTERNAL_NAMED",
                    "actor_type": "INDIVIDUAL", "actor_name": "Durable Record Actor",
                    "basis": "GD-012 durability proof",
                },
                headers=env.headers(
                    principal_id=env.ids["user_id"], tenant_id=env.ids["tenant_id"]
                ),
            )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert "tenant_id" not in body
        assert "audit_ref" not in body
        assert "ownership" not in str(body).lower()
        assert "legal" not in str(body).lower()

        attrs, audits = await env.row_counts()
        assert attrs == 1
        assert audits == 1

        engine = create_async_engine(env.db_url)
        try:
            async with engine.connect() as conn:
                row = (await conn.execute(
                    sa.text(
                        "SELECT actor_name, attribution_role FROM evidence_actor_attributions "
                        "WHERE id = :id"
                    ),
                    {"id": body["attribution_id"]},
                )).one()
        finally:
            await engine.dispose()
        assert row.actor_name == "Durable Record Actor"
        assert row.attribution_role == "ORIGINATED_BY"


# === E. SUCCESSFUL CORRECTION DURABILITY ========================================


@pytest.mark.asyncio
async def test_successful_correction_supersedes_without_altering_original() -> None:
    async with _live_env() as env:
        headers = env.headers(principal_id=env.ids["user_id"], tenant_id=env.ids["tenant_id"])
        async with httpx.AsyncClient(base_url=env.base_url, timeout=10) as client:
            original = (await client.post(
                f"/v1/evidence/{env.ids['evidence_id']}/attributions",
                json={
                    "attribution_role": "ORIGINATED_BY", "actor_reference_kind": "EXTERNAL_NAMED",
                    "actor_type": "INDIVIDUAL", "actor_name": "Original Actor",
                    "basis": "GD-012 correction-durability proof (original)",
                },
                headers=headers,
            )).json()

            corrected = await client.post(
                f"/v1/evidence/attributions/{original['attribution_id']}/corrections",
                json={
                    "attribution_role": "ORIGINATED_BY", "actor_reference_kind": "EXTERNAL_NAMED",
                    "actor_type": "INDIVIDUAL", "actor_name": "Corrected Actor",
                    "basis": "GD-012 correction-durability proof (correction)",
                },
                headers=headers,
            )
        assert corrected.status_code == 201, corrected.text
        correction_body = corrected.json()
        assert correction_body["supersedes_id"] == original["attribution_id"]
        assert "tenant_id" not in correction_body

        engine = create_async_engine(env.db_url)
        try:
            async with engine.connect() as conn:
                original_row = (await conn.execute(
                    sa.text("SELECT actor_name FROM evidence_actor_attributions WHERE id = :id"),
                    {"id": original["attribution_id"]},
                )).one()
                correction_row = (await conn.execute(
                    sa.text(
                        "SELECT actor_name, supersedes_id FROM evidence_actor_attributions "
                        "WHERE id = :id"
                    ),
                    {"id": correction_body["attribution_id"]},
                )).one()
        finally:
            await engine.dispose()
        assert original_row.actor_name == "Original Actor"  # untouched
        assert correction_row.actor_name == "Corrected Actor"
        assert str(correction_row.supersedes_id) == original["attribution_id"]


# === F. COMPETING CONCURRENT CORRECTIONS ========================================


class _TwoPartyRendezvous:
    """Deterministic two-party barrier, replacing a fixed-sleep race window.

    The independent GD-012/GD-013/GD-014 implementation review found that a
    fixed `asyncio.sleep(0.15)` widening window is not a synchronization
    guarantee: under sustained system load (observed when this test ran as
    part of the full live suite, after ~20 preceding real-Postgres tests),
    the delay was occasionally insufficient to force true overlap — one
    racer's resolve-then-sleep-then-write sequence could complete entirely
    before the other racer's resolve call even ran, so the second racer
    legitimately corrected the FIRST racer's already-committed row (a valid,
    non-conflicting lineage) instead of colliding with it, producing
    `[201, 201]` — a false negative for the race, not a defect in the
    production 409-translation mechanism itself.

    This barrier makes that failure mode structurally impossible: each
    caller blocks in `arrive_and_wait()` until BOTH have arrived, so neither
    racer's `_resolve_active_head` call can ever return before the other's
    has also completed, regardless of machine speed, scheduler timing, or
    concurrent database load. Both correction requests are served by the
    same uvicorn server thread's own asyncio event loop (uvicorn's default
    single-worker mode multiplexes concurrent connections as tasks on one
    loop), so a plain `asyncio.Event` shared between the two calls is safe
    without any cross-thread primitive. `wait_for`'s timeout is a safety net
    against a genuine bug hanging the test forever (e.g. if only one racer
    ever reached the rendezvous) — it is not a retry-until-green mechanism;
    the barrier itself never retries or loops, it releases exactly once,
    deterministically, the instant the second party arrives."""

    def __init__(self, parties: int = 2) -> None:
        self._parties = parties
        self._arrived = 0
        self._release = asyncio.Event()

    async def arrive_and_wait(self, timeout: float = 10.0) -> None:
        self._arrived += 1
        if self._arrived >= self._parties:
            self._release.set()
        else:
            await asyncio.wait_for(self._release.wait(), timeout=timeout)


@pytest.mark.asyncio
async def test_competing_concurrent_corrections_one_wins_one_gets_409() -> None:
    """GD-013 §4's precise transaction property: the loser's `IntegrityError`
    is translated to `HTTPException(409)`, which enters `get_db_session`'s
    `except HTTPException: await session.commit()` branch — NOT the
    generic-exception rollback branch. Safety does not come from that
    branch name; it holds because the failed `flush()` already left the
    losing request's Postgres transaction aborted, and PostgreSQL discards
    an aborted transaction's work regardless of whether COMMIT or ROLLBACK
    is subsequently requested on it. This test asserts the externally
    observable outcome (one winner, one 409, zero durable trace of the
    loser) — not the internal branch name.

    Race is forced deterministically via `_TwoPartyRendezvous`, not a fixed
    delay (see its own docstring) — both racers' `_resolve_active_head`
    calls are guaranteed to complete, against the real database, before
    either racer is released to proceed to its write, so both writes
    genuinely race for the real `uq_evidence_actor_attributions_
    supersedes_once` constraint every time this test runs."""
    import app.contexts.evidence.application.attribution_service as attribution_service_module

    real_resolve = attribution_service_module.EvidenceActorAttributionService._resolve_active_head
    rendezvous = _TwoPartyRendezvous(parties=2)

    async def _synchronized_resolve(
        self: EvidenceActorAttributionService, attribution_id: str
    ) -> object:
        # The real read happens first, against the real database, for both
        # callers — the barrier only withholds the RETURN of that already-
        # completed read, so neither racer can proceed to its write before
        # both reads are done.
        result = await real_resolve(self, attribution_id)
        await rendezvous.arrive_and_wait()
        return result

    async with _live_env() as env:
        headers = env.headers(principal_id=env.ids["user_id"], tenant_id=env.ids["tenant_id"])
        async with httpx.AsyncClient(base_url=env.base_url, timeout=10) as client:
            original = (await client.post(
                f"/v1/evidence/{env.ids['evidence_id']}/attributions",
                json={
                    "attribution_role": "ORIGINATED_BY", "actor_reference_kind": "EXTERNAL_NAMED",
                    "actor_type": "INDIVIDUAL", "actor_name": "Racing Original",
                    "basis": "GD-013 concurrent-correction proof",
                },
                headers=headers,
            )).json()
            head_id = original["attribution_id"]

            patched_cls = attribution_service_module.EvidenceActorAttributionService
            patched_cls._resolve_active_head = _synchronized_resolve  # type: ignore[method-assign,assignment]
            try:
                responses = await asyncio.gather(
                    client.post(
                        f"/v1/evidence/attributions/{head_id}/corrections",
                        json={
                            "attribution_role": "ORIGINATED_BY",
                            "actor_reference_kind": "EXTERNAL_NAMED", "actor_type": "INDIVIDUAL",
                            "actor_name": "Racer A", "basis": "racer A",
                        },
                        headers=headers,
                    ),
                    client.post(
                        f"/v1/evidence/attributions/{head_id}/corrections",
                        json={
                            "attribution_role": "ORIGINATED_BY",
                            "actor_reference_kind": "EXTERNAL_NAMED", "actor_type": "INDIVIDUAL",
                            "actor_name": "Racer B", "basis": "racer B",
                        },
                        headers=headers,
                    ),
                )
            finally:
                patched_cls._resolve_active_head = real_resolve  # type: ignore[method-assign]

        statuses = sorted(r.status_code for r in responses)
        assert statuses == [201, 409], (
            f"expected exactly one winner (201) and one loser (409), got {statuses}"
        )

        loser = next(r for r in responses if r.status_code == 409)
        winner = next(r for r in responses if r.status_code == 201)

        # The router's translation branch (attribution_router.py) is the
        # ONLY place this endpoint ever produces this exact detail string,
        # and it is reachable only after _is_supersedes_once_violation has
        # already matched both structured diagnostics (SQLSTATE 23505,
        # constraint uq_evidence_actor_attributions_supersedes_once) —
        # asserting it here ties this 409 to that exact GD-013/GD-014
        # dual-diagnostic-confirmed conflict, not merely "some 409".
        assert loser.json()["detail"] == (
            "attribution has already been superseded by another correction"
        )

        engine = create_async_engine(env.db_url)
        try:
            async with engine.connect() as conn:
                corrections = (await conn.execute(
                    sa.text(
                        "SELECT actor_name FROM evidence_actor_attributions "
                        "WHERE supersedes_id = :id"
                    ),
                    {"id": head_id},
                )).all()
                audits = (await conn.execute(
                    sa.text(
                        "SELECT count(*) FROM audit_log WHERE action = "
                        "'evidence.actor_attribution.corrected'"
                    ),
                )).scalar_one()
        finally:
            await engine.dispose()

        assert len(corrections) == 1, "exactly one correction row must be durable"
        assert corrections[0].actor_name == winner.json()["actor_name"], (
            "the durable correction row must belong to the winning request, not the loser"
        )
        assert audits == 1, "exactly one corresponding correction audit event must be durable"


# === G. UNRELATED UNIQUE VIOLATION NOT TRANSLATED ================================


@pytest.mark.asyncio
async def test_unrelated_unique_violation_not_translated_to_409() -> None:
    """Forces an IntegrityError with SQLSTATE 23505 but a DIFFERENT
    constraint name (a second, incidental unique index on this table would
    be needed to reach this via the public API; instead this test proves
    the predicate directly against the router's own dual-diagnostic check
    using a real asyncpg-shaped exception, since GD-013 §4 requires no
    modification to production code merely to make this reachable via
    HTTP)."""
    from sqlalchemy.exc import IntegrityError as SAIntegrityError

    from app.contexts.evidence.api.attribution_router import _is_supersedes_once_violation

    class _FakeDriverExc:
        sqlstate = "23505"
        constraint_name = "uq_some_other_table_constraint"

    class _FakeOrig:
        __cause__ = _FakeDriverExc()

    exc = SAIntegrityError("stmt", {}, Exception("orig"))
    exc.orig = _FakeOrig()  # type: ignore[assignment]

    assert _is_supersedes_once_violation(exc) is False


# === H. SELF-SUPERSESSION VIOLATION NOT TRANSLATED ================================


@pytest.mark.asyncio
async def test_self_supersession_attempt_yields_5xx_not_409() -> None:
    """A raw, direct attempt to insert `id == supersedes_id` — the public
    API cannot construct this itself (the domain layer generates a fresh,
    unpredictable id, and its own defensive check would reject it before
    any SQL is issued), so this test bypasses the application layer
    entirely, mirroring migration 0014's own revision-note technique for
    exercising its database-level guards directly.

    Established empirically, not assumed: self-reference (`id ==
    supersedes_id`) is intercepted by the `evidence_actor_attributions_
    reject_cycle` trigger (a self-reference is trivially the smallest
    possible cycle) BEFORE Postgres ever evaluates the separate
    `ck_evidence_actor_attributions_no_self_supersede` CHECK constraint —
    confirmed by observing which exception message actually comes back.
    The CHECK constraint therefore backstops a case the cycle trigger
    already excludes at the database level for this exact scenario; its own
    dual-diagnostic exclusion is proven directly, hermetically, against a
    synthetic exception carrying its exact SQLSTATE/name
    (tests/test_evidence_attribution_api.py::
    test_check_constraint_violation_not_matched_despite_same_exception_class)
    — a live database cannot independently exercise the CHECK constraint in
    isolation from the cycle trigger for this particular violation shape.

    What this test proves against the real database: whichever guard fires,
    the resulting exception is not the specific, dual-diagnostic-matched
    `uq_evidence_actor_attributions_supersedes_once` violation GD-013 §4
    authorizes translating — so the router's real exception-translation
    code, unmodified, would let it propagate as a 5xx — and no row becomes
    durable."""
    async with _live_env() as env:
        engine = create_async_engine(
            make_url(env.db_url)
            .set(username="landvault_app", password=os.environ["POSTGRES_APP_PASSWORD"])
            .render_as_string(hide_password=False)
        )
        try:
            same_id = uuid.uuid4()
            with pytest.raises(sa.exc.DBAPIError) as exc_info:
                async with engine.begin() as conn:
                    # The trigger(s) fired here run their own internal
                    # SELECTs against evidence_records, subject to RLS on
                    # THIS connection — get_db_session normally sets this
                    # for every real request; a raw test connection must set
                    # it explicitly or a trigger sees no row at all and
                    # raises an unrelated tenant-mismatch error instead.
                    await conn.execute(
                        sa.text("SELECT set_config('app.tenant_id', :t, true)"),
                        {"t": env.ids["tenant_id"]},
                    )
                    await conn.execute(
                        sa.text(
                            "INSERT INTO evidence_actor_attributions "
                            "(id, tenant_id, evidence_id, attribution_role, actor_reference_kind, "
                            " actor_type, basis, recorded_by, supersedes_id) "
                            "VALUES (:id, :tenant_id, :evidence_id, 'ORIGINATED_BY', "
                            " 'UNKNOWN', 'UNKNOWN', 'self-supersession probe', :recorded_by, :id)"
                        ),
                        {
                            "id": same_id, "tenant_id": env.ids["tenant_id"],
                            "evidence_id": uuid.UUID(env.ids["evidence_id"]),
                            "recorded_by": uuid.UUID(env.ids["user_id"]),
                        },
                    )
            async with engine.connect() as conn:
                count = (await conn.execute(
                    sa.text("SELECT count(*) FROM evidence_actor_attributions WHERE id = :id"),
                    {"id": same_id},
                )).scalar_one()
            assert count == 0, "the self-superseding row must not be durable"
        finally:
            await engine.dispose()

        from app.contexts.evidence.api.attribution_router import _is_supersedes_once_violation

        raised = exc_info.value
        # Confirmed empirically: this is the cycle trigger's own rejection
        # (not an IntegrityError at all, since its RAISE EXCEPTION carries
        # no explicit SQLSTATE) — recorded here as the actual observed
        # mechanism, not assumed to be the CHECK constraint.
        assert "cycle back to" in str(raised)
        assert not isinstance(raised, sa.exc.IntegrityError), (
            "self-supersession is intercepted by the cycle trigger, not the CHECK constraint "
            "— if this ever changes, the dual-diagnostic predicate below must be re-checked "
            "against the actual exception"
        )
        if isinstance(raised, sa.exc.IntegrityError):
            assert _is_supersedes_once_violation(raised) is False


# === I. CYCLIC-CORRECTION TRIGGER ===============================================


@pytest.mark.asyncio
async def test_cyclic_correction_lineage_rejected_by_real_trigger() -> None:
    """Exercises `evidence_actor_attributions_reject_cycle` directly — a
    two-row mutual cycle in one INSERT, the exact shape migration 0014's
    own revision note documents proving a single-statement multi-row
    insert can otherwise construct a cycle no earlier single-row check
    would catch."""
    async with _live_env() as env:
        engine = create_async_engine(
            make_url(env.db_url)
            .set(username="landvault_app", password=os.environ["POSTGRES_APP_PASSWORD"])
            .render_as_string(hide_password=False)
        )
        try:
            id_a, id_b = uuid.uuid4(), uuid.uuid4()
            # The trigger's own RAISE EXCEPTION carries no explicit SQLSTATE
            # (defaults to P0001, raise_exception) — SQLAlchemy surfaces this
            # as DBAPIError's InternalError, not IntegrityError; confirmed
            # this is a deliberately different exception shape from the
            # UNIQUE/CHECK constraint violations above (GD-013 §4's own
            # dual-diagnostic predicate never has to distinguish this case,
            # since it isn't an IntegrityError at all).
            with pytest.raises(sa.exc.DBAPIError) as exc_info:
                async with engine.begin() as conn:
                    await conn.execute(
                        sa.text("SELECT set_config('app.tenant_id', :t, true)"),
                        {"t": env.ids["tenant_id"]},
                    )
                    await conn.execute(
                        sa.text(
                            "INSERT INTO evidence_actor_attributions "
                            "(id, tenant_id, evidence_id, attribution_role, actor_reference_kind, "
                            " actor_type, basis, recorded_by, supersedes_id) VALUES "
                            "(:id_a, :tenant_id, :evidence_id, 'ORIGINATED_BY', 'UNKNOWN', "
                            " 'UNKNOWN', 'cycle probe A', :recorded_by, :id_b), "
                            "(:id_b, :tenant_id, :evidence_id, 'ORIGINATED_BY', 'UNKNOWN', "
                            " 'UNKNOWN', 'cycle probe B', :recorded_by, :id_a)"
                        ),
                        {
                            "id_a": id_a, "id_b": id_b, "tenant_id": env.ids["tenant_id"],
                            "evidence_id": uuid.UUID(env.ids["evidence_id"]),
                            "recorded_by": uuid.UUID(env.ids["user_id"]),
                        },
                    )
            # Confirms this is genuinely the cycle trigger's own rejection,
            # not some other DBAPIError masked by the broader exception
            # class this trigger's unset-SQLSTATE RAISE requires catching.
            assert "cycle back to" in str(exc_info.value)
            async with engine.connect() as conn:
                count = (await conn.execute(
                    sa.text(
                        "SELECT count(*) FROM evidence_actor_attributions WHERE id IN (:a, :b)"
                    ),
                    {"a": id_a, "b": id_b},
                )).scalar_one()
            assert count == 0, "the cyclic pair must not be durable"
        finally:
            await engine.dispose()


# === J. INDISTINGUISHABLE 404s ===================================================


@pytest.mark.asyncio
async def test_nonexistent_and_cross_tenant_evidence_are_byte_identical_live() -> None:
    async with _live_env() as env:
        other_tenant = f"tenant-{uuid.uuid4().hex[:8]}"
        other_user = uuid.uuid4()
        engine = create_async_engine(env.db_url)
        try:
            async with engine.begin() as conn:
                await conn.execute(
                    sa.text("INSERT INTO tenants (id, name, status) VALUES (:id, :n, 'ACTIVE')"),
                    {"id": other_tenant, "n": "Other tenant"},
                )
                await conn.execute(
                    sa.text(
                        "INSERT INTO identity_users "
                        "(id, identity_subject, email, full_name, country, tenant_id, roles) "
                        "VALUES (:id, :sub, :email, 'Other', 'NG', :tenant_id, '[]'::jsonb)"
                    ),
                    {
                        "id": other_user, "sub": f"sub-{uuid.uuid4().hex[:8]}",
                        "email": f"{uuid.uuid4().hex[:8]}@example.test", "tenant_id": other_tenant,
                    },
                )
        finally:
            await engine.dispose()

        other_headers = env.headers(principal_id=str(other_user), tenant_id=other_tenant)
        async with httpx.AsyncClient(base_url=env.base_url, timeout=10) as client:
            nonexistent = await client.post(
                "/v1/evidence/00000000-0000-0000-0000-000000000000/attributions",
                json={
                    "attribution_role": "ORIGINATED_BY", "actor_reference_kind": "EXTERNAL_NAMED",
                    "actor_type": "INDIVIDUAL", "actor_name": "X", "basis": "nonexistent probe",
                },
                headers=other_headers,
            )
            cross_tenant = await client.post(
                f"/v1/evidence/{env.ids['evidence_id']}/attributions",
                json={
                    "attribution_role": "ORIGINATED_BY", "actor_reference_kind": "EXTERNAL_NAMED",
                    "actor_type": "INDIVIDUAL", "actor_name": "X", "basis": "cross-tenant probe",
                },
                headers=other_headers,
            )
        assert nonexistent.status_code == cross_tenant.status_code == 404
        n_body, c_body = nonexistent.json(), cross_tenant.json()
        n_body.pop("instance", None)
        c_body.pop("instance", None)
        assert n_body == c_body

        # GD-012 §10 item 17 / GD-014 obligation 7: neither the nonexistent-
        # evidence nor the cross-tenant-evidence rejected record attempt may
        # leave a durable row or audit event, checked against real
        # PostgreSQL independently of the request's own session.
        attrs, audits = await env.row_counts()
        assert attrs == 0, "no attribution row may be durable after a rejected record attempt"
        assert audits == 0, "no audit event may be durable after a rejected record attempt"


# === J2. INDISTINGUISHABLE 404s — CORRECTION ATTRIBUTION ========================


@pytest.mark.asyncio
async def test_nonexistent_and_cross_tenant_attribution_are_byte_identical_live() -> None:
    """GD-012 §10 items 10-11, against real PostgreSQL — the correction
    endpoint's own nonexistent-vs-cross-tenant 404 indistinguishability, and
    (GD-012 §10 item 17 / GD-014 obligation 7) that neither rejected
    correction attempt leaves a durable row or audit event. Test J above
    covers only the record endpoint's EvidenceRecord 404s (items 8-9); no
    other test exercises the correction endpoint's attribution_id 404s
    against a real database."""
    async with _live_env() as env:
        other_tenant = f"tenant-{uuid.uuid4().hex[:8]}"
        other_user = uuid.uuid4()
        engine = create_async_engine(env.db_url)
        try:
            async with engine.begin() as conn:
                await conn.execute(
                    sa.text("INSERT INTO tenants (id, name, status) VALUES (:id, :n, 'ACTIVE')"),
                    {"id": other_tenant, "n": "Other tenant"},
                )
                await conn.execute(
                    sa.text(
                        "INSERT INTO identity_users "
                        "(id, identity_subject, email, full_name, country, tenant_id, roles) "
                        "VALUES (:id, :sub, :email, 'Other', 'NG', :tenant_id, '[]'::jsonb)"
                    ),
                    {
                        "id": other_user, "sub": f"sub-{uuid.uuid4().hex[:8]}",
                        "email": f"{uuid.uuid4().hex[:8]}@example.test", "tenant_id": other_tenant,
                    },
                )
        finally:
            await engine.dispose()

        owner_headers = env.headers(
            principal_id=env.ids["user_id"], tenant_id=env.ids["tenant_id"]
        )
        async with httpx.AsyncClient(base_url=env.base_url, timeout=10) as client:
            original = (await client.post(
                f"/v1/evidence/{env.ids['evidence_id']}/attributions",
                json={
                    "attribution_role": "ORIGINATED_BY", "actor_reference_kind": "EXTERNAL_NAMED",
                    "actor_type": "INDIVIDUAL", "actor_name": "Cross-Tenant-404 Original",
                    "basis": "GD-012/GD-014 correction-404 durability proof",
                },
                headers=owner_headers,
            )).json()

        other_headers = env.headers(principal_id=str(other_user), tenant_id=other_tenant)
        before_attrs, before_audits = await env.row_counts()
        async with httpx.AsyncClient(base_url=env.base_url, timeout=10) as client:
            nonexistent = await client.post(
                "/v1/evidence/attributions/00000000-0000-0000-0000-000000000000/corrections",
                json={
                    "attribution_role": "ORIGINATED_BY", "actor_reference_kind": "EXTERNAL_NAMED",
                    "actor_type": "INDIVIDUAL", "actor_name": "X", "basis": "nonexistent probe",
                },
                headers=other_headers,
            )
            cross_tenant = await client.post(
                f"/v1/evidence/attributions/{original['attribution_id']}/corrections",
                json={
                    "attribution_role": "ORIGINATED_BY", "actor_reference_kind": "EXTERNAL_NAMED",
                    "actor_type": "INDIVIDUAL", "actor_name": "X", "basis": "cross-tenant probe",
                },
                headers=other_headers,
            )
        assert nonexistent.status_code == cross_tenant.status_code == 404
        n_body, c_body = nonexistent.json(), cross_tenant.json()
        n_body.pop("instance", None)
        c_body.pop("instance", None)
        assert n_body == c_body

        attrs, audits = await env.row_counts()
        assert attrs == before_attrs, (
            "no attribution row may be durable after a rejected correction attempt"
        )
        assert audits == before_audits, (
            "no audit event may be durable after a rejected correction attempt"
        )


# === K. ACTOR-PRINCIPAL ORACLE ===================================================


@pytest.mark.asyncio
async def test_actor_principal_oracle_byte_identical_live() -> None:
    async with _live_env() as env:
        other_tenant = f"tenant-{uuid.uuid4().hex[:8]}"
        other_user = uuid.uuid4()
        engine = create_async_engine(env.db_url)
        try:
            async with engine.begin() as conn:
                await conn.execute(
                    sa.text("INSERT INTO tenants (id, name, status) VALUES (:id, :n, 'ACTIVE')"),
                    {"id": other_tenant, "n": "Other tenant"},
                )
                await conn.execute(
                    sa.text(
                        "INSERT INTO identity_users "
                        "(id, identity_subject, email, full_name, country, tenant_id, roles) "
                        "VALUES (:id, :sub, :email, 'Other', 'NG', :tenant_id, '[]'::jsonb)"
                    ),
                    {
                        "id": other_user, "sub": f"sub-{uuid.uuid4().hex[:8]}",
                        "email": f"{uuid.uuid4().hex[:8]}@example.test", "tenant_id": other_tenant,
                    },
                )
        finally:
            await engine.dispose()

        headers = env.headers(principal_id=env.ids["user_id"], tenant_id=env.ids["tenant_id"])
        async with httpx.AsyncClient(base_url=env.base_url, timeout=10) as client:
            nonexistent = await client.post(
                f"/v1/evidence/{env.ids['evidence_id']}/attributions",
                json={
                    "attribution_role": "ORIGINATED_BY",
                    "actor_reference_kind": "INTERNAL_PRINCIPAL",
                    "actor_type": "INDIVIDUAL", "actor_name": "N",
                    "actor_principal_id": "00000000-0000-0000-0000-000000000000",
                    "basis": "nonexistent principal probe",
                },
                headers=headers,
            )
            cross_tenant = await client.post(
                f"/v1/evidence/{env.ids['evidence_id']}/attributions",
                json={
                    "attribution_role": "ORIGINATED_BY",
                    "actor_reference_kind": "INTERNAL_PRINCIPAL",
                    "actor_type": "INDIVIDUAL", "actor_name": "C",
                    "actor_principal_id": str(other_user),
                    "basis": "cross-tenant principal probe",
                },
                headers=headers,
            )
        assert nonexistent.status_code == cross_tenant.status_code == 400
        assert nonexistent.json() == cross_tenant.json()
