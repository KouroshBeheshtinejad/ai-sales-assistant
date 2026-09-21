from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.db.database import Base, get_db
from app.db.models import Product, Store, User
from app.main import app
from app.routes.auth import create_access_token
from app.core.security import hash_password


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

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


@pytest.fixture()
def test_data(client):
    db = next(app.dependency_overrides[get_db]())

    user = User(
        email="order-api@example.com",
        password_hash=hash_password("password123"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    store = Store(
        name="Order API Store",
        owner_id=user.id,
    )
    db.add(store)
    db.commit()
    db.refresh(store)

    product = Product(
        store_id=store.id,
        name="API Product",
        description="Test product",
        price=Decimal("25.00"),
        stock=10,
        is_active=True,
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    token = create_access_token(str(user.id))
    print("TEST USER ID:", user.id)
    print("TEST TOKEN:", token)

    return {
        "user": user,
        "store": store,
        "product": product,
        "token": token,
    }


def auth_headers(test_data):
    return {
        "Authorization": f"Bearer {test_data['token']}",
    }


def add_item_to_cart(client, test_data, quantity=2):
    response = client.post(
        f"/cart/stores/{test_data['store'].id}/items",
        headers=auth_headers(test_data),
        json={
            "product_id": test_data["product"].id,
            "quantity": quantity,
        },
    )
    assert response.status_code == 200, response.text
    return response


def test_create_order(client, test_data):
    add_item_to_cart(client, test_data, quantity=2)

    response = client.post(
        f"/orders/stores/{test_data['store'].id}",
        headers=auth_headers(test_data),
        json={
            "customer_name": "Ali Ahmadi",
            "customer_phone": "09120000000",
            "customer_address": "Tehran",
        },
    )

    assert response.status_code == 201
    data = response.json()

    assert data["store_id"] == test_data["store"].id
    assert data["status"] == "pending"
    assert len(data["tracking_number"]) == 10
    assert data["tracking_number"].isdigit()
    assert data["invoice_number"].startswith("INV-")
    assert data["customer_name"] == "Ali Ahmadi"
    assert data["total_amount"] == "50.00"
    assert len(data["items"]) == 1
    assert data["items"][0]["product_name"] == "API Product"


def test_list_orders(client, test_data):
    add_item_to_cart(client, test_data)

    create_response = client.post(
        f"/orders/stores/{test_data['store'].id}",
        headers=auth_headers(test_data),
        json={
            "customer_name": "Ali",
            "customer_phone": "09120000000",
            "customer_address": "Tehran",
        },
    )
    assert create_response.status_code == 201

    response = client.get(
        "/orders",
        headers=auth_headers(test_data),
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]["status"] == "pending"


def test_get_order_details(client, test_data):
    add_item_to_cart(client, test_data)

    create_response = client.post(
        f"/orders/stores/{test_data['store'].id}",
        headers=auth_headers(test_data),
        json={
            "customer_name": "Ali",
            "customer_phone": "09120000000",
            "customer_address": "Tehran",
        },
    )
    order_id = create_response.json()["id"]

    response = client.get(
        f"/orders/{order_id}",
        headers=auth_headers(test_data),
    )

    assert response.status_code == 200
    assert response.json()["id"] == order_id
    assert len(response.json()["tracking_number"]) == 10
    assert len(response.json()["items"]) == 1


def test_track_order_by_tracking_number(client, test_data):
    add_item_to_cart(client, test_data)
    create_response = client.post(
        f"/orders/stores/{test_data['store'].id}",
        headers=auth_headers(test_data),
        json={
            "customer_name": "Ali",
            "customer_phone": "09120000000",
            "customer_address": "Tehran",
        },
    )
    tracking_number = create_response.json()["tracking_number"]

    response = client.get(f"/orders/track/{tracking_number}")

    assert response.status_code == 200
    assert response.json()["tracking_number"] == tracking_number
    assert response.json()["status"] == "pending"
    assert "customer_name" not in response.json()


def test_track_order_rejects_invalid_number(client, test_data):
    response = client.get("/orders/track/123")

    assert response.status_code == 404


def test_download_invoice_pdf(client, test_data):
    add_item_to_cart(client, test_data)
    create_response = client.post(
        f"/orders/stores/{test_data['store'].id}",
        headers=auth_headers(test_data),
        json={
            "customer_name": "Ali",
            "customer_phone": "09120000000",
            "customer_address": "Tehran",
        },
    )
    order_id = create_response.json()["id"]

    response = client.get(f"/orders/{order_id}/invoice", headers=auth_headers(test_data))

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_create_order_accepts_structured_customer_fields(client, test_data):
    add_item_to_cart(client, test_data)
    response = client.post(
        f"/orders/stores/{test_data['store'].id}",
        headers=auth_headers(test_data),
        json={
            "first_name": "Ali",
            "last_name": "Ahmadi",
            "email": "ali@example.com",
            "customer_phone": "09120000000",
            "customer_address": "Tehran",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["customer_name"] == "Ali Ahmadi"
    assert data["first_name"] == "Ali"
    assert data["last_name"] == "Ahmadi"
    assert data["email"] == "ali@example.com"


def test_cancel_order(client, test_data):
    add_item_to_cart(client, test_data, quantity=3)

    create_response = client.post(
        f"/orders/stores/{test_data['store'].id}",
        headers=auth_headers(test_data),
        json={
            "customer_name": "Ali",
            "customer_phone": "09120000000",
            "customer_address": "Tehran",
        },
    )
    order_id = create_response.json()["id"]

    response = client.post(
        f"/orders/{order_id}/cancel",
        headers=auth_headers(test_data),
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "cancelled"
    assert data["cancelled_at"] is not None


def test_create_order_with_empty_cart(client, test_data):
    response = client.post(
        f"/orders/stores/{test_data['store'].id}",
        headers=auth_headers(test_data),
        json={
            "customer_name": "Ali",
            "customer_phone": "09120000000",
            "customer_address": "Tehran",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Cart is empty"


def test_get_nonexistent_order(client, test_data):
    response = client.get(
        "/orders/99999",
        headers=auth_headers(test_data),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found"


def test_cancel_order_twice(client, test_data):
    add_item_to_cart(client, test_data)

    create_response = client.post(
        f"/orders/stores/{test_data['store'].id}",
        headers=auth_headers(test_data),
        json={
            "customer_name": "Ali",
            "customer_phone": "09120000000",
            "customer_address": "Tehran",
        },
    )
    order_id = create_response.json()["id"]

    first_cancel = client.post(
        f"/orders/{order_id}/cancel",
        headers=auth_headers(test_data),
    )
    assert first_cancel.status_code == 200

    second_cancel = client.post(
        f"/orders/{order_id}/cancel",
        headers=auth_headers(test_data),
    )

    assert second_cancel.status_code == 400
    assert "Only pending orders" in second_cancel.json()["detail"]