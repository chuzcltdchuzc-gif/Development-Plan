"""Hermetic composition-root wiring tests (GD-016 §11 tests 44, 47, 49, 50,
51, 52; §6).
"""
from __future__ import annotations

import io

import pytest
from fastapi import HTTPException
from jwt import InvalidTokenError

import app.contexts.identity.application.bootstrap_service as bootstrap_service
import app.contexts.identity.cli.bootstrap_first_tenant as cli_module
import app.kernel.audit as audit_module
from app.kernel.audit import audit, configure_eager_fallback, get_audit_store
from app.kernel.authorization.policies import reset_policies
from app.kernel.context import ExecutionContext, current_context, reset_context, set_context
from tests.fakes.audit_store import InMemoryAuditStore
from tests.fakes.identity import InMemoryTenantRepository, InMemoryUserRepository


@pytest.fixture(autouse=True)
def _reset_policy_registry():
    reset_policies()
    yield
    reset_policies()


class _Result:
    def __init__(self, value: int) -> None:
        self._value = value

    def scalar_one(self) -> int:
        return self._value


class _FakeSession:
    def __init__(self) -> None:
        self.executed: list[str] = []
        self.committed = False
        self.rolled_back = False
        self.closed = False

    async def execute(self, stmt):
        sql = str(stmt)
        self.executed.append(sql)
        if "count(*)" in sql.lower():
            return _Result(0)
        return _Result(0)

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def close(self) -> None:
        self.closed = True


class _FakeSessionFactory:
    def __init__(self) -> None:
        self.sessions: list[_FakeSession] = []

    def __call__(self) -> _FakeSession:
        session = _FakeSession()
        self.sessions.append(session)
        return session


class _FakeVerifier:
    def __init__(self, claims: dict | None = None, *, raises: Exception | None = None) -> None:
        self._claims = claims or {"sub": "wiring-test-subject", "email": "wiring@example.test"}
        self._raises = raises

    async def verify(self, token: str) -> dict:
        if self._raises is not None:
            raise self._raises
        return self._claims


async def _fake_hydrator(subject: str) -> dict | None:
    return {}


def _patch_full_wiring(
    monkeypatch: pytest.MonkeyPatch, *, call_order: list[str] | None = None
) -> _FakeSessionFactory:
    """Patches everything the real _amain()/run_bootstrap() composition
    touches that would otherwise require a real network or Postgres
    connection, while leaving the REAL configure_eager_fallback,
    register_bootstrap_policies, and enforce() call chain untouched (only
    instrumented with order-recording spies, when call_order is given)."""
    factory = _FakeSessionFactory()
    # Isolate the kernel's bare module-global eager-audit fallback per test
    # -- without this, a different test file's create_app() call (which
    # legitimately configures a REAL EagerPostgresAuditStore against the
    # hermetic suite's placeholder DATABASE_URL) leaks across tests via
    # that global, and these tests would otherwise attempt a real Postgres
    # connection depending on pytest's run order.
    monkeypatch.setattr(audit_module, "_eager_fallback", InMemoryAuditStore())
    monkeypatch.setattr(cli_module, "build_session_factory", lambda engine: factory)
    monkeypatch.setattr(cli_module, "EagerPostgresAuditStore", lambda session_factory: (
        InMemoryAuditStore()
    ))
    monkeypatch.setattr(cli_module, "SupabaseJWKSProvider", lambda **kwargs: object())
    monkeypatch.setattr(cli_module, "JwtVerifier", lambda **kwargs: _FakeVerifier())
    monkeypatch.setattr(
        cli_module, "build_production_context_hydrator", lambda session_factory: _fake_hydrator
    )
    monkeypatch.setattr(
        bootstrap_service, "PostgresTenantRepository", lambda session: InMemoryTenantRepository()
    )
    monkeypatch.setattr(
        bootstrap_service, "PostgresUserRepository", lambda session: InMemoryUserRepository()
    )

    async def _fake_audit_staged(session, action, **kwargs):
        return None

    monkeypatch.setattr(bootstrap_service, "audit_staged", _fake_audit_staged)

    if call_order is not None:
        real_configure_eager_fallback = configure_eager_fallback

        def _spy_configure_eager_fallback(store):
            call_order.append("configure_eager_fallback")
            return real_configure_eager_fallback(store)

        monkeypatch.setattr(cli_module, "configure_eager_fallback", _spy_configure_eager_fallback)

        real_enforce = bootstrap_service.enforce

        async def _spy_enforce(*args, **kwargs):
            call_order.append("enforce")
            return await real_enforce(*args, **kwargs)

        monkeypatch.setattr(bootstrap_service, "enforce", _spy_enforce)

    return factory


