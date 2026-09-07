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
    # extra="ignore": the root .env is shared with docker-compose and Alembic (POSTGRES_*,
    # MIGRATIONS_DATABASE_URL, KEYCLOAK_ADMIN*), none of which this app's own Settings consumes.
    # Required fields below still fail closed on their own if missing — this only stops rejecting
    # keys that belong to other processes reading the same file.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "staging", "production"]
    database_url: PostgresDsn
    # NoDecode: this is a plain comma-separated string on the wire, not JSON —
    # without it pydantic-settings tries (and fails) to JSON-parse the raw value
    # before our validator below ever sees it.
    cors_allowed_origins: Annotated[list[str], NoDecode]
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    app_name: str = "landvault-api"

    # ---- Keycloak (historical — B1 register/login/refresh proxy only) ----
    # Retired as the production identity provider by ADR-025 (Supabase Auth
    # takes that role now — see the supabase_* settings below). Kept, not
    # deleted: these still back the existing /v1/auth/register|login|refresh
    # endpoints, which are a separate, deferred disposition question
    # (IMVP-3 report §M) — not touched here.
    keycloak_realm_url: str
    keycloak_client_id: str
    keycloak_client_secret: str
    keycloak_admin_token_url: str
    keycloak_admin_api_url: str
    jwt_audience: str

    # ---- Supabase Auth (B1 — production identity provider, ADR-025) ------
    # `supabase_project_url` derives both the JWKS endpoint and the issuer
    # claim (`{url}/auth/v1/.well-known/jwks.json` and `{url}/auth/v1`
    # respectively) — the same single-setting-derives-the-rest pattern the
    # Keycloak realm_url setting above already uses, not a new convention.
    supabase_project_url: str
    # Supabase's own fixed convention for authenticated users' `aud` claim
    # is literally the string "authenticated" — configurable rather than
    # hardcoded so a differently-configured project isn't silently rejected,
    # but that is the expected value for the overwhelming majority of setups.
    supabase_jwt_audience: str = "authenticated"
    # ES256 is Supabase's current default for asymmetric (JWKS-published)
    # project signing keys. Configurable, not hardcoded into JwtVerifier
    # itself, because it's the one place a project-specific choice actually
    # varies — see app/kernel/security/jwt.py's own comment on why this
    # became a parameter rather than a second verifier class.
    supabase_jwt_algorithm: str = "ES256"

    # ---- Supabase Storage (B5 IMVP-5 — real StoragePort adapter; authorization/
    # trust model governed by docs/adr/ADR-027-supabase-storage-authorization-
    # and-tenant-isolation.md, Accepted — not ADR-025 E2, which describes
    # Postgres RLS only) ----
    # Server-side only — never sent to the browser, never logged (app.contexts.
    # evidence.adapters.supabase_storage). The backend authenticates to Storage
    # as itself (this key), never forwarding the caller's own Supabase JWT.
    # FastAPI's PDP/PEP is the *sole* tenant-authorization boundary for
    # Evidence Storage during the pilot (ADR-027 §10.0) — Storage's own RLS is
    # bypassed by this credential, not a second independent layer, unlike
    # Postgres. Accepts either of Supabase's current credential formats
    # (https://supabase.com/docs/guides/api/api-keys): a legacy JWT-form
    # service_role key, or the current non-JWT secret key (sb_secret_...) —
    # both carry the identical elevated, RLS-bypassing trust role ADR-027
    # governs; app.contexts.evidence.adapters.supabase_storage sends both
    # `apikey` and `Authorization: Bearer` with this value, live-verified
    # against Storage's actual object-level routes (not generic platform
    # docs alone — see that module's own docstring). Fail-closed:
    # no default, so a missing value aborts startup rather than silently
    # degrading (rule 2); the validator below also rejects the literal
    # unedited .env.example placeholder.
    supabase_service_role_key: str
    supabase_evidence_bucket: str = "evidence"

    @field_validator("supabase_service_role_key")
    @classmethod
    def _reject_unedited_placeholder(cls, value: str) -> str:
        # Deliberately narrow: only the exact literal .env.example default.
        # A broader "contains 'test'" heuristic would reject the test suite's
        # and export_openapi.py's own deliberate stand-in values
        # ("test-service-role-key") — a real credential's actual validity is
        # verified by Supabase's own API at call time, not guessable here.
        if value == "change-me-locally":
            raise ValueError(
                "SUPABASE_SERVICE_ROLE_KEY is still the unedited .env.example placeholder — "
                "set a real Supabase service_role or secret key before starting the backend."
            )
        return value

    @property
    def cookie_secure(self) -> bool:
        """Secure by construction, not by configuration: only ever False in
        `development`, so there is no env var whose omission silently
        weakens cookie security (docs/ENGINEERING_RULES.md #2)."""
        return self.environment != "development"

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
