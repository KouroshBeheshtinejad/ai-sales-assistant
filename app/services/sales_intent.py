from __future__ import annotations

import re
from enum import Enum
from functools import lru_cache

from app.services.text_utils import normalize_text, split_tokens


class SalesIntent(str, Enum):
    PRODUCT_SEARCH = "product_search"
    PRODUCT_INFO = "product_info"
    RECOMMENDATION = "recommendation"
    COMPARE = "compare"
    STORE_INFO = "store_info"
    CART_ADD = "cart_add"
    CART_VIEW = "cart_view"
    CART_REMOVE = "cart_remove"
    CART_CLEAR = "cart_clear"
    CHECKOUT = "checkout"
    ORDER_CREATE = "order_create"
    ORDER_STATUS = "order_status"
    GREETING = "greeting"
    THANKS = "thanks"
    GENERAL = "general"


# --------------------------------------------------------------------------
# Vocabulary (entries are written in normalised form: ی/ک, ASCII digits,
# ZWNJ replaced by a space).
# --------------------------------------------------------------------------

_GREETINGS = (
    "سلام", "درود", "وقت بخیر", "صبح بخیر", "عصر بخیر", "شب بخیر", "خسته نباشید",
    "hi", "hello", "hey", "good morning", "good evening", "good afternoon",
)
_THANKS = (
    "ممنون", "مرسی", "تشکر", "سپاس", "دستت درد", "دمت گرم", "خدانگهدار", "خداحافظ",
    "thanks", "thank you", "thx", "bye", "goodbye",
)
_CART_WORDS = ("سبد", "cart", "basket")
_ADD_WORDS = ("اضافه", "افزودن", "بذار", "بگذار", "بریز", "بزار", "add", "put")
_REMOVE_WORDS = ("حذف", "پاک", "بردار", "کم کن", "remove", "delete", "take out")
_CLEAR_WORDS = ("همه", "کل ", "خالی", "تمام", "clear", "empty", "everything")
_PURCHASE_VERBS = (
    "می خوام", "میخوام", "می خواهم", "میخواهم", "بخرم", "می خرم", "میخرم", "بخر ",
    "بده", "بدید", "بردارم", "سفارش بده", "i want", "i ll take", "i will take",
    "i would like", "i d like", "buy", "order",
)
_QUANTITY_EXPLICIT_RE = re.compile(
    r"(?<!\w)(?:\d{1,3}|یکی|یه|یک|دو|سه|چهار|پنج|شش|هفت|هشت|ده|one|two|three|four|five)\s*(?:عدد|تا|دانه|تایی|pcs|units?)(?!\w)"
    r"|(?<!\w)(?:دوتا|سه تا|چهارتا|پنجتا|یکی)(?!\w)"
    r"|(?<!\w)(?:quantity|qty)\s*\d+"
    r"|(?<!\w)(?:want|take|like|buy|order|add)\s+\d{1,3}(?!\w)"
    r"|(?<!\w)(?:میخوام|می خوام|می خواهم|بده|بدید)\s+\d{1,3}(?!\w)(?!\s*(?:سایز|size))"
)
_BARE_QUANTITY_RE = re.compile(
    r"^(?:\d{1,3}|یکی|یه|یک|دو|سه|چهار|پنج|شش|هفت|هشت|ده)\s*(?:عدد|تا|دانه|تایی)?(?:\s*(?:لطفا|ممنون))?$"
)
_ORDER_WORDS = ("سفارش", "order")
_TRACK_WORDS = (
    "پیگیری", "رهگیری", "وضعیت", "کجاست", "کجا رسید", "track", "tracking", "status", "where is",
)
_PLACE_WORDS = (
    "ثبت سفارش", "نهایی", "ثبتش کن", "place order", "place my order", "complete my order",
    "finalize", "خرید نهایی", "سفارش بده", "سفارشمو ثبت",
)
_CHECKOUT_WORDS = (
    "checkout", "check out", "تسویه", "پرداخت", "تکمیل خرید", "pay now", "pay for",
)
_PAYMENT_INFO_MARKERS = ("روش", "methods", "options", "چه نوع", "درگاه", "قسطی", "اقساط", "installment")
_COMPARE_WORDS = (
    "مقایسه", "فرقشون", "فرق", "تفاوت", "compare", "comparison", "difference", "versus",
    " vs ", "کدوم بهتر", "کدام بهتر", "کدومشون",
)
_RECOMMEND_WORDS = (
    "پیشنهاد", "توصیه", "recommend", "suggest", "best", "بهترین",
    "چی بخرم", "چه چیزی بخرم", "چی بگیرم", "کدوم رو بگیرم", "مناسب", "suitable", "good for",
    "gift", "کادو", "هدیه",
)
_STORE_INFO_WORDS = (
    "ارسال", "تحویل", "پست", "مرجوع", "بازپرداخت", "عودت", "استرداد", "پس بدم", "پس بدهم",
    "برگردون", "برگردان", "تعویض", "گارانتی", "ضمانت", "ساعت کاری", "ساعات کاری",
    "ساعت کار", "باز هستید", "باز هستین", "آدرس", "نشانی", "تماس", "شماره تلفن", "شماره تماس",
    "قوانین", "سیاست", "شرایط", "فروشنده", "فروشگاه", "درباره", "تخفیف", "کد تخفیف",
    "delivery", "deliver", "shipping", "return", "refund", "exchange", "warranty", "guarantee",
    "hours", "contact", "address", "phone", "policy", "policies", "terms", "about",
    "discount", "coupon", "payment method",
)
_LISTING_PHRASES = (
    "لیست محصولات", "لیست کالا", "لیست کالاها", "محصولات موجود", "کالاهای موجود", "چه محصولاتی",
    "چه کالاهایی", "چی دارید", "چی دارین", "چه چیزهایی دارید", "چه چیزی دارید", "محصولاتتون",
    "محصولاتتان", "کالاهاتون", "show products", "list products",
    "available products", "what do you sell", "what do you have", "what products",
    "all products", "your products", "catalog", "catalogue", "menu", "منو",
)
_SUPERLATIVES = (
    "ارزان ترین", "ارزانترین", "گران ترین", "گرانترین", "ارزونترین", "ارزون ترین",
    "جدید ترین", "جدیدترین", "پرفروش", "محبوب ترین", "محبوبترین",
    "cheapest", "most expensive", "priciest", "newest", "best seller", "bestseller", "popular",
)
_PRODUCT_INFO_WORDS = (
    "قیمت", "چند", "چنده", "چقدره", "چقدر", "موجود", "موجودی", "رنگ", "سایز", "اندازه", "ویژگی",
    "مشخصات", "معرفی", "توضیح", "جنس", "دارید", "دارین", "دارد", "داره", "هست", "هستش",
    "price", "cost", "how much", "stock", "available", "availability", "in stock", "size",
    "color", "colour", "specs", "specification", "features", "material", "do you have",
    "tell me about", "describe",
)
_PRODUCT_SEARCH_WORDS = (
    "محصول", "کالا", "دنبال", "میخوام", "می خوام", "می خواهم", "بخرم", "نشون بده", "نشان بده",
    "product", "item", "search", "find", "looking for", "show me", "i need", "i want",
)
_FOLLOWUP_MARKERS = (
    "همین", "همون", "این", "اون", "آن", "اینو", "اونو", "اینم", "همینو", "همونو",
    "قبلی", "بالایی", "پایینی", "اولی", "دومی", "سومی", "آخری", "it", "that", "this",
    "that one", "this one", "its", "them",
)
_PRONOUN_SUFFIX_RE = re.compile(
    r"(?:قیمت|موجودی|رنگ|سایز|جنس|مشخصات|ویژگی|گارانتی|تخفیف|اندازه)(?:ش|شون|شو)(?!\w)"
)
_ORDINALS = {
    "اول": 1, "اولین": 1, "اولی": 1, "first": 1, "1st": 1,
    "دوم": 2, "دومین": 2, "دومی": 2, "second": 2, "2nd": 2,
    "سوم": 3, "سومین": 3, "سومی": 3, "third": 3, "3rd": 3,
    "چهارم": 4, "چهارمین": 4, "fourth": 4, "4th": 4,
    "پنجم": 5, "پنجمین": 5, "fifth": 5, "5th": 5,
    "آخر": -1, "آخرین": -1, "آخری": -1, "last": -1,
}
_AMBIGUOUS_PHRASES = (
    "راهنمایی می کنید", "راهنمایی کنید", "کمک می کنید", "کمک کنید", "میشه کمک", "میشه راهنمایی",
    "می توانید راهنمایی کنید", "می تونید کمک", "can you help", "help me", "i need help",
    "need help", "یه سوال دارم", "یک سوال دارم", "سوال دارم", "i have a question",
)


