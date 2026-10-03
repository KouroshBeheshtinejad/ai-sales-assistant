"""Offline "brain" of the sales assistant.

This module turns the retrieved store data (the same prompt a hosted LLM gets)
into a fluent, grounded answer **without any model**.  It powers
``MockLLMProvider`` and is the safety net the agent falls back to whenever a
hosted model is unavailable, slow, empty, or produces ungrounded numbers — so
the customer always receives a useful answer built from real store data.

Answers are Persian by default and English when the customer writes English.
"""

from __future__ import annotations

import json
import re
import zlib
from dataclasses import dataclass, field
from typing import Sequence

from app.services.sales_intent import (
    SalesIntent,
    detect_intent,
    is_ambiguous_request,
    is_followup_reference,
    superlative_kind,
)
from app.services.text_utils import (
    content_tokens,
    detect_language,
    extract_budget,
    format_price,
    normalize_text,
    split_sentences,
)

NOT_FOUND_MARKER = "No matching information was found."

# --------------------------------------------------------------------------
# Parsed prompt model
# --------------------------------------------------------------------------


@dataclass
class PromptProduct:
    name: str
    description: str = ""
    price: str = "0"
    stock: int = 0
    id: int | None = None
    size: str = ""
    color: str = ""
    attributes: str = ""


@dataclass
class PromptFAQ:
    question: str
    answer: str


@dataclass
class PromptKnowledge:
    title: str
    content: str


@dataclass
class ParsedPrompt:
    question: str = ""
    guidance: str = ""
    store_name: str = ""
    store_about: str = ""
    products: list[PromptProduct] = field(default_factory=list)
    faqs: list[PromptFAQ] = field(default_factory=list)
    knowledge: list[PromptKnowledge] = field(default_factory=list)
    conflict: bool = False

    @property
    def empty(self) -> bool:
        return not (self.products or self.faqs or self.knowledge)


_Q_RE = re.compile(r"Customer question:\s*\n(.*?)\n\s*\n(?:Response guidance:|Retrieved store data:)", re.S)
_G_RE = re.compile(r"Response guidance:\s*\n(.*?)\n\s*\n\s*Retrieved store data:", re.S)
_LEGACY_PRODUCT_RE = re.compile(
    r"^-\s*(?P<name>.+?):\s*(?P<desc>.*?);\s*price=(?P<price>[-\d.]+);\s*stock=(?P<stock>-?\d+)\s*$"
)
_LEGACY_FAQ_RE = re.compile(r"^-\s*Q:\s*(?P<q>.*?)\n\s*A:\s*(?P<a>.*)$", re.S)


def _parse_product_line(line: str) -> PromptProduct | None:
    line = line.strip()
    if " | " in line and "price=" in line:
        pieces = [piece.strip() for piece in line.lstrip("- ").split(" | ")]
        fields: dict[str, str] = {}
        name = ""
        for piece in pieces:
            key, sep, value = piece.partition("=")
            if sep and key in {"id", "price", "stock", "size", "color", "attributes", "description"}:
                fields[key] = value
            elif not name:
                name = piece
        try:
            stock = int(fields.get("stock", "0"))
        except ValueError:
            stock = 0
        description = fields.get("description", "")
        return PromptProduct(
            name=name,
            description="" if description == "No description" else description,
            price=fields.get("price", "0"),
            stock=stock,
            id=int(fields["id"]) if fields.get("id", "").isdigit() else None,
            size=fields.get("size", ""),
            color=fields.get("color", ""),
            attributes=fields.get("attributes", ""),
        )
    legacy = _LEGACY_PRODUCT_RE.match(line)
    if legacy:
        desc = legacy.group("desc")
        return PromptProduct(
            name=legacy.group("name"),
            description="" if desc == "No description" else desc,
            price=legacy.group("price"),
            stock=int(legacy.group("stock")),
        )
    return None


