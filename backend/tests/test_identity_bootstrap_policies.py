"""Hermetic tests for the two bootstrap PDP policies (GD-016 §11 tests
2-6, 13-18, 24, 48) — docs/GD-016-adr-031-initial-supabase-identity-
bootstrap-implementation-authorization.md, implementing ADR-031 as
qualified by ADR-032.
"""
from __future__ import annotations

import pytest

from app.contexts.identity.authorization.bootstrap_policies import (
    FIRST_TENANT_ACTION,
    PREFLIGHT_ACTION,
    _bootstrap_first_tenant,
    _bootstrap_preflight,
    register_bootstrap_policies,
)
from app.kernel.authorization.decisions import Effect
from app.kernel.authorization.pdp import authorize
from app.kernel.authorization.policies import reset_policies
from app.kernel.context import ExecutionContext


@pytest.fixture(autouse=True)
def _reset_and_register_bootstrap_policies():
    reset_policies()
    register_bootstrap_policies()
    yield
    reset_policies()


def _ctx(**overrides) -> ExecutionContext:
    defaults: dict = {"principal_id": "sub_test", "tenant_id": None, "roles": ()}
    defaults.update(overrides)
    return ExecutionContext(**defaults)


# ---- Test 2 / 3: both allowed roles succeed at both stages -----------------


@pytest.mark.parametrize("role", ["compliance_officer", "surveyor_general"])
def test_preflight_permits_allowed_role(role: str) -> None:
    decision = authorize(
        PREFLIGHT_ACTION,
        resource={"requested_role": role},
        env={"invocation_channel": "bootstrap_cli"},
        ctx=_ctx(),
    )
    assert decision.permitted
    assert decision.policy_id == PREFLIGHT_ACTION


@pytest.mark.parametrize("role", ["compliance_officer", "surveyor_general"])
def test_first_tenant_permits_allowed_role(role: str) -> None:
    decision = authorize(
        FIRST_TENANT_ACTION,
        resource={"requested_role": role},
        env={"preflight_permitted": True, "platform_empty": True},
        ctx=_ctx(),
    )
    assert decision.permitted
    assert decision.policy_id == FIRST_TENANT_ACTION


# ---- Test 4: general_user requested role rejected --------------------------


def test_preflight_rejects_general_user_requested_role() -> None:
    decision = authorize(
        PREFLIGHT_ACTION,
        resource={"requested_role": "general_user"},
        env={"invocation_channel": "bootstrap_cli"},
        ctx=_ctx(),
    )
    assert not decision.permitted
    assert decision.policy_id == PREFLIGHT_ACTION


# ---- Test 5: super_admin requested role rejected ----------------------------


def test_preflight_rejects_super_admin_requested_role() -> None:
    decision = authorize(
        PREFLIGHT_ACTION,
        resource={"requested_role": "super_admin"},
        env={"invocation_channel": "bootstrap_cli"},
        ctx=_ctx(),
    )
    assert not decision.permitted
    assert decision.policy_id == PREFLIGHT_ACTION


# ---- Test 6: every other/unknown role string rejected -----------------------


@pytest.mark.parametrize("role", ["", "field_agent", "nonexistent_role", "COMPLIANCE_OFFICER"])
def test_preflight_rejects_unknown_role(role: str) -> None:
    decision = authorize(
        PREFLIGHT_ACTION,
        resource={"requested_role": role},
        env={"invocation_channel": "bootstrap_cli"},
        ctx=_ctx(),
    )
    assert not decision.permitted


# ---- Test 13: existing effective tenant/roles rejected at Stage 1 ----------


def test_preflight_rejects_effective_tenant() -> None:
    decision = authorize(
        PREFLIGHT_ACTION,
        resource={"requested_role": "compliance_officer"},
        env={"invocation_channel": "bootstrap_cli"},
        ctx=_ctx(tenant_id="ten_existing"),
    )
    assert not decision.permitted


def test_preflight_rejects_effective_roles() -> None:
    decision = authorize(
        PREFLIGHT_ACTION,
        resource={"requested_role": "compliance_officer"},
        env={"invocation_channel": "bootstrap_cli"},
        ctx=_ctx(roles=("general_user",)),
    )
    assert not decision.permitted


# ---- Test 14: suspended/inactive shape does not itself prove emptiness ----


