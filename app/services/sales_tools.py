from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models import Product


def search_products(
    db: Session,
    store_id: int,
    query: str,
) -> list[dict[str, Any]]:
    """
    Search active products in one store.

    This is a transactional catalog tool, not a replacement for the
    general RAG retrieval layer.
    """
    normalized_query = " ".join(query.strip().lower().split())

    products_query = (
        db.query(Product)
        .filter(
            Product.store_id == store_id,
            Product.is_active.is_(True),
        )
    )

    # A generic product request should return the active catalog.
    generic_queries = {
        "",
        "محصول",
        "محصولات",
        "کالا",
        "کالاها",
        "product",
        "products",
        "item",
        "items",
        "لیست محصولات",
        "لیست کالا",
        "محصولات موجود",
        "کالاهای موجود",
        "چه محصولاتی",
        "چه کالاهایی",
        "show products",
        "list products",
        "available products",
        "محصولات موجود را نشان بده",
        "کالاهای موجود را نشان بده",
    }

    if normalized_query not in generic_queries:
        search_pattern = f"%{normalized_query}%"
        products_query = products_query.filter(
            or_(
                Product.name.ilike(search_pattern),
                Product.description.ilike(search_pattern),
            )
        )

    products = products_query.order_by(Product.id).limit(20).all()

    results: list[dict[str, Any]] = []

    for product in products:
        price = product.price
        price_value = str(price) if isinstance(price, Decimal) else str(price)

        results.append(
            {
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "price": price_value,
                "stock": product.stock - product.reserved_stock,
                "size": product.size,
                "color": product.color,
                "attributes": product.attributes or {},
                "is_active": product.is_active,
            }
        )

    return results
