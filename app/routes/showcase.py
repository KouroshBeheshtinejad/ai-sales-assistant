"""Public showcase used by the landing page.

Returns a small random sample of live stores and products so the marketing page
always shows real, current data. Only fields that are already public on the
storefront are exposed (see ``/public/stores/{id}/catalog``).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Product, Store
from app.core.business_types import BUSINESS_TYPES


router = APIRouter(tags=["Public Showcase"])

DESCRIPTION_LIMIT = 160


def _shorten(text: str | None) -> str | None:
    if not text:
        return None
    text = " ".join(text.split())
    if len(text) <= DESCRIPTION_LIMIT:
        return text
    return text[: DESCRIPTION_LIMIT - 1].rstrip() + "…"


def _sellable():
    """Active products that still have unreserved stock."""
    return (
        Product.is_active.is_(True),
        Product.stock - Product.reserved_stock > 0,
    )


@router.get("/public/showcase")
def public_showcase(
    stores: int = Query(6, ge=0, le=12),
    products: int = Query(8, ge=0, le=24),
    db: Session = Depends(get_db),
):
    # Stores that currently have at least one sellable product, with that count.
    counts = (
        db.query(Product.store_id.label("store_id"), func.count(Product.id).label("n"))
        .filter(*_sellable())
        .group_by(Product.store_id)
        .subquery()
    )
    store_rows = (
        db.query(Store, counts.c.n)
        .join(counts, counts.c.store_id == Store.id)
        .order_by(func.random())
        .limit(stores)
        .all()
        if stores
        else []
    )
    product_rows = (
        db.query(Product, Store)
        .join(Store, Store.id == Product.store_id)
        .filter(*_sellable())
        .order_by(func.random())
        .limit(products)
        .all()
        if products
        else []
    )

    payload = {
        "stats": {
            "stores": db.query(func.count(func.distinct(Product.store_id))).filter(*_sellable()).scalar() or 0,
            "products": db.query(func.count(Product.id)).filter(*_sellable()).scalar() or 0,
        },
        "stores": [
            {
                "id": store.id,
                "name": store.name,
                "description": _shorten(store.description),
                "logo_url": store.logo_url,
                "business_type": store.business_type,
                "country_code": store.country_code,
                "currency": store.currency,
                "product_count": product_count,
            }
            for store, product_count in store_rows
        ],
        "products": [
            {
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
            for product, store in product_rows
        ],
    }
    # A random sample must not be cached by browsers or proxies.
    return JSONResponse(payload, headers={"Cache-Control": "no-store"})


@router.get("/public/search")
def public_search(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(4, ge=1, le=8),
    db: Session = Depends(get_db),
):
    query = q.strip()
    if not query:
        return JSONResponse({"query": query, "stores": [], "products": []}, headers={"Cache-Control": "no-store"})

    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    exact = escaped
    prefix = f"{escaped}%"
    contains = f"%{escaped}%"
    like = {"escape": "\\"}
    store_counts = (
        db.query(Product.store_id.label("store_id"), func.count(Product.id).label("product_count"))
        .filter(*_sellable())
        .group_by(Product.store_id)
        .subquery()
    )
    store_match = or_(Store.name.ilike(contains, **like), Store.description.ilike(contains, **like))
    store_rank = case(
        (Store.name.ilike(exact, **like), 0),
        (Store.name.ilike(prefix, **like), 1),
        else_=2,
    )
    store_rows = (
        db.query(Store, store_counts.c.product_count)
        .join(store_counts, store_counts.c.store_id == Store.id)
        .filter(store_match)
        .order_by(store_rank, Store.name, Store.id)
        .limit(limit)
        .all()
    )

    product_match = or_(
        Product.name.ilike(contains, **like),
        Product.description.ilike(contains, **like),
        Store.name.ilike(contains, **like),
    )
    product_rank = case(
        (Product.name.ilike(exact, **like), 0),
        (Product.name.ilike(prefix, **like), 1),
        (Product.name.ilike(contains, **like), 2),
        (Store.name.ilike(exact, **like), 3),
        (Store.name.ilike(prefix, **like), 4),
        else_=5,
    )
    product_rows = (
        db.query(Product, Store)
        .join(Store, Store.id == Product.store_id)
        .filter(*_sellable(), product_match)
        .order_by(product_rank, Product.name, Product.id)
        .limit(limit)
        .all()
    )

    return JSONResponse(
        {
            "query": query,
            "stores": [
                {
                    "id": store.id,
                    "name": store.name,
                    "description": _shorten(store.description),
                    "logo_url": store.logo_url,
                    "business_type": store.business_type,
                    "currency": store.currency,
                    "product_count": product_count,
                }
                for store, product_count in store_rows
            ],
            "products": [
                {
                    "id": product.id,
                    "name": product.name,
                    "description": _shorten(product.description),
                    "image_url": product.image_url,
                    "price": str(product.price),
                    "currency": store.currency,
                    "stock": product.stock - product.reserved_stock,
                    "store_id": store.id,
                    "store_name": store.name,
                }
                for product, store in product_rows
            ],
        },
        headers={"Cache-Control": "no-store"},
    )


@router.get("/public/stores")
def public_stores_by_business_type(
    business_type: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    valid_slugs = {item["slug"] for item in BUSINESS_TYPES}
    if business_type not in valid_slugs:
        raise HTTPException(status_code=404, detail="Business type not found")

    product_counts = (
        db.query(Product.store_id.label("store_id"), func.count(Product.id).label("product_count"))
        .filter(*_sellable())
        .group_by(Product.store_id)
        .subquery()
    )
    query = (
        db.query(Store, product_counts.c.product_count)
        .join(product_counts, product_counts.c.store_id == Store.id)
        .filter(Store.business_type == business_type)
        .order_by(Store.name, Store.id)
    )
    total = query.count()
    rows = query.offset(offset).limit(limit).all()
    return JSONResponse(
        {
            "business_type": business_type,
            "total": total,
            "stores": [
                {
                    "id": store.id,
                    "name": store.name,
                    "description": _shorten(store.description),
                    "logo_url": store.logo_url,
                    "business_type": store.business_type,
                    "product_count": product_count,
                }
                for store, product_count in rows
            ],
        },
        headers={"Cache-Control": "no-store"},
    )