def test_preflight_permits_on_empty_shape_regardless_of_history() -> None:
    """ctx.tenant_id is None and ctx.roles == () is, by ADR-031's own
    documented reading, "no effective hydrated context right now" — not
    proof the subject never existed (the same shape also results from a
    suspended user or an archived tenant, per context_hydration's
    fail-closed behaviour). Stage 1 correctly cannot and does not try to
    distinguish these cases from this shape alone; the real anti-replay
    guarantee is Stage 2's authoritative env["platform_empty"], not this
    ctx shape. Proven here: Stage 1 PERMIT; confirmed by
    test_first_tenant_denies_when_platform_not_empty below that Stage 2
    denies on the real fact regardless of this PERMIT."""
    decision = authorize(
        PREFLIGHT_ACTION,
        resource={"requested_role": "compliance_officer"},
        env={"invocation_channel": "bootstrap_cli"},
        ctx=_ctx(),
    )
    assert decision.permitted


# ---- Test 15: matching-action condition failure -> explicit DENY, never None


def test_preflight_policy_fn_never_returns_none_for_its_own_action() -> None:
    ctx = _ctx(tenant_id="already-has-one")
    decision = _bootstrap_preflight(
        ctx, PREFLIGHT_ACTION, {"requested_role": "compliance_officer"},
        {"invocation_channel": "bootstrap_cli"},
    )
    assert decision is not None
    assert decision.effect == Effect.DENY


def test_first_tenant_policy_fn_never_returns_none_for_its_own_action() -> None:
    ctx = _ctx()
    decision = _bootstrap_first_tenant(
        ctx, FIRST_TENANT_ACTION, {"requested_role": "compliance_officer"},
        {"preflight_permitted": True, "platform_empty": False},
    )
    assert decision is not None
    assert decision.effect == Effect.DENY


# ---- Test 16: super_admin + bootstrap_preflight -> DENY before priority 20 -


def test_super_admin_principal_denied_before_platform_super_admin() -> None:
    """The ADR-032 case this whole module exists to fix: a super_admin-role
    principal invoking identity.bootstrap_preflight must be denied by the
    bootstrap policy itself (priority 15), never reaching -- let alone
    being permitted by -- platform.super_admin (priority 20)."""
    decision = authorize(
        PREFLIGHT_ACTION,
        resource={"requested_role": "compliance_officer"},
        env={"invocation_channel": "bootstrap_cli"},
        ctx=_ctx(roles=("super_admin",)),
    )
    assert not decision.permitted
    assert decision.policy_id == PREFLIGHT_ACTION
    assert decision.policy_id != "platform.super_admin"


# ---- Test 17: unrelated action + super_admin unaffected --------------------


def test_unrelated_action_super_admin_still_permitted_unchanged() -> None:
    decision = authorize(
        "registry.parcel.read", ctx=_ctx(principal_id="usr_admin", roles=("super_admin",))
    )
    assert decision.permitted
    assert decision.policy_id == "platform.super_admin"


# ---- Test 18: wrong/missing invocation_channel -> explicit DENY ------------


def test_preflight_rejects_wrong_invocation_channel() -> None:
    decision = authorize(
        PREFLIGHT_ACTION,
        resource={"requested_role": "compliance_officer"},
        env={"invocation_channel": "http"},
        ctx=_ctx(),
    )
    assert not decision.permitted


def test_preflight_rejects_missing_invocation_channel() -> None:
    decision = authorize(
        PREFLIGHT_ACTION, resource={"requested_role": "compliance_officer"}, env={}, ctx=_ctx()
    )
    assert not decision.permitted


# ---- Test 24: final PDP, platform_empty=False -> explicit DENY -------------


def test_first_tenant_denies_when_platform_not_empty() -> None:
    decision = authorize(
        FIRST_TENANT_ACTION,
        resource={"requested_role": "compliance_officer"},
        env={"preflight_permitted": True, "platform_empty": False},
        ctx=_ctx(),
    )
    assert not decision.permitted
    assert decision.policy_id == FIRST_TENANT_ACTION


def test_first_tenant_denies_when_preflight_not_permitted() -> None:
    decision = authorize(
        FIRST_TENANT_ACTION,
        resource={"requested_role": "compliance_officer"},
        env={"preflight_permitted": False, "platform_empty": True},
        ctx=_ctx(),
    )
    assert not decision.permitted


# ---- Test 48: unrelated PDP behaviour byte-for-byte unchanged --------------


def test_unrelated_action_pdp_behaviour_unchanged_for_ordinary_user() -> None:
    decision = authorize("identity.register", ctx=ExecutionContext(principal_id="anonymous"))
    assert decision.permitted
    assert decision.policy_id == "platform.anonymous_public"


def test_bootstrap_policy_fns_defer_on_unrelated_action() -> None:
    ctx = _ctx(roles=("super_admin",))
    assert _bootstrap_preflight(ctx, "registry.parcel.read", {}, {}) is None
    assert _bootstrap_first_tenant(ctx, "registry.parcel.read", {}, {}) is None
