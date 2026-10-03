from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models import Conversation, Order, Product, Store
from app.services.cart_service import CartService


def _product_dict(product: Product) -> dict[str, Any]:
    available = product.stock - product.reserved_stock
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": str(product.price),
        "stock": available,
        "in_stock": available > 0,
        "size": product.size,
        "color": product.color,
        "attributes": product.attributes or {},
        "is_active": product.is_active,
    }


def search_products(
    db: Session,
    store_id: int,
    query: str,
) -> list[dict[str, Any]]:
    """
    Search active products in one store.

    Uses the same typo-tolerant, synonym-aware retrieval as the RAG layer; a
    generic request ("products", "menu") returns the in-stock catalog.
    """
    from app.services.chat_retrieval import retrieve_store_context  # local: avoids import cycle

    cleaned = " ".join((query or "").strip().split())
    products: list[Product] = []
    if cleaned:
        context = retrieve_store_context(db, store_id, cleaned)
        if context is not None:
            products = list(context.products)
    if not products:
        pattern = f"%{cleaned.lower()}%"
        base = db.query(Product).filter(Product.store_id == store_id, Product.is_active.is_(True))
        if cleaned and cleaned.lower() not in _GENERIC_QUERIES:
            base = base.filter(or_(Product.name.ilike(pattern), Product.description.ilike(pattern)))
        products = base.order_by(Product.id).limit(20).all()
    return [_product_dict(product) for product in products[:20]]


_GENERIC_QUERIES = {
    "", "محصول", "محصولات", "کالا", "کالاها", "product", "products", "item", "items",
    "لیست محصولات", "لیست کالا", "محصولات موجود", "کالاهای موجود", "چه محصولاتی",
    "چه کالاهایی", "show products", "list products", "available products", "menu", "منو",
}


def search_knowledge(db: Session, store_id: int, query: str) -> dict[str, Any]:
    """Look up the store's FAQs and knowledge-base passages (policies, hours, ...)."""
    from app.services.chat_retrieval import retrieve_store_context

    context = retrieve_store_context(db, store_id, (query or "").strip())
    if context is None:
        raise ValueError("Store not found")
    passages = {match.record.id: match.passages for match in context.matches if match.passages}
    return {
        "faqs": [{"question": faq.question, "answer": faq.answer} for faq in context.faqs],
        "knowledge": [
            {
                "title": entry.title,
                "content": " … ".join(passages.get(entry.id, ())) or entry.content,
            }
            for entry in context.knowledge_entries
        ],
        "found": bool(context.faqs or context.knowledge_entries),
    }


def compare_products(db: Session, store_id: int, product_ids: list[int]) -> dict[str, Any]:
    ids = list(dict.fromkeys(product_ids))
    if len(ids) < 2:
        raise ValueError("Provide at least two product ids to compare")
    products = [get_product(db, store_id, pid) for pid in ids[:4]]
    priced = sorted(products, key=lambda item: float(item["price"]))
    return {
        "products": products,
        "cheapest_product_id": priced[0]["id"],
        "most_expensive_product_id": priced[-1]["id"],
    }


def get_store_info(db: Session, store_id: int) -> dict[str, Any]:
    store = db.get(Store, store_id)
    if store is None:
        raise ValueError("Store not found")
    return {
        "name": store.name,
        "description": store.description,
        "business_type": store.business_type,
        "categories": [item.get("name") for item in (store.categories or []) if isinstance(item, dict)],
    }


def track_order(db: Session, store_id: int, tracking_number: str) -> dict[str, Any]:
    """Look up an order by its 10-digit tracking number (the number is the secret)."""
    from app.services.order_service import OrderService

    order = OrderService.get_order_by_tracking_number(db, (tracking_number or "").strip())
    if order is None or order.store_id != store_id or (not order.paid_at and not order.tracking_number):
        raise ValueError("Order not found")
    return {"tracking_number": order.tracking_number, "status": order.status, "total_amount": str(order.total_amount)}


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
    user_id, guest_token = context.get("user_id"), context.get("guest_token")
    if user_id is None and not guest_token:
        raise ValueError("No customer session is available for this action")
    return user_id, guest_token


def _cart_payload(cart) -> dict[str, Any]:
    items = []
    total = Decimal("0")
    for item in cart.items:
        product = item.product
        price = Decimal(str(product.price)) if product else None
        subtotal = price * item.quantity if price is not None else None
        if subtotal is not None:
            total += subtotal
        items.append(
            {
                "product_id": item.product_id,
                "name": product.name if product else None,
                "quantity": item.quantity,
                "price": str(product.price) if product else None,
                "subtotal": str(subtotal) if subtotal is not None else None,
            }
        )
    return {"cart_id": cart.id, "items": items, "total": str(total)}


def add_to_cart(db: Session, store_id: int, product_id: int, quantity: int, context: dict[str, Any]) -> dict[str, Any]:
    if quantity < 1 or quantity > 100:
        raise ValueError("Quantity must be between 1 and 100")
    user_id, guest_token = _identity(context)
    cart = CartService.add_item(db, user_id, store_id, product_id, quantity, guest_token)
    return _cart_payload(cart)


def update_cart_quantity(db: Session, store_id: int, product_id: int, quantity: int, context: dict[str, Any]) -> dict[str, Any]:
    if quantity < 1 or quantity > 100:
        raise ValueError("Quantity must be between 1 and 100")
    user_id, guest_token = _identity(context)
    cart = CartService.update_item(db, user_id, store_id, product_id, quantity, guest_token)
    return _cart_payload(cart)


def remove_from_cart(db: Session, store_id: int, product_id: int, context: dict[str, Any]) -> dict[str, Any]:
    user_id, guest_token = _identity(context)
    cart = CartService.remove_item(db, user_id, store_id, product_id, guest_token)
    return _cart_payload(cart)


def get_cart(db: Session, store_id: int, context: dict[str, Any]) -> dict[str, Any]:
    user_id, guest_token = _identity(context)
    return _cart_payload(CartService.get_or_create_cart(db, user_id, store_id, guest_token))


def clear_cart(db: Session, store_id: int, context: dict[str, Any]) -> dict[str, Any]:
    user_id, guest_token = _identity(context)
    CartService.clear_cart(db, user_id, store_id, guest_token)
    return {"cart_id": None, "items": []}


def get_order(db: Session, order_id: int, context: dict[str, Any]) -> dict[str, Any]:
    user_id, guest_token = _identity(context)
    order = db.get(Order, order_id)
    store_id = context.get("store_id")
    if (
        order is None
        or (store_id is not None and order.store_id != store_id)
        or (user_id is not None and order.user_id != user_id)
        or (user_id is None and (guest_token is None or order.guest_token != guest_token))
    ):
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
