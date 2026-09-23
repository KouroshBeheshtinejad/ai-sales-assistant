import os
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db.models import Product, Store, User
from app.services.cart_service import CartService
from app.services.order_service import OrderService


DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.postgres


@pytest.fixture
def postgres_db():
    if not DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL concurrency tests")
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = session_factory()
    try:
        yield db, session_factory
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_concurrent_orders_cannot_oversell(postgres_db):
    db, session_factory = postgres_db
    seller = User(email="pg-seller@example.com", password_hash="hash", is_verified=True)
    first = User(email="pg-first@example.com", password_hash="hash", is_verified=True)
    second = User(email="pg-second@example.com", password_hash="hash", is_verified=True)
    db.add_all([seller, first, second])
    db.flush()
    store = Store(name="Postgres concurrency store", owner_id=seller.id)
    db.add(store)
    db.flush()
    product = Product(
        store_id=store.id,
        name="Single stock product",
        price=Decimal("10.00"),
        stock=1,
        reserved_stock=0,
        is_active=True,
    )
    db.add(product)
    db.commit()
    for user in (first, second):
        CartService.add_item(db, user.id, store.id, product.id, 1)

    def checkout(user_id: int):
        session = session_factory()
        try:
            return OrderService.create_order(
                db=session,
                user_id=user_id,
                store_id=store.id,
                customer_name="Customer",
                customer_phone="09120000000",
                customer_address="Tehran",
                idempotency_key=f"pg-{user_id}",
            ).id
        except ValueError:
            session.rollback()
            return None
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(checkout, [first.id, second.id]))

    assert sum(result is not None for result in results) == 1
    db.refresh(product)
    assert product.stock == 1
    assert product.reserved_stock == 1
    assert product.reserved_stock <= product.stock
