"""Hermetic CLI argument/stdin tests (GD-016 §11 tests 7, 12, 41, 42
hermetic half; §4)."""
from __future__ import annotations

import pytest
from jwt import InvalidTokenError

from app.contexts.identity.cli.bootstrap_first_tenant import (
    BootstrapCliError,
    build_arg_parser,
    verify_and_build_context,
)
from app.main import create_app


class _RaisingVerifier:
    async def verify(self, token: str) -> dict:
        raise InvalidTokenError("bad token")


async def _noop_hydrator(subject: str) -> dict | None:
    return None


# ---- Test 7: malformed/expired JWT -----------------------------------------


@pytest.mark.asyncio
async def test_malformed_jwt_fails_closed_before_any_binding() -> None:
    with pytest.raises(BootstrapCliError, match="invalid or expired"):
        await verify_and_build_context(
            token="not-a-real-token", verifier=_RaisingVerifier(), hydrator=_noop_hydrator
        )


# ---- Test 12: no --email argument exists under any name --------------------


def test_arg_parser_has_no_email_argument() -> None:
    parser = build_arg_parser()
    dests = {action.dest for action in parser._actions}
    assert "email" not in dests
    for action in parser._actions:
        for opt in action.option_strings:
            assert "email" not in opt.lower()


def test_arg_parser_has_no_token_argument() -> None:
    parser = build_arg_parser()
    dests = {action.dest for action in parser._actions}
    assert "token" not in dests
    for action in parser._actions:
        for opt in action.option_strings:
            assert "token" not in opt.lower()


def test_arg_parser_requires_tenant_role_full_name_country() -> None:
    parser = build_arg_parser()
    dests = {action.dest for action in parser._actions}
    assert {"tenant_name", "role", "full_name", "country"}.issubset(dests)
    with pytest.raises(SystemExit):
        parser.parse_args([])  # all four are required


def test_arg_parser_role_choices_limited_to_allowlist() -> None:
    parser = build_arg_parser()
    role_action = next(a for a in parser._actions if a.dest == "role")
    assert set(role_action.choices) == {"compliance_officer", "surveyor_general"}


# ---- Test 41: no HTTP route exposes either bootstrap action ----------------


def test_no_http_route_exposes_bootstrap_actions() -> None:
    app = create_app()
    for route in app.routes:
        path = getattr(route, "path", "")
        name = getattr(route, "name", "") or ""
        assert "bootstrap" not in path.lower()
        assert "bootstrap" not in name.lower()


def test_cli_module_defines_no_router() -> None:
    import app.contexts.identity.cli.bootstrap_first_tenant as cli_module

    assert not hasattr(cli_module, "router")
    assert not hasattr(cli_module, "APIRouter")


# ---- Test 42 (hermetic half): token never appears in error text -----------


@pytest.mark.asyncio
async def test_token_never_appears_in_rejection_message() -> None:
    secret_token = "sb-super-secret-token-xyz-987654321"  # noqa: S105 - test fixture only

    class _SecretLeakCheckVerifier:
        async def verify(self, token: str) -> dict:
            raise InvalidTokenError(f"rejected token {token}")  # what NOT reusing it looks like

    # verify_and_build_context's own BootstrapCliError message is fixed
    # text ("invalid or expired access token") and never interpolates the
    # raw token or the underlying exception's own message/args.
    with pytest.raises(BootstrapCliError) as exc_info:
        await verify_and_build_context(
            token=secret_token, verifier=_SecretLeakCheckVerifier(), hydrator=_noop_hydrator
        )
    assert secret_token not in str(exc_info.value)
