"""Identity API router — /v1/auth/*.

Routers are composition only: parse + validate via DTOs, call AuthService,
shape the response and set the refresh cookie. No business logic lives
here. AuthService is built fresh per request (Depends(get_auth_service)),
never a fixed instance shared across requests — see
app.contexts.identity.dependencies for why.
"""
from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Header, Request, Response, status

from app.contexts.identity.api.dtos import LoginRequest, RegisterRequest, TokenResponse
from app.contexts.identity.application.auth_service import AuthService
from app.contexts.identity.dependencies import get_auth_service
from app.kernel.authorization.pep import require_auth
from app.kernel.config import get_settings
from app.kernel.context import ExecutionContext

REFRESH_COOKIE_NAME = "lv_refresh"
REFRESH_COOKIE_PATH = "/v1/auth"

router = APIRouter(prefix="/v1/auth", tags=["identity"])


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    fwd = request.headers.get("x-forwarded-for")
    ip = fwd.split(",", 1)[0].strip() if fwd else (request.client.host if request.client else None)
    return request.headers.get("user-agent"), ip


def _set_refresh_cookie(response: Response, refresh_token: str, *, secure: bool) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


def _token_response(tokens: dict) -> dict:
    return {
        "access_token": tokens["access_token"],
        "token_type": tokens["token_type"],
        "expires_in": tokens["expires_in"],
        "user": tokens["user"],
    }


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    tokens = await auth_service.register_local(
        email=body.email, password=body.password, full_name=body.full_name, country=body.country
    )
    _set_refresh_cookie(response, tokens["refresh_token"], secure=get_settings().cookie_secure)
    return _token_response(tokens)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    ua, ip = _client_meta(request)
    tokens = await auth_service.login_local(
        email=body.email, password=body.password, user_agent=ua, ip=ip
    )
    _set_refresh_cookie(response, tokens["refresh_token"], secure=get_settings().cookie_secure)
    return _token_response(tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    x_refresh_token: str | None = Header(default=None),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    refresh_token = refresh_cookie or x_refresh_token or ""
    ua, ip = _client_meta(request)
    tokens = await auth_service.refresh(refresh_token=refresh_token, user_agent=ua, ip=ip)
    _set_refresh_cookie(response, tokens["refresh_token"], secure=get_settings().cookie_secure)
    return _token_response(tokens)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    _ctx: ExecutionContext = Depends(require_auth),
    auth_service: AuthService = Depends(get_auth_service),
) -> Response:
    await auth_service.logout(refresh_token=refresh_cookie)
    _clear_refresh_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me")
async def me(ctx: ExecutionContext = Depends(require_auth)) -> dict:
    return {
        "user_id": ctx.principal_id,
        "email": ctx.email,
        "country": ctx.country,
        "tenant_id": ctx.tenant_id,
        "organization_id": ctx.organization_id,
        "roles": list(ctx.roles),
    }
