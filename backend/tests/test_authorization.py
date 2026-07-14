import pytest

from app.kernel.authorization.decisions import Decision
from app.kernel.authorization.pdp import authorize
from app.kernel.authorization.policies import register_policy, reset_policies
from app.kernel.context import ExecutionContext


@pytest.fixture(autouse=True)
def _reset_policy_registry():
    reset_policies()
    yield
    reset_policies()


def test_default_deny_when_no_policy_matches() -> None:
    ctx = ExecutionContext(principal_id="usr_1", roles=("general_user",))
    decision = authorize("some.unregistered.action", ctx=ctx)
    assert decision.effect == Decision.deny().effect
    assert decision.policy_id == "platform.default_deny"


def test_anonymous_denied_by_default() -> None:
    decision = authorize("identity.user.read")
    assert not decision.permitted


def test_anonymous_can_register_and_login() -> None:
    assert authorize("identity.register").permitted
    assert authorize("identity.login").permitted


def test_super_admin_permitted_everything() -> None:
    ctx = ExecutionContext(principal_id="usr_admin", roles=("super_admin",))
    decision = authorize("any.action.whatsoever", ctx=ctx)
    assert decision.permitted


def test_crashing_policy_denies_for_safety() -> None:
    def _boom(ctx, action, resource, env):
        raise RuntimeError("boom")

    register_policy("test.crash", 5, "always crashes", _boom)
    ctx = ExecutionContext(principal_id="usr_1", roles=("general_user",))
    decision = authorize("whatever", ctx=ctx)
    assert not decision.permitted
    assert decision.policy_id == "test.crash"


def test_tenant_isolation_denies_cross_tenant_unless_super_admin() -> None:
    ctx = ExecutionContext(principal_id="usr_1", tenant_id="ten_a", roles=("general_user",))
    decision = authorize("identity.user.read", resource={"tenant_id": "ten_b"}, ctx=ctx)
    assert not decision.permitted
    assert decision.policy_id == "platform.tenant_isolation"


def test_tenant_isolation_allows_super_admin_cross_tenant() -> None:
    ctx = ExecutionContext(principal_id="usr_1", tenant_id="ten_a", roles=("super_admin",))
    decision = authorize("identity.user.read", resource={"tenant_id": "ten_b"}, ctx=ctx)
    assert decision.permitted
