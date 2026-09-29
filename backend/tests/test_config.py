import pytest
from pydantic import ValidationError

from app.kernel.config import Settings


def test_missing_database_url_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    # _env_file=None: a real .env exists at repo root (local dev) and would otherwise supply
    # DATABASE_URL regardless of the process-env deletion above, since pydantic-settings reads
    # the dotenv file as its own source independent of monkeypatch. Disabling it here isolates
    # the assertion this test actually makes — a missing DATABASE_URL fails closed — from
    # whatever happens to be in the developer's local .env.
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_wildcard_cors_origin_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")
    with pytest.raises(ValidationError):
        Settings()  # type: ignore[call-arg]


def test_empty_cors_origin_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "")
    with pytest.raises(ValidationError):
        Settings()  # type: ignore[call-arg]
