"""CSRF protection for server-rendered, cookie-authenticated forms."""

from __future__ import annotations

import hmac
import logging
import secrets

from fastapi import HTTPException, Request, status

from app.core.config import cookie_settings


CSRF_COOKIE_NAME = "csrf_token"
CSRF_FORM_FIELD_NAME = "csrf_token"
logger = logging.getLogger(__name__)


def ensure_csrf_token(request: Request) -> str:
    token = request.cookies.get(CSRF_COOKIE_NAME) or secrets.token_urlsafe(32)
    request.state.csrf_token = token
    return token


def set_csrf_cookie(request: Request, response) -> None:
    token = getattr(request.state, "csrf_token", None)
    if not token or request.cookies.get(CSRF_COOKIE_NAME) == token:
        return
    settings = cookie_settings()
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.secure,
        samesite=settings.samesite,
        max_age=settings.max_age_seconds,
    )


async def require_csrf_token(request: Request) -> None:
    form_data = await request.form()
    submitted_token = form_data.get(CSRF_FORM_FIELD_NAME)
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    if not (
        isinstance(submitted_token, str)
        and cookie_token
        and hmac.compare_digest(submitted_token, cookie_token)
    ):
        logger.warning("Rejected CSRF validation method=%s path=%s", request.method, request.url.path)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token",
        )
