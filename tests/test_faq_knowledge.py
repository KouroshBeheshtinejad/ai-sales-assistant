import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.db.database import Base, get_db
from app.db import models
from app.main import app


SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
        user = models.User(email=email, password_hash=hash_password("StrongPass123!"))
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def create_store(user_id: int, name: str = "Demo Store", business_type: str = "clothing"):
    db = TestingSessionLocal()
    try:
        store = models.Store(
            name=name,
            description="Test store",
            business_type=business_type,
            owner_id=user_id,
        )
        db.add(store)
        db.commit()
        db.refresh(store)
        return store
    finally:
        db.close()


def auth_headers(user_id: int):
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


def test_create_and_list_faqs(client):
    user = create_user("owner@example.com")
    store = create_store(user.id)
    headers = auth_headers(user.id)

    create_response = client.post(
        f"/stores/{store.id}/faqs",
        json={"question": "How fast is delivery?", "answer": "Within 3 business days."},
        headers=headers,
    )
    assert create_response.status_code == 201
    data = create_response.json()
    assert data["question"] == "How fast is delivery?"
    assert data["store_id"] == store.id

    list_response = client.get(f"/stores/{store.id}/faqs", headers=headers)
    assert list_response.status_code == 200
    payload = list_response.json()
    assert len(payload) == 1
    assert payload[0]["answer"] == "Within 3 business days."


def test_update_and_delete_faq(client):
    user = create_user("owner2@example.com")
    store = create_store(user.id)
    headers = auth_headers(user.id)

    create_response = client.post(
        f"/stores/{store.id}/faqs",
        json={"question": "Return policy?", "answer": "30 days."},
        headers=headers,
    )
    faq_id = create_response.json()["id"]

    update_response = client.put(
        f"/stores/{store.id}/faqs/{faq_id}",
        json={"question": "Return policy updated", "answer": "60 days."},
        headers=headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["question"] == "Return policy updated"

    delete_response = client.delete(f"/stores/{store.id}/faqs/{faq_id}", headers=headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "FAQ deleted successfully"


def test_create_and_list_knowledge_entries(client):
    user = create_user("owner3@example.com")
    store = create_store(user.id, name="Knowledge Store")
    headers = auth_headers(user.id)

    create_response = client.post(
        f"/stores/{store.id}/knowledge",
        json={"title": "Shipping policy", "content": "Free shipping over $50."},
        headers=headers,
    )
    assert create_response.status_code == 201
    entry = create_response.json()
    assert entry["title"] == "Shipping policy"
    assert entry["store_id"] == store.id

    list_response = client.get(f"/stores/{store.id}/knowledge", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_update_and_delete_knowledge_entry(client):
    user = create_user("owner4@example.com")
    store = create_store(user.id)
    headers = auth_headers(user.id)

    create_response = client.post(
        f"/stores/{store.id}/knowledge",
        json={"title": "Warranty", "content": "12-month warranty."},
        headers=headers,
    )
    knowledge_id = create_response.json()["id"]

    update_response = client.put(
        f"/stores/{store.id}/knowledge/{knowledge_id}",
        json={"title": "Warranty extended", "content": "24-month warranty."},
        headers=headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Warranty extended"

    delete_response = client.delete(f"/stores/{store.id}/knowledge/{knowledge_id}", headers=headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Knowledge entry deleted successfully"


def test_reject_unauthorized_store_access(client):
    owner = create_user("owner5@example.com")
    attacker = create_user("attacker@example.com")
    store = create_store(owner.id, name="Private Store")
    headers = auth_headers(attacker.id)

    response = client.get(f"/stores/{store.id}/faqs", headers=headers)
    assert response.status_code == 404

    response = client.post(
        f"/stores/{store.id}/faqs",
        json={"question": "Forbidden", "answer": "Nope."},
        headers=headers,
    )
    assert response.status_code == 404


def test_reject_access_to_another_users_faq_and_knowledge(client):
    owner = create_user("owner6@example.com")
    attacker = create_user("attacker2@example.com")
    store = create_store(owner.id)
    headers = auth_headers(owner.id)
    faq_response = client.post(
        f"/stores/{store.id}/faqs",
        json={"question": "Original", "answer": "Answer"},
        headers=headers,
    )
    faq_id = faq_response.json()["id"]

    knowledge_response = client.post(
        f"/stores/{store.id}/knowledge",
        json={"title": "Original KB", "content": "Answer"},
        headers=headers,
    )
    knowledge_id = knowledge_response.json()["id"]

    attacker_headers = auth_headers(attacker.id)

    assert client.get(f"/stores/{store.id}/faqs/{faq_id}", headers=attacker_headers).status_code == 404
    assert client.put(f"/stores/{store.id}/faqs/{faq_id}", json={"question": "Hacked", "answer": "No"}, headers=attacker_headers).status_code == 404
    assert client.get(f"/stores/{store.id}/knowledge/{knowledge_id}", headers=attacker_headers).status_code == 404
    assert client.put(f"/stores/{store.id}/knowledge/{knowledge_id}", json={"title": "Hacked", "content": "No"}, headers=attacker_headers).status_code == 404


def test_missing_store_and_missing_records_return_404(client):
    user = create_user("owner7@example.com")
    headers = auth_headers(user.id)

    assert client.get("/stores/999/faqs", headers=headers).status_code == 404
    assert client.get("/stores/999/knowledge", headers=headers).status_code == 404

    store = create_store(user.id)
    faq_response = client.post(
        f"/stores/{store.id}/faqs",
        json={"question": "Q", "answer": "A"},
        headers=headers,
    )
    faq_id = faq_response.json()["id"]
    assert client.get(f"/stores/{store.id}/faqs/{faq_id + 999}", headers=headers).status_code == 404

    knowledge_response = client.post(
        f"/stores/{store.id}/knowledge",
        json={"title": "KB", "content": "A"},
        headers=headers,
    )
    knowledge_id = knowledge_response.json()["id"]
    assert client.get(f"/stores/{store.id}/knowledge/{knowledge_id + 999}", headers=headers).status_code == 404


def test_invalid_required_fields_are_rejected(client):
    user = create_user("owner8@example.com")
    store = create_store(user.id)
    headers = auth_headers(user.id)

    empty_faq = client.post(
        f"/stores/{store.id}/faqs",
        json={"question": "", "answer": ""},
        headers=headers,
    )
    assert empty_faq.status_code == 422

    empty_knowledge = client.post(
        f"/stores/{store.id}/knowledge",
        json={"title": "", "content": ""},
        headers=headers,
    )
    assert empty_knowledge.status_code == 422
