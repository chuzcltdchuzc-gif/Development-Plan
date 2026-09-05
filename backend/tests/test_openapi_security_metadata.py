"""OpenAPI Security Metadata Hardening.

Asserts the FastAPI-exported schema accurately documents bearer
authentication — a documentation-fidelity contract, not a runtime-auth
test (those already exist: test_unprovisioned_identity.py,
test_authorization.py, test_b2_tenants.py, etc., and stay green
unchanged by this slice). Uses the same router objects app.main wires
(via tests.app_factory), so this schema is what production actually
exports, minus the DB/JWKS wiring these assertions don't need.
"""
from __future__ import annotations

from tests.app_factory import build_test_app


def _schema() -> dict:
    return build_test_app().app.openapi()


def test_bearer_security_scheme_is_declared_correctly() -> None:
    schemes = _schema()["components"]["securitySchemes"]
    assert schemes.keys() == {"SupabaseBearerAuth"}
    scheme = schemes["SupabaseBearerAuth"]
    assert scheme["type"] == "http"
    assert scheme["scheme"] == "bearer"
    assert scheme["bearerFormat"] == "JWT"


def test_representative_protected_routes_require_bearer_auth() -> None:
    schema = _schema()
    expected = [
        ("get", "/v1/parcels"),  # Registry
        ("put", "/v1/spatial/parcels/{parcel_id}/geometry"),  # Spatial
        ("get", "/v1/admin/tenants"),  # Admin
        ("get", "/v1/auth/me"),  # Auth (require_auth, not just role-gated)
    ]
    for method, path in expected:
        op = schema["paths"][path][method]
        assert op.get("security") == [{"SupabaseBearerAuth": []}], (
            f"{method.upper()} {path} should require SupabaseBearerAuth"
        )


def test_protected_routes_no_longer_show_raw_auth_header_as_a_plain_parameter() -> None:
    """Before this hardening, every protected route's *only* representation
    of auth was a plain optional `authorization` header / `lv_access`
    cookie parameter (current_context_dep's old Header()/Cookie() params).
    Now that extraction reads `request.headers`/`request.cookies` directly,
    those parameters must be gone — replaced entirely by the `security`
    requirement asserted above."""
    schema = _schema()
    op = schema["paths"]["/v1/parcels"]["get"]
    param_names = {p["name"] for p in op.get("parameters") or []}
    assert "authorization" not in param_names
    assert "lv_access" not in param_names


def test_genuinely_public_routes_have_no_security_requirement() -> None:
    schema = _schema()
    expected = [
        ("post", "/v1/auth/register"),
        ("post", "/v1/auth/login"),
        ("post", "/v1/auth/invitations/accept"),
        ("post", "/v1/auth/refresh"),
    ]
    for method, path in expected:
        op = schema["paths"][path][method]
        assert not op.get("security"), (
            f"{method.upper()} {path} is a public route and must not require bearer auth"
        )


def test_no_oauth_scopes_or_schemes_invented() -> None:
    schema = _schema()
    for scheme in schema["components"]["securitySchemes"].values():
        assert scheme["type"] != "oauth2"
    for methods in schema["paths"].values():
        for op in methods.values():
            for requirement in op.get("security") or []:
                for scopes in requirement.values():
                    assert scopes == []
