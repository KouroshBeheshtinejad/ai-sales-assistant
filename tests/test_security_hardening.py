import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import config
from app.core.csrf import CSRF_COOKIE_NAME
from app.db.database import Base, get_db
from app.main import app
from app import main


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
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


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
    assert "access_token" in valid.headers["set-cookie"]


def test_cookie_authenticated_store_form_requires_csrf_token(client):
    csrf_token = client.get("/auth/register").cookies.get(CSRF_COOKIE_NAME)
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

    assert missing.status_code == 403
    assert valid.status_code == 303


def test_logout_requires_csrf_token(client):
    csrf_token = client.get("/auth/register").cookies.get(CSRF_COOKIE_NAME)
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


def test_liveness_and_readiness_checks(client):
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").json() == {"status": "ready"}


def test_security_headers_are_present(client):
    response = client.get("/health/live")

    assert response.headers["content-security-policy"].startswith("default-src 'self'")
    assert response.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
