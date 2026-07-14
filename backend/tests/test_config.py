import pytest
from pydantic import ValidationError

from app.kernel.config import Settings


def test_missing_database_url_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings()  # type: ignore[call-arg]  # required fields come from env, not call args


def test_wildcard_cors_origin_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")
    with pytest.raises(ValidationError):
        Settings()  # type: ignore[call-arg]


def test_empty_cors_origin_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "")
    with pytest.raises(ValidationError):
        Settings()  # type: ignore[call-arg]
