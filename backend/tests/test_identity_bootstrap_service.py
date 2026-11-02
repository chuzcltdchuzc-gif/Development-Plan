"""Hermetic orchestration tests for `bootstrap_service.bootstrap_first_tenant`
(GD-016 §11 tests 19, 20, 22, 25-28, 30 (hermetic half), 33, 34, 43).

Fakes the bootstrap-transaction session and the Tenant/User repositories
(monkeypatched onto the already-imported `bootstrap_service` module, never
modifying the production file) so these tests exercise the real PDP/audit
control flow without a live Postgres. Real-PostgreSQL-only requirements
(actual EXCLUSIVE locking, actual RLS, actual transaction MVCC visibility)
are proven separately in backend/tests/live/.
"""
from __future__ import annotations

import copy

import pytest
from fastapi import HTTPException

import app.contexts.identity.application.bootstrap_service as bootstrap_service
from app.contexts.identity.authorization.bootstrap_policies import register_bootstrap_policies
from app.kernel.audit import configure_audit_store, reset_audit_store
from app.kernel.authorization.policies import reset_policies
from app.kernel.context import ExecutionContext, current_context, reset_context, set_context
from tests.fakes.audit_store import InMemoryAuditStore

# ---- shared fakes -----------------------------------------------------------


class _Result:
    def __init__(self, value: int) -> None:
        self._value = value

    def scalar_one(self) -> int:
        return self._value


class _FakeBootstrapSession:
    def __init__(self, tenant_backing: dict) -> None:
        self.tenant_backing = tenant_backing
        self.pending: list = []
        self.executed: list[str] = []
        self.committed = False
        self.rolled_back = False
        self.closed = False

    async def execute(self, stmt):
        sql = str(stmt)
        self.executed.append(sql)
        if "count(*)" in sql.lower():
            return _Result(len(self.tenant_backing))
        return _Result(0)

    async def commit(self) -> None:
        for finalize in self.pending:
            finalize()
        self.pending.clear()
        self.committed = True

    async def rollback(self) -> None:
        self.pending.clear()
        self.rolled_back = True

    async def close(self) -> None:
        self.closed = True


class _TransactionalRepo:
    """Minimal fake standing in for PostgresTenantRepository/
    PostgresUserRepository: writes are deferred to `session.pending` and
    only land in `backing` when the fake session's own commit() runs --
    discarded entirely on rollback(), exactly the visibility a real
    Postgres transaction gives this module's own session.commit()/
    rollback() calls."""

    def __init__(self, backing: dict, session: _FakeBootstrapSession, id_attr: str) -> None:
        self._backing = backing
        self._session = session
        self._id_attr = id_attr

    async def add(self, obj):
        snapshot = copy.deepcopy(obj)
        key = getattr(snapshot, self._id_attr)
        self._session.pending.append(lambda: self._backing.__setitem__(key, snapshot))
        return copy.deepcopy(obj)

    async def update(self, obj, **_kwargs):
        snapshot = copy.deepcopy(obj)
        key = getattr(snapshot, self._id_attr)
        self._session.pending.append(lambda: self._backing.__setitem__(key, snapshot))
        return copy.deepcopy(obj)

    async def get(self, key):
        found = self._backing.get(key)
        return copy.deepcopy(found) if found else None


class _FakeSessionFactory:
    def __init__(self, tenant_backing: dict) -> None:
        self.tenant_backing = tenant_backing
        self.sessions: list[_FakeBootstrapSession] = []

    def __call__(self) -> _FakeBootstrapSession:
        session = _FakeBootstrapSession(self.tenant_backing)
        self.sessions.append(session)
        return session


class _FailingAuditStore(InMemoryAuditStore):
    """Fails append() for a specific real action name (used for the
    independent override-use audit) or a specific target action carried
    in the eager authz.permit/authz.deny payload (used for the two
    enforce() calls, which otherwise share the same action-name prefix)."""

    def __init__(
        self, *, fail_on_action_name: str | None = None, fail_on_payload_action: str | None = None
    ) -> None:
        super().__init__()
        self._fail_on_action_name = fail_on_action_name
        self._fail_on_payload_action = fail_on_payload_action

    async def append(self, entry) -> None:
        if self._fail_on_action_name and entry.action == self._fail_on_action_name:
            raise RuntimeError("simulated independent-audit append failure")
        if self._fail_on_payload_action and entry.payload.get("action") == (
            self._fail_on_payload_action
        ):
            raise RuntimeError("simulated independent-audit append failure")
        await super().append(entry)


