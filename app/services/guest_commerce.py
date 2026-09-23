from __future__ import annotations

import re
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models import Cart, Product
from app.services.cart_service import CartService

_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_QUANTITY_WORDS = {
    "یکی": 1,
    "یک": 1,
    "یک عدد": 1,
    "دوتا": 2,
    "دو تا": 2,
    "دو": 2,
    "سه تا": 3,
    "سه": 3,
    "چهار تا": 4,
    "چهار": 4,
    "پنج تا": 5,
    "پنج": 5,
}


def normalize_digits(value: str) -> str:
    return value.translate(_PERSIAN_DIGITS).translate(_ARABIC_DIGITS)


def extract_quantity(text: str) -> int | None:
    normalized = normalize_digits(" ".join(text.lower().split()))
    for phrase, quantity in sorted(_QUANTITY_WORDS.items(), key=lambda item: -len(item[0])):
        if re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", normalized):
            return quantity
    match = re.search(r"(?<!\w)(\d{1,3})\s*(?:عدد|تا|دانه)(?!\w)", normalized)
    if match:
        return int(match.group(1))
    return None


def resolve_product(
    db: Session,
    store_id: int,
    question: str,
    history: list[dict[str, str]] | None = None,
) -> Product | None:
    catalog = (
        db.query(Product)
        .filter(Product.store_id == store_id, Product.is_active.is_(True))
        .order_by(Product.id)
        .all()
    )
    if not catalog:
        return None
    normalized_question = normalize_digits(question).lower()

    def score_products(text: str) -> list[tuple[int, Product]]:
        scored: list[tuple[int, Product]] = []
        normalized = normalize_digits(text).lower()
        for product in catalog:
            normalized_name = normalize_digits(product.name).lower()
            if normalized_name in normalized:
                scored.append((100, product))
                continue
            name_tokens = [
                token for token in normalized_name.split() if len(token) > 1
            ]
            score = sum(2 if token in normalized else 0 for token in name_tokens)
            if product.color and normalize_digits(product.color).lower() in normalized:
                score += 2
            if product.size and any(
                size.strip() in normalized for size in product.size.split("،")
            ):
                score += 1
            if score:
                scored.append((score, product))
        return sorted(scored, key=lambda item: (-item[0], item[1].id))

    scored = score_products(normalized_question)
    if not scored and history:
        scored = score_products(
            " ".join(message.get("content", "") for message in history[-8:])
        )

    if not scored:
        return None
    if len(scored) > 1 and scored[0][0] == scored[1][0]:
        return None
    return scored[0][1]


def get_cart(db: Session, *, store_id: int, guest_token: str) -> Cart:
    return CartService.get_or_create_cart(
        db=db,
        user_id=None,
        store_id=store_id,
        guest_token=guest_token,
    )


def cart_summary(cart: Cart) -> str:
    if not cart.items:
        return "سبد خرید شما خالی است."
    lines = ["سبد خرید شما:"]
    total = Decimal("0.00")
    for item in cart.items:
        if item.product is None:
            continue
        price = Decimal(str(item.product.price))
        subtotal = price * item.quantity
        total += subtotal
        lines.append(f"- {item.product.name}: {item.quantity} عدد × {price} = {subtotal}")
    lines.append(f"مبلغ کل: {total}")
    return "\n".join(lines)


def extract_customer_fields(text: str) -> dict[str, str]:
    normalized = text.strip()
    fields: dict[str, str] = {}
    phone = re.search(r"(?:09|\+989)\d{9,10}", normalize_digits(normalized))
    if phone:
        fields["phone"] = phone.group(0)
    name = re.search(
        r"(?:^|[,،\n])\s*(?:نام|اسم)\s*(?:من|:)?\s*([^,،\n]+)",
        normalized,
        re.IGNORECASE,
    )
    if name:
        fields["name"] = name.group(1).strip()
    address = re.search(r"آدرس\s*(?:من|:)?\s*([^\n]+)", normalized, re.IGNORECASE)
    if address:
        fields["address"] = address.group(1).strip()
    return fields


def is_confirmation(text: str) -> bool:
    normalized = re.sub(r"[،,!؟؟.!؛;:]", " ", text.strip().lower())
    normalized = " ".join(normalized.split())
    return normalized in {"بله", "بله ثبت کن", "ثبت کن", "تایید", "تأیید", "yes", "confirm"}


def is_checkout_cancellation(text: str) -> bool:
    normalized = re.sub(r"[،,!؟؟.!؛;:]", " ", text.strip().lower())
    normalized = " ".join(normalized.split())
    return normalized in {"نه", "لغو", "انصراف", "cancel", "no"}
