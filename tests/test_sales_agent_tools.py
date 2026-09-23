import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db.models import Product, Store, User
from app.services.sales_agent import SalesAgentService
from app.services import sales_tools
from app.services.privacy_retention import purge_expired_conversation_messages
from app.db.models import Conversation, Message, Order


class ToolLoopProvider:
    def __init__(self):
        self.calls = []

    def complete(self, system_prompt, user_prompt, messages=None, tools=None, response_format=None):
        self.calls.append({"messages": messages, "tools": tools})
        if len(self.calls) == 1:
            return {
                "content": "",
                "tool_calls": [{
                    "id": "call-1",
                    "function": {
                        "name": "add_to_cart",
                        "arguments": json.dumps({"product_id": 1, "quantity": 2}),
                    },
                }],
            }
        return "به سبد اضافه شد."


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_sales_agent_executes_validated_tool_and_returns_final_answer(db):
    seller = User(email="agent-seller@example.com", password_hash="hash", is_verified=True)
    customer = User(email="agent-customer@example.com", password_hash="hash", is_verified=True)
    store = Store(name="Agent Store", owner=seller)
    product = Product(name="Burger", price=10, stock=5, store=store, is_active=True)
    db.add_all([seller, customer, store, product])
    db.commit()

    provider = ToolLoopProvider()
    answer = SalesAgentService(db, provider).respond(
        store.id,
        "دو تا برگر میخوام",
        context={"user_id": customer.id, "guest_token": None},
    )

    assert answer == "به سبد اضافه شد."
    assert any(tool["function"]["name"] == "add_to_cart" for tool in provider.calls[0]["tools"])


def test_tool_arguments_cannot_cross_customer_ownership(db):
    from app.services.sales_tools import get_order
    from app.db.models import Order

    seller = User(email="owner-seller@example.com", password_hash="hash", is_verified=True)
    owner = User(email="owner@example.com", password_hash="hash", is_verified=True)
    attacker = User(email="attacker@example.com", password_hash="hash", is_verified=True)
    store = Store(name="Ownership Store", owner=seller)
    order = Order(
        user=owner,
        store=store,
        status="pending",
        customer_name="Owner",
        customer_phone="09120000000",
        customer_address="Tehran",
        total_amount=10,
    )
    db.add_all([seller, owner, attacker, store, order])
    db.commit()

    with pytest.raises(ValueError, match="Order not found"):
        get_order(db, order.id, {"user_id": attacker.id, "guest_token": None})


def test_sales_tools_cover_catalog_cart_checkout_and_order_reads(db):
    seller = User(email="tools-seller@example.com", password_hash="hash", is_verified=True)
    customer = User(email="tools-customer@example.com", password_hash="hash", is_verified=True)
    store = Store(name="Tools Store", owner=seller)
    product = Product(name="Burger", description="Fresh burger", price=10, stock=5, store=store, is_active=True)
    conversation = Conversation(store=store, guest_token="guest-tools")
    db.add_all([seller, customer, store, product, conversation])
    db.commit()
    user_context = {"user_id": customer.id, "guest_token": None, "conversation": conversation}
    guest_context = {"user_id": None, "guest_token": conversation.guest_token, "conversation": conversation}

    assert sales_tools.search_products(db, store.id, "burger")[0]["id"] == product.id
    assert sales_tools.get_product(db, store.id, product.id)["price"] == "10.00"
    assert sales_tools.get_product_stock(db, store.id, product.id)["stock"] == 5
    assert sales_tools.add_to_cart(db, store.id, product.id, 2, user_context)["items"][0]["quantity"] == 2
    assert sales_tools.update_cart_quantity(db, store.id, product.id, 1, user_context)["items"][0]["quantity"] == 1
    assert sales_tools.get_cart(db, store.id, user_context)["items"][0]["name"] == "Burger"
    assert sales_tools.remove_from_cart(db, store.id, product.id, user_context)["items"] == []
    sales_tools.add_to_cart(db, store.id, product.id, 1, guest_context)
    assert sales_tools.start_checkout(db, store.id, guest_context)["state"] == "awaiting_customer"


def test_sales_tool_validation_rejects_bad_quantity_and_store_scope(db):
    seller = User(email="validation-seller@example.com", password_hash="hash", is_verified=True)
    store = Store(name="Validation Store", owner=seller)
    product = Product(name="Item", price=10, stock=1, store=store, is_active=True)
    other_store = Store(name="Other Store", owner=seller)
    db.add_all([seller, store, product, other_store])
    db.commit()

    with pytest.raises(ValueError, match="between 1 and 100"):
        sales_tools.add_to_cart(db, store.id, product.id, 0, {"user_id": seller.id})
    with pytest.raises(ValueError, match="not found"):
        sales_tools.get_product(db, other_store.id, product.id)


def test_privacy_retention_removes_only_expired_messages(db):
    seller = User(email="retention-seller@example.com", password_hash="hash", is_verified=True)
    store = Store(name="Retention Store", owner=seller)
    conversation = Conversation(store=store, guest_token="retention-guest")
    db.add_all([seller, store, conversation])
    db.flush()
    db.add(Message(conversation=conversation, role="user", content="old"))
    db.add(Message(conversation=conversation, role="user", content="new"))
    db.commit()
    deleted = purge_expired_conversation_messages(db, 90)
    assert deleted == 0
    with pytest.raises(ValueError):
        purge_expired_conversation_messages(db, 0)