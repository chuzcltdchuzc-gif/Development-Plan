"""Application entrypoint — FastAPI app factory (B0 kernel)."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine

from app.kernel.config import get_settings
from app.kernel.errors import register_error_handlers
from app.kernel.health import build_health_router
from app.kernel.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)

    engine = create_async_engine(str(settings.database_url))
    app.include_router(build_health_router(engine))

    return app


app = create_app()
