import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.db.database import Base, get_db
from app.db.models import Store, User
from app.main import app


@pytest.fixture
def support_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = session_factory()
    users = {
        "customer": User(email="support-customer@example.com", password_hash=hash_password("StrongPass123!")),
        "other_customer": User(email="support-other@example.com", password_hash=hash_password("StrongPass123!")),
        "agent": User(email="support-agent@example.com", password_hash=hash_password("StrongPass123!"), role="support"),
        "other_agent": User(email="support-agent-two@example.com", password_hash=hash_password("StrongPass123!"), role="support"),
    }
    db.add_all(users.values())
    db.commit()
    db.add(Store(name="Northwind Store", owner_id=users["customer"].id))
    db.commit()
    tokens = {key: create_access_token(str(user.id), user.token_version) for key, user in users.items()}
    db.close()

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, {key: {"Authorization": f"Bearer {token}"} for key, token in tokens.items()}
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_customer_support_conversation_is_private_and_claimable(support_client):
    client, headers = support_client
    created = client.post(
        "/api/support/conversations",
        headers=headers["customer"],
        json={"message": "I need help with my order"},
    )
    assert created.status_code == 201
    conversation_id = created.json()["id"]

    assert client.get("/api/support/queue", headers=headers["customer"]).status_code == 403
    assert client.get(
        f"/api/support/conversations/{conversation_id}", headers=headers["other_customer"]
    ).status_code == 404

    queue = client.get("/api/support/queue", headers=headers["agent"])
    assert queue.status_code == 200
    assert [item["id"] for item in queue.json()] == [conversation_id]
    assert client.get("/api/support/summary", headers=headers["agent"]).json() == {
        "attention_count": 1,
        "kind": "queue",
    }
    assert client.post(
        f"/api/support/queue/{conversation_id}/claim", headers=headers["agent"]
    ).status_code == 200
    assert client.post(
        f"/api/support/queue/{conversation_id}/claim", headers=headers["other_agent"]
    ).status_code == 409
    assert client.post(
        f"/api/support/queue/{conversation_id}/reply",
        headers=headers["agent"],
        json={"message": "We are checking this for you."},
    ).status_code == 200

    detail = client.get(
        f"/api/support/conversations/{conversation_id}", headers=headers["customer"]
    )
    assert detail.status_code == 200
    assert [message["content"] for message in detail.json()["messages"]] == [
        "I need help with my order",
        "We are checking this for you.",
    ]
    assert client.get("/api/support/summary", headers=headers["customer"]).json() == {
        "attention_count": 1,
        "kind": "replies",
    }


def test_cookie_authenticated_support_mutation_requires_csrf_header(support_client):
    client, headers = support_client
    client.cookies.set("access_token", headers["customer"]["Authorization"].removeprefix("Bearer "))
    client.cookies.set("csrf_token", "expected-token")

    blocked = client.post("/api/support/conversations", json={"message": "Help"})
    allowed = client.post(
        "/api/support/conversations",
        headers={"X-CSRF-Token": "expected-token"},
        json={"message": "Help"},
    )

    assert blocked.status_code == 403
    assert allowed.status_code == 201


def test_cookie_authenticated_legacy_api_mutation_requires_csrf_header(support_client):
    client, headers = support_client
    client.cookies.set("access_token", headers["customer"]["Authorization"].removeprefix("Bearer "))
    client.cookies.set("csrf_token", "expected-token")
    payload = {"store_id": 10, "name": "Probe", "price": 1}

    blocked = client.post("/products/", json=payload)
    passed_csrf = client.post(
        "/products/",
        headers={"X-CSRF-Token": "expected-token"},
        json=payload,
    )

    assert blocked.status_code == 403
    assert passed_csrf.status_code == 404


def test_support_can_search_stores_and_start_assigned_store_conversation(support_client):
    client, headers = support_client
    assert client.get("/api/support/stores?q=Northwind", headers=headers["customer"]).status_code == 403

    search = client.get("/api/support/stores?q=Northwind", headers=headers["agent"])
    assert search.status_code == 200
    stores = search.json()
    assert len(stores) == 1
    assert stores[0]["name"] == "Northwind Store"

    created = client.post(
        "/api/support/conversations",
        headers=headers["agent"],
        json={"store_id": stores[0]["id"], "message": "We are following up on a customer complaint."},
    )
    assert created.status_code == 201
    conversation_id = created.json()["id"]
    queued = client.get("/api/support/queue", headers=headers["agent"]).json()
    item = next(item for item in queued if item["id"] == conversation_id)
    assert item["status"] == "assigned"
    assert item["assigned_to"] is not None

    replied = client.post(
        f"/api/support/queue/{conversation_id}/reply",
        headers=headers["agent"],
        json={"message": "Could you confirm the order status?"},
    )
    assert replied.status_code == 200
    store_reply = client.post(
        f"/api/support/conversations/{conversation_id}/reply",
        headers=headers["customer"],
        json={"message": "The order is being prepared."},
    )
    assert store_reply.status_code == 200
    detail = client.get(
        f"/api/support/conversations/{conversation_id}", headers=headers["customer"]
    )
    assert detail.status_code == 200
    assert [message["role"] for message in detail.json()["messages"]] == ["user", "user", "assistant"]