"""Sets required env vars before app.main is imported by any test module."""
import os

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://landvault:landvault@localhost:5432/landvault_test"
)
os.environ.setdefault("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.setdefault("KEYCLOAK_REALM_URL", "https://idp.test/realms/landvault")
os.environ.setdefault("KEYCLOAK_CLIENT_ID", "landvault-api-test")
os.environ.setdefault("KEYCLOAK_CLIENT_SECRET", "test-secret")
os.environ.setdefault(
    # Client-credentials tokens come from the client's OWN realm, not
    # `master` — confirmed against a live Keycloak (401 otherwise).
    "KEYCLOAK_ADMIN_TOKEN_URL", "https://idp.test/realms/landvault/protocol/openid-connect/token"
)
os.environ.setdefault("KEYCLOAK_ADMIN_API_URL", "https://idp.test/admin/realms/landvault")
os.environ.setdefault("JWT_AUDIENCE", "landvault-api")
# Supabase Auth (B1 — production identity provider, ADR-025). Only
# SUPABASE_PROJECT_URL has no default in Settings; the placeholder below is
# never actually contacted by the hermetic suite (nothing here exercises a
# real JWKS fetch — that's SupabaseJWKSProvider, unit-tested separately
# against tests/fakes/supabase_jwks.py, not against this URL).
os.environ.setdefault("SUPABASE_PROJECT_URL", "https://test-project.supabase.test")
