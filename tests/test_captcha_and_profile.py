import itertools
from unittest import mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.db.database import Base, get_db
from app.db.models import Store, StoreMembership, User
from app.main import app
from app.routes.auth import create_access_token
from app.services.captcha_service import generate_captcha, verify_captcha
from app.services.verification_service import issue_code


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def _db(client):
    return next(app.dependency_overrides[get_db]())


def _solved_captcha(client, digits="12345"):
    """Issues a captcha through the real endpoint and returns (token, correct_code),
    using a patched RNG so the test knows the code without parsing the PNG."""
    cycle = itertools.cycle(int(d) for d in digits)
    with mock.patch("app.services.captcha_service.secrets.randbelow", side_effect=lambda _n: next(cycle)):
        response = client.get("/api/captcha")
    assert response.status_code == 200
    body = response.json()
    assert body["image"].startswith("data:image/png;base64,")
    return body["captcha_token"], digits


def _register_user(db, **overrides):
    defaults = dict(email="seller@example.com", password_hash=hash_password("Secret123!"), is_verified=True)
    defaults.update(overrides)
    user = User(**defaults)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestCaptchaService:
    def test_correct_answer_is_valid_once(self, client):
        db = _db(client)
        cycle = itertools.cycle([9, 9, 0, 0, 1])
        with mock.patch("app.services.captcha_service.secrets.randbelow", side_effect=lambda _n: next(cycle)):
            token, _image = generate_captcha(db)
        assert verify_captcha(db, token, "99001") is True
        # Single-use: the same token cannot be replayed even with the right answer.
        assert verify_captcha(db, token, "99001") is False

    def test_wrong_answer_is_rejected_and_consumes_the_challenge(self, client):
        db = _db(client)
        cycle = itertools.cycle([1, 1, 1, 1, 1])
        with mock.patch("app.services.captcha_service.secrets.randbelow", side_effect=lambda _n: next(cycle)):
            token, _image = generate_captcha(db)
        assert verify_captcha(db, token, "00000") is False
        assert verify_captcha(db, token, "11111") is False  # already consumed by the wrong attempt

    def test_unknown_token_is_rejected(self, client):
        db = _db(client)
        assert verify_captcha(db, "not-a-real-token", "12345") is False


class TestVerificationCodeLogging:
    def test_issued_email_and_sms_codes_are_logged_when_enabled(self, client, monkeypatch, caplog):
        db = _db(client)
        user = _register_user(db, email="otp-log@example.com", phone="+15551234567")
        monkeypatch.setenv("LOG_VERIFICATION_CODES", "true")

        with caplog.at_level("WARNING", logger="app.services.verification_service"):
            email_code = issue_code(db, user, "email")
            sms_code = issue_code(db, user, "phone")

        assert f"channel=email target=o***@example.com code={email_code}" in caplog.text
        assert f"channel=phone target=***4567 code={sms_code}" in caplog.text

    def test_codes_are_not_logged_unless_explicitly_enabled(self, client, monkeypatch, caplog):
        db = _db(client)
        user = _register_user(db)
        monkeypatch.delenv("LOG_VERIFICATION_CODES", raising=False)

        with caplog.at_level("WARNING", logger="app.services.verification_service"):
            code = issue_code(db, user, "email")

        assert code not in caplog.text
        assert "verification_code_issued" not in caplog.text


class TestCaptchaEndpoint:
    def test_issues_token_and_image(self, client):
        response = client.get("/api/captcha")
        assert response.status_code == 200
        body = response.json()
        assert body["captcha_token"]
        assert body["image"].startswith("data:image/png;base64,")


