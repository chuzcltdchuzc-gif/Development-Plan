"""RFC 7807 (application/problem+json) error responses.

No endpoint returns an ad-hoc error shape — every error, including
unhandled exceptions, is normalized to a Problem Details document.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

PROBLEM_MEDIA_TYPE = "application/problem+json"


def _problem_response(status_code: int, title: str, detail: str, instance: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        media_type=PROBLEM_MEDIA_TYPE,
        content={
            "type": "about:blank",
            "title": title,
            "status": status_code,
            "detail": detail,
            "instance": instance,
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "HTTP error"
        return _problem_response(exc.status_code, detail, detail, str(request.url))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _problem_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Validation error",
            str(exc.errors()),
            str(request.url),
        )

    @app.exception_handler(Exception)
    async def handle_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception", exc_info=exc)
        return _problem_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Internal server error",
            "An unexpected error occurred.",
            str(request.url),
        )
