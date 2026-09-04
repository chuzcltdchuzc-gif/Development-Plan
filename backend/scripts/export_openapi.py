#!/usr/bin/env python3
"""Deterministic FastAPI OpenAPI exporter (OpenAPI Source-of-Truth Hardening).

Loads the production app definition (`app.main.create_app`) and writes its
authoritative OpenAPI schema to `lib/api-spec/openapi.yaml` — the single
generated-client input. No database or network I/O occurs: SQLAlchemy
engines and the Supabase JWKS provider are constructed lazily by
`create_app()` and never touched here; `app.openapi()` only introspects
already-registered routes/models.

The env vars `Settings` requires are fail-closed (app/kernel/config.py) but
irrelevant to the exported *shape* — only route registration (fixed in
code) affects that. The placeholders below are the same ones
tests/conftest.py already uses for the identical reason, not real
credentials.

Usage:
    python backend/scripts/export_openapi.py          # write the spec
    python backend/scripts/export_openapi.py --check  # CI drift gate
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
SPEC_PATH = REPO_ROOT / "lib" / "api-spec" / "openapi.yaml"

_HEADER = """\
# GENERATED FILE — do not edit by hand.
# Source of truth: backend/app (FastAPI). Regenerate with:
#   python backend/scripts/export_openapi.py
# CI (frontend-ci.yml) fails the build if this file drifts from that output.
"""


def _set_placeholder_settings() -> None:
    # Same placeholders as backend/tests/conftest.py, for the same reason:
    # Settings is fail-closed (must be present to construct the app) but no
    # value here influences the exported OpenAPI shape.
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
        "KEYCLOAK_ADMIN_TOKEN_URL", "https://idp.test/realms/landvault/protocol/openid-connect/token"
    )
    os.environ.setdefault("KEYCLOAK_ADMIN_API_URL", "https://idp.test/admin/realms/landvault")
    os.environ.setdefault("JWT_AUDIENCE", "landvault-api")
    os.environ.setdefault("SUPABASE_PROJECT_URL", "https://test-project.supabase.test")


def _load_app():
    _set_placeholder_settings()
    sys.path.insert(0, str(BACKEND_ROOT))
    from app.main import create_app

    return create_app()


def export_schema_yaml() -> str:
    import yaml

    app = _load_app()
    schema = app.openapi()
    body = yaml.dump(schema, sort_keys=False, default_flow_style=False, allow_unicode=True)
    return _HEADER + "\n" + body


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the committed spec would change, without writing",
    )
    args = parser.parse_args()

    content = export_schema_yaml()

    if args.check:
        current = SPEC_PATH.read_text(encoding="utf-8") if SPEC_PATH.exists() else ""
        if current != content:
            print(
                f"::error::{SPEC_PATH} is stale relative to the current FastAPI app. "
                "Run 'python backend/scripts/export_openapi.py' and commit the result.",
                file=sys.stderr,
            )
            return 1
        print(f"{SPEC_PATH} matches the current FastAPI app.")
        return 0

    SPEC_PATH.write_text(content, encoding="utf-8")
    print(f"Wrote {SPEC_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
