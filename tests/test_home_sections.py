import pytest
from fastapi import FastAPI, Header
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db import models
from app.db.database import Base, get_db
from app.routes.auth import get_current_user
from app.routes.home_sections import MAX_PER_STORE, MAX_SECTIONS, router


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

GOD_EMAIL = "god@example.com"


def _client():
    app = FastAPI()
    app.include_router(router, prefix="/api")

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def current_user(x_test_user: str | None = Header(default=None)):
        from fastapi import HTTPException

        if not x_test_user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        with TestingSessionLocal() as session:
            user = session.scalar(select(models.User).where(models.User.email == x_test_user))
            session.expunge(user)
            return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = current_user
    return TestClient(app)


GOD = {"X-Test-User": GOD_EMAIL}
OWNER = {"X-Test-User": "owner@example.com"}


@pytest.fixture(autouse=True)
def database(monkeypatch):
    monkeypatch.setenv("GOD_USER_EMAIL", GOD_EMAIL)
    Base.metadata.create_all(bind=engine)
    with TestingSessionLocal() as db:
        db.add(models.User(email=GOD_EMAIL, password_hash=hash_password("Secret123!"), is_verified=True, role="god"))
        owner = models.User(email="owner@example.com", password_hash=hash_password("Secret123!"), is_verified=True, role="store_owner")
        db.add(owner)
        db.flush()
        _seed_catalog(db, owner.id)
        db.commit()
    yield
    Base.metadata.drop_all(bind=engine)


def _seed_catalog(db, owner_id):
    def store(name, business_type):
        item = models.Store(name=name, owner_id=owner_id, business_type=business_type)
        db.add(item)
        db.flush()
        return item

    cafe = store("Cafe", "cafe")
    diner = store("Diner", "restaurant")
    shoes = store("Shoes", "clothing")
    store("Closed bakery", "bakery")
    for index in range(6):
        db.add(models.Product(name=f"Latte {index}", price=10, stock=5, store_id=cafe.id))
    db.add(models.Product(name="Soup", price=20, stock=3, store_id=diner.id))
    db.add(models.Product(name="Sold out soup", price=20, stock=0, store_id=diner.id))
    db.add(models.Product(name="Sneaker", price=90, stock=2, store_id=shoes.id))


def _payload(**overrides):
    base = {"title": "Hungry?", "kind": "stores", "business_types": ["cafe", "restaurant"]}
    base.update(overrides)
    return base


