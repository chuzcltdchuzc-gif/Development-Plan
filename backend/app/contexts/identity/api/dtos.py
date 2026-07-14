"""Identity API request/response shapes.

`RegisterRequest` deliberately has no `role` field — self-registration can
never assign a role (docs/adr/ADR-004 point 4); the service always defaults
to the platform's lowest-privilege role.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str
    full_name: str
    country: str | None = None


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str


class AssignRoleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str


class UserView(BaseModel):
    model_config = ConfigDict(extra="allow")

    user_id: str
    email: str
    full_name: str
    country: str
    tenant_id: str
    roles: list[str]
    account_status: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: dict
