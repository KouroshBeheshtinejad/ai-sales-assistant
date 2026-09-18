from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db.models import Conversation, Product, Store, User
from app.services.cart_service import CartService
from app.services.guest_commerce import extract_quantity, resolve_product


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def make_store(db, name):
    user = User(email=f"{name}@example.com", password_hash="hash")
    db.add(user)
    db.flush()
    store = Store(name=name, owner_id=user.id, business_type="clothing")
    db.add(store)
    db.flush()
    return store


def make_product(db, store, name, color="مشکی", size="۴۲", stock=5, active=True):
    product = Product(
        store_id=store.id,
        name=name,
        description=name,
        color=color,
        size=size,
        price=Decimal("100.00"),
        stock=stock,
        is_active=active,
    )
    db.add(product)
    db.flush()
    return product


def test_quantity_normalization_rejects_false_positive_and_signed_values():
    assert extract_quantity("دو تا") == 2
    assert extract_quantity("دوتا") == 2
    assert extract_quantity("۳ عدد") == 3
    assert extract_quantity("٣ عدد") == 3
    assert extract_quantity("2") == 2
    assert extract_quantity("دوست دارم") is None
    assert extract_quantity("-2") == -2
    assert extract_quantity("۰") == 0


def test_resolver_uses_current_product_evidence_before_history(db):
    store = make_store(db, "resolver")
    previous = make_product(db, store, "کتونی سفید", color="سفید")
    current = make_product(db, store, "کتونی مشکی", color="مشکی")
    history = [{"role": "user", "content": previous.name}]

    assert resolve_product(db, store.id, "کتونی مشکی", history) is current


def test_resolver_returns_none_for_ambiguous_history(db):
    store = make_store(db, "ambiguous")
    first = make_product(db, store, "کتونی اول")
    second = make_product(db, store, "کتونی دوم")
    history = [
        {"role": "user", "content": first.name},
        {"role": "user", "content": second.name},
    ]

    assert resolve_product(db, store.id, "دو تا می‌خوام", history) is None


def test_resolver_only_returns_active_products_from_requested_store(db):
    store = make_store(db, "active-store")
    other_store = make_store(db, "other-store")
    inactive = make_product(db, store, "کفش غیرفعال", active=False)
    other = make_product(db, other_store, "کفش فروشگاه دیگر")

    assert resolve_product(db, store.id, inactive.name) is None
    assert resolve_product(db, store.id, other.name) is None


def test_guest_cart_token_is_bound_to_its_conversation_store(db):
    store = make_store(db, "guest-owner")
    other_store = make_store(db, "guest-other")
    conversation = Conversation(store_id=store.id, guest_token="secure-token", status="active")
    db.add(conversation)
    db.commit()

    cart = CartService.get_or_create_cart(
        db, user_id=None, store_id=store.id, guest_token="secure-token"
    )
    assert cart.store_id == store.id

    with pytest.raises(ValueError, match="not valid for this store"):
        CartService.get_or_create_cart(
            db, user_id=None, store_id=other_store.id, guest_token="secure-token"
        )