def parse_prompt(user_prompt: str) -> ParsedPrompt:
    parsed = ParsedPrompt()
    match = _Q_RE.search(user_prompt)
    parsed.question = match.group(1).strip() if match else user_prompt.strip()
    guidance = _G_RE.search(user_prompt)
    parsed.guidance = guidance.group(1).strip() if guidance else ""
    _, _, data = user_prompt.partition("Retrieved store data:")
    data = data.split("\n\nConversation history:")[0].strip()
    parsed.conflict = "Data quality notice:" in data

    for line in data.splitlines():
        if line.startswith("Store: ") and not parsed.store_name:
            parsed.store_name = line[7:].strip()
        elif line.startswith("About the store: "):
            parsed.store_about = line[17:].strip()

    blocks = [block.strip() for block in re.split(r"\n\s*\n", data) if block.strip()]
    section = ""
    for block in blocks:
        first, _, rest = block.partition("\n")
        if first.startswith("SOURCE: FAQ"):
            q = re.search(r"^Q:\s*(.*?)\nA:\s*(.*)$", rest, re.S)
            if q:
                parsed.faqs.append(PromptFAQ(q.group(1).strip(), q.group(2).strip()))
        elif first.startswith("SOURCE: KNOWLEDGE_BASE"):
            k = re.search(r"^Title:\s*(.*?)\nContent:\s*(.*)$", rest, re.S)
            if k:
                parsed.knowledge.append(PromptKnowledge(k.group(1).strip(), k.group(2).strip()))
        elif first.startswith("SOURCE: PRODUCT"):
            product = _parse_product_line(rest)
            if product:
                parsed.products.append(product)
        elif first.rstrip(":").casefold() in {"faqs", "products", "knowledge base", "knowledge"}:
            section = first.rstrip(":").casefold()
            body = rest
            if section == "faqs":
                for item in re.split(r"\n(?=- Q:)", body):
                    legacy = _LEGACY_FAQ_RE.match(item.strip())
                    if legacy:
                        parsed.faqs.append(PromptFAQ(legacy.group("q").strip(), legacy.group("a").strip()))
            elif section == "products":
                for line in body.splitlines():
                    product = _parse_product_line(line)
                    if product:
                        parsed.products.append(product)
        elif section == "faqs" and block.startswith("- Q:"):
            legacy = _LEGACY_FAQ_RE.match(block)
            if legacy:
                parsed.faqs.append(PromptFAQ(legacy.group("q").strip(), legacy.group("a").strip()))
        elif section == "products" and block.startswith("-"):
            product = _parse_product_line(block)
            if product:
                parsed.products.append(product)
    return parsed


# --------------------------------------------------------------------------
# Wording
# --------------------------------------------------------------------------

_COLORS = {
    "مشکی": "black", "سفید": "white", "قرمز": "red", "آبی": "blue", "سبز": "green", "زرد": "yellow",
    "نارنجی": "orange", "بنفش": "purple", "صورتی": "pink", "طوسی": "gray", "خاکستری": "gray",
    "قهوه ای": "brown", "کرم": "cream", "بژ": "beige", "نقره ای": "silver", "طلایی": "gold",
    "سرمه ای": "navy", "black": "black", "white": "white", "red": "red", "blue": "blue", "green": "green",
    "yellow": "yellow", "orange": "orange", "purple": "purple", "pink": "pink", "gray": "gray",
    "grey": "gray", "brown": "brown", "beige": "beige", "silver": "silver", "gold": "gold", "navy": "navy",
}
_COLOR_FA = {v: k for k, v in reversed(list(_COLORS.items())) if not k.isascii()}