def _create(client, **overrides):
    response = client.post("/api/admin/home-sections", headers=GOD, json=_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


def test_admin_endpoints_are_god_only():
    client = _client()
    section = _create(client)
    calls = [
        ("get", "/api/admin/home-sections", None),
        ("post", "/api/admin/home-sections", _payload()),
        ("patch", f"/api/admin/home-sections/{section['id']}", {"title": "x"}),
        ("put", "/api/admin/home-sections/order", {"ids": [section["id"]]}),
        ("delete", f"/api/admin/home-sections/{section['id']}", None),
        ("get", f"/api/admin/home-sections/{section['id']}/preview", None),
    ]
    for method, url, body in calls:
        kwargs = {"json": body} if body is not None else {}
        assert getattr(client, method)(url, headers=OWNER, **kwargs).status_code == 403, (method, url)
        assert getattr(client, method)(url, **kwargs).status_code == 401, (method, url)


def test_role_alone_is_not_enough_without_the_configured_god_email(monkeypatch):
    client = _client()
    monkeypatch.setenv("GOD_USER_EMAIL", "someone-else@example.com")
    assert client.get("/api/admin/home-sections", headers=GOD).status_code == 403


@pytest.mark.parametrize(
    "overrides",
    [
        {"title": "   "},
        {"title": "x" * 121},
        {"business_types": []},
        {"business_types": ["not_a_type"]},
        {"kind": "banners"},
        {"background_color": "red"},
        {"background_color": "#12345"},
        {"item_limit": 0},
        {"item_limit": 25},
        {"titles": {"xx": "unsupported language"}},
        {"titles": {"en": "x" * 121}},
    ],
)
def test_invalid_sections_are_rejected(overrides):
    response = _client().post("/api/admin/home-sections", headers=GOD, json=_payload(**overrides))
    assert response.status_code == 422


def test_input_is_normalised():
    section = _create(
        _client(),
        title="  Hungry   now?  ",
        titles={"en": "  Hungry? ", "fa": "   "},
        business_types=["cafe", "cafe", "restaurant"],
        background_color="#FFAA00",
    )
    assert section["title"] == "Hungry now?"
    assert section["titles"] == {"en": "Hungry?"}
    assert section["business_types"] == ["cafe", "restaurant"]
    assert section["background_color"] == "#ffaa00"
    assert section["is_active"] is True and section["item_limit"] == 12


def test_section_count_is_capped():
    client = _client()
    for _ in range(MAX_SECTIONS):
        _create(client)
    response = client.post("/api/admin/home-sections", headers=GOD, json=_payload())
    assert response.status_code == 409


def test_update_delete_and_reorder_are_audited():
    client = _client()
    first, second, third = (_create(client, title=f"S{index}") for index in range(3))
    assert [first["position"], second["position"], third["position"]] == [0, 1, 2]

    updated = client.patch(
        f"/api/admin/home-sections/{first['id']}",
        headers=GOD,
        json={"title": "Renamed", "is_active": False, "item_limit": 6, "business_types": ["clothing"]},
    ).json()
    assert updated["title"] == "Renamed" and updated["is_active"] is False
    assert updated["item_limit"] == 6 and updated["business_types"] == ["clothing"]
    again = client.patch(f"/api/admin/home-sections/{first['id']}", headers=GOD, json={"kind": None}).json()
    assert again["kind"] == "stores" and again["title"] == "Renamed"

    reordered = client.put(
        "/api/admin/home-sections/order", headers=GOD, json={"ids": [third["id"], first["id"], second["id"]]}
    )
    assert [item["id"] for item in reordered.json()] == [third["id"], first["id"], second["id"]]
    listing = client.get("/api/admin/home-sections", headers=GOD).json()
    assert [item["id"] for item in listing] == [third["id"], first["id"], second["id"]]

    for bad in ([third["id"]], [third["id"], first["id"], first["id"]], [third["id"], first["id"], 999]):
        assert client.put("/api/admin/home-sections/order", headers=GOD, json={"ids": bad}).status_code == 400

    assert client.delete(f"/api/admin/home-sections/{second['id']}", headers=GOD).status_code == 204
    assert client.delete(f"/api/admin/home-sections/{second['id']}", headers=GOD).status_code == 404
    assert client.patch("/api/admin/home-sections/9999", headers=GOD, json={"title": "x"}).status_code == 404

    with TestingSessionLocal() as db:
        actions = [log.action for log in db.scalars(select(models.AuditLog).order_by(models.AuditLog.id))]
    assert actions.count("home_section.created") == 3
    assert actions.count("home_section.updated") == 2
    assert actions.count("home_section.reordered") == 1
    assert actions.count("home_section.deleted") == 1


def test_public_store_section_only_lists_live_stores_of_the_chosen_types():
    client = _client()
    _create(client, business_types=["cafe", "restaurant", "bakery"])
    response = client.get("/api/public/home-sections")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    (section,) = response.json()["sections"]
    assert sorted(item["name"] for item in section["items"]) == ["Cafe", "Diner"]
    assert {item["product_count"] for item in section["items"]} == {6, 1}
    assert "is_active" not in section and "position" not in section


def test_public_product_section_hides_unsellable_products_and_caps_one_big_store():
    client = _client()
    _create(client, kind="products", business_types=["cafe", "restaurant"], item_limit=24)
    (section,) = client.get("/api/public/home-sections").json()["sections"]
    names = [item["name"] for item in section["items"]]
    assert "Sold out soup" not in names and "Sneaker" not in names
    assert len(names) == len(set(names)) == 7
    assert section["items"][0]["store_name"] in {"Cafe", "Diner"}

    _create(client, title="Small", kind="products", business_types=["cafe", "restaurant"], item_limit=4)
    small = client.get("/api/public/home-sections").json()["sections"][1]
    cafe_items = [item for item in small["items"] if item["store_name"] == "Cafe"]
    assert len(small["items"]) == 4 and len(cafe_items) <= MAX_PER_STORE
    assert any(item["store_name"] == "Diner" for item in small["items"])


def test_public_page_skips_inactive_and_empty_sections_and_keeps_order():
    client = _client()
    food = _create(client, title="Food")
    hidden = _create(client, title="Hidden", is_active=False)
    empty = _create(client, title="Empty", business_types=["bakery"])
    fashion = _create(client, title="Fashion", business_types=["clothing"])

    order = [fashion["id"], food["id"], hidden["id"], empty["id"]]
    assert client.put("/api/admin/home-sections/order", headers=GOD, json={"ids": order}).status_code == 200
    titles = [section["title"] for section in client.get("/api/public/home-sections").json()["sections"]]
    assert titles == ["Fashion", "Food"]


def test_public_endpoint_needs_no_login_and_exposes_no_private_fields():
    client = _client()
    _create(client, kind="products", business_types=["cafe"])
    body = client.get("/api/public/home-sections").json()
    item = body["sections"][0]["items"][0]
    assert set(item) == {"id", "name", "description", "image_url", "price", "stock", "store_id", "store_name", "business_type"}


def test_preview_works_for_inactive_sections():
    client = _client()
    section = _create(client, is_active=False)
    assert client.get("/api/public/home-sections").json()["sections"] == []
    preview = client.get(f"/api/admin/home-sections/{section['id']}/preview", headers=GOD).json()
    assert preview["is_active"] is False and len(preview["items"]) == 2


def test_section_decoration_and_pinned_items_are_validated_and_publicly_rendered():
    client = _client()
    with TestingSessionLocal() as db:
        pinned_id = db.scalar(select(models.Product.id).where(models.Product.name == "Latte 0"))

    section = _create(
        client,
        kind="products",
        business_types=["cafe", "restaurant"],
        subtitle="  Fresh   picks ",
        subtitles={"en": "  Just   in "},
        background_color_2="#FFB199",
        pattern="zellij",
        edge="wave",
        card_style="glass",
        icon="🔥",
        show_all_link=False,
        pinned_ids=[pinned_id, pinned_id],
        fill_random=False,
        item_limit=12,
    )

    assert section["pinned_ids"] == [pinned_id]
    assert section["pinned_items"] == [
        {"id": pinned_id, "name": "Latte 0", "business_type": "cafe", "store_name": "Cafe", "visible": True}
    ]
    assert section["subtitle"] == "Fresh picks"
    assert section["subtitles"] == {"en": "Just in"}
    assert section["background_color_2"] == "#ffb199"

    public = client.get("/api/public/home-sections").json()["sections"][0]
    assert public["items"][0]["id"] == pinned_id
    assert public["pattern"] == "zellij" and public["edge"] == "wave"
    assert public["card_style"] == "glass" and public["show_all_link"] is False
    assert "pinned_ids" not in public and "fill_random" not in public
    assert client.post(
        "/api/admin/home-sections",
        headers=GOD,
        json=_payload(pattern="unknown"),
    ).status_code == 422
    assert client.post(
        "/api/admin/home-sections",
        headers=GOD,
        json=_payload(kind="stores", business_types=["restaurant"], pinned_ids=[pinned_id]),
    ).status_code == 422


def test_pin_candidates_are_god_only_and_type_changes_prune_pins():
    client = _client()
    with TestingSessionLocal() as db:
        pinned_id = db.scalar(select(models.Store.id).where(models.Store.name == "Cafe"))

    candidate_url = "/api/admin/home-sections/candidates?kind=stores&business_types=cafe&q=Caf"
    assert client.get(candidate_url, headers=OWNER).status_code == 403
    assert client.get(candidate_url).status_code == 401
    candidates = client.get(candidate_url, headers=GOD).json()["items"]
    assert [item["id"] for item in candidates] == [pinned_id]

    section = _create(client, business_types=["cafe"], pinned_ids=[pinned_id], fill_random=False)
    updated = client.patch(
        f"/api/admin/home-sections/{section['id']}",
        headers=GOD,
        json={"business_types": ["restaurant"]},
    ).json()
    assert updated["pinned_ids"] == []