# ---- Test 44: configure_eager_fallback strictly before first enforce() ----


@pytest.mark.asyncio
async def test_eager_fallback_configured_before_first_enforce(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_order: list[str] = []
    _patch_full_wiring(monkeypatch, call_order=call_order)
    monkeypatch.setattr(
        cli_module.sys, "stdin", io.StringIO("fake-supabase-access-token\n")
    )

    exit_code = await cli_module._amain(
        ["--tenant-name", "Wiring Test Tenant", "--role", "compliance_officer",
         "--full-name", "Wiring Founder", "--country", "NG"]
    )

    assert exit_code == 0
    assert "configure_eager_fallback" in call_order
    assert "enforce" in call_order
    assert call_order.index("configure_eager_fallback") < call_order.index("enforce")


# ---- Test 52: negative probe -- unconfigured eager store cannot proceed ---


@pytest.mark.asyncio
async def test_unconfigured_eager_store_cannot_silently_proceed() -> None:
    from app.kernel import audit as audit_module

    ctx_token = set_context(ExecutionContext(principal_id="probe-subject"))
    previous_fallback = audit_module._eager_fallback
    audit_module._eager_fallback = None
    # Several OTHER existing test files (test_audit_dag_verifier.py,
    # test_evidence_service.py, test_evidence_upload.py, tests/app_factory.py)
    # call configure_audit_store() without ever resetting the token they
    # discard, so _store_var can carry a leftover value from an earlier
    # test in the same session regardless of run order -- explicitly force
    # it unset here rather than assuming nothing upstream has set it.
    store_token = audit_module._store_var.set(None)
    try:
        with pytest.raises(RuntimeError, match="audit store not configured"):
            await audit("identity.bootstrap.rls_override_used", resource_type="tenant")
    finally:
        audit_module._store_var.reset(store_token)
        audit_module._eager_fallback = previous_fallback
        reset_context(ctx_token)


def test_get_audit_store_raises_when_nothing_configured() -> None:
    from app.kernel import audit as audit_module

    previous_fallback = audit_module._eager_fallback
    audit_module._eager_fallback = None
    store_token = audit_module._store_var.set(None)
    try:
        with pytest.raises(RuntimeError, match="not configured"):
            get_audit_store()
    finally:
        audit_module._store_var.reset(store_token)
        audit_module._eager_fallback = previous_fallback


# ---- Test 47: bootstrap policies never registered in the FastAPI process -


def test_bootstrap_policies_not_registered_by_app_factory() -> None:
    import inspect

    import app.main as main_module

    source = inspect.getsource(main_module)
    assert "register_bootstrap_policies" not in source
    assert "bootstrap_policies" not in source


def test_cli_module_never_imported_by_app_main() -> None:
    import inspect

    import app.main as main_module

    source = inspect.getsource(main_module)
    assert "cli.bootstrap_first_tenant" not in source
    assert "bootstrap_service" not in source


# ---- Test 49: ExecutionContext reset exactly once on success --------------


@pytest.mark.asyncio
async def test_context_reset_exactly_once_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    factory = _patch_full_wiring(monkeypatch)
    reset_calls: list[object] = []
    import app.contexts.identity.cli.bootstrap_first_tenant as cli_mod
    real_reset_context = cli_mod.reset_context

    def _spy_reset_context(token):
        reset_calls.append(token)
        return real_reset_context(token)

    monkeypatch.setattr(cli_mod, "reset_context", _spy_reset_context)

    result = await cli_mod.run_bootstrap(
        token="fake-token",
        tenant_name="Tenant A",
        requested_role="compliance_officer",
        full_name="Founder",
        country="NG",
        verifier=_FakeVerifier(),
        hydrator=_fake_hydrator,
        session_factory=factory,
    )
    assert result.role == "compliance_officer"
    assert len(reset_calls) == 1
    # ambient context is clean again afterward
    assert current_context().is_anonymous


# ---- Test 51: every post-binding failure path resets exactly once ---------


@pytest.mark.asyncio
async def test_context_reset_exactly_once_on_stage1_deny(monkeypatch: pytest.MonkeyPatch) -> None:
    factory = _patch_full_wiring(monkeypatch)
    import app.contexts.identity.cli.bootstrap_first_tenant as cli_mod
    reset_calls: list[object] = []
    real_reset_context = cli_mod.reset_context

    def _spy_reset_context(token):
        reset_calls.append(token)
        return real_reset_context(token)

    monkeypatch.setattr(cli_mod, "reset_context", _spy_reset_context)

    # A verifier whose hydrator-independent claims are fine, but whose
    # hydrated attrs simulate an already-provisioned identity -> Stage 1
    # DENY, a post-binding failure path.
    async def _already_provisioned_hydrator(subject: str) -> dict | None:
        return {"tenant_id": "ten_existing", "roles": ["general_user"]}

    with pytest.raises(HTTPException):
        await cli_mod.run_bootstrap(
            token="fake-token",
            tenant_name="Tenant A",
            requested_role="compliance_officer",
            full_name="Founder",
            country="NG",
            verifier=_FakeVerifier(),
            hydrator=_already_provisioned_hydrator,
            session_factory=factory,
        )
    assert len(reset_calls) == 1
    assert current_context().is_anonymous


@pytest.mark.asyncio
async def test_context_reset_exactly_once_on_mutation_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = _patch_full_wiring(monkeypatch)
    import app.contexts.identity.cli.bootstrap_first_tenant as cli_mod

    async def _failing_audit_staged(session, action, **kwargs):
        raise RuntimeError("simulated post-binding mutation failure")

    monkeypatch.setattr(bootstrap_service, "audit_staged", _failing_audit_staged)

    reset_calls: list[object] = []
    real_reset_context = cli_mod.reset_context

    def _spy_reset_context(token):
        reset_calls.append(token)
        return real_reset_context(token)

    monkeypatch.setattr(cli_mod, "reset_context", _spy_reset_context)

    with pytest.raises(RuntimeError, match="simulated"):
        await cli_mod.run_bootstrap(
            token="fake-token",
            tenant_name="Tenant A",
            requested_role="compliance_officer",
            full_name="Founder",
            country="NG",
            verifier=_FakeVerifier(),
            hydrator=_fake_hydrator,
            session_factory=factory,
        )
    assert len(reset_calls) == 1
    assert current_context().is_anonymous


# ---- Test 50: pre-binding failures never bind or reset a context ----------


@pytest.mark.asyncio
async def test_prebinding_failure_never_binds_or_resets_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.contexts.identity.cli.bootstrap_first_tenant as cli_mod

    reset_calls: list[object] = []
    real_reset_context = cli_mod.reset_context

    def _spy_reset_context(token):
        reset_calls.append(token)
        return real_reset_context(token)

    monkeypatch.setattr(cli_mod, "reset_context", _spy_reset_context)

    # Pre-existing ambient state the pre-binding failure must leave alone.
    sentinel_ctx = ExecutionContext(principal_id="pre-existing-ambient-subject")
    sentinel_token = set_context(sentinel_ctx)
    try:
        with pytest.raises(cli_mod.BootstrapCliError, match="invalid or expired"):
            await cli_mod.run_bootstrap(
                token="bad-token",
                tenant_name="Tenant A",
                requested_role="compliance_officer",
                full_name="Founder",
                country="NG",
                verifier=_FakeVerifier(raises=InvalidTokenError("bad token")),
                hydrator=_fake_hydrator,
                session_factory=_FakeSessionFactory(),
            )
        assert reset_calls == []  # set_context()/reset_context() never reached
        assert current_context() is sentinel_ctx  # ambient state untouched
    finally:
        reset_context(sentinel_token)