_TEXT = {
    "fa": {
        "currency": " تومان",
        "stock_n": "{n} عدد",
        "greeting": [
            "سلام! به {store} خوش آمدید 🌟 من دستیار خرید شما هستم. دربارهٔ محصولات، قیمت، موجودی، "
            "ارسال و قوانین فروشگاه بپرسید یا همین‌جا سفارش بدهید.",
            "سلام و وقت بخیر! من دستیار {store} هستم. هر سؤالی دربارهٔ محصولات و سفارش دارید بپرسید؛ "
            "با کمال میل کمک می‌کنم.",
        ],
        "thanks": [
            "خواهش می‌کنم! اگر سؤال دیگری دربارهٔ محصولات یا سفارشتان دارید، در خدمتم.",
            "قابل شما را نداشت! هر زمان کمک خواستید همین‌جا هستم.",
        ],
        "clarify": "حتماً کمک می‌کنم! لطفاً بگویید دقیقاً دربارهٔ کدام محصول یا موضوع سؤال دارید؟",
        "conflict": (
            "در اطلاعات ثبت‌شدهٔ فروشگاه برای این موضوع تناقض وجود دارد، بنابراین نمی‌توانم پاسخ قطعی بدهم. "
            "لطفاً پیش از تصمیم‌گیری با فروشنده تماس بگیرید."
        ),
        "not_found": (
            "اطلاعات مرتبط و کافی دربارهٔ این موضوع در اطلاعات فروشگاه پیدا نشد. برای اطمینان، لطفاً "
            "مستقیماً با فروشنده تماس بگیرید. دربارهٔ محصولات، قیمت، موجودی یا قوانین فروشگاه هم "
            "هر سؤالی دارید با کمال میل پاسخ می‌دهم."
        ),
        "budget_none": "در این محدودهٔ قیمتی محصولی پیدا نشد. اگر بودجهٔ دیگری مدنظر دارید بفرمایید تا گزینه‌های مناسب را پیشنهاد کنم.",
        "policy_one": "طبق اطلاعات ثبت‌شدهٔ فروشگاه، {text}",
        "policy_many": "طبق اطلاعات ثبت‌شدهٔ فروشگاه:",
        "out_of_stock": "«{name}» در حال حاضر ناموجود است.",
        "price_stock": "«{name}» با قیمت {price} موجود است ({stock}).",
        "price_only": "قیمت «{name}» {price} است.",
        "low_stock": "فقط {n} عدد باقی مانده است.",
        "yes_have": "بله، «{name}»{variant} موجود است؛ قیمت {price} و موجودی {stock}.",
        "attr_missing": "برای «{name}» {kind} «{wanted}» ثبت نشده است؛ {kind} موجود: {have}.",
        "attr_unknown": "برای «{name}» {kind} «{wanted}» در اطلاعات ثبت‌شده وجود ندارد.",
        "kind_color": "رنگ",
        "kind_size": "سایز",
        "list_head": "این گزینه‌ها را دارم:",
        "found_head": "این موارد مرتبط را پیدا کردم:",
        "list_item": "• «{name}» — {price} ({stock})",
        "list_item_oos": "• «{name}» — {price} (ناموجود)",
        "cheapest": "ارزان‌ترین گزینهٔ موجود «{name}» با قیمت {price} است ({stock}).",
        "priciest": "گران‌ترین گزینه «{name}» با قیمت {price} است ({stock}).",
        "newest": "جدیدترین محصول ثبت‌شده «{name}» با قیمت {price} است ({stock}).",
        "others": "گزینه‌های دیگر:",
        "recommend": "با توجه به درخواست شما، «{name}» را پیشنهاد می‌کنم{reason}. قیمت {price} و موجودی {stock}.",
        "reason": " چون {text}",
        "recommend_alt": "گزینهٔ دیگر: «{name}» با قیمت {price}.",
        "compare_head": "مقایسهٔ این محصولات:",
        "compare_item": "• «{name}» — {price}، موجودی {stock}{extra}",
        "compare_cheaper": "از نظر قیمت «{name}» ارزان‌تر است (حدود {diff} کمتر).",
        "describe": "«{name}»: {text}",
        "details": "قیمت: {price} | موجودی: {stock}",
        "budget_head": "در بودجهٔ شما ({range}) این گزینه‌ها را دارم:",
        "next_cart": "اگر مایلید همین حالا به سبد خریدتان اضافه کنم، تعداد موردنظر را بفرمایید.",
        "next_help": "اگر سؤال دیگری دارید یا انتخاب مشخصی مدنظر است، بفرمایید.",
        "tool_ok": "انجام شد ✅",
        "tool_fail": "متأسفانه نتوانستم این کار را انجام دهم: {reason}",
        "cart_head": "سبد خرید شما:",
        "cart_total": "مبلغ کل: {total}",
        "checkout_next": "برای ثبت سفارش، نام، شماره تلفن و آدرس خود را بفرستید.",
        "up_to": "تا {n}",
        "from": "از {n}",
        "between": "{a} تا {b}",
    },
    "en": {
        "currency": "",
        "stock_n": "{n} in stock",
        "greeting": [
            "Hello! Welcome to {store} 🌟 I'm your shopping assistant. Ask me about products, prices, "
            "stock, delivery or store policies — or order right here in the chat.",
        ],
        "thanks": ["You're welcome! Let me know if you need anything else about products or your order."],
        "clarify": "Happy to help! Which product or topic would you like to know about?",
        "conflict": (
            "The store's records contain conflicting information about this, so I can't give a definite "
            "answer. Please contact the seller before deciding."
        ),
        "not_found": (
            "I couldn't find enough relevant information about this in the store's data. Please contact the "
            "seller directly to be sure. I'm glad to help with products, prices, stock or store policies."
        ),
        "budget_none": "I couldn't find any product in that price range. Tell me another budget and I'll suggest options.",
        "policy_one": "According to the store's information, {text}",
        "policy_many": "According to the store's information:",
        "out_of_stock": "\"{name}\" is currently out of stock.",
        "price_stock": "\"{name}\" is available at {price} ({stock}).",
        "price_only": "The price of \"{name}\" is {price}.",
        "low_stock": "Only {n} left.",
        "yes_have": "Yes, \"{name}\"{variant} is available at {price}, {stock}.",
        "attr_missing": "No {kind} \"{wanted}\" is listed for \"{name}\"; available {kind}: {have}.",
        "attr_unknown": "\"{name}\" has no {kind} \"{wanted}\" in the store's records.",
        "kind_color": "color",
        "kind_size": "size",
        "list_head": "Here is what I have:",
        "found_head": "I found these related items:",
        "list_item": "• \"{name}\" — {price} ({stock})",
        "list_item_oos": "• \"{name}\" — {price} (out of stock)",
        "cheapest": "The cheapest available option is \"{name}\" at {price} ({stock}).",
        "priciest": "The most expensive option is \"{name}\" at {price} ({stock}).",
        "newest": "The newest product is \"{name}\" at {price} ({stock}).",
        "others": "Other options:",
        "recommend": "Based on your request I'd suggest \"{name}\"{reason}. Price {price}, {stock}.",
        "reason": " because {text}",
        "recommend_alt": "Another option: \"{name}\" at {price}.",
        "compare_head": "Comparison:",
        "compare_item": "• \"{name}\" — {price}, {stock}{extra}",
        "compare_cheaper": "\"{name}\" is the cheaper one (about {diff} less).",
        "describe": "\"{name}\": {text}",
        "details": "Price: {price} | Stock: {stock}",
        "budget_head": "Within your budget ({range}) I have:",
        "next_cart": "If you'd like, tell me the quantity and I'll add it to your cart right away.",
        "next_help": "Let me know if you have another question or a specific choice in mind.",
        "tool_ok": "Done ✅",
        "tool_fail": "Sorry, I couldn't do that: {reason}",
        "cart_head": "Your cart:",
        "cart_total": "Total: {total}",
        "checkout_next": "To place the order, send your name, phone number and address.",
        "up_to": "up to {n}",
        "from": "from {n}",
        "between": "{a} to {b}",
    },
}

