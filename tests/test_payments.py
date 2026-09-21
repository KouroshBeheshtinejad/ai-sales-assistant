from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.db.database import Base, get_db
from app.db.models import Product, Store, User
from app.main import app


@pytest.fixture()
def payment_context():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = session_factory()
    user = User(email="payments@example.com", password_hash=hash_password("StrongPass123!"))
    db.add(user)
    db.flush()
    store = Store(name="Payment Store", owner_id=user.id)
    db.add(store)
    db.flush()
    product = Product(name="Payment Product", price=Decimal("12.50"), stock=2, store_id=store.id, is_active=True)
    db.add(product)
    db.commit()
    context = {"user_id": user.id, "store_id": store.id, "product_id": product.id, "token": create_access_token(str(user.id))}
    db.close()

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, context
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def auth_headers(context):
    return {"Authorization": f"Bearer {context['token']}"}


def create_order(client, context):
    cart = client.post(
        f"/cart/stores/{context['store_id']}/items",
        headers=auth_headers(context),
        json={"product_id": context["product_id"], "quantity": 1},
    )
    assert cart.status_code == 200
    order = client.post(
        f"/orders/stores/{context['store_id']}",
        headers=auth_headers(context),
        json={"customer_name": "Ali", "customer_phone": "0912", "customer_address": "Tehran"},
    )
    assert order.status_code == 201
    return order.json()


def test_payment_requires_configured_provider(payment_context, monkeypatch):
    client, context = payment_context
    monkeypatch.delenv("PAYMENT_PROVIDER", raising=False)
    order = create_order(client, context)

    response = client.post(
        f"/payments/orders/{order['id']}",
        headers={**auth_headers(context), "Idempotency-Key": "payment-disabled-1"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Payment provider is not configured"


def test_mock_payment_is_idempotent_and_server_verified(payment_context, monkeypatch):
    client, context = payment_context
    monkeypatch.setenv("PAYMENT_PROVIDER", "mock")
    order = create_order(client, context)
    headers = {**auth_headers(context), "Idempotency-Key": "payment-mock-1"}

    created = client.post(f"/payments/orders/{order['id']}", headers=headers)
    assert created.status_code == 201
    payment = created.json()
    assert payment["status"] == "pending"
    assert payment["authority"].startswith("mock-")

    repeated = client.post(f"/payments/orders/{order['id']}", headers=headers)
    assert repeated.status_code == 201
    assert repeated.json()["id"] == payment["id"]

    verified = client.post(
        f"/payments/{payment['id']}/verify",
        headers=auth_headers(context),
        json={"authority": payment["authority"]},
    )
    assert verified.status_code == 200
    assert verified.json()["status"] == "paid"
    assert verified.json()["transaction_id"].startswith("mock-tx-")

    db = next(app.dependency_overrides[get_db]())
    try:
        product = db.get(Product, context["product_id"])
        assert product.reserved_stock == 0
    finally:
        db.close()

    invalid = client.post(
        f"/payments/{payment['id']}/verify",
        headers=auth_headers(context),
        json={"authority": "mock-invalid"},
    )
    assert invalid.status_code == 400