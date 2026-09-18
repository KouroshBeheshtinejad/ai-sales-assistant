from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.db import models
from app.db.database import Base, get_db
from app.main import app
from app.routes.chat import get_llm_provider
from app.services.llm_provider import MockLLMProvider

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def client():
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_llm_provider] = lambda: MockLLMProvider()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_unauthenticated_guest_chat_to_order_and_seller_visibility(client):
    db = SessionLocal()
    seller = models.User(email="e2e-seller@example.com", password_hash=hash_password("StrongPass123!"))
    db.add(seller)
    db.flush()
    store = models.Store(name="E2E Fashion", owner_id=seller.id, business_type="clothing")
    db.add(store)
    db.flush()
    product = models.Product(
        store_id=store.id,
        name="کتونی مشکی",
        description="کتونی مشکی مناسب پیاده‌روی",
        size="۴۲",
        color="مشکی",
        price=Decimal("2450000.00"),
        stock=5,
        is_active=True,
    )
    db.add(product)
    db.commit()
    store_id, seller_id, product_id = store.id, seller.id, product.id
    db.close()

    assert client.get(f"/public/stores/{store_id}").status_code == 200
    first = client.post(f"/public/stores/{store_id}/chat", json={"question": "کتونی مشکی سایز ۴۲ دارید؟"})
    assert first.status_code == 200, first.text
    guest_token = first.json()["guest_token"]
    headers = {"X-Guest-Token": guest_token}

    follow_up = client.post(
        f"/public/stores/{store_id}/chat",
        headers=headers,
        json={"question": "همون محصول رو معرفی کن"},
    )
    assert follow_up.status_code == 200

    added = client.post(
        f"/public/stores/{store_id}/chat",
        headers=headers,
        json={"question": "دو تا می‌خوام"},
    )
    assert added.status_code == 200, added.text
    assert "به سبد خرید اضافه شد" in added.json()["answer"]

    viewed = client.post(
        f"/public/stores/{store_id}/chat",
        headers=headers,
        json={"question": "سبد خرید رو ببین"},
    )
    assert viewed.status_code == 200
    assert "کتونی مشکی" in viewed.json()["answer"]
    assert "2 عدد" in viewed.json()["answer"]

    checkout = client.post(
        f"/public/stores/{store_id}/chat",
        headers=headers,
        json={"question": "checkout"},
    )
    assert checkout.status_code == 200
    assert "نام" in checkout.json()["answer"]

    details = client.post(
        f"/public/stores/{store_id}/chat",
        headers=headers,
        json={"question": "نام: علی احمدی، تلفن: 09120000000، آدرس: تهران"},
    )
    assert details.status_code == 200
    assert "آیا سفارش را ثبت کنم" in details.json()["answer"]

    confirmed = client.post(
        f"/public/stores/{store_id}/chat",
        headers=headers,
        json={"question": "بله"},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert "ثبت شد" in confirmed.json()["answer"]

    duplicate = client.post(
        f"/public/stores/{store_id}/chat",
        headers=headers,
        json={"question": "بله"},
    )
    assert duplicate.status_code == 200

    db = SessionLocal()
    order = db.query(models.Order).filter_by(store_id=store_id, guest_token=guest_token).one()
    stored_product = db.get(models.Product, product_id)
    assert order.total_amount == Decimal("4900000.00")
    assert order.items[0].quantity == 2
    assert stored_product.stock == 3
    order_id = order.id
    db.close()

    guest_order = client.get(f"/orders/stores/{store_id}/guest/{order_id}", headers=headers)
    assert guest_order.status_code == 200
    assert guest_order.json()["id"] == order_id

    seller_headers = {"Authorization": f"Bearer {create_access_token(seller_id)}"}
    seller_orders = client.get(f"/seller/orders/stores/{store_id}", headers=seller_headers)
    assert seller_orders.status_code == 200
    assert seller_orders.json()[0]["id"] == order_id

    conversations = client.get(f"/seller/conversations/stores/{store_id}", headers=seller_headers)
    assert conversations.status_code == 200
    assert conversations.json()[0]["last_order_id"] == order_id
    assert any(message["content"] == "بله" for message in conversations.json()[0]["messages"])

    db = SessionLocal()
    other_store = models.Store(name="Other Store", owner_id=seller_id, business_type="clothing")
    db.add(other_store)
    db.commit()
    other_store_id = other_store.id
    db.close()

    cross_store_cart = client.get(
        f"/cart/stores/{other_store_id}", headers=headers
    )
    assert cross_store_cart.status_code == 404
    cross_store_order = client.get(
        f"/orders/stores/{other_store_id}/guest/{order_id}", headers=headers
    )
    assert cross_store_order.status_code == 404