_ERRORS_FA = {
    "insufficient stock": "موجودی کافی نیست.",
    "product not found": "این محصول در فروشگاه پیدا نشد.",
    "product is not active": "این محصول در حال حاضر فعال نیست.",
    "does not belong to this store": "این محصول متعلق به این فروشگاه نیست.",
    "cart is empty": "سبد خرید شما خالی است.",
    "quantity must be between": "تعداد باید بین ۱ تا ۱۰۰ باشد.",
    "quantity cannot exceed": "حداکثر تعداد مجاز برای هر محصول ۱۰۰ عدد است.",
    "order not found": "سفارشی با این مشخصات پیدا نشد.",
    "no customer session": "برای این کار ابتدا باید گفتگو را از دکمهٔ چت فروشگاه شروع کنید.",
}


def friendly_error(message: str, lang: str = "fa") -> str:
    lowered = (message or "").casefold()
    if lang == "fa":
        for needle, text in _ERRORS_FA.items():
            if needle in lowered:
                return text
        return "درخواست قابل انجام نبود."
    return (message or "The request could not be completed.").rstrip(".") + "."


def _pick(variants: Sequence[str], seed: str) -> str:
    return variants[zlib.crc32(seed.encode("utf-8")) % len(variants)]


def _money(value: str | float, lang: str) -> str:
    return f"{format_price(value)}{_TEXT[lang]['currency']}"


