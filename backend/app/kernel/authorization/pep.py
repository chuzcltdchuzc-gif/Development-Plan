"""Policy Enforcement Point — single FastAPI dependency that:

1. Extracts the access token (Authorization: Bearer ... or the access cookie)
2. Verifies its signature against the IdP's JWKS (RS256)
3. Looks up roles/tenant/country/org via the context hydrator (NEVER trusts
   the token for these — Keycloak's token only proves `sub`; our own
   Postgres is the single source of truth for authorization attributes,
   per docs/adr/ADR-004 point 5)
4. Sets the resulting ExecutionContext for the current request
5. Audits the access decision when `enforce()` is invoked downstream

This dependency replaces ad-hoc auth checks in routers — there is exactly
one authorization path (docs/ENGINEERING_RULES.md #1). The hydrator is a
plain callback (not an Identity-context import) so the kernel stays
domain-agnostic — see app.contexts.identity.api.wiring for what's bound here.
"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from contextvars import Token

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from jwt import InvalidTokenError

from app.kernel.audit import audit
from app.kernel.authorization.decisions import Decision
from app.kernel.authorization.pdp import authorize
from app.kernel.context import (
    ANONYMOUS,
    ExecutionContext,
    reset_context,
    set_context,
)
from app.kernel.security.jwt import JwtVerifier

logger = logging.getLogger("kernel.authorization.pep")

# Looks up a principal's authorization attributes by IdP subject. Returns
# None if the subject has no corresponding local record (e.g. mid-registration).
ContextHydrator = Callable[[str], Awaitable[dict | None]]

_verifier: JwtVerifier | None = None
_hydrator: ContextHydrator | None = None


def configure_pep(verifier: JwtVerifier, hydrator: ContextHydrator) -> None:
    """Bind the kernel JWT verifier + context hydrator (called once at app startup)."""
    global _verifier, _hydrator
    _verifier = verifier
    _hydrator = hydrator


def _extract_bearer(authorization: str | None, cookie_token: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    if cookie_token:
        return cookie_token.strip() or None
    return None


def _request_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",", 1)[0].strip()
    return request.client.host if request.client else None


async def _build_context_from_token(request: Request, token: str | None) -> ExecutionContext:
    if not token or _verifier is None or _hydrator is None:
        return ExecutionContext(
            principal_id=ANONYMOUS.principal_id,
            request_ip=_request_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    try:
        claims = await _verifier.verify(token)
    except InvalidTokenError as exc:
        logger.info("invalid access token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        ) from exc

    subject = str(claims["sub"])
    attrs = await _hydrator(subject) or {}

    return ExecutionContext(
        # Our own internal user id when hydration finds a local record;
        # falls back to the raw IdP subject only when it doesn't (e.g. a
        # valid Keycloak session with no local account yet) — in that case
        # roles is empty and the PDP default-denies almost everything anyway.
        principal_id=attrs.get("principal_id", subject),
        email=attrs.get("email", claims.get("email")),
        country=attrs.get("country"),
        tenant_id=attrs.get("tenant_id"),
        organization_id=attrs.get("organization_id"),
        roles=tuple(attrs.get("roles") or ()),
        jti=claims.get("jti"),
        request_ip=_request_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


async def current_context_dep(
    request: Request,
    authorization: str | None = Header(default=None),
    lv_access: str | None = Cookie(default=None),
) -> ExecutionContext:
    """Build the ExecutionContext for the current request (may be anonymous)."""
    token = _extract_bearer(authorization, lv_access)
    ctx = await _build_context_from_token(request, token)
    token_ref = set_context(ctx)
    request.state.kernel_ctx_token = token_ref
    return ctx


async def require_auth(
    ctx: ExecutionContext = Depends(current_context_dep),
) -> ExecutionContext:
    if ctx.is_anonymous:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return ctx


def require_role(*roles: str) -> Callable[..., Awaitable[ExecutionContext]]:
    """Return a dependency allowing only principals having ANY of the given roles."""

    async def _dep(ctx: ExecutionContext = Depends(require_auth)) -> ExecutionContext:
        if not ctx.has_any_role(*roles):
            await audit(
                "authz.deny",
                resource_type="role_gate",
                decision="DENY",
                payload={"required": list(roles), "actual": list(ctx.roles)},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"requires one of roles: {list(roles)}",
            )
        return ctx

    return _dep


async def enforce(
    action: str, *, resource: dict | None = None, env: dict | None = None
) -> Decision:
    """Programmatic PDP check. Raises 403 on DENY; audits both outcomes."""
    decision = authorize(action, resource=resource, env=env)
    await audit(
        action="authz." + ("permit" if decision.permitted else "deny"),
        resource_type=(resource or {}).get("resource_type", "unknown"),
        resource_id=(resource or {}).get("resource_id"),
        decision=decision.effect.value,
        payload={"action": action, "reason": decision.reason, "policy_id": decision.policy_id},
    )
    if not decision.permitted:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=decision.reason)
    return decision


def release_context(token: Token[ExecutionContext]) -> None:
    reset_context(token)
