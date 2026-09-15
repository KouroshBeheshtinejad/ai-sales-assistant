"""Environment-backed settings with strict production requirements."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass


PRODUCTION_ENVIRONMENTS = frozenset({"production", "prod"})


def app_environment() -> str:
    return os.getenv("APP_ENV", "development").strip().casefold()


def is_production() -> bool:
    return app_environment() in PRODUCTION_ENVIRONMENTS


def _enabled(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on"}


def database_url() -> str:
    value = os.getenv("DATABASE_URL")
    if value:
        return value
    if is_production():
        raise RuntimeError("DATABASE_URL must be configured when APP_ENV is production")
    return "sqlite:///./ai_sales.db"


def secret_key() -> str:
    value = os.getenv("SECRET_KEY")
    if value:
        return value
    if is_production():
        raise RuntimeError("SECRET_KEY must be configured when APP_ENV is production")
    return secrets.token_urlsafe(32)


def allowed_hosts() -> list[str]:
    configured_hosts = [
        host.strip() for host in os.getenv("APP_ALLOWED_HOSTS", "").split(",") if host.strip()
    ]
    if configured_hosts:
        if is_production() and "*" in configured_hosts:
            raise RuntimeError("APP_ALLOWED_HOSTS cannot include * in production")
        return configured_hosts
    if is_production():
        raise RuntimeError("APP_ALLOWED_HOSTS must be configured when APP_ENV is production")
    return ["*"]


@dataclass(frozen=True)
class CookieSettings:
    secure: bool
    samesite: str
    max_age_seconds: int


def cookie_settings() -> CookieSettings:
    secure = True if is_production() else _enabled(os.getenv("SESSION_COOKIE_SECURE"), False)
    samesite = os.getenv("SESSION_COOKIE_SAMESITE", "lax").casefold()
    if samesite not in {"lax", "strict", "none"}:
        raise RuntimeError("SESSION_COOKIE_SAMESITE must be lax, strict, or none")
    if samesite == "none" and not secure:
        raise RuntimeError("SESSION_COOKIE_SAMESITE=none requires SESSION_COOKIE_SECURE=true")
    return CookieSettings(secure=secure, samesite=samesite, max_age_seconds=60 * 60)
