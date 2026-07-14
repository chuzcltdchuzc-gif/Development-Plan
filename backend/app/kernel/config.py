"""Fail-closed application configuration.

Every security-relevant setting is required with no default — a missing
value must abort startup, never silently degrade to a permissive one.
See docs/ENGINEERING_RULES.md #2 and CLAUDE.md rule 2.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="forbid")

    environment: Literal["development", "staging", "production"]
    database_url: PostgresDsn
    # NoDecode: this is a plain comma-separated string on the wire, not JSON —
    # without it pydantic-settings tries (and fails) to JSON-parse the raw value
    # before our validator below ever sees it.
    cors_allowed_origins: Annotated[list[str], NoDecode]
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    app_name: str = "landvault-api"

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _parse_and_guard_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            value = [origin.strip() for origin in value.split(",") if origin.strip()]
        if not value:
            raise ValueError("CORS_ALLOWED_ORIGINS must list at least one explicit origin")
        if "*" in value:
            raise ValueError(
                "CORS_ALLOWED_ORIGINS must not contain '*' — wildcard origin combined "
                "with credentials was the Emergent audit's CORS finding (ADR-004)."
            )
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # required fields come from env, not call args
