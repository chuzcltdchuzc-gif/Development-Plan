"""Standalone operator entrypoint and sole composition root for the GD-016
/ ADR-031 (as qualified by ADR-032) first-tenant bootstrap command.

No new HTTP route exists anywhere in this module, and `app/main.py` is
never modified to import or register anything from it -- the running
FastAPI application process never registers either bootstrap PDP action
and can never reach either, through any router (GD-016 §3/§4/§6/§12).

Invoked as a standalone process:

    python -m app.contexts.identity.cli.bootstrap_first_tenant \\
        --tenant-name "..." --role compliance_officer \\
        --full-name "..." --country NG
    (the Supabase access token is read from stdin, never from argv)
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Awaitable, Callable

from fastapi import HTTPException
from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.contexts.identity.adapters.supabase import SupabaseJWKSProvider, supabase_issuer
from app.contexts.identity.application.bootstrap_service import (
    BootstrapResult,
    bootstrap_first_tenant,
)
from app.contexts.identity.authorization.bootstrap_policies import (
    ALLOWED_BOOTSTRAP_ROLES,
    register_bootstrap_policies,
)
from app.contexts.identity.context_hydration import build_production_context_hydrator
from app.contexts.identity.domain.value_objects import CountryCode, Email
from app.kernel.audit import configure_eager_fallback
from app.kernel.audit_postgres import EagerPostgresAuditStore
from app.kernel.config import get_settings
from app.kernel.context import ExecutionContext, reset_context, set_context
from app.kernel.db import build_session_factory
from app.kernel.security.jwt import JwtVerifier

ContextHydrator = Callable[[str], Awaitable[dict | None]]


class BootstrapCliError(Exception):
    """A clean, operator-facing rejection -- never carries the token."""


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bootstrap-first-tenant",
        description=(
            "GD-016 / ADR-031 (as qualified by ADR-032): provision the "
            "platform's first tenant and first privileged user. The "
            "Supabase access token is read from stdin only -- never as a "
            "command-line argument."
        ),
    )
    parser.add_argument("--tenant-name", required=True, help="Name of the first tenant")
    parser.add_argument(
        "--role",
        required=True,
        choices=sorted(ALLOWED_BOOTSTRAP_ROLES),
        help="Role granted to the first user",
    )
    parser.add_argument("--full-name", required=True, help="First user's full name")
    parser.add_argument(
        "--country", required=True, help="ISO 3166-1 alpha-2 country code (no default)"
    )
    # Deliberately no --email argument anywhere in this parser (GD-016 §4):
    # the email is sourced exclusively from the verified JWT's own `email`
    # claim (see verify_and_build_context below), never from an operator
    # argument, and may never be overridden by one.
    return parser


def validate_cli_inputs(args: argparse.Namespace) -> tuple[str, str, str, str]:
    """Tenant name / role / full name / country validation (GD-016 §4).
    Raises `BootstrapCliError` on any failure. Performed before the token
    is even read from stdin -- no PDP call, no session, no audit write
    occurs if this fails."""
    tenant_name = (args.tenant_name or "").strip()
    if not tenant_name:
        raise BootstrapCliError("tenant name must not be empty")
    full_name = (args.full_name or "").strip()
    if not full_name:
        raise BootstrapCliError("full name must not be empty")
    if args.role not in ALLOWED_BOOTSTRAP_ROLES:
        # argparse's own `choices=` already enforces this; kept as an
        # explicit, defense-in-depth check for any non-argparse caller.
        raise BootstrapCliError(f"role must be one of {sorted(ALLOWED_BOOTSTRAP_ROLES)}")
    try:
        country = CountryCode((args.country or "").upper()).value
    except ValueError as exc:
        raise BootstrapCliError(f"country is invalid: {exc}") from exc
    return tenant_name, args.role, full_name, country


async def verify_and_build_context(
    *, token: str, verifier: JwtVerifier, hydrator: ContextHydrator
) -> tuple[str, ExecutionContext]:
    """GD-016 §9 steps 1-2 (§6 steps 7-10): verify the token, validate the
    verified email (§5), hydrate, and construct -- but do not yet bind --
    the bootstrap `ExecutionContext`. Raises `BootstrapCliError` on any
    failure; none of these failures ever call `set_context()` (§6 step 11,
    mandatory test 50)."""
    try:
        claims = await verifier.verify(token)
    except InvalidTokenError as exc:
        raise BootstrapCliError("invalid or expired access token") from exc

    subject = str(claims["sub"])
    raw_email = claims.get("email")
    if not raw_email or not str(raw_email).strip():
        raise BootstrapCliError("verified token carries no usable email claim")
    try:
        normalized_email = Email.parse(str(raw_email)).value
    except ValueError as exc:
        raise BootstrapCliError(f"verified token's email claim is invalid: {exc}") from exc

    attrs = await hydrator(subject) or {}
    # principal_id is bound to `subject` -- the cryptographically verified
    # Supabase JWT `sub` -- directly and unconditionally, never to
    # attrs.get("principal_id", subject). That hydrator fallback is
    # correct for ordinary HTTP runtime behaviour (an already-provisioned
    # active user's internal LandVault id); it is not the bootstrap
    # actor-attribution rule ADR-031 establishes, under which every
    # bootstrap audit event must record the verified subject itself,
    # regardless of whatever internal id the hydrator also resolves for
    # it (GD-016 §6 step 10, §9 actor-attribution rule). Hydrated attrs
    # are used only for country/tenant_id/organization_id/roles/
    # attributes -- never for principal_id.
    ctx = ExecutionContext(
        principal_id=subject,
        email=normalized_email,
        country=attrs.get("country"),
        tenant_id=attrs.get("tenant_id"),
        organization_id=attrs.get("organization_id"),
        roles=tuple(attrs.get("roles") or ()),
        attributes=attrs.get("attributes") or {},
    )
    return subject, ctx


async def run_bootstrap(
    *,
    token: str,
    tenant_name: str,
    requested_role: str,
    full_name: str,
    country: str,
    verifier: JwtVerifier,
    hydrator: ContextHydrator,
    session_factory: async_sessionmaker[AsyncSession],
) -> BootstrapResult:
    """Full orchestration for one bootstrap attempt, given an
    already-constructed verifier/hydrator/session_factory. `_amain` below
    builds these from settings for a real invocation; tests inject fakes
    directly."""
    subject, ctx = await verify_and_build_context(
        token=token, verifier=verifier, hydrator=hydrator
    )
    # Always set by verify_and_build_context's own ExecutionContext(email=
    # normalized_email, ...) construction -- narrows ExecutionContext.email's
    # general `str | None` for the (necessarily str) bootstrap_first_tenant
    # parameter below.
    assert ctx.email is not None
    # First point at which any bootstrap ExecutionContext exists in the
    # ambient ContextVar at all (§6 step 11).
    token_ref = set_context(ctx)
    try:
        register_bootstrap_policies()
        return await bootstrap_first_tenant(
            session_factory=session_factory,
            subject=subject,
            email=ctx.email,
            full_name=full_name,
            country=country,
            tenant_name=tenant_name,
            requested_role=requested_role,
        )
    finally:
        # Every post-binding exit path -- success, Stage-1/Stage-2 DENY,
        # any audit or mutation failure -- resets the context exactly once
        # (§6 step 15, mandatory test 51).
        reset_context(token_ref)


async def _amain(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        tenant_name, role, full_name, country = validate_cli_inputs(args)
    except BootstrapCliError as exc:
        print(f"bootstrap rejected: {exc}", file=sys.stderr)
        return 1

    token = sys.stdin.readline().strip()
    if not token:
        print("bootstrap rejected: no access token supplied on stdin", file=sys.stderr)
        return 1

    settings = get_settings()
    engine = create_async_engine(str(settings.database_url))
    try:
        session_factory = build_session_factory(engine)
        # Before any call to enforce() -- a deterministic, mandatory
        # wiring requirement of this composition root, not an optional
        # fallback (GD-016 §6 step 4, mandatory tests 44/52).
        configure_eager_fallback(EagerPostgresAuditStore(session_factory))

        jwks = SupabaseJWKSProvider(project_url=settings.supabase_project_url)
        verifier = JwtVerifier(
            jwks=jwks,
            issuer=supabase_issuer(settings.supabase_project_url),
            audience=settings.supabase_jwt_audience,
            algorithms=[settings.supabase_jwt_algorithm],
        )
        hydrator = build_production_context_hydrator(session_factory)

        result = await run_bootstrap(
            token=token,
            tenant_name=tenant_name,
            requested_role=role,
            full_name=full_name,
            country=country,
            verifier=verifier,
            hydrator=hydrator,
            session_factory=session_factory,
        )
    except BootstrapCliError as exc:
        print(f"bootstrap rejected: {exc}", file=sys.stderr)
        return 1
    except HTTPException as exc:
        print(f"bootstrap denied: {exc.detail}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - operational failure path
        print(f"bootstrap failed: {exc}", file=sys.stderr)
        return 1
    finally:
        await engine.dispose()

    print(
        f"bootstrap succeeded: tenant_id={result.tenant_id} user_id={result.user_id} "
        f"role={result.role}"
    )
    return 0


def main() -> None:
    sys.exit(asyncio.run(_amain()))


if __name__ == "__main__":
    main()
