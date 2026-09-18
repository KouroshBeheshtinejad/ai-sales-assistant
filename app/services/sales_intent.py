from __future__ import annotations

from enum import Enum


class SalesIntent(str, Enum):
    PRODUCT_SEARCH = "product_search"
    PRODUCT_INFO = "product_info"
    RECOMMENDATION = "recommendation"
    STORE_INFO = "store_info"
    CART_ADD = "cart_add"
    CART_VIEW = "cart_view"
    CHECKOUT = "checkout"
    ORDER_CREATE = "order_create"
    ORDER_STATUS = "order_status"
    GENERAL = "general"


def detect_intent(text: str) -> SalesIntent:
    normalized = " ".join(text.strip().lower().split())

    if any(term in normalized for term in (
        "سبد", "cart", "basket",
    )):
        if any(term in normalized for term in (
            "اضافه", "افزودن", "بذار", "بگذار", "add",
        )):
            return SalesIntent.CART_ADD
        return SalesIntent.CART_VIEW

    if any(term in normalized for term in (
        "سفارش", "order",
    )):
        if any(term in normalized for term in (
            "پیگیری", "وضعیت", "کجاست", "track", "status",
        )):
            return SalesIntent.ORDER_STATUS
        if any(term in normalized for term in (
            "ثبت", "نهایی", "خرید", "place", "create",
        )):
            return SalesIntent.ORDER_CREATE

    if any(term in normalized for term in (
        "فروشگاه", "قوانین", "ارسال", "مرجوعی",
        "بازپرداخت", "فروشنده", "درباره فروشگاه",
    )):
        return SalesIntent.STORE_INFO

    if any(term in normalized for term in (
        "پرداخت", "تسویه", "checkout",
    )):
        return SalesIntent.CHECKOUT

    if any(term in normalized for term in (
        "پیشنهاد", "پیشنهاد بده", "چی بخرم",
        "چه چیزی بخرم", "recommend", "suggest", "best",
    )):
        return SalesIntent.RECOMMENDATION

    if any(term in normalized for term in (
        "لیست محصولات", "لیست کالا", "محصولات موجود", "کالاهای موجود",
        "چه محصولاتی", "چه کالاهایی", "show products", "list products",
        "available products",
    )):
        return SalesIntent.PRODUCT_SEARCH

    if any(term in normalized for term in (
        "قیمت", "موجود", "موجودی", "رنگ", "سایز",
        "ویژگی", "مشخصات", "price", "stock", "size",
    )):
        return SalesIntent.PRODUCT_INFO

    if any(term in normalized for term in (
        "محصول", "کالا", "دنبال", "میخوام", "می‌خوام",
        "product", "search", "find",
    )) and not any(term in normalized for term in (
        "مرجوع", "بازپرداخت", "پس بدهم", "پس بدم", "برگردان",
        "refund", "return", "ارسال", "قوانین",
    )):
        return SalesIntent.PRODUCT_SEARCH

    if any(term in normalized for term in (
        "فروشگاه", "قوانین", "ارسال", "مرجوعی",
        "فروشنده", "درباره فروشگاه",
    )):
        return SalesIntent.STORE_INFO

    return SalesIntent.GENERAL
