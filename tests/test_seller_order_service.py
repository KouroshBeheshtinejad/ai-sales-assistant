from decimal import Decimal

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db.models import (
    Order,
    OrderItem,
    Product,
    Store,
    User,
)
from app.services.seller_order_service import SellerOrderService


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
    )

    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def create_user(db, email):
    user = User(
        email=email,
        password_hash="hashed-password",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def create_store(db, owner_id, name="Test Store"):
    store = Store(
        name=name,
        description="Test store description",
        business_type="retail",
        owner_id=owner_id,
    )
    db.add(store)
    db.commit()
    db.refresh(store)

    return store


def create_product(
    db,
    store_id,
    name="Test Product",
    price=Decimal("100.00"),
):
    product = Product(
        store_id=store_id,
        name=name,
        description="Test product description",
        price=price,
        stock=10,
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    return product


def create_order(db, user_id, store_id, product):
    order = Order(
        user_id=user_id,
        store_id=store_id,
        status="pending",
        customer_name="Test Customer",
        customer_phone="09120000000",
        customer_address="Test Address",
        total_amount=product.price,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    order_item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        product_name=product.name,
        unit_price=product.price,
        quantity=1,
        line_total=product.price,
    )
    db.add(order_item)
    db.commit()
    db.refresh(order)

    return order


def test_seller_can_list_store_orders(db):
    seller = create_user(db, "seller@example.com")
    customer = create_user(db, "customer@example.com")

    store = create_store(db, seller.id)
    product = create_product(db, store.id)

    order = create_order(
        db=db,
        user_id=customer.id,
        store_id=store.id,
        product=product,
    )

    orders = SellerOrderService.list_store_orders(
        db=db,
        seller_id=seller.id,
        store_id=store.id,
    )

    assert len(orders) == 1
    assert orders[0].id == order.id
    assert orders[0].store_id == store.id


def test_seller_cannot_list_orders_of_another_store(db):
    seller = create_user(db, "seller@example.com")
    another_seller = create_user(db, "another@example.com")
    customer = create_user(db, "customer@example.com")

    another_store = create_store(
        db,
        owner_id=another_seller.id,
        name="Another Store",
    )
    product = create_product(db, another_store.id)

    create_order(
        db=db,
        user_id=customer.id,
        store_id=another_store.id,
        product=product,
    )

    with pytest.raises(ValueError, match="Store not found"):
        SellerOrderService.list_store_orders(
            db=db,
            seller_id=seller.id,
            store_id=another_store.id,
        )


def test_seller_can_get_order_from_owned_store(db):
    seller = create_user(db, "seller@example.com")
    customer = create_user(db, "customer@example.com")

    store = create_store(db, seller.id)
    product = create_product(db, store.id)

    order = create_order(
        db=db,
        user_id=customer.id,
        store_id=store.id,
        product=product,
    )

    result = SellerOrderService.get_order(
        db=db,
        seller_id=seller.id,
        order_id=order.id,
    )

    assert result.id == order.id
    assert result.store_id == store.id
    assert len(result.items) == 1


def test_seller_cannot_get_order_from_another_store(db):
    seller = create_user(db, "seller@example.com")
    another_seller = create_user(db, "another@example.com")
    customer = create_user(db, "customer@example.com")

    another_store = create_store(
        db,
        owner_id=another_seller.id,
        name="Another Store",
    )
    product = create_product(db, another_store.id)

    order = create_order(
        db=db,
        user_id=customer.id,
        store_id=another_store.id,
        product=product,
    )

    with pytest.raises(ValueError, match="Order not found"):
        SellerOrderService.get_order(
            db=db,
            seller_id=seller.id,
            order_id=order.id,
        )


def test_seller_can_update_order_status(db):
    seller = create_user(db, "seller@example.com")
    customer = create_user(db, "customer@example.com")

    store = create_store(db, seller.id)
    product = create_product(db, store.id)

    order = create_order(
        db=db,
        user_id=customer.id,
        store_id=store.id,
        product=product,
    )

    updated_order = SellerOrderService.update_status(
        db=db,
        seller_id=seller.id,
        order_id=order.id,
        new_status="confirmed",
    )

    assert updated_order.status == "confirmed"


def test_seller_cancellation_releases_reserved_stock(db):
    seller = create_user(db, "seller-cancel@example.com")
    customer = create_user(db, "customer-cancel@example.com")
    store = create_store(db, seller.id)
    product = create_product(db, store.id)
    product.stock = 10
    product.reserved_stock = 1
    db.commit()
    order = create_order(db, customer.id, store.id, product)

    cancelled = SellerOrderService.update_status(
        db=db,
        seller_id=seller.id,
        order_id=order.id,
        new_status="cancelled",
    )

    db.refresh(product)
    assert cancelled.status == "cancelled"
    assert product.stock == 10
    assert product.reserved_stock == 0


def test_seller_cannot_make_invalid_status_transition(db):
    seller = create_user(db, "seller@example.com")
    customer = create_user(db, "customer@example.com")

    store = create_store(db, seller.id)
    product = create_product(db, store.id)

    order = create_order(
        db=db,
        user_id=customer.id,
        store_id=store.id,
        product=product,
    )

    with pytest.raises(ValueError, match="Cannot change status"):
        SellerOrderService.update_status(
            db=db,
            seller_id=seller.id,
            order_id=order.id,
            new_status="delivered",
        )


def test_seller_cannot_use_invalid_status(db):
    seller = create_user(db, "seller@example.com")
    customer = create_user(db, "customer@example.com")

    store = create_store(db, seller.id)
    product = create_product(db, store.id)

    order = create_order(
        db=db,
        user_id=customer.id,
        store_id=store.id,
        product=product,
    )

    with pytest.raises(ValueError, match="Invalid status"):
        SellerOrderService.update_status(
            db=db,
            seller_id=seller.id,
            order_id=order.id,
            new_status="unknown_status",
        )