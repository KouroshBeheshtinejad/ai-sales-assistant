import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db.models import User, Store, Product
from app.services.cart_service import CartService
from app.services.order_service import OrderService


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
    )

    Base.metadata.create_all(engine)

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def test_data(db):
    user = User(
        email="order-test@example.com",
        password_hash="test-hash",
    )

    store = Store(
        name="Order Test Store",
        owner=user,
    )

    product = Product(
        name="Order Product",
        description="Product for order tests",
        price=100000,
        stock=10,
        store=store,
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    db.refresh(store)
    db.refresh(product)

    return {
        "user": user,
        "store": store,
        "product": product,
    }


def add_product_to_cart(db, test_data, quantity=2):
    return CartService.add_item(
        db=db,
        user_id=test_data["user"].id,
        store_id=test_data["store"].id,
        product_id=test_data["product"].id,
        quantity=quantity,
    )


def create_order(db, test_data):
    return OrderService.create_order(
        db=db,
        user_id=test_data["user"].id,
        store_id=test_data["store"].id,
        customer_name="Ali Ahmadi",
        customer_phone="09120000000",
        customer_address="Tehran, Iran",
    )


def test_create_order(db, test_data):
    add_product_to_cart(db, test_data, quantity=2)

    order = create_order(db, test_data)

    assert order.id is not None
    assert order.user_id == test_data["user"].id
    assert order.store_id == test_data["store"].id
    assert order.status == "pending"
    assert order.customer_name == "Ali Ahmadi"
    assert order.customer_phone == "09120000000"
    assert order.customer_address == "Tehran, Iran"


def test_order_total_and_item_snapshot(db, test_data):
    add_product_to_cart(db, test_data, quantity=3)

    order = create_order(db, test_data)

    assert order.total_amount == 300000
    assert len(order.items) == 1

    item = order.items[0]
    assert item.product_id == test_data["product"].id
    assert item.product_name == "Order Product"
    assert item.unit_price == 100000
    assert item.quantity == 3
    assert item.line_total == 300000


def test_create_order_reduces_stock(db, test_data):
    add_product_to_cart(db, test_data, quantity=4)

    create_order(db, test_data)

    db.refresh(test_data["product"])
    assert test_data["product"].stock == 6


def test_create_order_clears_cart(db, test_data):
    add_product_to_cart(db, test_data, quantity=2)

    create_order(db, test_data)

    cart = CartService.get_or_create_cart(
        db=db,
        user_id=test_data["user"].id,
        store_id=test_data["store"].id,
    )

    assert cart.items == []


def test_reject_empty_cart(db, test_data):
    with pytest.raises(ValueError, match="Cart is empty"):
        create_order(db, test_data)


def test_reject_insufficient_stock(db, test_data):
    add_product_to_cart(db, test_data, quantity=5)

    product = test_data["product"]
    product.stock = 3
    db.commit()

    with pytest.raises(
        ValueError,
        match="Insufficient stock",
    ):
        create_order(db, test_data)


def test_get_order_by_id(db, test_data):
    add_product_to_cart(db, test_data)

    order = create_order(db, test_data)

    found = OrderService.get_order_by_id(
        db=db,
        order_id=order.id,
        user_id=test_data["user"].id,
    )

    assert found is not None
    assert found.id == order.id


def test_do_not_get_another_users_order(db, test_data):
    add_product_to_cart(db, test_data)

    order = create_order(db, test_data)

    other_user = User(
        email="another-user@example.com",
        password_hash="test-hash",
    )
    db.add(other_user)
    db.commit()
    db.refresh(other_user)

    found = OrderService.get_order_by_id(
        db=db,
        order_id=order.id,
        user_id=other_user.id,
    )

    assert found is None


def test_list_user_orders(db, test_data):
    add_product_to_cart(db, test_data)

    first_order = create_order(db, test_data)

    # ایجاد محصول دوم برای سفارش دوم
    second_product = Product(
        name="Second Product",
        description="Second test product",
        price=50000,
        stock=10,
        store_id=test_data["store"].id,
        is_active=True,
    )
    db.add(second_product)
    db.commit()
    db.refresh(second_product)

    CartService.add_item(
        db=db,
        user_id=test_data["user"].id,
        store_id=test_data["store"].id,
        product_id=second_product.id,
        quantity=1,
    )

    second_order = create_order(db, test_data)

    orders = OrderService.list_user_orders(
        db=db,
        user_id=test_data["user"].id,
    )

    order_ids = [order.id for order in orders]

    assert first_order.id in order_ids
    assert second_order.id in order_ids
    assert len(orders) == 2


def test_cancel_pending_order(db, test_data):
    add_product_to_cart(db, test_data, quantity=3)

    order = create_order(db, test_data)

    db.refresh(test_data["product"])
    assert test_data["product"].stock == 7

    cancelled = OrderService.cancel_order(
        db=db,
        order_id=order.id,
        user_id=test_data["user"].id,
    )

    assert cancelled.status == "cancelled"
    assert cancelled.cancelled_at is not None

    db.refresh(test_data["product"])
    assert test_data["product"].stock == 10


def test_reject_cancelled_order_cancellation(db, test_data):
    add_product_to_cart(db, test_data, quantity=2)

    order = create_order(db, test_data)

    OrderService.cancel_order(
        db=db,
        order_id=order.id,
        user_id=test_data["user"].id,
    )

    with pytest.raises(
        ValueError,
        match="Only pending orders can be cancelled",
    ):
        OrderService.cancel_order(
            db=db,
            order_id=order.id,
            user_id=test_data["user"].id,
        )