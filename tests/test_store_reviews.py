from datetime import datetime, timezone

from app.core.security import create_access_token, hash_password
from app.db import models
from app.db.database import Base, get_db
from app.main import app
from app.services.verification_service import issue_code

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def make_user(email="buyer@example.com", phone="+1234567890"):
    db = TestingSessionLocal()
    try:
        user = models.User(
            email=email,
            password_hash=hash_password("StrongPass123!"),
            first_name="Test",
            last_name="Buyer",
            phone=phone,
            is_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def make_store(owner_email="owner@example.com", store_name="Demo Shop"):
    db = TestingSessionLocal()
    try:
        owner = db.query(models.User).filter(models.User.email == owner_email).first()
        if owner is None:
            owner = models.User(
                email=owner_email,
                password_hash=hash_password("StrongPass123!"),
                first_name="Demo",
                last_name="Owner",
                is_verified=True,
            )
            db.add(owner)
            db.flush()
        store = models.Store(
            name=store_name,
            description="Fresh goods and local service",
            owner_id=owner.id,
            business_type="clothing",
        )
        db.add(store)
        db.commit()
        db.refresh(store)
        return store
    finally:
        db.close()


def make_order(store_id, user_id, *, paid=True):
    db = TestingSessionLocal()
    try:
        order = models.Order(
            store_id=store_id,
            user_id=user_id,
            guest_token=None,
            customer_name="Test Buyer",
            customer_phone="+1234567890",
            customer_address="Test address",
            total_amount=10.00,
            currency="IRT",
            status="paid" if paid else "pending",
            paid_at=datetime.now(timezone.utc).replace(tzinfo=None) if paid else None,
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        return order
    finally:
        db.close()


def test_review_requires_paid_order_and_one_review_per_user():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    try:
        user = make_user()
        store = make_store()
        token = create_access_token(user.id, user.token_version)
        with TestClient(app) as client:
            response = client.post(
                f"/api/public/stores/{store.id}/reviews",
                json={"rating": 5, "comment": "Loved it"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 403

            make_order(store.id, user.id, paid=True)
            first = client.post(
                f"/api/public/stores/{store.id}/reviews",
                json={"rating": 5, "comment": "Loved it"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert first.status_code == 200
            second = client.post(
                f"/api/public/stores/{store.id}/reviews",
                json={"rating": 4, "comment": "Changed my mind"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert second.status_code == 409
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


def test_verification_message_is_polished_for_email(monkeypatch):
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    try:
        class FakeEmailProvider:
            def __init__(self):
                self.calls = []

            def send(self, *, email, subject, message, html_message=None):
                self.calls.append({"email": email, "subject": subject, "message": message, "html_message": html_message})

        provider = FakeEmailProvider()
        monkeypatch.setenv("OTP_PROVIDER", "email")
        monkeypatch.setattr("app.services.verification_service.get_email_provider", lambda: provider)

        user = make_user(email="codeuser@example.com", phone="+1111111111")
        code = issue_code(TestingSessionLocal(), user, "email")
        assert len(code) == 8 and code.isdigit()
        assert "کد تایید" in provider.calls[0]["message"] or "verification code" in provider.calls[0]["message"].lower()
        assert "NAVA" in provider.calls[0]["subject"] or "NAVA" in provider.calls[0]["message"]
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