_PREFIX_GUARD = r"(?<![\u0600-\u06ffA-Za-z0-9])"


@lru_cache(maxsize=4096)
def _word_regex(word: str) -> re.Pattern[str]:
    stripped = word.strip()
    if stripped.isascii():
        # Latin words must match whole tokens; multi-word phrases as a unit.
        return re.compile(rf"(?<![A-Za-z0-9]){re.escape(stripped)}(?![A-Za-z0-9])")
    # Persian: no letter may precede the word ("بازپرداخت" is not "پرداخت"),
    # but suffixes (ها، م، ش ...) are allowed.
    return re.compile(_PREFIX_GUARD + re.escape(stripped))


def _has(text: str, words: tuple[str, ...]) -> bool:
    """Whole-word / phrase containment tuned for Persian and English."""
    return any(_word_regex(word).search(text) for word in words)


def normalize_message(text: str) -> str:
    return normalize_text(re.sub(r"[?!؟.,;:\"'«»()\[\]{}…]+", " ", text or ""))


def _word_count(text: str) -> int:
    return len(split_tokens(text))


def is_ambiguous_request(text: str) -> bool:
    normalized = normalize_message(text)
    if not normalized:
        return False
    return any(phrase in normalized for phrase in _AMBIGUOUS_PHRASES) and _word_count(normalized) <= 7


