"""Hermetic verified-email-contract tests (GD-016 §11 tests 8-11; §5)."""
from __future__ import annotations

import pytest

from app.contexts.identity.cli.bootstrap_first_tenant import (
    BootstrapCliError,
    verify_and_build_context,
)


class _FakeVerifier:
    def __init__(self, claims: dict | None = None, *, raises: Exception | None = None) -> None:
        self._claims = claims
        self._raises = raises

    async def verify(self, token: str) -> dict:
        if self._raises is not None:
            raise self._raises
        assert self._claims is not None
        return self._claims


async def _noop_hydrator(subject: str) -> dict | None:
    return None


BASE_CLAIMS = {"sub": "supabase-subject-1", "email": "user@example.test"}


# ---- Test 8: verified claims missing email entirely ------------------------


@pytest.mark.asyncio
async def test_missing_email_claim_fails_closed_before_binding() -> None:
    claims = {"sub": "supabase-subject-1"}  # no "email" key at all
    verifier = _FakeVerifier(claims)
    with pytest.raises(BootstrapCliError, match="no usable email"):
        await verify_and_build_context(token="t", verifier=verifier, hydrator=_noop_hydrator)


# ---- Test 9: blank/whitespace-only email claim ------------------------------


@pytest.mark.asyncio
async def test_blank_email_claim_fails_closed() -> None:
    claims = {**BASE_CLAIMS, "email": "   "}
    verifier = _FakeVerifier(claims)
    with pytest.raises(BootstrapCliError, match="no usable email"):
        await verify_and_build_context(token="t", verifier=verifier, hydrator=_noop_hydrator)


@pytest.mark.asyncio
async def test_empty_string_email_claim_fails_closed() -> None:
    claims = {**BASE_CLAIMS, "email": ""}
    verifier = _FakeVerifier(claims)
    with pytest.raises(BootstrapCliError, match="no usable email"):
        await verify_and_build_context(token="t", verifier=verifier, hydrator=_noop_hydrator)


# ---- Test 10: malformed email claim (fails Email.parse's regex) ------------


@pytest.mark.asyncio
async def test_malformed_email_claim_fails_closed() -> None:
    claims = {**BASE_CLAIMS, "email": "not-an-email-address"}
    verifier = _FakeVerifier(claims)
    with pytest.raises(BootstrapCliError, match="invalid"):
        await verify_and_build_context(token="t", verifier=verifier, hydrator=_noop_hydrator)


# ---- Test 11: valid email claim, mixed case/whitespace, normalized --------


@pytest.mark.asyncio
async def test_valid_email_claim_is_normalized() -> None:
    claims = {**BASE_CLAIMS, "email": "  User.Name@Example.TEST  "}
    verifier = _FakeVerifier(claims)
    subject, ctx = await verify_and_build_context(
        token="t", verifier=verifier, hydrator=_noop_hydrator
    )
    assert subject == "supabase-subject-1"
    assert ctx.email == "user.name@example.test"
    assert ctx.principal_id == "supabase-subject-1"
