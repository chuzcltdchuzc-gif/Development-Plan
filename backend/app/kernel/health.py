"""Liveness/readiness health checks.

Readiness fails closed: any dependency-check error reports not-ready,
never a swallowed exception reported as a pass (docs/DOD.md #1).
"""
from __future__ import annotations

from fastapi import APIRouter, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


def build_health_router(engine: AsyncEngine) -> APIRouter:
    router = APIRouter(tags=["health"])

    @router.get("/health/live")
    async def liveness() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/health/ready")
    async def readiness(response: Response) -> dict[str, str]:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"status": "not_ready", "reason": "database_unreachable"}
        return {"status": "ready"}

    return router