def is_greeting(text: str) -> bool:
    normalized = normalize_message(text)
    return (
        bool(normalized)
        and _word_count(normalized) <= 5
        and _has(normalized, _GREETINGS)
        and not _has(normalized, _PRODUCT_INFO_WORDS + _CART_WORDS + _ORDER_WORDS)
    )


def is_thanks(text: str) -> bool:
    normalized = normalize_message(text)
    return bool(normalized) and _word_count(normalized) <= 6 and _has(normalized, _THANKS)


def is_catalog_listing(text: str) -> bool:
    return _has(normalize_message(text), _LISTING_PHRASES)


def superlative_kind(text: str) -> str | None:
    """Return ``cheapest``/``priciest``/``newest``/``popular`` when asked for one."""
    normalized = normalize_message(text)
    if not _has(normalized, _SUPERLATIVES):
        return None
    if any(word in normalized for word in ("ارزان", "ارزون", "cheapest")):
        return "cheapest"
    if any(word in normalized for word in ("گران", "most expensive", "priciest")):
        return "priciest"
    if any(word in normalized for word in ("جدید", "newest")):
        return "newest"
    return "popular"


def extract_ordinal(text: str) -> int | None:
    """Return a 1-based ordinal (``-1`` for “last”) found in *text*."""
    for token in split_tokens(text):
        if token in _ORDINALS:
            return _ORDINALS[token]
    return None