def _patch_repos(monkeypatch: pytest.MonkeyPatch, tenant_backing: dict, user_backing: dict) -> None:
    monkeypatch.setattr(
        bootstrap_service,
        "PostgresTenantRepository",
        lambda session: _TransactionalRepo(tenant_backing, session, "tenant_id"),
    )
    monkeypatch.setattr(
        bootstrap_service,
        "PostgresUserRepository",
        lambda session: _TransactionalRepo(user_backing, session, "user_id"),
    )


def _fake_audit_staged_factory(recorded: list):
    async def _fake_audit_staged(
        session, action, *, resource_type="unknown", resource_id=None, decision=None,
        payload=None, entry_id=None,
    ):
        if getattr(session, "_force_staged_failure_on", None) == action:
            raise RuntimeError("simulated staged-audit append failure")
        ctx = current_context()
        recorded.append(
            {
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "principal_id": ctx.principal_id,
                "payload": payload or {},
            }
        )

    return _fake_audit_staged


@pytest.fixture(autouse=True)
def _reset_and_register_bootstrap_policies():
    reset_policies()
    register_bootstrap_policies()
    yield
    reset_policies()


def _bind_ctx(**overrides) -> tuple[ExecutionContext, object]:
    defaults: dict = {"principal_id": "supabase-subject-1", "tenant_id": None, "roles": ()}
    defaults.update(overrides)
    ctx = ExecutionContext(**defaults)
    return ctx, set_context(ctx)


async def _run(
    monkeypatch: pytest.MonkeyPatch,
    *,
    tenant_backing: dict | None = None,
    user_backing: dict | None = None,
    audit_store: InMemoryAuditStore | None = None,
    staged_recorder: list | None = None,
    requested_role: str = "compliance_officer",
    force_staged_failure_on: str | None = None,
):
    tenant_backing = tenant_backing if tenant_backing is not None else {}
    user_backing = user_backing if user_backing is not None else {}
    audit_store = audit_store if audit_store is not None else InMemoryAuditStore()
    staged_recorder = staged_recorder if staged_recorder is not None else []

    _patch_repos(monkeypatch, tenant_backing, user_backing)
    monkeypatch.setattr(
        bootstrap_service, "audit_staged", _fake_audit_staged_factory(staged_recorder)
    )

    factory = _FakeSessionFactory(tenant_backing)
    if force_staged_failure_on:
        original_call = factory.__call__

        def _call_with_force():
            session = original_call()
            session._force_staged_failure_on = force_staged_failure_on
            return session

        factory.__call__ = _call_with_force  # type: ignore[method-assign]

    token = configure_audit_store(audit_store)
    try:
        result = await bootstrap_service.bootstrap_first_tenant(
            session_factory=factory,
            subject="supabase-subject-1",
            email="founder@example.test",
            full_name="Founder User",
            country="NG",
            tenant_name="First Tenant",
            requested_role=requested_role,
        )
        return result, factory, audit_store, staged_recorder, tenant_backing, user_backing
    finally:
        reset_audit_store(token)


# ---- Test 19: Stage-1 DENY -> override never activated ---------------------


@pytest.mark.asyncio
async def test_stage1_deny_never_activates_override(monkeypatch: pytest.MonkeyPatch) -> None:
    ctx, token = _bind_ctx(tenant_id="already-provisioned")
    try:
        tenant_backing: dict = {}
        _patch_repos(monkeypatch, tenant_backing, {})
        factory = _FakeSessionFactory(tenant_backing)
        audit_token = configure_audit_store(InMemoryAuditStore())
        try:
            with pytest.raises(HTTPException):
                await bootstrap_service.bootstrap_first_tenant(
                    session_factory=factory,
                    subject="supabase-subject-1",
                    email="founder@example.test",
                    full_name="Founder User",
                    country="NG",
                    tenant_name="First Tenant",
                    requested_role="compliance_officer",
                )
        finally:
            reset_audit_store(audit_token)
        assert factory.sessions == []  # session_factory() was never called
    finally:
        reset_context(token)


# ---- Test 20: Stage-1 audit-write failure -> fails closed -------------------


@pytest.mark.asyncio
async def test_stage1_audit_failure_never_activates_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx, token = _bind_ctx()
    try:
        tenant_backing: dict = {}
        failing_store = _FailingAuditStore(fail_on_payload_action="identity.bootstrap_preflight")
        with pytest.raises(RuntimeError, match="simulated"):
            await _run(monkeypatch, tenant_backing=tenant_backing, audit_store=failing_store)
    finally:
        reset_context(token)


# ---- Test 22: override-use audit failure -> fails closed before probe -----


