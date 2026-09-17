import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.db.database import Base, get_db
from app.db import models
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
        user = models.User(
            email=email,
            password_hash=hash_password("StrongPass123!"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def create_store(user_id: int, name: str = "Demo Store"):
    db = TestingSessionLocal()
    try:
        store = models.Store(
            name=name,
            description="Test store",
            business_type="clothing",
            owner_id=user_id,
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
        product = models.Product(
            name="Test Product",
            description="A test product",
            price=100000,
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


def auth_headers(user_id: int):
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


def test_get_empty_cart(client):
    user = create_user("cart-user@example.com")
    store = create_store(user.id)
    headers = auth_headers(user.id)

    response = client.get(
        f"/cart/stores/{store.id}",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert data["user_id"] == user.id
    assert data["store_id"] == store.id
    assert data["items"] == []
    assert data["total_amount"] == 0


def test_add_item_to_cart(client):
    user = create_user("add-item@example.com")
    store = create_store(user.id)
    product = create_product(store.id)
    headers = auth_headers(user.id)

    response = client.post(
        f"/cart/stores/{store.id}/items",
        json={
            "product_id": product.id,
            "quantity": 2,
        },
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["product_id"] == product.id
    assert data["items"][0]["quantity"] == 2
    assert data["items"][0]["product_name"] == "Test Product"
    assert data["total_amount"] == 200000


def test_update_cart_item(client):
    user = create_user("update-item@example.com")
    store = create_store(user.id)
    product = create_product(store.id)
    headers = auth_headers(user.id)

    client.post(
        f"/cart/stores/{store.id}/items",
        json={"product_id": product.id, "quantity": 2},
        headers=headers,
    )

    response = client.patch(
        f"/cart/stores/{store.id}/items/{product.id}",
        json={"quantity": 5},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["items"][0]["quantity"] == 5
    assert data["total_amount"] == 500000


def test_remove_cart_item(client):
    user = create_user("remove-item@example.com")
    store = create_store(user.id)
    product = create_product(store.id)
    headers = auth_headers(user.id)

    client.post(
        f"/cart/stores/{store.id}/items",
        json={"product_id": product.id, "quantity": 2},
        headers=headers,
    )

    response = client.delete(
        f"/cart/stores/{store.id}/items/{product.id}",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total_amount"] == 0


def test_clear_cart(client):
    user = create_user("clear-cart@example.com")
    store = create_store(user.id)
    product = create_product(store.id)
    headers = auth_headers(user.id)

    client.post(
        f"/cart/stores/{store.id}/items",
        json={"product_id": product.id, "quantity": 3},
        headers=headers,
    )

    response = client.delete(
        f"/cart/stores/{store.id}",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total_amount"] == 0


def test_reject_quantity_greater_than_stock(client):
    user = create_user("stock-check@example.com")
    store = create_store(user.id)
    product = create_product(store.id)
    headers = auth_headers(user.id)

    response = client.post(
        f"/cart/stores/{store.id}/items",
        json={
            "product_id": product.id,
            "quantity": 11,
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert "Insufficient stock" in response.json()["detail"]


def test_reject_invalid_quantity(client):
    user = create_user("invalid-quantity@example.com")
    store = create_store(user.id)
    product = create_product(store.id)
    headers = auth_headers(user.id)

    response = client.post(
        f"/cart/stores/{store.id}/items",
        json={
            "product_id": product.id,
            "quantity": 0,
        },
        headers=headers,
    )

    assert response.status_code == 422


def test_require_authentication(client):
    response = client.get("/cart/stores/1")
    assert response.status_code in (401, 403)