def _stock_text(stock: int, lang: str) -> str:
    return _TEXT[lang]["stock_n"].format(n=stock)


# --------------------------------------------------------------------------
# Composition helpers
# --------------------------------------------------------------------------


def _overlap_score(question_tokens: set[str], text: str) -> float:
    tokens = set(content_tokens(text))
    return float(len(question_tokens & tokens))


def _best_sentences(text: str, question_tokens: set[str], limit: int = 3) -> str:
    sentences = split_sentences(text)
    if len(sentences) <= limit or len(text) <= 360:
        return " ".join(sentences) if sentences else text
    scored = [(_overlap_score(question_tokens, s), i, s) for i, s in enumerate(sentences)]
    scored.sort(key=lambda item: (-item[0], item[1]))
    chosen = sorted(scored[:limit], key=lambda item: item[1])
    return " ".join(item[2] for item in chosen)


def _short_reason(description: str, limit: int = 110) -> str:
    sentences = split_sentences(description)
    text = sentences[0] if sentences else description
    text = text.strip().rstrip(".،؛;")
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def _product_variant(product: PromptProduct, lang: str) -> str:
    bits = []
    if product.color:
        bits.append(("رنگ " if lang == "fa" else "color ") + product.color)
    if product.size:
        bits.append(("سایز " if lang == "fa" else "size ") + product.size)
    return f" ({'، '.join(bits) if lang == 'fa' else ', '.join(bits)})" if bits else ""


def _select_named_products(question: str, products: list[PromptProduct]) -> list[PromptProduct]:
    """Products whose name the customer actually mentioned (best first)."""
    from app.services.product_resolver import STRONG_SCORE  # noqa: F401  (documented threshold)

    q_tokens = set(content_tokens(question))
    q_norm = normalize_text(question)
    scored: list[tuple[float, int, PromptProduct]] = []
    for index, product in enumerate(products):
        name_norm = normalize_text(product.name)
        name_tokens = set(content_tokens(product.name))
        if name_norm and name_norm in q_norm:
            scored.append((100.0, index, product))
            continue
        if not name_tokens:
            continue
        shared = len(name_tokens & q_tokens)
        if shared:
            scored.append((shared / len(name_tokens) * 10 + shared, index, product))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [item[2] for item in scored if item[0] >= 5.5]


def _requested_colors(question: str) -> list[str]:
    normalized = f" {normalize_text(question)} "
    found = []
    for word, canonical in _COLORS.items():
        if f" {word} " in normalized or (not word.isascii() and f" {word}" in normalized and normalized.count(word)):
            if canonical not in [c for c, _ in found]:
                found.append((canonical, word))
    return [word for _, word in found]


def _requested_size(question: str) -> str | None:
    match = re.search(r"(?:سایز|اندازه|size)\s*[:：]?\s*([A-Za-z0-9]{1,4}|\d{2,3})", normalize_text(question), re.I)
    return match.group(1).casefold() if match else None


def _product_haystack(product: PromptProduct) -> str:
    return normalize_text(f"{product.name} {product.description} {product.color} {product.attributes}")


