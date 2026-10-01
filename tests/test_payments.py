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
from app.services.payment_service import PaymentProviderNotConfigured, get_payment_provider


@pytest.fixture()
def payment_context():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = session_factory()
    user = User(email="payments@example.com", password_hash=hash_password("StrongPass123!"), is_verified=True)
    db.add(user)
    db.flush()
    store = Store(name="Payment Store", owner_id=user.id)
    db.add(store)
    db.flush()
    product = Product(name="Payment Product", price=Decimal("12.50"), stock=2, store_id=store.id, is_active=True)
    db.add(product)
    support_user = User(email="support-target@example.com", password_hash=hash_password("StrongPass123!"))
    db.add(support_user)
    db.flush()
    other_store = Store(name="Other Store", owner_id=support_user.id)
    db.add(other_store)
    db.commit()
    context = {
        "user_id": user.id,
        "store_id": store.id,
        "product_id": product.id,
        "token": create_access_token(str(user.id)),
        "support_user_id": support_user.id,
        "support_token": create_access_token(str(support_user.id)),
        "other_store_id": other_store.id,
    }
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
    created = order.json()
    assert created["tracking_number"] is None
    assert created["invoice_number"] is None
    assert client.get(f"/orders/{created['id']}/invoice", headers=auth_headers(context)).status_code == 404
    seller_orders = client.get(
        f"/seller/orders/stores/{context['store_id']}",
        headers=auth_headers(context),
    )
    assert seller_orders.status_code == 200
    assert seller_orders.json() == []
    return created


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


def test_production_rejects_mock_payment_provider(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PAYMENT_PROVIDER", "mock")

    with pytest.raises(PaymentProviderNotConfigured):
        get_payment_provider()


def test_god_role_is_server_managed_and_support_is_read_only(payment_context, monkeypatch):
    client, context = payment_context
    monkeypatch.setenv("GOD_USER_EMAIL", "payments@example.com")
    god_headers = auth_headers(context)

    profile = client.get("/api/auth/me", headers=god_headers)
    assert profile.status_code == 200
    assert profile.json()["role"] == "god"
    stores = client.get("/api/stores/", headers=god_headers)
    assert {store["id"] for store in stores.json()} == {context["store_id"], context["other_store_id"]}

    promoted = client.patch(
        f"/api/admin/users/{context['support_user_id']}/role",
        headers=god_headers,
        json={"role": "support"},
    )
    assert promoted.status_code == 200
    assert promoted.json()["role"] == "support"

    support_headers = {"Authorization": f"Bearer {context['support_token']}"}
    assert client.get("/api/admin/orders", headers=support_headers).status_code == 200
    assert client.get("/api/admin/users", headers=support_headers).status_code == 403
    assert client.patch(
        f"/api/admin/users/{context['user_id']}/role",
        headers=support_headers,
        json={"role": "seller"},
    ).status_code == 403


def test_unconfigured_users_cannot_access_admin_routes(payment_context):
    client, context = payment_context
    response = client.get("/api/admin/users", headers=auth_headers(context))
    assert response.status_code == 403


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
    finalized = client.get(f"/orders/{order['id']}", headers=auth_headers(context))
    assert finalized.status_code == 200
    assert finalized.json()["tracking_number"]
    assert finalized.json()["invoice_number"]
    seller_orders = client.get(
        f"/seller/orders/stores/{context['store_id']}",
        headers=auth_headers(context),
    )
    assert seller_orders.status_code == 200
    assert len(seller_orders.json()) == 1
    assert seller_orders.json()[0]["tracking_number"]
    assert seller_orders.json()[0]["invoice_number"]
    invoice = client.get(f"/orders/{order['id']}/invoice", headers=auth_headers(context))
    assert invoice.status_code == 200
    assert invoice.headers["content-type"] == "application/pdf"
    localized_invoice = client.get(
        f"/orders/{order['id']}/invoice?locale=de&timezone=Europe%2FBerlin",
        headers=auth_headers(context),
    )
    assert localized_invoice.status_code == 200
    assert localized_invoice.headers["content-disposition"].endswith("-de.pdf\"")
    invalid_locale = client.get(
        f"/orders/{order['id']}/invoice?locale=it",
        headers=auth_headers(context),
    )
    assert invalid_locale.status_code == 400

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


def test_gateway_callback_verifies_payment_on_server(payment_context, monkeypatch):
    client, context = payment_context
    monkeypatch.setenv("PAYMENT_PROVIDER", "mock")
    order = create_order(client, context)
    created = client.post(
        f"/payments/orders/{order['id']}",
        headers={**auth_headers(context), "Idempotency-Key": "gateway-callback-1"},
    )
    assert created.status_code == 201

    callback = client.get(
        "/api/payments/callback",
        params={"Authority": created.json()["authority"], "Status": "OK"},
        follow_redirects=False,
    )
    assert callback.status_code == 303
    assert "payment=success" in callback.headers["location"]
    finalized = client.get(f"/orders/{order['id']}", headers=auth_headers(context))
    assert finalized.status_code == 200
    assert finalized.json()["tracking_number"]