class TestRegisterAndLoginRequireCaptcha:
    def test_register_fails_without_solving_captcha(self, client):
        token, _code = _solved_captcha(client)
        response = client.post("/api/auth/register", json={
            "email": "new@example.com",
            "password": "Secret123!",
            "captcha_token": token,
            "captcha_answer": "wrong",
        })
        assert response.status_code == 400
        assert "captcha" in response.json()["detail"].lower()

    def test_register_succeeds_with_correct_captcha(self, client):
        token, code = _solved_captcha(client)
        response = client.post("/api/auth/register", json={
            "email": "new@example.com",
            "password": "Secret123!",
            "captcha_token": token,
            "captcha_answer": code,
        })
        assert response.status_code == 200
        assert response.json()["role"] == "customer"
        assert response.json()["approval_status"] == "active"

    def test_privileged_role_registration_waits_for_approval(self, client):
        token, code = _solved_captcha(client)
        response = client.post("/api/auth/register", json={
            "email": "owner-request@example.com",
            "password": "Secret123!",
            "role": "store_owner",
            "captcha_token": token,
            "captcha_answer": code,
        })
        assert response.status_code == 200
        assert response.json()["role"] == "store_owner"
        assert response.json()["approval_status"] == "pending"
        assert response.json()["approval_required"] is True

    def test_store_admin_registration_creates_pending_tenant_membership(self, client):
        db = _db(client)
        owner = _register_user(db, email="tenant-owner@example.com", role="store_owner")
        store = Store(name="Tenant Store", owner_id=owner.id)
        db.add(store)
        db.commit()
        token, code = _solved_captcha(client)
        response = client.post("/api/auth/register", json={
            "email": "tenant-admin@example.com",
            "password": "Secret123!",
            "role": "store_admin",
            "store_id": store.id,
            "captcha_token": token,
            "captcha_answer": code,
        })
        assert response.status_code == 200
        admin = db.query(User).filter_by(email="tenant-admin@example.com").one()
        membership = db.query(StoreMembership).filter_by(user_id=admin.id, store_id=store.id).one()
        assert admin.approval_status == "pending"
        assert membership.status == "pending"

    def test_login_rejects_a_role_different_from_the_saved_role(self, client):
        db = _db(client)
        _register_user(db, role="store_owner")
        token, code = _solved_captcha(client)
        response = client.post("/api/auth/login", json={
            "email": "seller@example.com",
            "password": "Secret123!",
            "role": "support",
            "captcha_token": token,
            "captcha_answer": code,
        })
        assert response.status_code == 403
        assert response.json()["detail"] == "Selected role does not match this account"

    def test_login_rejects_verified_but_unapproved_support_account(self, client):
        db = _db(client)
        _register_user(db, role="support", approval_status="pending")
        token, code = _solved_captcha(client)
        response = client.post("/api/auth/login", json={
            "email": "seller@example.com",
            "password": "Secret123!",
            "role": "support",
            "captcha_token": token,
            "captcha_answer": code,
        })
        assert response.status_code == 403
        assert response.json()["detail"] == "Account approval is pending"

    def test_login_fails_without_captcha_even_with_correct_password(self, client):
        db = _db(client)
        _register_user(db)
        token, _code = _solved_captcha(client)
        response = client.post("/api/auth/login", json={
            "email": "seller@example.com",
            "password": "Secret123!",
            "captcha_token": token,
            "captcha_answer": "00000",
        })
        assert response.status_code == 400

    def test_login_succeeds_with_correct_captcha_and_credentials(self, client):
        db = _db(client)
        _register_user(db)
        token, code = _solved_captcha(client)
        response = client.post("/api/auth/login", json={
            "email": "seller@example.com",
            "password": "Secret123!",
            "captcha_token": token,
            "captcha_answer": code,
        })
        assert response.status_code == 200


