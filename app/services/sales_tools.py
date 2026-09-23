from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models import Product
from app.db.models import Conversation, Order
from app.services.cart_service import CartService


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


def get_product(db: Session, store_id: int, product_id: int) -> dict[str, Any]:
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.store_id == store_id,
        Product.is_active.is_(True),
    ).first()
    if product is None:
        raise ValueError("Product not found in this store")
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": str(product.price),
        "stock": product.stock - product.reserved_stock,
        "size": product.size,
        "color": product.color,
        "attributes": product.attributes or {},
    }


def get_product_stock(db: Session, store_id: int, product_id: int) -> dict[str, Any]:
    product = get_product(db, store_id, product_id)
    return {"product_id": product["id"], "name": product["name"], "stock": product["stock"]}


def _identity(context: dict[str, Any]) -> tuple[int | None, str | None]:
    return context.get("user_id"), context.get("guest_token")


def add_to_cart(db: Session, store_id: int, product_id: int, quantity: int, context: dict[str, Any]) -> dict[str, Any]:
    if quantity < 1 or quantity > 100:
        raise ValueError("Quantity must be between 1 and 100")
    user_id, guest_token = _identity(context)
    cart = CartService.add_item(db, user_id, store_id, product_id, quantity, guest_token)
    return {"cart_id": cart.id, "items": [{"product_id": item.product_id, "quantity": item.quantity} for item in cart.items]}


def update_cart_quantity(db: Session, store_id: int, product_id: int, quantity: int, context: dict[str, Any]) -> dict[str, Any]:
    if quantity < 1 or quantity > 100:
        raise ValueError("Quantity must be between 1 and 100")
    user_id, guest_token = _identity(context)
    cart = CartService.update_item(db, user_id, store_id, product_id, quantity, guest_token)
    return {"cart_id": cart.id, "items": [{"product_id": item.product_id, "quantity": item.quantity} for item in cart.items]}


def remove_from_cart(db: Session, store_id: int, product_id: int, context: dict[str, Any]) -> dict[str, Any]:
    user_id, guest_token = _identity(context)
    cart = CartService.remove_item(db, user_id, store_id, product_id, guest_token)
    return {"cart_id": cart.id, "items": [{"product_id": item.product_id, "quantity": item.quantity} for item in cart.items]}


def get_cart(db: Session, store_id: int, context: dict[str, Any]) -> dict[str, Any]:
    user_id, guest_token = _identity(context)
    cart = CartService.get_or_create_cart(db, user_id, store_id, guest_token)
    return {"cart_id": cart.id, "items": [{"product_id": item.product_id, "name": item.product.name if item.product else None, "quantity": item.quantity, "price": str(item.product.price) if item.product else None} for item in cart.items]}


def clear_cart(db: Session, store_id: int, context: dict[str, Any]) -> dict[str, Any]:
    user_id, guest_token = _identity(context)
    CartService.clear_cart(db, user_id, store_id, guest_token)
    return {"cart_id": None, "items": []}


def get_order(db: Session, order_id: int, context: dict[str, Any]) -> dict[str, Any]:
    user_id, guest_token = _identity(context)
    order = db.get(Order, order_id)
    if order is None or (user_id is not None and order.user_id != user_id) or (user_id is None and order.guest_token != guest_token):
        raise ValueError("Order not found")
    return {"id": order.id, "status": order.status, "tracking_number": order.tracking_number, "total_amount": str(order.total_amount)}


def get_order_status(db: Session, order_id: int, context: dict[str, Any]) -> dict[str, Any]:
    order = get_order(db, order_id, context)
    return {"order_id": order["id"], "status": order["status"]}


def get_tracking_information(db: Session, order_id: int, context: dict[str, Any]) -> dict[str, Any]:
    order = get_order(db, order_id, context)
    return {"order_id": order["id"], "tracking_number": order["tracking_number"], "status": order["status"]}


def start_checkout(db: Session, store_id: int, context: dict[str, Any]) -> dict[str, Any]:
    conversation = context.get("conversation")
    if not isinstance(conversation, Conversation):
        raise ValueError("Checkout conversation is not available")
    cart = get_cart(db, store_id, context)
    if not cart["items"]:
        raise ValueError("Cart is empty")
    conversation.checkout_state = "awaiting_customer"
    db.commit()
    return {"state": conversation.checkout_state, "cart": cart}
