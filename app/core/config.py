"""Environment-backed settings with strict production requirements."""

from __future__ import annotations

import os
import secrets

from dotenv import load_dotenv
from dataclasses import dataclass


PRODUCTION_ENVIRONMENTS = frozenset({"production", "prod"})

load_dotenv()


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
        if is_production() and (
            len(value) < 32
            or value.casefold() in {
                "replace-with-a-long-random-secret",
                "replace-with-secret",
                "change-this-development-secret",
            }
            or value.casefold().startswith("replace-with-")
        ):
            raise RuntimeError("SECRET_KEY must be a random value of at least 32 characters")
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


def validate_production_configuration() -> None:
    if not is_production():
        return
    secret_key()
    database_url()
    allowed_hosts()
    if not os.getenv("REDIS_URL", "").strip():
        raise RuntimeError("REDIS_URL is required in production for distributed rate limiting")
    payment_provider = os.getenv("PAYMENT_PROVIDER", "disabled").strip().casefold()
    if payment_provider not in {"disabled", "zarinpal"}:
        raise RuntimeError("Unsupported PAYMENT_PROVIDER")
    if payment_provider == "zarinpal" and not all(
        os.getenv(name, "").strip()
        for name in ("PAYMENT_MERCHANT_ID", "PAYMENT_CALLBACK_URL")
    ):
        raise RuntimeError("PAYMENT_MERCHANT_ID and PAYMENT_CALLBACK_URL are required")
    email_provider = os.getenv("EMAIL_PROVIDER", "disabled").strip().casefold()
    if email_provider not in {"disabled", "smtp"}:
        raise RuntimeError("Unsupported EMAIL_PROVIDER")
    if email_provider == "smtp" and not all(
        os.getenv(name, "").strip()
        for name in ("SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM")
    ):
        raise RuntimeError("SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, and SMTP_FROM are required")
    otp_provider = os.getenv("OTP_PROVIDER", "disabled").strip().casefold()
    if otp_provider not in {"disabled", "email", "sms"}:
        raise RuntimeError("Unsupported OTP_PROVIDER")
    if otp_provider == "email" and email_provider != "smtp":
        raise RuntimeError("OTP_PROVIDER=email requires EMAIL_PROVIDER=smtp")
    if otp_provider == "sms" and not os.getenv("SMS_WEBHOOK_URL", "").strip():
        raise RuntimeError("OTP_PROVIDER=sms requires SMS_WEBHOOK_URL")
    chat_provider = os.getenv("AI_CHAT_PROVIDER", "disabled").strip().casefold()
    if chat_provider == "openai" and not os.getenv("AI_CHAT_API_KEY", "").strip():
        raise RuntimeError("AI_CHAT_API_KEY is required when AI_CHAT_PROVIDER=openai")
    if not all(
        os.getenv(name, "").strip()
        for name in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET")
    ):
        raise RuntimeError("Cloudinary configuration is required for production uploads")
