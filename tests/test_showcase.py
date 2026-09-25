from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db import models
from app.db.database import Base, get_db
from app.routes.showcase import router


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _client():
    # A minimal app: the showcase router does not depend on auth, chat or providers.
    app = FastAPI()
    app.include_router(router)
    app.include_router(router, prefix="/api")

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _seed(db):
    owner = models.User(email="owner@example.com", password_hash=hash_password("Secret123!"), is_verified=True)
    db.add(owner)
    db.flush()
    busy = models.Store(name="Busy store", description="x" * 400, owner_id=owner.id)
    empty = models.Store(name="Empty store", owner_id=owner.id)
    db.add_all([busy, empty])
    db.flush()
    db.add_all(
        [
            models.Product(name="Visible", price=10, stock=5, store_id=busy.id),
            models.Product(name="Sold out", price=10, stock=0, store_id=busy.id),
            models.Product(name="Fully reserved", price=10, stock=2, reserved_stock=2, store_id=busy.id),
            models.Product(name="Inactive", price=10, stock=5, is_active=False, store_id=busy.id),
        ]
    )
    db.commit()
    return busy.id


def setup_function():
    Base.metadata.create_all(bind=engine)


def teardown_function():
    Base.metadata.drop_all(bind=engine)


def test_showcase_only_returns_sellable_products_and_their_stores():
    with TestingSessionLocal() as db:
        busy_id = _seed(db)

    response = _client().get("/public/showcase")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["stats"] == {"stores": 1, "products": 1}
    assert [store["id"] for store in body["stores"]] == [busy_id]
    assert body["stores"][0]["product_count"] == 1
    assert len(body["stores"][0]["description"]) <= 160
    assert [product["name"] for product in body["products"]] == ["Visible"]
    assert body["products"][0]["store_name"] == "Busy store"
    assert body["products"][0]["stock"] == 5


def test_showcase_is_available_under_api_prefix_and_respects_limits():
    with TestingSessionLocal() as db:
        _seed(db)

    client = _client()
    assert client.get("/api/public/showcase?stores=0&products=0").json()["stores"] == []
    assert client.get("/api/public/showcase?stores=99").status_code == 422


def test_showcase_is_empty_without_data():
    body = _client().get("/public/showcase").json()
    assert body == {"stats": {"stores": 0, "products": 0}, "stores": [], "products": []}