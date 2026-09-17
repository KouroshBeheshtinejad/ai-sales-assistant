from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.db.database import Base, get_db
from app.db.models import Order, OrderItem, Product, Store, User
from app.main import app


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


@pytest.fixture(scope="function")
def client():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db

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


def create_user(email: str):
    db = TestingSessionLocal()

    try:
        user = User(
            email=email,
            password_hash=hash_password("StrongPass123!"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        return user
    finally:
        db.close()


def create_store(owner_id: int, name: str = "Seller API Store"):
    db = TestingSessionLocal()

    try:
        store = Store(
            name=name,
            description="Test store",
            business_type="clothing",
            owner_id=owner_id,
        )
        db.add(store)
        db.commit()
        db.refresh(store)

        return store
    finally:
        db.close()


def create_product(store_id: int):
    db = TestingSessionLocal()

    try:
        product = Product(
            name="Seller API Product",
            description="Test product",
            price=Decimal("100.00"),
            stock=10,
            store_id=store_id,
            is_active=True,
        )
        db.add(product)
        db.commit()
        db.refresh(product)

        return product
    finally:
        db.close()


def create_order(user_id: int, store_id: int, product_id: int):
    db = TestingSessionLocal()

    try:
        order = Order(
            user_id=user_id,
            store_id=store_id,
            status="pending",
            customer_name="Test Customer",
            customer_phone="09120000000",
            customer_address="Test Address",
            total_amount=Decimal("100.00"),
        )
        db.add(order)
        db.commit()
        db.refresh(order)

        order_item = OrderItem(
            order_id=order.id,
            product_id=product_id,
            product_name="Seller API Product",
            unit_price=Decimal("100.00"),
            quantity=1,
            line_total=Decimal("100.00"),
        )
        db.add(order_item)
        db.commit()
        db.refresh(order)

        return order
    finally:
        db.close()


def auth_headers(user_id: int):
    token = create_access_token(user_id)
    return {
        "Authorization": f"Bearer {token}",
    }


@pytest.fixture()
def test_data(client):
    seller = create_user("seller-api@example.com")
    customer = create_user("customer-api@example.com")
    another_seller = create_user("another-seller-api@example.com")

    store = create_store(seller.id)
    another_store = create_store(
        another_seller.id,
        name="Another Store",
    )

    product = create_product(store.id)
    order = create_order(
        user_id=customer.id,
        store_id=store.id,
        product_id=product.id,
    )

    return {
        "seller": seller,
        "customer": customer,
        "another_seller": another_seller,
        "store": store,
        "another_store": another_store,
        "product": product,
        "order": order,
    }


def test_seller_can_list_store_orders(client, test_data):
    response = client.get(
        f"/seller/orders/stores/{test_data['store'].id}",
        headers=auth_headers(test_data["seller"].id),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == test_data["order"].id
    assert data[0]["store_id"] == test_data["store"].id
    assert data[0]["status"] == "pending"


def test_seller_cannot_list_another_store_orders(client, test_data):
    response = client.get(
        f"/seller/orders/stores/{test_data['store'].id}",
        headers=auth_headers(test_data["another_seller"].id),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Store not found"


def test_seller_can_get_order_details(client, test_data):
    response = client.get(
        f"/seller/orders/{test_data['order'].id}",
        headers=auth_headers(test_data["seller"].id),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == test_data["order"].id
    assert data["store_id"] == test_data["store"].id
    assert len(data["items"]) == 1
    assert data["items"][0]["product_name"] == "Seller API Product"


def test_seller_cannot_get_another_store_order(client, test_data):
    response = client.get(
        f"/seller/orders/{test_data['order'].id}",
        headers=auth_headers(test_data["another_seller"].id),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found"


def test_seller_can_update_order_status(client, test_data):
    response = client.patch(
        f"/seller/orders/{test_data['order'].id}/status",
        headers=auth_headers(test_data["seller"].id),
        json={"status": "confirmed"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == test_data["order"].id
    assert data["status"] == "confirmed"


def test_seller_cannot_make_invalid_status_transition(client, test_data):
    response = client.patch(
        f"/seller/orders/{test_data['order'].id}/status",
        headers=auth_headers(test_data["seller"].id),
        json={"status": "delivered"},
    )

    assert response.status_code == 400
    assert "Cannot change status" in response.json()["detail"]


def test_seller_cannot_use_invalid_status(client, test_data):
    response = client.patch(
        f"/seller/orders/{test_data['order'].id}/status",
        headers=auth_headers(test_data["seller"].id),
        json={"status": "invalid_status"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid status"


def test_seller_orders_requires_authentication(client, test_data):
    response = client.get(
        f"/seller/orders/stores/{test_data['store'].id}",
    )

    assert response.status_code in (401, 403)