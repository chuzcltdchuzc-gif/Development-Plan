"""HTTP security hardening.

A single middleware sets production-grade security headers on every
response, plus an in-process sliding-window rate limiter for auth-sensitive
routes. Security is a kernel concern, never a per-route concern.
"""
from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from collections.abc import Callable
from typing import cast

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# ---- 1. Headers ----------------------------------------------------------

DEFAULT_CSP = (
    "default-src 'self'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'; "
    "object-src 'none'; "
    "img-src 'self' data: blob:; "
    "font-src 'self' data:; "
    "style-src 'self' 'unsafe-inline'; "
    "script-src 'self'; "
    "connect-src 'self'; "
    "upgrade-insecure-requests"
)

DEFAULT_PERMISSIONS_POLICY = (
    "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
    "magnetometer=(), microphone=(), payment=(), usb=()"
)


def _build_security_headers() -> dict[str, str]:
    return {
        "Content-Security-Policy": os.environ.get("CSP_OVERRIDE", DEFAULT_CSP),
        "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
        "Cross-Origin-Opener-Policy": "same-origin",
        "Cross-Origin-Resource-Policy": "same-origin",
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Permissions-Policy": DEFAULT_PERMISSIONS_POLICY,
    }


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Appends the platform's security headers to every response. Idempotent:
    a header a downstream handler already set is never overridden."""

    def __init__(self, app: FastAPI) -> None:
        super().__init__(app)
        self._headers = _build_security_headers()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Starlette types call_next's return as Any; it is always a Response.
        response = cast(Response, await call_next(request))
        for key, value in self._headers.items():
            if key not in response.headers:
                response.headers[key] = value
        return response


# ---- 2. Rate limiter ------------------------------------------------------
# A pragmatic in-process sliding-window limiter (per-process, not distributed
# — production fronts this with edge/ingress rate limiting as defence in
# depth's outer layer; this middleware is the inner layer).

RATE_LIMITS: dict[str, tuple[int, int]] = {
    # path prefix -> (max_requests, window_seconds)
    "/v1/auth/login": (10, 60),
    "/v1/auth/register": (5, 60),
    "/v1/auth/refresh": (30, 60),
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window per-IP rate limiter. Returns 429 on overflow."""

    def __init__(self, app: FastAPI, *, enabled: bool = True) -> None:
        super().__init__(app)
        self._enabled = enabled
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _bucket(self, path: str) -> tuple[int, int] | None:
        for prefix, limit in RATE_LIMITS.items():
            if path.startswith(prefix):
                return limit
        return None

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self._enabled:
            return cast(Response, await call_next(request))
        bucket = self._bucket(request.url.path)
        if bucket is None:
            return cast(Response, await call_next(request))
        max_requests, window = bucket
        key = f"{self._client_ip(request)}::{self._prefix_for(request.url.path)}"
        now = time.monotonic()
        hits = self._hits[key]
        cutoff = now - window
        while hits and hits[0] < cutoff:
            hits.popleft()
        if len(hits) >= max_requests:
            retry_after = int(window - (now - hits[0])) if hits else window
            return JSONResponse(
                status_code=429,
                media_type="application/problem+json",
                content={
                    "type": "about:blank",
                    "title": "Too Many Requests",
                    "status": 429,
                    "detail": f"Limit {max_requests}/{window}s exceeded for "
                    f"{self._prefix_for(request.url.path)}",
                    "instance": str(request.url),
                },
                headers={"Retry-After": str(max(1, retry_after))},
            )
        hits.append(now)
        return cast(Response, await call_next(request))

    @staticmethod
    def _client_ip(request: Request) -> str:
        """The direct TCP peer only — NEVER X-Forwarded-For, which any
        client can set to an arbitrary value. Confirmed against a live
        server: trusting it made the rate limiter completely bypassable
        (a different spoofed IP per request, zero 429s across 15 requests
        that would otherwise have tripped the limit at request 11). There
        is no configured trusted-reverse-proxy allowlist in this
        deployment (docs/adr/ADR-004's "only trusted behind a configured
        proxy allowlist" — the allowlist doesn't exist yet, so the header
        is untrusted, full stop, not partially trusted)."""
        return request.client.host if request.client else "unknown"

    @staticmethod
    def _prefix_for(path: str) -> str:
        for prefix in RATE_LIMITS:
            if path.startswith(prefix):
                return prefix
        return path


def configure_security(app: FastAPI, *, rate_limit_enabled: bool = True) -> None:
    # Starlette's add_middleware stub can't express a middleware class whose
    # __init__ takes extra kwargs beyond `app` — a known stub limitation, not
    # a real type error (both classes are exercised directly by tests too).
    app.add_middleware(RateLimitMiddleware, enabled=rate_limit_enabled)  # type: ignore[arg-type]
    app.add_middleware(SecurityHeadersMiddleware)  # type: ignore[arg-type]
