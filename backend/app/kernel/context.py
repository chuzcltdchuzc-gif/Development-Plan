"""Request-scoped execution context.

Carries the verified principal's identity and attributes through every
downstream call. Built once by the PEP from a verified JWT's claims — never
from request body/query params, which callers can put anything in
(docs/ENGINEERING_RULES.md #1, #3).
"""
from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass, field

ANONYMOUS_PRINCIPAL_ID = "anonymous"


@dataclass(frozen=True)
class ExecutionContext:
    principal_id: str
    email: str | None = None
    country: str | None = None
    tenant_id: str | None = None
    organization_id: str | None = None
    roles: tuple[str, ...] = ()
    scopes: tuple[str, ...] = ()
    attributes: dict = field(default_factory=dict)
    session_id: str | None = None
    jti: str | None = None
    correlation_id: str | None = None
    request_ip: str | None = None
    user_agent: str | None = None

    @property
    def is_anonymous(self) -> bool:
        return self.principal_id == ANONYMOUS_PRINCIPAL_ID

    @property
    def is_authenticated(self) -> bool:
        return not self.is_anonymous

    def has_any_role(self, *roles: str) -> bool:
        return bool(set(self.roles) & set(roles))


ANONYMOUS = ExecutionContext(principal_id=ANONYMOUS_PRINCIPAL_ID)

_current: ContextVar[ExecutionContext] = ContextVar(
    "landvault_execution_context", default=ANONYMOUS
)


def current_context() -> ExecutionContext:
    return _current.get()


def set_context(ctx: ExecutionContext) -> Token[ExecutionContext]:
    return _current.set(ctx)


def reset_context(token: Token[ExecutionContext]) -> None:
    _current.reset(token)
