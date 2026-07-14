"""Policy Information Point — supplies attributes the PDP needs.

Principal attributes come entirely from the verified JWT claims carried on
the ExecutionContext (no DB lookups in the hot path). Domain code uses
`resource_descriptor` to build the resource dict passed to `authorize()`.
"""
from __future__ import annotations

from typing import Any

from app.kernel.context import ExecutionContext, current_context


def principal_attributes(ctx: ExecutionContext | None = None) -> dict[str, Any]:
    ctx = ctx or current_context()
    return {
        "principal_id": ctx.principal_id,
        "country": ctx.country,
        "tenant_id": ctx.tenant_id,
        "organization_id": ctx.organization_id,
        "roles": list(ctx.roles),
        **dict(ctx.attributes),
    }


def resource_descriptor(
    resource_type: str,
    *,
    resource_id: str | None = None,
    tenant_id: str | None = None,
    country: str | None = None,
    organization_id: str | None = None,
    owner_id: str | None = None,
    classification: str | None = None,
    extra: dict | None = None,
) -> dict[str, Any]:
    desc: dict[str, Any] = {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "tenant_id": tenant_id,
        "country": country,
        "organization_id": organization_id,
        "owner_id": owner_id,
        "classification": classification,
    }
    if extra:
        desc.update(extra)
    return {k: v for k, v in desc.items() if v is not None}
