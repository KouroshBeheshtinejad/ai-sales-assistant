from datetime import datetime, timedelta, timezone
import itertools
from unittest import mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import config
from app.core.csrf import CSRF_COOKIE_NAME
from app.db.database import Base, get_db
from app.db.models import PasswordResetToken, User
from app.core.security import create_access_token, hash_password
from app.routes.auth import _reset_hash
from app.main import app
from app import main
from app.services.verification_service import issue_code


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def client(monkeypatch):
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(main, "engine", engine)
    with TestClient(app, headers={"host": "localhost"}) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _solved_captcha(client, digits="12345"):
    """Issues a real captcha challenge and returns (token, correct_code), using a
    patched RNG so the test knows the code without parsing the PNG image."""
    cycle = itertools.cycle(int(d) for d in digits)
    with mock.patch("app.services.captcha_service.secrets.randbelow", side_effect=lambda _n: next(cycle)):
        response = client.get("/api/captcha")
    return response.json()["captcha_token"], digits


def test_production_configuration_requires_database_url_and_secret_key(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        config.database_url()
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        config.secret_key()


def test_production_configuration_requires_explicit_allowed_hosts(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("APP_ALLOWED_HOSTS", raising=False)

    with pytest.raises(RuntimeError, match="APP_ALLOWED_HOSTS"):
        config.allowed_hosts()


def test_production_configuration_rejects_incomplete_real_providers(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://nava:nava@localhost/nava")
    monkeypatch.setenv("SECRET_KEY", "x" * 40)
    monkeypatch.setenv("APP_ALLOWED_HOSTS", "example.com")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("PAYMENT_PROVIDER", "zarinpal")
    monkeypatch.setenv("PAYMENT_CREDENTIAL_ENCRYPTION_KEY", "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=")
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("OTP_PROVIDER", "email")
    monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "cloud")
    monkeypatch.setenv("CLOUDINARY_API_KEY", "key")
    monkeypatch.setenv("CLOUDINARY_API_SECRET", "secret")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USERNAME", "user")
    monkeypatch.setenv("SMTP_PASSWORD", "password")
    monkeypatch.setenv("SMTP_FROM", "noreply@example.com")

    config.validate_production_configuration()


def test_cookie_policy_requires_secure_cookies_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")

    settings = config.cookie_settings()

    assert settings.secure is True
    assert settings.samesite == "lax"


def test_cookie_policy_rejects_insecure_samesite_none(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")
    monkeypatch.setenv("SESSION_COOKIE_SAMESITE", "none")

    with pytest.raises(RuntimeError, match="requires"):
        config.cookie_settings()


def test_form_csrf_rejects_missing_token_and_accepts_matching_token(client):
    page = client.get("/auth/register")
    csrf_token = client.cookies.get(CSRF_COOKIE_NAME)

    assert page.status_code == 200
    assert csrf_token
    assert csrf_token in page.text

    missing = client.post(
        "/auth/register-form",
        data={"email": "csrf@example.com", "password": "StrongPass123!"},
        follow_redirects=False,
    )
    valid = client.post(
        "/auth/register-form",
        data={
            "email": "csrf@example.com",
            "password": "StrongPass123!",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )

    assert missing.status_code == 403
    assert valid.status_code == 303
    assert valid.headers["location"] == "/auth/login"


def test_cookie_authenticated_store_form_requires_csrf_token(client):
    client.get("/auth/register")
    csrf_token = client.cookies.get(CSRF_COOKIE_NAME)
    client.post(
        "/auth/register-form",
        data={
            "email": "store-form@example.com",
            "password": "StrongPass123!",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )

    missing = client.post(
        "/stores/new",
        data={"name": "CSRF Store", "business_type": "clothing"},
        follow_redirects=False,
    )
    valid = client.post(
        "/stores/new",
        data={
            "name": "CSRF Store",
            "business_type": "clothing",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )

    assert missing.status_code == 401
    assert valid.status_code == 401


def test_logout_requires_csrf_token(client):
    client.get("/auth/register")
    csrf_token = client.cookies.get(CSRF_COOKIE_NAME)
    client.post(
        "/auth/register-form",
        data={
            "email": "logout@example.com",
            "password": "StrongPass123!",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )

    missing = client.post("/auth/logout", follow_redirects=False)
    valid = client.post(
        "/auth/logout",
        data={"csrf_token": csrf_token},
        follow_redirects=False,
    )

    assert missing.status_code == 403
    assert valid.status_code == 303


def test_logout_revokes_the_authenticated_token(client):
    db = next(override_get_db())
    user = User(
        email="logout-revoke@example.com",
        password_hash=hash_password("StrongPass123!"),
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.close()
    token, code = _solved_captcha(client)
    login = client.post(
        "/auth/login",
        json={"email": "logout-revoke@example.com", "password": "StrongPass123!", "captcha_token": token, "captcha_answer": code},
    )
    token = login.json()["access_token"]
    client.get("/auth/register")
    csrf_token = client.cookies.get(CSRF_COOKIE_NAME)

    response = client.post(
        "/auth/logout",
        data={"csrf_token": csrf_token},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    ).status_code == 401


def test_liveness_and_readiness_checks(client):
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").json() == {"status": "ready"}
    assert client.get("/health/db").status_code == 401


def test_security_headers_are_present(client):
    response = client.get("/health/live")

    assert response.headers["content-security-policy"].startswith("default-src 'self'")
    assert response.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"


def test_swagger_docs_are_public_and_allow_the_ui_initializer(client):
    response = client.get("/docs")

    assert response.status_code == 200
    assert "swagger-ui" in response.text
    assert "'unsafe-inline'" in response.headers["content-security-policy"]
    assert client.get("/openapi.json").status_code == 200


def test_login_rate_limit_can_be_configured(client, monkeypatch):
    monkeypatch.setenv("AUTH_RATE_LIMIT_REQUESTS", "1")
    token1, code1 = _solved_captcha(client)
    client.post("/auth/login", json={"email": "missing@example.com", "password": "StrongPass123!", "captcha_token": token1, "captcha_answer": code1})
    token2, code2 = _solved_captcha(client)
    response = client.post("/auth/login", json={"email": "missing@example.com", "password": "StrongPass123!", "captcha_token": token2, "captcha_answer": code2})

    assert response.status_code == 429


def test_api_registration_requires_verification_before_login(client):
    reg_token, reg_code = _solved_captcha(client)
    registered = client.post(
        "/auth/register",
        json={"email": "verify@example.com", "password": "StrongPass123!", "phone": "09120000000", "captcha_token": reg_token, "captcha_answer": reg_code},
    )
    assert registered.status_code == 200
    assert registered.json()["verification_required"] is True

    blocked_token, blocked_code = _solved_captcha(client)
    blocked = client.post(
        "/auth/login",
        json={"email": "verify@example.com", "password": "StrongPass123!", "captcha_token": blocked_token, "captcha_answer": blocked_code},
    )
    assert blocked.status_code == 403

    db = next(override_get_db())
    try:
        user = db.query(User).filter(User.email == "verify@example.com").one()
        email_code = issue_code(db, user, "email")
        phone_code = issue_code(db, user, "phone")
    finally:
        db.close()

    verified = client.post(
        "/auth/verify",
        json={"email": "verify@example.com", "email_code": email_code, "phone_code": phone_code},
    )
    assert verified.status_code == 200
    login_token, login_code = _solved_captcha(client)
    assert client.post(
        "/auth/login",
        json={"email": "verify@example.com", "password": "StrongPass123!", "captcha_token": login_token, "captcha_answer": login_code},
    ).status_code == 200


def test_versioned_api_alias_is_available(client):
    token, code = _solved_captcha(client)
    response = client.post(
        "/api/auth/login",
        json={"email": "missing@example.com", "password": "StrongPass123!", "captcha_token": token, "captcha_answer": code},
    )

    assert response.status_code == 401


def test_password_reset_is_expiring_one_time_and_invalidates_sessions(client):
    db = next(override_get_db())
    user = User(email="reset@example.com", password_hash=hash_password("OldPass123!"), is_verified=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    raw_token = "reset-token-for-security-test-1234567890"
    db.add(PasswordResetToken(user_id=user.id, token_hash=_reset_hash(raw_token), expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)))
    db.commit()
    old_token = create_access_token(user.id, user.token_version)
    db.close()

    response = client.post("/auth/password-reset/confirm", json={"token": raw_token, "new_password": "NewPass123!"})
    assert response.status_code == 200
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {old_token}"}).status_code == 401
    login_token, login_code = _solved_captcha(client)
    assert client.post("/auth/login", json={"email": "reset@example.com", "password": "NewPass123!", "captcha_token": login_token, "captcha_answer": login_code}).status_code == 200
    assert client.post("/auth/password-reset/confirm", json={"token": raw_token, "new_password": "OtherPass123!"}).status_code == 400