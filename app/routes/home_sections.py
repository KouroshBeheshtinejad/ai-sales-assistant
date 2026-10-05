"""Curated, randomly sampled rows for the public home page.

The platform admin (``god``) creates any number of sections. Each one has a title,
a background colour, a list of business types and a kind (``stores`` or
``products``). The public endpoint returns, for every active section, a fresh
random sample of live stores or sellable products from those business types.
Only data that is already public on the storefront is exposed.
"""

from __future__ import annotations

import random
from collections import defaultdict
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.business_types import BUSINESS_TYPES
from app.db.database import get_db
from app.db.models import HomeSection, Product, Store, User
from app.routes.admin import _require_god
from app.routes.auth import get_current_user
from app.routes.showcase import DESCRIPTION_LIMIT, _sellable, _shorten
from app.services.audit_service import record_audit_log


router = APIRouter(tags=["Home Sections"])

SUPPORTED_LOCALES = ("fa", "en", "es", "de", "fr")
MAX_SECTIONS = 20
MAX_PER_STORE = 3
_VALID_SLUGS = {item["slug"] for item in BUSINESS_TYPES}
_COLOR_PATTERN = r"^#[0-9a-fA-F]{6}$"


def _clean_titles(value: dict[str, str] | None) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    for code, text in (value or {}).items():
        if code not in SUPPORTED_LOCALES:
            raise ValueError(f"Unsupported language: {code}")
        text = " ".join(str(text).split())
        if len(text) > 120:
            raise ValueError("Titles can be at most 120 characters")
        if text:
            cleaned[code] = text
    return cleaned


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
    item_limit: int = Field(12, ge=1, le=24)
    is_active: bool = True

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Title is required")
        return value

    @field_validator("titles")
    @classmethod
    def _titles(cls, value: dict[str, str]) -> dict[str, str]:
        return _clean_titles(value)

    @field_validator("business_types")
    @classmethod
    def _types(cls, value: list[str]) -> list[str]:
        return _clean_business_types(value)

    @field_validator("background_color")
    @classmethod
    def _color(cls, value: str) -> str:
        return value.lower()


class HomeSectionUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=120)
    titles: dict[str, str] | None = None
    kind: Literal["stores", "products"] | None = None
    business_types: list[str] | None = Field(None, min_length=1, max_length=len(BUSINESS_TYPES))
    background_color: str | None = Field(None, pattern=_COLOR_PATTERN)
    item_limit: int | None = Field(None, ge=1, le=24)
    is_active: bool | None = None

    @field_validator("title")
    @classmethod
    def _title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = " ".join(value.split())
        if not value:
            raise ValueError("Title is required")
        return value

    @field_validator("titles")
    @classmethod
    def _titles(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        return None if value is None else _clean_titles(value)

    @field_validator("business_types")
    @classmethod
    def _types(cls, value: list[str] | None) -> list[str] | None:
        return None if value is None else _clean_business_types(value)

    @field_validator("background_color")
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
        "stock": product.stock - product.reserved_stock,
        "store_id": store.id,
        "store_name": store.name,
        "business_type": store.business_type,
    }


def _spread(rows: list[tuple[Product, Store]], limit: int) -> list[tuple[Product, Store]]:
    chosen: list[tuple[Product, Store]] = []
    leftovers: list[tuple[Product, Store]] = []
    per_store: dict[int, int] = defaultdict(int)
    for product, store in rows:
        if len(chosen) >= limit:
            break
        if per_store[store.id] < MAX_PER_STORE:
            per_store[store.id] += 1
            chosen.append((product, store))
        else:
            leftovers.append((product, store))
    chosen.extend(leftovers[: max(0, limit - len(chosen))])
    return chosen


def build_section_items(db: Session, section: HomeSection) -> list[dict]:
    types = [slug for slug in (section.business_types or []) if slug in _VALID_SLUGS]
    if not types:
        return []
    limit = max(1, min(int(section.item_limit or 12), 24))

    if section.kind == "stores":
        counts = (
            select(Product.store_id.label("store_id"), func.count(Product.id).label("n"))
            .where(*_sellable())
            .group_by(Product.store_id)
            .subquery()
        )
        rows = db.execute(
            select(Store, counts.c.n)
            .join(counts, counts.c.store_id == Store.id)
            .where(Store.business_type.in_(types))
            .order_by(func.random())
            .limit(limit)
        ).all()
        return [_store_item(store, count) for store, count in rows]

    rows = db.execute(
        select(Product, Store)
        .join(Store, Store.id == Product.store_id)
        .where(*_sellable(), Store.business_type.in_(types))
        .order_by(func.random())
        .limit(limit * 4)
    ).all()
    picked = _spread([(product, store) for product, store in rows], limit)
    random.shuffle(picked)
    return [_product_item(product, store) for product, store in picked]


def _public_section(db: Session, section: HomeSection) -> dict | None:
    items = build_section_items(db, section)
    if not items:
        return None
    payload = _section_config(section)
    payload.pop("is_active")
    payload.pop("position")
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
    return [_section_config(section) for section in sections]


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
    return _section_config(section)


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
    return _section_config(section)


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
