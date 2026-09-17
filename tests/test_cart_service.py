import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db.models import User, Store, Product
from app.services.cart_service import CartService


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
        email="test@example.com",
        password_hash="test-hash",
    )

    store = Store(
        name="Test Store",
        owner=user,
    )

    product = Product(
        name="Test Product",
        description="A test product",
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


def test_get_or_create_cart(db, test_data):
    user = test_data["user"]
    store = test_data["store"]

    cart = CartService.get_or_create_cart(
        db=db,
        user_id=user.id,
        store_id=store.id,
    )

    assert cart.id is not None
    assert cart.user_id == user.id
    assert cart.store_id == store.id
    assert cart.items == []


def test_add_item(db, test_data):
    user = test_data["user"]
    store = test_data["store"]
    product = test_data["product"]

    cart = CartService.add_item(
        db=db,
        user_id=user.id,
        store_id=store.id,
        product_id=product.id,
        quantity=2,
    )

    assert len(cart.items) == 1
    assert cart.items[0].product_id == product.id
    assert cart.items[0].quantity == 2


def test_add_same_item_increases_quantity(db, test_data):
    user = test_data["user"]
    store = test_data["store"]
    product = test_data["product"]

    CartService.add_item(
        db=db,
        user_id=user.id,
        store_id=store.id,
        product_id=product.id,
        quantity=2,
    )

    cart = CartService.add_item(
        db=db,
        user_id=user.id,
        store_id=store.id,
        product_id=product.id,
        quantity=3,
    )

    assert len(cart.items) == 1
    assert cart.items[0].quantity == 5


def test_update_item(db, test_data):
    user = test_data["user"]
    store = test_data["store"]
    product = test_data["product"]

    CartService.add_item(
        db=db,
        user_id=user.id,
        store_id=store.id,
        product_id=product.id,
        quantity=2,
    )

    cart = CartService.update_item(
        db=db,
        user_id=user.id,
        store_id=store.id,
        product_id=product.id,
        quantity=7,
    )

    assert cart.items[0].quantity == 7


def test_remove_item(db, test_data):
    user = test_data["user"]
    store = test_data["store"]
    product = test_data["product"]

    CartService.add_item(
        db=db,
        user_id=user.id,
        store_id=store.id,
        product_id=product.id,
        quantity=2,
    )

    cart = CartService.remove_item(
        db=db,
        user_id=user.id,
        store_id=store.id,
        product_id=product.id,
    )

    assert cart.items == []


def test_clear_cart(db, test_data):
    user = test_data["user"]
    store = test_data["store"]
    product = test_data["product"]

    CartService.add_item(
        db=db,
        user_id=user.id,
        store_id=store.id,
        product_id=product.id,
        quantity=2,
    )

    CartService.clear_cart(
        db=db,
        user_id=user.id,
        store_id=store.id,
    )

    cart = CartService.get_or_create_cart(
        db=db,
        user_id=user.id,
        store_id=store.id,
    )

    assert cart.items == []


def test_calculate_total(db, test_data):
    user = test_data["user"]
    store = test_data["store"]
    product = test_data["product"]

    cart = CartService.add_item(
        db=db,
        user_id=user.id,
        store_id=store.id,
        product_id=product.id,
        quantity=3,
    )

    total = CartService.calculate_total(cart)

    assert total == 300000


def test_reject_invalid_quantity(db, test_data):
    user = test_data["user"]
    store = test_data["store"]
    product = test_data["product"]

    with pytest.raises(ValueError, match="Quantity must be greater than zero"):
        CartService.add_item(
            db=db,
            user_id=user.id,
            store_id=store.id,
            product_id=product.id,
            quantity=0,
        )


def test_reject_insufficient_stock(db, test_data):
    user = test_data["user"]
    store = test_data["store"]
    product = test_data["product"]

    with pytest.raises(ValueError, match="Insufficient stock"):
        CartService.add_item(
            db=db,
            user_id=user.id,
            store_id=store.id,
            product_id=product.id,
            quantity=11,
        )