def _attribute_check(question: str, product: PromptProduct, lang: str) -> tuple[str, str] | None:
    """Return ("ok"|"missing", text) when the customer asked about colour/size."""
    text = _TEXT[lang]
    colors = _requested_colors(question)
    if colors:
        haystack = _product_haystack(product)
        for wanted in colors:
            canonical = _COLORS.get(wanted, wanted)
            variants = {w for w, c in _COLORS.items() if c == canonical}
            if not any(v in haystack for v in variants):
                key = "attr_missing" if product.color else "attr_unknown"
                return "missing", text[key].format(
                    name=product.name, kind=text["kind_color"], wanted=wanted, have=product.color
                )
    size = _requested_size(question)
    if size:
        have_sizes = {s.strip().casefold() for s in re.split(r"[،,/ ]+", normalize_text(product.size)) if s.strip()}
        if have_sizes and size not in have_sizes:
            return "missing", text["attr_missing"].format(
                name=product.name, kind=text["kind_size"], wanted=size, have=product.size
            )
    return None


def _budget_phrase(budget: tuple[int | None, int | None], lang: str) -> str:
    low, high = budget
    t = _TEXT[lang]
    if low is not None and high is not None:
        return t["between"].format(a=format_price(low), b=format_price(high))
    if high is not None:
        return t["up_to"].format(n=format_price(high))
    if low is not None:
        return t["from"].format(n=format_price(low))
    return ""


def _product_line(product: PromptProduct, lang: str) -> str:
    t = _TEXT[lang]
    if product.stock <= 0:
        return t["list_item_oos"].format(name=product.name, price=_money(product.price, lang))
    return t["list_item"].format(
        name=product.name, price=_money(product.price, lang), stock=_stock_text(product.stock, lang)
    )


def _answer_single_product(question: str, product: PromptProduct, intent: SalesIntent, lang: str, seed: str) -> str:
    t = _TEXT[lang]
    price = _money(product.price, lang)
    if product.stock <= 0:
        base = t["out_of_stock"].format(name=product.name)
        check = _attribute_check(question, product, lang)
        return f"{base} {check[1]}" if check else base

    check = _attribute_check(question, product, lang)
    if check and check[0] == "missing":
        return f"{check[1]} " + t["details"].format(price=price, stock=_stock_text(product.stock, lang))

    asked_availability = any(
        word in normalize_text(question) for word in ("دارید", "دارین", "هست", "موجود", "have", "available", "stock")
    )
    asked_info = any(
        word in normalize_text(question)
        for word in ("معرفی", "مشخصات", "توضیح", "ویژگی", "جنس", "describe", "tell me about", "specs", "features", "about")
    )
    parts: list[str] = []
    if asked_info and (product.description or product.attributes):
        description = product.description or ""
        extra = f" ({product.attributes})" if product.attributes else ""
        parts.append(t["describe"].format(name=product.name, text=(description.rstrip(".") + extra).strip()))
        parts.append(t["details"].format(price=price, stock=_stock_text(product.stock, lang)))
    elif asked_availability and (product.color or product.size or check is None):
        parts.append(
            t["yes_have"].format(
                name=product.name,
                variant=_product_variant(product, lang),
                price=price,
                stock=_stock_text(product.stock, lang),
            )
        )
    else:
        parts.append(
            t["price_stock"].format(name=product.name, price=price, stock=_stock_text(product.stock, lang))
        )
    if product.stock <= 3:
        parts.append(t["low_stock"].format(n=product.stock))
    parts.append(t["next_cart"])
    return "\n".join(parts) if asked_info else " ".join(parts)