class TestProfileCompletion:
    def _headers(self, db):
        user = _register_user(db)
        return {"Authorization": f"Bearer {create_access_token(user.id, user.token_version)}"}, user

    def test_me_reports_incomplete_profile_for_a_fresh_account(self, client):
        db = _db(client)
        headers, _user = self._headers(db)
        response = client.get("/api/auth/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["profile_complete"] is False

    def test_update_me_requires_a_ten_digit_national_id(self, client):
        db = _db(client)
        headers, user = self._headers(db)
        token, code = _solved_captcha(client)
        payload = {
            "first_name": "سارا", "last_name": "محمدی", "email": user.email,
            "phone": "09120000000", "national_id": "12345",  # too short
            "business_address": "تهران", "business_phone": "02100000000",
            "captcha_token": token, "captcha_answer": code,
        }
        response = client.patch("/api/auth/me", json=payload, headers=headers)
        assert response.status_code == 422

    def test_update_me_completes_the_profile(self, client):
        db = _db(client)
        headers, user = self._headers(db)
        token, code = _solved_captcha(client)
        payload = {
            "first_name": "سارا", "last_name": "محمدی", "email": user.email,
            "phone": "09120000000", "national_id": "1234567890",
            "business_address": "تهران، خیابان ولیعصر", "business_phone": "02100000000",
            "captcha_token": token, "captcha_answer": code,
        }
        response = client.patch("/api/auth/me", json=payload, headers=headers)
        assert response.status_code == 200
        assert response.json()["verification_required"] is False

        me = client.get("/api/auth/me", headers=headers).json()
        assert me["profile_complete"] is True
        assert me["national_id"] == "1234567890"
        assert me["business_address"] == "تهران، خیابان ولیعصر"

    def test_update_me_rejects_a_national_id_already_used_by_someone_else(self, client):
        db = _db(client)
        _register_user(db, email="first@example.com", national_id="1111111111")
        headers, user = self._headers(db)
        token, code = _solved_captcha(client)
        payload = {
            "first_name": "A", "last_name": "B", "email": user.email,
            "phone": "09120000000", "national_id": "1111111111",
            "business_address": "x", "business_phone": "02100000000",
            "captcha_token": token, "captcha_answer": code,
        }
        response = client.patch("/api/auth/me", json=payload, headers=headers)
        assert response.status_code == 400
        assert "national id" in response.json()["detail"].lower()

    def test_update_me_requires_a_fresh_captcha(self, client):
        db = _db(client)
        headers, user = self._headers(db)
        token, code = _solved_captcha(client)
        payload = {
            "first_name": "A", "last_name": "B", "email": user.email,
            "phone": "09120000000", "national_id": "1234567890",
            "business_address": "x", "business_phone": "02100000000",
            "captcha_token": token, "captcha_answer": code,
        }
        first = client.patch("/api/auth/me", json=payload, headers=headers)
        assert first.status_code == 200
        # Re-submitting with the same, already-used captcha must fail.
        second = client.patch("/api/auth/me", json=payload, headers=headers)
        assert second.status_code == 400

    def test_changing_email_requires_re_verification(self, client):
        db = _db(client)
        headers, user = self._headers(db)
        token, code = _solved_captcha(client)
        payload = {
            "first_name": "A", "last_name": "B", "email": "changed@example.com",
            "phone": "09120000000", "national_id": "1234567890",
            "business_address": "x", "business_phone": "02100000000",
            "captcha_token": token, "captcha_answer": code,
        }
        response = client.patch("/api/auth/me", json=payload, headers=headers)
        assert response.status_code == 200
        assert response.json()["verification_required"] is True

        db.refresh(user)
        assert user.is_verified is False
        assert user.email == "changed@example.com"

    def test_changing_password_issues_a_new_token_that_still_works(self, client):
        db = _db(client)
        headers, user = self._headers(db)
        token, code = _solved_captcha(client)
        payload = {
            "first_name": "A", "last_name": "B", "email": user.email,
            "phone": "09120000000", "national_id": "1234567890",
            "business_address": "x", "business_phone": "02100000000",
            "password": "NewSecret123!", "confirm_password": "NewSecret123!",
            "captcha_token": token, "captcha_answer": code,
        }
        response = client.patch("/api/auth/me", json=payload, headers=headers)
        assert response.status_code == 200
        new_token = response.json()["access_token"]
        assert new_token

        # The old bearer token is now stale (token_version bumped)...
        stale = client.get("/api/auth/me", headers=headers)
        assert stale.status_code == 401

        # ...but the freshly issued one works.
        fresh = client.get("/api/auth/me", headers={"Authorization": f"Bearer {new_token}"})
        assert fresh.status_code == 200

    def test_mismatched_password_confirmation_is_rejected(self, client):
        db = _db(client)
        headers, user = self._headers(db)
        token, code = _solved_captcha(client)
        payload = {
            "first_name": "A", "last_name": "B", "email": user.email,
            "phone": "09120000000", "national_id": "1234567890",
            "business_address": "x", "business_phone": "02100000000",
            "password": "NewSecret123!", "confirm_password": "Different123!",
            "captcha_token": token, "captcha_answer": code,
        }
        response = client.patch("/api/auth/me", json=payload, headers=headers)
        assert response.status_code == 422


class TestSellerAccountRouteIsRegistered:
    def test_seller_account_spa_route_exists(self):
        # Every client-side seller route must have a matching server route that falls
        # back to index.html, or a direct browser visit / refresh 404s. This guards
        # against forgetting to whitelist a new seller page (see app/main.py).
        from app.main import app as real_app

        paths = {route.path for route in real_app.routes if "GET" in getattr(route, "methods", set())}
        assert "/seller/account" in paths