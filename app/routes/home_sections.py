"""Curated, randomly sampled rows for the public home page.

The platform admin (``god``) creates any number of sections. Each one has a title,
a background colour, a list of business types and a kind (``stores`` or
``products``). The public endpoint returns, for every active section, a fresh
random sample of live stores or sellable products from those business types.
Only data that is already public on the storefront is exposed.
"""

from __future__ import annotations

import random
from collections import Counter, defaultdict
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.business_types import BUSINESS_TYPES
from app.db.database import get_db
from app.db.models import HomeSection, Product, Store, User
from app.routes.admin import _require_god
from app.routes.auth import get_current_user
from app.routes.showcase import _sellable, _shorten
from app.services.audit_service import record_audit_log


router = APIRouter(tags=["Home Sections"])

SUPPORTED_LOCALES = ("fa", "en", "es", "de", "fr", "it")
MAX_SECTIONS = 20
MAX_PER_STORE = 3
_VALID_SLUGS = {item["slug"] for item in BUSINESS_TYPES}
_COLOR_PATTERN = r"^#[0-9a-fA-F]{6}$"
_OPTIONAL_COLOR_PATTERN = r"^(#[0-9a-fA-F]{6})?$"
PATTERNS = ("none", "dots", "grid", "diagonal", "waves", "zellij")
EDGES = ("straight", "wave", "curve")
CARD_STYLES = ("solid", "glass")
ICONS = (
    "🍔", "🍕", "☕", "🍰", "🥗", "🛒", "👗", "👟", "💄", "💎", "🏠", "🔧", "💻", "📱",
    "💊", "🐾", "🌿", "🌸", "🎨", "📚", "🎁", "🎉", "🚗", "✨", "🔥", "⭐", "💖", "🎓", "🧸", "🎵", "⚽",
)
SUBTITLE_MAX = 160
MAX_PINNED = 24


def _clean_titles(value: dict[str, str] | None) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    for code, title_text in (value or {}).items():
        if code not in SUPPORTED_LOCALES:
            raise ValueError(f"Unsupported language: {code}")
        title_text = " ".join(str(title_text).split())
        if len(title_text) > 120:
            raise ValueError("Titles can be at most 120 characters")
        if title_text:
            cleaned[code] = title_text
    return cleaned


def _clean_subtitles(value: dict[str, str] | None) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    for code, text_value in (value or {}).items():
        if code not in SUPPORTED_LOCALES:
            raise ValueError(f"Unsupported language: {code}")
        text_value = " ".join(str(text_value).split())
        if len(text_value) > SUBTITLE_MAX:
            raise ValueError(f"Subtitles can be at most {SUBTITLE_MAX} characters")
        if text_value:
            cleaned[code] = text_value
    return cleaned


def _clean_pins(value: list[int] | None) -> list[int] | None:
    if value is None:
        return None
    if any(item < 1 for item in value):
        raise ValueError("Invalid item id")
    return list(dict.fromkeys(value))


def _clean_icon(value: str | None) -> str | None:
    if value is not None and value and value not in ICONS:
        raise ValueError("Unknown icon")
    return value


def _clean_business_types(value: list[str]) -> list[str]:
    seen: list[str] = []
    for slug in value:
        if slug not in _VALID_SLUGS:
            raise ValueError(f"Unknown business type: {slug}")
        if slug not in seen:
            seen.append(slug)
    if not seen:
        raise ValueError("Choose at least one business type")
    return seen


class HomeSectionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    titles: dict[str, str] = Field(default_factory=dict)
    kind: Literal["stores", "products"] = "stores"
    business_types: list[str] = Field(min_length=1, max_length=len(BUSINESS_TYPES))
    background_color: str = Field("#f2f7f6", pattern=_COLOR_PATTERN)
    background_color_2: str = Field("", pattern=_OPTIONAL_COLOR_PATTERN)
    pattern: Literal["none", "dots", "grid", "diagonal", "waves", "zellij"] = "none"
    edge: Literal["straight", "wave", "curve"] = "straight"
    card_style: Literal["solid", "glass"] = "solid"
    icon: str = Field("", max_length=8)
    subtitle: str = Field("", max_length=SUBTITLE_MAX)
    subtitles: dict[str, str] = Field(default_factory=dict)
    show_all_link: bool = True
    pinned_ids: list[int] = Field(default_factory=list, max_length=MAX_PINNED)
    fill_random: bool = True
    item_limit: int = Field(12, ge=1, le=24)
    is_active: bool = True

    @field_validator("title", "subtitle")
    @classmethod
    def _text(cls, value: str, info) -> str:
        value = " ".join(value.split())
        if info.field_name == "title" and not value:
            raise ValueError("Title is required")
        return value

    @field_validator("titles")
    @classmethod
    def _titles(cls, value: dict[str, str]) -> dict[str, str]:
        return _clean_titles(value)

    @field_validator("subtitles")
    @classmethod
    def _subtitles(cls, value: dict[str, str]) -> dict[str, str]:
        return _clean_subtitles(value)

    @field_validator("icon")
    @classmethod
    def _icon(cls, value: str) -> str:
        return _clean_icon(value) or ""

    @field_validator("pinned_ids")
    @classmethod
    def _pins(cls, value: list[int]) -> list[int]:
        return _clean_pins(value) or []

    @field_validator("business_types")
    @classmethod
    def _types(cls, value: list[str]) -> list[str]:
        return _clean_business_types(value)

    @field_validator("background_color", "background_color_2")
    @classmethod
    def _color(cls, value: str) -> str:
        return value.lower()


class HomeSectionUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=120)
    titles: dict[str, str] | None = None
    kind: Literal["stores", "products"] | None = None
    business_types: list[str] | None = Field(None, min_length=1, max_length=len(BUSINESS_TYPES))
    background_color: str | None = Field(None, pattern=_COLOR_PATTERN)
    background_color_2: str | None = Field(None, pattern=_OPTIONAL_COLOR_PATTERN)
    pattern: Literal["none", "dots", "grid", "diagonal", "waves", "zellij"] | None = None
    edge: Literal["straight", "wave", "curve"] | None = None
    card_style: Literal["solid", "glass"] | None = None
    icon: str | None = Field(None, max_length=8)
    subtitle: str | None = Field(None, max_length=SUBTITLE_MAX)
    subtitles: dict[str, str] | None = None
    show_all_link: bool | None = None
    pinned_ids: list[int] | None = Field(None, max_length=MAX_PINNED)
    fill_random: bool | None = None
    item_limit: int | None = Field(None, ge=1, le=24)
    is_active: bool | None = None

    @field_validator("title", "subtitle")
    @classmethod
    def _text(cls, value: str | None, info) -> str | None:
        if value is None:
            return None
        value = " ".join(value.split())
        if info.field_name == "title" and not value:
            raise ValueError("Title is required")
        return value

    @field_validator("titles")
    @classmethod
    def _titles(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        return None if value is None else _clean_titles(value)

    @field_validator("subtitles")
    @classmethod
    def _subtitles(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        return None if value is None else _clean_subtitles(value)

    @field_validator("icon")
    @classmethod
    def _icon(cls, value: str | None) -> str | None:
        return _clean_icon(value)

    @field_validator("pinned_ids")
    @classmethod
    def _pins(cls, value: list[int] | None) -> list[int] | None:
        return _clean_pins(value)

    @field_validator("business_types")
    @classmethod
    def _types(cls, value: list[str] | None) -> list[str] | None:
        return None if value is None else _clean_business_types(value)

    @field_validator("background_color", "background_color_2")
    @classmethod
    def _color(cls, value: str | None) -> str | None:
        return None if value is None else value.lower()


class HomeSectionOrder(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=MAX_SECTIONS)


def _section_config(section: HomeSection) -> dict:
    return {
        "id": section.id,
        "title": section.title,
        "titles": section.titles or {},
        "kind": section.kind,
        "business_types": list(section.business_types or []),
        "background_color": section.background_color,
        "background_color_2": section.background_color_2 or "",
        "pattern": section.pattern,
        "edge": section.edge,
        "card_style": section.card_style,
        "icon": section.icon or "",
        "subtitle": section.subtitle or "",
        "subtitles": section.subtitles or {},
        "show_all_link": section.show_all_link,
        "pinned_ids": list(section.pinned_ids or []),
        "fill_random": section.fill_random,
        "item_limit": section.item_limit,
        "position": section.position,
        "is_active": section.is_active,
    }


def _audit_state(section: HomeSection) -> dict:
    return _section_config(section)


def _store_item(store: Store, product_count: int) -> dict:
    return {
        "id": store.id,
        "name": store.name,
        "description": _shorten(store.description),
        "logo_url": store.logo_url,
        "business_type": store.business_type,
        "product_count": product_count,
    }


def _product_item(product: Product, store: Store) -> dict:
    return {
        "id": product.id,
        "name": product.name,
        "description": _shorten(product.description),
        "image_url": product.image_url,
        "price": str(product.price),
        "currency": store.currency,
        "stock": product.stock - product.reserved_stock,
        "store_id": store.id,
        "store_name": store.name,
        "business_type": store.business_type,
    }


def _spread(
    rows: list[tuple[Product, Store]], limit: int, seed: Counter | None = None
) -> list[tuple[Product, Store]]:
    chosen: list[tuple[Product, Store]] = []
    leftovers: list[tuple[Product, Store]] = []
    per_store: dict[int, int] = defaultdict(int, seed or {})
    for product, store in rows:
        if len(chosen) >= limit:
            break
        if per_store[store.id] < MAX_PER_STORE:
            per_store[store.id] += 1
            chosen.append((product, store))
        else:
            leftovers.append((product, store))
    chosen.extend(leftovers[: limit - len(chosen)])
    return chosen


def _stores_stmt(types: list[str], *, ids: list[int] | None = None, exclude: list[int] | None = None):
    counts = (
        select(Product.store_id.label("store_id"), func.count(Product.id).label("n"))
        .where(*_sellable())
        .group_by(Product.store_id)
        .subquery()
    )
    stmt = select(Store, counts.c.n).join(counts, counts.c.store_id == Store.id).where(Store.business_type.in_(types))
    if ids is not None:
        stmt = stmt.where(Store.id.in_(ids))
    if exclude:
        stmt = stmt.where(Store.id.not_in(exclude))
    return stmt


def _products_stmt(types: list[str], *, ids: list[int] | None = None, exclude: list[int] | None = None):
    stmt = (
        select(Product, Store)
        .join(Store, Store.id == Product.store_id)
        .where(*_sellable(), Store.business_type.in_(types))
    )
    if ids is not None:
        stmt = stmt.where(Product.id.in_(ids))
    if exclude:
        stmt = stmt.where(Product.id.not_in(exclude))
    return stmt


def _pinned_items(db: Session, kind: str, types: list[str], ids: list[int]) -> list[dict]:
    if not ids or not types:
        return []
    if kind == "stores":
        found = {store.id: (store, count) for store, count in db.execute(_stores_stmt(types, ids=ids)).all()}
        return [_store_item(*found[item]) for item in ids if item in found]
    found = {product.id: (product, store) for product, store in db.execute(_products_stmt(types, ids=ids)).all()}
    return [_product_item(*found[item]) for item in ids if item in found]


def _existing_pin_ids(db: Session, kind: str, types: list[str], ids: list[int]) -> set[int]:
    if not ids or not types:
        return set()
    if kind == "stores":
        stmt = select(Store.id).where(Store.id.in_(ids), Store.business_type.in_(types))
    else:
        stmt = select(Product.id).join(Store, Store.id == Product.store_id).where(
            Product.id.in_(ids), Store.business_type.in_(types)
        )
    return set(db.scalars(stmt).all())


def _check_pins(db: Session, kind: str, types: list[str], ids: list[int]) -> None:
    valid = _existing_pin_ids(db, kind, types, ids)
    missing = [item for item in ids if item not in valid]
    if missing:
        raise HTTPException(status_code=422, detail=f"Items do not belong to the selected business types: {missing}")


def _describe_pins(db: Session, section: HomeSection) -> list[dict]:
    ids = list(section.pinned_ids or [])
    if not ids:
        return []
    types = [slug for slug in (section.business_types or []) if slug in _VALID_SLUGS]
    live = {item["id"] for item in _pinned_items(db, section.kind, types, ids)}
    if section.kind == "stores":
        rows = db.execute(select(Store.id, Store.name, Store.business_type).where(Store.id.in_(ids))).all()
        info = {
            row.id: {"id": row.id, "name": row.name, "business_type": row.business_type, "store_name": None}
            for row in rows
        }
    else:
        rows = db.execute(
            select(Product.id, Product.name, Store.name.label("store_name"), Store.business_type)
            .join(Store, Store.id == Product.store_id)
            .where(Product.id.in_(ids))
        ).all()
        info = {
            row.id: {"id": row.id, "name": row.name, "business_type": row.business_type, "store_name": row.store_name}
            for row in rows
        }
    return [{**info[item], "visible": item in live} for item in ids if item in info]


def _admin_config(db: Session, section: HomeSection) -> dict:
    payload = _section_config(section)
    payload["pinned_items"] = _describe_pins(db, section)
    return payload


def build_section_items(db: Session, section: HomeSection) -> list[dict]:
    types = [slug for slug in (section.business_types or []) if slug in _VALID_SLUGS]
    if not types:
        return []
    limit = max(1, min(int(section.item_limit or 12), 24))
    pinned = _pinned_items(db, section.kind, types, list(section.pinned_ids or []))[:limit]
    if not section.fill_random or len(pinned) >= limit:
        return pinned
    room = limit - len(pinned)
    taken = [item["id"] for item in pinned]

    if section.kind == "stores":
        rows = db.execute(_stores_stmt(types, exclude=taken).order_by(func.random()).limit(room)).all()
        return pinned + [_store_item(store, count) for store, count in rows]

    rows = db.execute(_products_stmt(types, exclude=taken).order_by(func.random()).limit(room * 4)).all()
    picked = _spread(
        [(product, store) for product, store in rows],
        room,
        Counter(item["store_id"] for item in pinned),
    )
    random.shuffle(picked)
    return pinned + [_product_item(product, store) for product, store in picked]


def _public_section(db: Session, section: HomeSection) -> dict | None:
    items = build_section_items(db, section)
    if not items:
        return None
    payload = _section_config(section)
    for private in ("is_active", "position", "pinned_ids", "fill_random"):
        payload.pop(private)
    payload["items"] = items
    return payload


def _home_sections_available(db: Session) -> bool:
    try:
        db.execute(text("SELECT 1 FROM home_sections LIMIT 1"))
        return True
    except SQLAlchemyError:
        return False


@router.get("/public/home-sections")
def public_home_sections(db: Session = Depends(get_db)):
    if not _home_sections_available(db):
        return JSONResponse({"sections": []}, headers={"Cache-Control": "no-store"})
    try:
        sections = db.scalars(
            select(HomeSection)
            .where(HomeSection.is_active.is_(True))
            .order_by(HomeSection.position, HomeSection.id)
            .limit(MAX_SECTIONS)
        ).all()
    except SQLAlchemyError:
        return JSONResponse({"sections": []}, headers={"Cache-Control": "no-store"})
    payload = [item for item in (_public_section(db, section) for section in sections) if item]
    return JSONResponse({"sections": payload}, headers={"Cache-Control": "no-store"})


def _get_or_404(db: Session, section_id: int) -> HomeSection:
    section = db.get(HomeSection, section_id)
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    return section


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("/admin/home-sections")
def list_home_sections(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_god(current_user)
    if not _home_sections_available(db):
        return []
    try:
        sections = db.scalars(select(HomeSection).order_by(HomeSection.position, HomeSection.id)).all()
    except SQLAlchemyError:
        return []
    return [_admin_config(db, section) for section in sections]


@router.post("/admin/home-sections", status_code=status.HTTP_201_CREATED)
def create_home_section(
    data: HomeSectionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_god(current_user)
    total = db.scalar(select(func.count(HomeSection.id))) or 0
    if total >= MAX_SECTIONS:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"At most {MAX_SECTIONS} sections are allowed")
    _check_pins(db, data.kind, data.business_types, data.pinned_ids)
    last_position = db.scalar(select(func.max(HomeSection.position)))
    section = HomeSection(
        **data.model_dump(),
        position=0 if last_position is None else last_position + 1,
    )
    db.add(section)
    db.flush()
    record_audit_log(
        db,
        actor=current_user,
        action="home_section.created",
        resource_type="home_section",
        resource_id=section.id,
        after_state=_audit_state(section),
        ip_address=_ip(request),
    )
    db.commit()
    db.refresh(section)
    return _admin_config(db, section)


@router.put("/admin/home-sections/order")
def reorder_home_sections(
    data: HomeSectionOrder,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_god(current_user)
    sections = {section.id: section for section in db.scalars(select(HomeSection)).all()}
    if len(set(data.ids)) != len(data.ids) or set(data.ids) != set(sections):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order must list every section exactly once")
    before = [section.id for section in sorted(sections.values(), key=lambda item: (item.position, item.id))]
    for position, section_id in enumerate(data.ids):
        sections[section_id].position = position
    record_audit_log(
        db,
        actor=current_user,
        action="home_section.reordered",
        resource_type="home_section",
        resource_id="order",
        before_state={"ids": before},
        after_state={"ids": data.ids},
        ip_address=_ip(request),
    )
    db.commit()
    return [_section_config(sections[section_id]) for section_id in data.ids]


@router.patch("/admin/home-sections/{section_id}")
def update_home_section(
    section_id: int,
    data: HomeSectionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_god(current_user)
    section = _get_or_404(db, section_id)
    changes = data.model_dump(exclude_unset=True)
    changes = {key: value for key, value in changes.items() if value is not None}
    kind = changes.get("kind", section.kind)
    types = changes.get("business_types", section.business_types)
    if "pinned_ids" in changes:
        _check_pins(db, kind, types, changes["pinned_ids"])
    elif kind != section.kind:
        changes["pinned_ids"] = []
    else:
        valid = _existing_pin_ids(db, kind, types, list(section.pinned_ids or []))
        changes["pinned_ids"] = [item for item in (section.pinned_ids or []) if item in valid]
    before = _audit_state(section)
    for key, value in changes.items():
        setattr(section, key, value)
    db.flush()
    record_audit_log(
        db,
        actor=current_user,
        action="home_section.updated",
        resource_type="home_section",
        resource_id=section.id,
        before_state=before,
        after_state=_audit_state(section),
        ip_address=_ip(request),
    )
    db.commit()
    db.refresh(section)
    return _admin_config(db, section)


@router.delete("/admin/home-sections/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_home_section(
    section_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_god(current_user)
    section = _get_or_404(db, section_id)
    record_audit_log(
        db,
        actor=current_user,
        action="home_section.deleted",
        resource_type="home_section",
        resource_id=section.id,
        before_state=_audit_state(section),
        ip_address=_ip(request),
    )
    db.delete(section)
    db.commit()


@router.get("/admin/home-sections/{section_id}/preview")
def preview_home_section(
    section_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_god(current_user)
    section = _get_or_404(db, section_id)
    payload = _section_config(section)
    payload["items"] = build_section_items(db, section)
    return JSONResponse(payload, headers={"Cache-Control": "no-store"})


@router.get("/admin/home-sections/candidates")
def pin_candidates(
    kind: Literal["stores", "products"],
    business_types: str = Query(..., min_length=1, max_length=1000),
    q: str = Query("", max_length=100),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_god(current_user)
    types = list(dict.fromkeys(slug.strip() for slug in business_types.split(",") if slug.strip()))
    try:
        types = _clean_business_types(types)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    query = q.strip()
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"
    like = {"escape": "\\"}
    if kind == "stores":
        stmt = _stores_stmt(types)
        if query:
            stmt = stmt.where(or_(Store.name.ilike(pattern, **like), Store.description.ilike(pattern, **like)))
        rows = db.execute(stmt.order_by(Store.name, Store.id).limit(limit)).all()
        items = [
            {"id": store.id, "name": store.name, "business_type": store.business_type, "store_name": None}
            for store, _count in rows
        ]
    else:
        stmt = _products_stmt(types)
        if query:
            stmt = stmt.where(
                or_(
                    Product.name.ilike(pattern, **like),
                    Product.description.ilike(pattern, **like),
                    Store.name.ilike(pattern, **like),
                )
            )
        rows = db.execute(stmt.order_by(Product.name, Product.id).limit(limit)).all()
        items = [
            {
                "id": product.id,
                "name": product.name,
                "business_type": store.business_type,
                "store_name": store.name,
            }
            for product, store in rows
        ]
    return JSONResponse({"items": items}, headers={"Cache-Control": "no-store"})