def _answer_compare(products: list[PromptProduct], lang: str) -> str:
    t = _TEXT[lang]
    lines = [t["compare_head"]]
    for product in products[:4]:
        extra_bits = []
        if product.color:
            extra_bits.append(("رنگ " if lang == "fa" else "color ") + product.color)
        if product.size:
            extra_bits.append(("سایز " if lang == "fa" else "size ") + product.size)
        if product.description:
            extra_bits.append(_short_reason(product.description, 70))
        extra = " — " + "، ".join(extra_bits) if extra_bits and lang == "fa" else (
            " — " + ", ".join(extra_bits) if extra_bits else ""
        )
        lines.append(
            t["compare_item"].format(
                name=product.name,
                price=_money(product.price, lang),
                stock=_stock_text(max(product.stock, 0), lang),
                extra=extra,
            )
        )
    try:
        ordered = sorted(products[:4], key=lambda p: float(p.price))
        if len(ordered) >= 2 and float(ordered[0].price) != float(ordered[-1].price):
            diff = float(ordered[-1].price) - float(ordered[0].price)
            lines.append(t["compare_cheaper"].format(name=ordered[0].name, diff=_money(diff, lang)))
    except ValueError:
        pass
    return "\n".join(lines)


def _answer_listing(products: list[PromptProduct], intent: SalesIntent, question: str, lang: str, mode: str | None) -> str:
    t = _TEXT[lang]
    kind = superlative_kind(question)
    budget = extract_budget(question)
    if kind and products:
        first = products[0]
        key = {"cheapest": "cheapest", "priciest": "priciest", "newest": "newest"}.get(kind)
        if key:
            text = t[key].format(
                name=first.name, price=_money(first.price, lang), stock=_stock_text(max(first.stock, 0), lang)
            )
            rest = products[1:3]
            if rest:
                text += "\n" + t["others"] + "\n" + "\n".join(_product_line(p, lang) for p in rest)
            return text
    head = t["list_head"]
    if budget != (None, None):
        head = t["budget_head"].format(range=_budget_phrase(budget, lang))
    lines = [head] + [_product_line(p, lang) for p in products[:8]]
    lines.append(t["next_help"])
    return "\n".join(lines)


def _answer_recommendation(question: str, products: list[PromptProduct], lang: str) -> str:
    t = _TEXT[lang]
    budget = extract_budget(question)
    pool = [p for p in products if p.stock > 0] or products
    q_tokens = set(content_tokens(question))
    ranked = sorted(
        pool,
        key=lambda p: (-_overlap_score(q_tokens, f"{p.name} {p.description}"), pool.index(p)),
    )
    best = ranked[0]
    reason = ""
    if best.description:
        reason = t["reason"].format(text=_short_reason(best.description))
    lines = [
        t["recommend"].format(
            name=best.name,
            reason=reason,
            price=_money(best.price, lang),
            stock=_stock_text(max(best.stock, 0), lang),
        )
    ]
    alternative = next((p for p in ranked[1:] if p.stock > 0), None)
    if alternative:
        lines.append(t["recommend_alt"].format(name=alternative.name, price=_money(alternative.price, lang)))
    lines.append(t["next_cart"])
    if budget != (None, None):
        lines.insert(0, t["budget_head"].format(range=_budget_phrase(budget, lang)))
    return "\n".join(lines)


def _policy_answer(parsed: ParsedPrompt, lang: str) -> str | None:
    t = _TEXT[lang]
    q_tokens = set(content_tokens(parsed.question))
    units: list[tuple[float, str]] = []
    for faq in parsed.faqs:
        score = _overlap_score(q_tokens, f"{faq.question} {faq.answer}") + 1.5 * _overlap_score(q_tokens, faq.question)
        units.append((score, _best_sentences(faq.answer, q_tokens)))
    for entry in parsed.knowledge:
        score = _overlap_score(q_tokens, f"{entry.title} {entry.content}") + 1.5 * _overlap_score(q_tokens, entry.title)
        units.append((score, _best_sentences(entry.content, q_tokens)))
    if not units:
        return None
    ordered = sorted(enumerate(units), key=lambda item: (-item[1][0], item[0]))
    top_score = ordered[0][1][0]
    chosen: list[str] = []
    for _, (score, text) in ordered[:3]:
        if text and text not in chosen and (not chosen or score >= max(top_score * 0.6, 1)):
            chosen.append(text.strip())
    if len(chosen) == 1:
        return t["policy_one"].format(text=chosen[0])
    return t["policy_many"] + "\n" + "\n".join(f"• {text}" for text in chosen)


# --------------------------------------------------------------------------
# Entry points
# --------------------------------------------------------------------------