@pytest.mark.asyncio
async def test_override_audit_failure_fails_closed_before_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx, token = _bind_ctx()
    try:
        tenant_backing: dict = {}
        failing_store = _FailingAuditStore(
            fail_on_action_name="identity.bootstrap.rls_override_used"
        )
        _patch_repos(monkeypatch, tenant_backing, {})
        monkeypatch.setattr(bootstrap_service, "audit_staged", _fake_audit_staged_factory([]))
        factory = _FakeSessionFactory(tenant_backing)
        audit_token = configure_audit_store(failing_store)
        try:
            with pytest.raises(RuntimeError, match="simulated"):
                await bootstrap_service.bootstrap_first_tenant(
                    session_factory=factory,
                    subject="supabase-subject-1",
                    email="founder@example.test",
                    full_name="Founder User",
                    country="NG",
                    tenant_name="First Tenant",
                    requested_role="compliance_officer",
                )
        finally:
            reset_audit_store(audit_token)
        assert len(factory.sessions) == 1
        session = factory.sessions[0]
        assert session.rolled_back is True
        assert session.committed is False
        assert not any("lock table" in sql.lower() for sql in session.executed)
        assert tenant_backing == {}
    finally:
        reset_context(token)


# ---- Test 25: final-PDP audit-write failure -> fails closed; no mutation --


@pytest.mark.asyncio
async def test_final_pdp_audit_failure_rolls_back_no_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx, token = _bind_ctx()
    try:
        tenant_backing: dict = {}
        failing_store = _FailingAuditStore(
            fail_on_payload_action="identity.bootstrap_first_tenant"
        )
        with pytest.raises(RuntimeError, match="simulated"):
            await _run(monkeypatch, tenant_backing=tenant_backing, audit_store=failing_store)
        assert tenant_backing == {}
    finally:
        reset_context(token)


# ---- Test 26/27/28: final role set is exactly [requested_role] ------------


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["compliance_officer", "surveyor_general"])
async def test_final_user_roles_equal_exactly_requested_role(
    monkeypatch: pytest.MonkeyPatch, role: str
) -> None:
    ctx, token = _bind_ctx()
    try:
        result, _factory, _store, _staged, _tb, user_backing = await _run(
            monkeypatch, requested_role=role
        )
        user = user_backing[result.user_id]
        assert user.roles == [role]
        assert "general_user" not in user.roles  # test 27
        assert "super_admin" not in user.roles  # test 28
    finally:
        reset_context(token)


# ---- Test 30 (hermetic half): staged-audit failure rolls everything back --


@pytest.mark.asyncio
async def test_staged_audit_failure_rolls_back_tenant_user_and_both_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx, token = _bind_ctx()
    try:
        tenant_backing: dict = {}
        user_backing: dict = {}
        _patch_repos(monkeypatch, tenant_backing, user_backing)
        monkeypatch.setattr(
            bootstrap_service, "audit_staged", _fake_audit_staged_factory([])
        )
        factory = _FakeSessionFactory(tenant_backing)

        async def _failing_audit_staged(session, action, **kwargs):
            if action == "identity.user.registered":
                raise RuntimeError("simulated staged-audit append failure")
            # identity.tenant.bootstrapped succeeds first, same as production order

        monkeypatch.setattr(bootstrap_service, "audit_staged", _failing_audit_staged)
        audit_token = configure_audit_store(InMemoryAuditStore())
        try:
            with pytest.raises(RuntimeError, match="simulated"):
                await bootstrap_service.bootstrap_first_tenant(
                    session_factory=factory,
                    subject="supabase-subject-1",
                    email="founder@example.test",
                    full_name="Founder User",
                    country="NG",
                    tenant_name="First Tenant",
                    requested_role="compliance_officer",
                )
        finally:
            reset_audit_store(audit_token)
        assert tenant_backing == {}  # rolled back -- never finalized
        assert user_backing == {}
        assert factory.sessions[0].rolled_back is True
        assert factory.sessions[0].committed is False
    finally:
        reset_context(token)


# ---- Test 33: second bootstrap after success fails closed ------------------


@pytest.mark.asyncio
async def test_second_bootstrap_after_success_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx, token = _bind_ctx()
    try:
        tenant_backing: dict = {}
        user_backing: dict = {}
        result, factory, store, staged, tb, ub = await _run(
            monkeypatch, tenant_backing=tenant_backing, user_backing=user_backing
        )
        assert len(tenant_backing) == 1

        audit_token = configure_audit_store(InMemoryAuditStore())
        try:
            with pytest.raises(HTTPException):
                await bootstrap_service.bootstrap_first_tenant(
                    session_factory=factory,
                    subject="supabase-subject-2",
                    email="second@example.test",
                    full_name="Second Founder",
                    country="NG",
                    tenant_name="Second Tenant",
                    requested_role="surveyor_general",
                )
        finally:
            reset_audit_store(audit_token)
        assert len(tenant_backing) == 1  # unchanged -- no second tenant
    finally:
        reset_context(token)


# ---- Test 34: failed first attempt remains safely retryable ---------------


