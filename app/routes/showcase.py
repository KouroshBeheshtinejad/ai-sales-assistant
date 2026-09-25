"""Public showcase used by the landing page.

Returns a small random sample of live stores and products so the marketing page
always shows real, current data. Only fields that are already public on the
storefront are exposed (see ``/public/stores/{id}/catalog``).
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Product, Store


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