def compose_answer(parsed: ParsedPrompt, history: Sequence[dict] | None = None) -> str:
    question = parsed.question
    lang = detect_language(question)
    t = _TEXT[lang]
    seed = question
    intent = detect_intent(question, [m for m in (history or []) if isinstance(m, dict)])
    store = parsed.store_name or ("فروشگاه" if lang == "fa" else "our store")

    if "ambiguous" in parsed.guidance.casefold() or is_ambiguous_request(question):
        return t["clarify"]
    if intent == SalesIntent.GREETING:
        return _pick(t["greeting"], seed).format(store=store)
    if intent == SalesIntent.THANKS:
        return _pick(t["thanks"], seed)
    if parsed.conflict:
        return t["conflict"]
    if parsed.empty:
        if extract_budget(question) != (None, None) and intent in {
            SalesIntent.PRODUCT_SEARCH, SalesIntent.RECOMMENDATION, SalesIntent.PRODUCT_INFO,
        }:
            return t["budget_none"]
        return t["not_found"]

    has_policy = bool(parsed.faqs or parsed.knowledge)
    products = parsed.products

    if intent == SalesIntent.STORE_INFO and has_policy:
        policy = _policy_answer(parsed, lang)
        if policy:
            return policy

    if products:
        named = _select_named_products(question, products)
        wants_listing = superlative_kind(question) is not None or extract_budget(question) != (None, None)
        if intent == SalesIntent.COMPARE and len(products) >= 2:
            return _answer_compare(named if len(named) >= 2 else products, lang)
        if intent == SalesIntent.RECOMMENDATION and not named:
            return _answer_recommendation(question, products, lang)
        if wants_listing or (len(products) > 1 and not named and not is_followup_reference(question)):
            if has_policy and intent == SalesIntent.STORE_INFO:
                pass
            else:
                return _answer_listing(products, intent, question, lang, None)
        subject = named or ([products[0]] if len(products) == 1 or is_followup_reference(question) else [])
        if len(subject) == 1:
            answer = _answer_single_product(question, subject[0], intent, lang, seed)
            if has_policy and intent in {SalesIntent.STORE_INFO}:
                policy = _policy_answer(parsed, lang)
                if policy:
                    return f"{policy}\n{answer}"
            return answer
        if len(subject) > 1:
            lines = [t["found_head"]] + [_product_line(p, lang) for p in subject[:5]]
            lines.append(t["next_help"])
            return "\n".join(lines)
        if len(products) > 1:
            return _answer_listing(products, intent, question, lang, None)

    policy = _policy_answer(parsed, lang)
    if policy:
        return policy
    return t["not_found"]


def compose_tool_answer(messages: Sequence[dict], question: str = "") -> str:
    """Summarise tool results for the customer (used when a model is unavailable)."""
    lang = detect_language(question) if question else "fa"
    t = _TEXT[lang]
    lines: list[str] = []
    for message in messages:
        if message.get("role") != "tool":
            continue
        try:
            payload = json.loads(message.get("content") or "{}")
        except (TypeError, ValueError):
            continue
        if not payload.get("ok", True) and payload.get("error"):
            lines.append(t["tool_fail"].format(reason=friendly_error(str(payload["error"]), lang)))
            continue
        result = payload.get("result", payload)
        if isinstance(result, dict) and "items" in result:
            items = result.get("items") or []
            if not items:
                lines.append("سبد خرید شما خالی است." if lang == "fa" else "Your cart is empty.")
                continue
            lines.append(t["tool_ok"])
            lines.append(t["cart_head"])
            for item in items:
                name = item.get("name") or f"#{item.get('product_id')}"
                line = f"• {name} × {item.get('quantity')}"
                lines.append(line)
            if result.get("total"):
                lines.append(t["cart_total"].format(total=_money(result["total"], lang)))
        elif isinstance(result, dict) and result.get("state") == "awaiting_customer":
            lines.append(t["checkout_next"])
        else:
            lines.append(t["tool_ok"])
    return "\n".join(lines) or t["tool_ok"]
