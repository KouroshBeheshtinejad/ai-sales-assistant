"""Deterministic commerce actions inside the chat.

Prices, stock and cart changes never depend on a language model: the same code
paths as the storefront API are used, so the assistant behaves identically with
a hosted model, the offline assistant, or no AI at all.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models import Conversation, Product
from app.services.cart_service import CartService
from app.services.grounded_responder import friendly_error
from app.services.guest_commerce import (
    cart_summary,
    extract_bare_quantity,
    extract_customer_fields,
    extract_quantity,
    get_cart,
    is_checkout_cancellation,
    is_confirmation,
    normalize_digits,
)
from app.services.order_service import OrderService
from app.services.product_resolver import resolve_product_reference
from app.services.sales_intent import SalesIntent, detect_intent
from contextvars import ContextVar

from app.services.text_utils import conversation_language, detect_language

CONFIRMATION_REPLY_FA = (
    "برای نهایی‌کردن سفارش و پرداخت امن، لطفاً از دکمه سبد خرید وارد تسویه‌حساب شوید. "
    "تا پیش از تأیید پرداخت، سفارش یا کد رهگیری صادر نمی‌شود."
)
CONFIRMATION_REPLY_EN = (
    "To finalize your order and pay securely, please use the cart button to go to checkout. "
    "No order or tracking code is issued until the payment is confirmed."
)

_STATUS_FA = {
    "pending": "در انتظار تأیید",
    "confirmed": "تأیید شده",
    "preparing": "در حال آماده‌سازی",
    "shipped": "ارسال شده",
    "delivered": "تحویل داده شده",
    "cancelled": "لغو شده",
}
_STATUS_EN = {
    "pending": "pending confirmation",
    "confirmed": "confirmed",
    "preparing": "being prepared",
    "shipped": "shipped",
    "delivered": "delivered",
    "cancelled": "cancelled",
}


_LANG: ContextVar[str | None] = ContextVar("chat_flow_lang", default=None)


def _t(question: str, fa: str, en: str) -> str:
    language = _LANG.get() or detect_language(question)
    return en if language == "en" else fa


@dataclass
class FlowResult:
    answer: str
    handled: bool = True


def reset_checkout(conversation: Conversation, *, keep_state: bool = False) -> None:
    if not keep_state:
        conversation.checkout_state = "idle"
    conversation.checkout_idempotency_key = None
    conversation.checkout_customer_name = None
    conversation.checkout_customer_phone = None
    conversation.checkout_customer_address = None


def _active_products(db: Session, store_id: int) -> list[Product]:
    return (
        db.query(Product)
        .filter(Product.store_id == store_id, Product.is_active.is_(True))
        .order_by(Product.id)
        .all()
    )


def _cart_products(cart) -> list[Product]:
    return [item.product for item in cart.items if item.product is not None]


def _choose_text(question: str, candidates: list[Product]) -> str:
    names = "، ".join(f"«{p.name}»" for p in candidates[:4])
    return _t(
        question,
        f"منظورتان کدام یک است؟ {names}",
        "Which one do you mean? " + ", ".join(f'"{p.name}"' for p in candidates[:4]),
    )


def _add_to_cart(db, store_id, guest_token, question, history) -> str:
    products = _active_products(db, store_id)
    resolution = resolve_product_reference(question, products, history)
    if resolution.ambiguous:
        return _choose_text(question, resolution.candidates)
    product = resolution.product
    if product is None:
        return _t(question, "محصول را دقیق‌تر مشخص می‌کنید؟", "Could you tell me exactly which product you mean?")
    quantity = extract_quantity(question)
    if quantity is None and history and history[-1].get("role") == "assistant":
        last = history[-1].get("content", "")
        if "چه تعدادی" in last or "how many" in last.casefold():
            quantity = extract_bare_quantity(question)
    if quantity is None:
        return _t(
            question,
            f"چه تعدادی از «{product.name}» می‌خواهید؟",
            f'How many of "{product.name}" would you like?',
        )
    try:
        cart = CartService.add_item(
            db=db, user_id=None, guest_token=guest_token, store_id=store_id,
            product_id=product.id, quantity=quantity,
        )
    except ValueError as exc:
        db.rollback()
        lang = detect_language(question)
        available = (product.stock or 0) - (product.reserved_stock or 0)
        reason = friendly_error(str(exc), lang)
        if "insufficient" in str(exc).lower() and available > 0:
            return _t(
                question,
                f"فقط {available} عدد از «{product.name}» موجود است. همین تعداد را اضافه کنم؟",
                f'Only {available} of "{product.name}" are available. Shall I add that many?',
            )
        return reason
    return _t(
        question,
        f"{quantity} عدد «{product.name}» به سبد خرید اضافه شد.\n{cart_summary(cart)}\n"
        "برای ادامه می‌توانید محصول دیگری اضافه کنید یا بگویید «تسویه‌حساب».",
        f'Added {quantity} × "{product.name}" to your cart.\n{cart_summary(cart)}\n'
        "You can add more items or say \"checkout\".",
    )


def _remove_from_cart(db, store_id, guest_token, question, history) -> str:
    cart = get_cart(db, store_id=store_id, guest_token=guest_token)
    in_cart = _cart_products(cart)
    if not in_cart:
        return _t(question, "سبد خرید شما خالی است.", "Your cart is empty.")
    resolution = resolve_product_reference(question, in_cart, history)
    if resolution.ambiguous:
        return _choose_text(question, resolution.candidates)
    if resolution.product is None:
        if len(in_cart) == 1:
            resolution.product = in_cart[0]
        else:
            return _choose_text(question, in_cart)
    product = resolution.product
    cart = CartService.remove_item(db, None, store_id, product.id, guest_token)
    return _t(
        question,
        f"«{product.name}» از سبد خرید حذف شد.\n{cart_summary(cart)}",
        f'Removed "{product.name}" from your cart.\n{cart_summary(cart)}',
    )


def _order_status(db, store_id, question) -> str:
    match = re.search(r"(?<!\d)(\d{10})(?!\d)", normalize_digits(question))
    if not match:
        return _t(
            question,
            "برای پیگیری سفارش، کد رهگیری ۱۰ رقمی خود را همین‌جا بفرستید یا از صفحهٔ «پیگیری سفارش» استفاده کنید.",
            "To track an order, send your 10-digit tracking number here or use the order tracking page.",
        )
    order = OrderService.get_order_by_tracking_number(db, match.group(1))
    if order is None or order.store_id != store_id:
        return _t(question, "سفارشی با این کد رهگیری پیدا نشد. لطفاً کد را دوباره بررسی کنید.",
                  "No order was found for that tracking number. Please double-check it.")
    status_fa = _STATUS_FA.get(order.status, order.status)
    status_en = _STATUS_EN.get(order.status, order.status)
    return _t(question, f"وضعیت سفارش شما: {status_fa}.", f"Your order status: {status_en}.")


def _start_checkout(db, conversation, store_id, guest_token, question) -> str:
    cart = get_cart(db, store_id=store_id, guest_token=guest_token)
    if not cart.items:
        return _t(
            question,
            "سبد خرید شما خالی است. ابتدا یک محصول به سبد اضافه کنید.",
            "Your cart is empty. Please add a product first.",
        )
    fields = extract_customer_fields(question)
    conversation.checkout_customer_name = fields.get("name")
    conversation.checkout_customer_phone = fields.get("phone")
    conversation.checkout_customer_address = fields.get("address")
    if all(fields.get(key) for key in ("name", "phone", "address")):
        conversation.checkout_state = "awaiting_confirmation"
        conversation.checkout_idempotency_key = uuid.uuid4().hex
        return _t(
            question,
            f"{cart_summary(cart)}\nآیا سفارش را ثبت کنم؟",
            f"{cart_summary(cart)}\nShall I place the order?",
        )
    conversation.checkout_state = "awaiting_customer"
    return _t(
        question,
        "برای checkout لطفاً نام، شماره تلفن و آدرس خود را ارسال کنید.",
        "To check out, please send your name, phone number and address.",
    )


def _collect_customer(db, conversation, store_id, guest_token, question) -> str | None:
    fields = extract_customer_fields(question)
    if not fields:
        return None
    if fields.get("name"):
        conversation.checkout_customer_name = fields["name"]
    if fields.get("phone"):
        conversation.checkout_customer_phone = fields["phone"]
    if fields.get("address"):
        conversation.checkout_customer_address = fields["address"]
    if all((
        conversation.checkout_customer_name,
        conversation.checkout_customer_phone,
        conversation.checkout_customer_address,
    )):
        conversation.checkout_state = "awaiting_confirmation"
        conversation.checkout_idempotency_key = uuid.uuid4().hex
        cart = get_cart(db, store_id=store_id, guest_token=guest_token)
        return _t(
            question,
            f"اطلاعات دریافت شد.\n{cart_summary(cart)}\nآیا سفارش را ثبت کنم؟",
            f"Got your details.\n{cart_summary(cart)}\nShall I place the order?",
        )
    missing_fa, missing_en = [], []
    if not conversation.checkout_customer_name:
        missing_fa.append("نام")
        missing_en.append("name")
    if not conversation.checkout_customer_phone:
        missing_fa.append("شماره تلفن")
        missing_en.append("phone number")
    if not conversation.checkout_customer_address:
        missing_fa.append("آدرس")
        missing_en.append("address")
    return _t(
        question,
        "لطفاً این موارد را ارسال کنید: " + "، ".join(missing_fa),
        "Please send the following: " + ", ".join(missing_en),
    )


def checkout_reminder(conversation: Conversation, question: str) -> str:
    """Appended to answers while a checkout is in progress."""
    if conversation.checkout_state == "awaiting_confirmation":
        return _t(question, "\n\nبرای ادامهٔ ثبت سفارش، «بله» یا «ثبت کن» را ارسال کنید (یا «لغو»).",
                  "\n\nTo continue with your order, send \"yes\" (or \"cancel\").")
    if conversation.checkout_state == "awaiting_customer":
        return _t(question, "\n\nبرای ادامهٔ ثبت سفارش، نام، شماره تلفن و آدرس خود را بفرستید (یا «لغو»).",
                  "\n\nTo continue, send your name, phone number and address (or \"cancel\").")
    return ""


def handle_commerce_turn(
    db: Session,
    conversation: Conversation,
    *,
    store_id: int,
    guest_token: str | None,
    question: str,
    history: list[dict[str, str]],
) -> str | None:
    """Return a deterministic answer, or ``None`` to let the assistant answer."""
    if not guest_token:
        return None
    _LANG.set(conversation_language(question, history))

    state = conversation.checkout_state
    if state == "awaiting_confirmation":
        if is_confirmation(question):
            reset_checkout(conversation)
            return _t(question, CONFIRMATION_REPLY_FA, CONFIRMATION_REPLY_EN)
        if is_checkout_cancellation(question):
            reset_checkout(conversation)
            return _t(question, "ثبت سفارش لغو شد. هر زمان خواستید دوباره شروع می‌کنیم.",
                      "Checkout cancelled. We can start again whenever you like.")
    elif state == "awaiting_customer":
        if is_checkout_cancellation(question):
            reset_checkout(conversation)
            return _t(question, "ثبت سفارش لغو شد. هر زمان خواستید دوباره شروع می‌کنیم.",
                      "Checkout cancelled. We can start again whenever you like.")
        collected = _collect_customer(db, conversation, store_id, guest_token, question)
        if collected is not None:
            return collected

    intent = detect_intent(question, history)
    if intent == SalesIntent.CART_ADD:
        return _add_to_cart(db, store_id, guest_token, question, history)
    if intent == SalesIntent.CART_VIEW:
        return cart_summary(get_cart(db, store_id=store_id, guest_token=guest_token))
    if intent == SalesIntent.CART_REMOVE:
        return _remove_from_cart(db, store_id, guest_token, question, history)
    if intent == SalesIntent.CART_CLEAR:
        CartService.clear_cart(db, None, store_id, guest_token)
        return _t(question, "سبد خرید شما خالی شد.", "Your cart is now empty.")
    if intent in {SalesIntent.CHECKOUT, SalesIntent.ORDER_CREATE}:
        return _start_checkout(db, conversation, store_id, guest_token, question)
    if intent == SalesIntent.ORDER_STATUS:
        return _order_status(db, store_id, question)
    return None