def is_followup_reference(text: str) -> bool:
    """True when the message refers back to something said earlier (it/this/همون)."""
    normalized = normalize_message(text)
    if _PRONOUN_SUFFIX_RE.search(normalized):
        return True
    tokens = set(split_tokens(normalized))
    return any(marker in tokens for marker in _FOLLOWUP_MARKERS if " " not in marker) or any(
        f" {marker} " in f" {normalized} " for marker in _FOLLOWUP_MARKERS if " " in marker
    )


def is_bare_quantity(text: str) -> bool:
    return bool(_BARE_QUANTITY_RE.match(normalize_message(text)))


def has_explicit_quantity(text: str) -> bool:
    return bool(_QUANTITY_EXPLICIT_RE.search(normalize_message(text)))


def detect_intent(text: str, history: list[dict[str, str]] | None = None) -> SalesIntent:
    normalized = normalize_message(text)
    if not normalized:
        return SalesIntent.GENERAL

    # A bare quantity right after the assistant asked "how many?" is an add-to-cart.
    if history and is_bare_quantity(normalized):
        last_assistant = next(
            (m.get("content", "") for m in reversed(history) if m.get("role") == "assistant"), ""
        )
        if "چه تعدادی" in last_assistant or "how many" in last_assistant.casefold():
            return SalesIntent.CART_ADD

    if is_greeting(normalized):
        return SalesIntent.GREETING
    if is_thanks(normalized):
        return SalesIntent.THANKS

    if _has(normalized, _CART_WORDS):
        if _has(normalized, _REMOVE_WORDS):
            return SalesIntent.CART_CLEAR if _has(normalized, _CLEAR_WORDS) else SalesIntent.CART_REMOVE
        if _has(normalized, _ADD_WORDS):
            return SalesIntent.CART_ADD
        if "خالی" in normalized or "clear" in normalized or "empty" in normalized:
            return SalesIntent.CART_CLEAR
        return SalesIntent.CART_VIEW

    if _has(normalized, _ADD_WORDS) and _has(normalized, ("کن", "کنید", "add", "put")):
        return SalesIntent.CART_ADD

    if _has(normalized, _PURCHASE_VERBS) and (
        has_explicit_quantity(normalized)
        or ("بخرم" in normalized and not any(q in normalized for q in ("چطور", "چگونه", "how")))
    ):
        return SalesIntent.CART_ADD

    if _has(normalized, _ORDER_WORDS + ("رهگیری", "tracking")):
        if _has(normalized, _PLACE_WORDS):
            return SalesIntent.ORDER_CREATE
        if _has(normalized, _TRACK_WORDS):
            return SalesIntent.ORDER_STATUS
    if _has(normalized, _PLACE_WORDS):
        return SalesIntent.ORDER_CREATE

    if _has(normalized, _CHECKOUT_WORDS):
        if _has(normalized, _PAYMENT_INFO_MARKERS):
            return SalesIntent.STORE_INFO
        return SalesIntent.CHECKOUT

    if _has(normalized, _COMPARE_WORDS):
        return SalesIntent.COMPARE
    if _has(normalized, _RECOMMEND_WORDS):
        return SalesIntent.RECOMMENDATION
    if is_catalog_listing(normalized) or superlative_kind(normalized):
        return SalesIntent.PRODUCT_SEARCH
    if _has(normalized, _STORE_INFO_WORDS) and not _has(normalized, ("سایز", "رنگ", "قیمت", "price", "size")):
        return SalesIntent.STORE_INFO
    if _has(normalized, _PRODUCT_INFO_WORDS):
        return SalesIntent.PRODUCT_INFO
    if _has(normalized, _PRODUCT_SEARCH_WORDS):
        return SalesIntent.PRODUCT_SEARCH
    if _has(normalized, _STORE_INFO_WORDS):
        return SalesIntent.STORE_INFO
    return SalesIntent.GENERAL