@pytest.mark.asyncio
async def test_failed_attempt_is_safely_retryable_when_platform_still_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx, token = _bind_ctx()
    try:
        tenant_backing: dict = {}
        user_backing: dict = {}
        _patch_repos(monkeypatch, tenant_backing, user_backing)
        factory = _FakeSessionFactory(tenant_backing)

        async def _failing_audit_staged(session, action, **kwargs):
            raise RuntimeError("simulated failure on first attempt")

        monkeypatch.setattr(bootstrap_service, "audit_staged", _failing_audit_staged)
        audit_token = configure_audit_store(InMemoryAuditStore())
        try:
            with pytest.raises(RuntimeError, match="simulated"):
                await bootstrap_service.bootstrap_first_tenant(
                    session_factory=factory,
                    subject="supabase-subject-1",
                    email="founder@example.test",
                    full_name="Founder User",
                    country="NG",
                    tenant_name="First Tenant",
                    requested_role="compliance_officer",
                )
        finally:
            reset_audit_store(audit_token)
        assert tenant_backing == {}  # first attempt left platform genuinely empty

        monkeypatch.setattr(
            bootstrap_service, "audit_staged", _fake_audit_staged_factory([])
        )
        audit_token = configure_audit_store(InMemoryAuditStore())
        try:
            result = await bootstrap_service.bootstrap_first_tenant(
                session_factory=factory,
                subject="supabase-subject-1",
                email="founder@example.test",
                full_name="Founder User",
                country="NG",
                tenant_name="First Tenant",
                requested_role="compliance_officer",
            )
        finally:
            reset_audit_store(audit_token)
        assert len(tenant_backing) == 1
        assert result.tenant_id in tenant_backing
    finally:
        reset_context(token)


# ---- Test 43: principal_id attribution, including the adversarial case ----


@pytest.mark.asyncio
async def test_principal_id_is_always_the_verified_subject(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every audit event emitted during a successful bootstrap carries the
    verified Supabase subject as principal_id -- regardless of whatever
    different internal LandVault id a hydrator might separately resolve
    for the same subject (that id is never placed into ctx.principal_id in
    the first place -- proven upstream in test_identity_bootstrap_cli.py /
    test_identity_bootstrap_email.py's verify_and_build_context tests;
    this test proves every audit event downstream of a correctly-bound
    context propagates it correctly, never substituting anything else)."""
    verified_subject = "supabase-subject-xyz"
    deliberately_unused_internal_id = "internal-landvault-uuid-DIFFERENT"
    ctx, token = _bind_ctx(principal_id=verified_subject)
    try:
        audit_store = InMemoryAuditStore()
        staged_recorder: list = []
        result, _factory, store, staged, _tb, _ub = await _run(
            monkeypatch, audit_store=audit_store, staged_recorder=staged_recorder
        )
        eager_entries = await audit_store.all_entries()
        assert eager_entries, "expected at least the Stage-1/Stage-2/override-use eager entries"
        for entry in eager_entries:
            assert entry.principal_id == verified_subject
            assert entry.principal_id != deliberately_unused_internal_id
        assert staged_recorder, "expected both staged successful-mutation events"
        for staged_entry in staged_recorder:
            assert staged_entry["principal_id"] == verified_subject
            assert staged_entry["principal_id"] != deliberately_unused_internal_id
    finally:
        reset_context(token)


@pytest.mark.asyncio
async def test_principal_id_is_verified_subject_on_stage1_deny_too(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stage-1 DENY sub-case: a subject that already has an effective
    tenant/roles (as a hydrator would report for an already-provisioned
    active identity) is denied at Stage 1 -- and the resulting DENY audit
    event still carries the verified subject as principal_id, never the
    hydrated internal id this scenario simulates having resolved."""
    verified_subject = "supabase-subject-already-provisioned"
    ctx, token = _bind_ctx(principal_id=verified_subject, tenant_id="ten_already_exists")
    try:
        tenant_backing: dict = {}
        _patch_repos(monkeypatch, tenant_backing, {})
        factory = _FakeSessionFactory(tenant_backing)
        audit_store = InMemoryAuditStore()
        audit_token = configure_audit_store(audit_store)
        try:
            with pytest.raises(HTTPException):
                await bootstrap_service.bootstrap_first_tenant(
                    session_factory=factory,
                    subject=verified_subject,
                    email="founder@example.test",
                    full_name="Founder User",
                    country="NG",
                    tenant_name="First Tenant",
                    requested_role="compliance_officer",
                )
        finally:
            reset_audit_store(audit_token)
        entries = await audit_store.all_entries()
        assert entries
        deny_entries = [e for e in entries if e.decision == "DENY"]
        assert deny_entries
        for entry in deny_entries:
            assert entry.principal_id == verified_subject
    finally:
        reset_context(token)
