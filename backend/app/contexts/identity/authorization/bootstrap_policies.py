"""Bootstrap PDP policies — docs/GD-016-adr-031-initial-supabase-identity-
bootstrap-implementation-authorization.md, implementing docs/adr/
ADR-031-initial-supabase-identity-bootstrap-and-first-tenant-provisioning.md
as qualified by docs/adr/ADR-032-bootstrap-pdp-action-ownership-and-
explicit-deny-semantics.md.

Both policies are action-owning: they return `None` (defer) for any action
other than their own, and an *explicit* `Decision.deny(...)` — never
`None` — for their own action when any required condition fails. This is
the exact ADR-032 correction over ADR-031's original "otherwise: defer
(None) -> PDP default-deny" wording, which would otherwise let a failed
bootstrap check fall through to the registry's existing, unconditional-on-
action `platform.super_admin` policy (priority 20). Registering these at
priorities 15/16 places them before that policy; returning an explicit DENY
on failure is what actually stops evaluation there (GD-016 is implemented
`as qualified by ADR-032` — this module exists only because registering at
a lower priority, by itself, does not close that gap).

`register_bootstrap_policies()` must be called only by the bootstrap CLI's
own process (`app.contexts.identity.cli.bootstrap_first_tenant`) — never by
`app/main.py`. The running FastAPI application process never registers
either action, so no HTTP caller of any kind can ever reach them (GD-016
§3, §12).
"""
from __future__ import annotations

from app.kernel.authorization.decisions import Decision
from app.kernel.authorization.policies import register_policy
from app.kernel.context import ExecutionContext

ALLOWED_BOOTSTRAP_ROLES = frozenset({"compliance_officer", "surveyor_general"})

PREFLIGHT_ACTION = "identity.bootstrap_preflight"
FIRST_TENANT_ACTION = "identity.bootstrap_first_tenant"


def _bootstrap_preflight(
    ctx: ExecutionContext, action: str, resource: dict, env: dict
) -> Decision | None:
    if action != PREFLIGHT_ACTION:
        return None
    if (
        ctx.is_authenticated
        and ctx.tenant_id is None
        and ctx.roles == ()
        and env.get("invocation_channel") == "bootstrap_cli"
        and resource.get("requested_role") in ALLOWED_BOOTSTRAP_ROLES
    ):
        return Decision.permit(
            reason="bootstrap preflight conditions satisfied", policy_id=PREFLIGHT_ACTION
        )
    return Decision.deny(
        reason="bootstrap preflight conditions not satisfied", policy_id=PREFLIGHT_ACTION
    )


def _bootstrap_first_tenant(
    ctx: ExecutionContext, action: str, resource: dict, env: dict
) -> Decision | None:
    if action != FIRST_TENANT_ACTION:
        return None
    if (
        ctx.is_authenticated
        and ctx.tenant_id is None
        and ctx.roles == ()
        and env.get("preflight_permitted") is True
        and env.get("platform_empty") is True
        and resource.get("requested_role") in ALLOWED_BOOTSTRAP_ROLES
    ):
        return Decision.permit(
            reason="bootstrap first-tenant conditions satisfied", policy_id=FIRST_TENANT_ACTION
        )
    return Decision.deny(
        reason="bootstrap first-tenant conditions not satisfied", policy_id=FIRST_TENANT_ACTION
    )


def register_bootstrap_policies() -> None:
    """Registers both bootstrap policies at priorities 15/16 — strictly
    before `platform.super_admin` (20), after `platform.tenant_isolation`
    (10)/`platform.country_isolation` (11), which are already no-ops for
    bootstrap's resource shape. `register_policy` raises on re-registering
    an already-registered id, so this function itself is not idempotent —
    callers (the CLI entrypoint; tests, via `reset_policies()` between
    cases) are responsible for registering at most once per process state."""
    register_policy(
        PREFLIGHT_ACTION,
        15,
        "Bootstrap Stage 1 - minimum privileged read probe authorization",
        _bootstrap_preflight,
    )
    register_policy(
        FIRST_TENANT_ACTION,
        16,
        "Bootstrap Stage 2 - initial Tenant/User provisioning mutation authorization",
        _bootstrap_first_tenant,
    )
