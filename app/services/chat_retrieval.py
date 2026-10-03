"""Store-scoped hybrid retrieval (RAG) for the sales assistant.

Pipeline
--------
1. Load the store's *active* FAQs, knowledge-base entries and products.
2. Lexical ranking with a BM25F-style scorer (title boosted over body), typo
   tolerant (trigram/edit-distance expansion), prefix aware, and boosted by
   store-domain *concepts* (delivery, returns, warranty, payment ...) and
   cross-language product synonyms (برگر ↔ burger, گوشی ↔ phone ...).
3. Optional semantic ranking (pgvector / embedding provider) fused with the
   lexical score; failures silently fall back to lexical retrieval.
4. A relevance gate rejects incidental one-word matches so unrelated questions
   (weather, bitcoin ...) never pull store data into the answer.
5. Long knowledge-base text is split into passages and only the best passages
   are returned, so nothing is cut mid-sentence.
6. Follow-up questions («قیمتش چنده؟») are resolved against the conversation;
   catalog listings, superlatives («ارزان‌ترین») and budgets («زیر ۳ میلیون»)
   are answered from the real catalog.

Prices and stock are **never** read from the index: ``format_context`` always
prints the live database values.
"""

from __future__ import annotations

import json
import logging
import math
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal, Sequence

from sqlalchemy.orm import Session

from app.db.models import FAQ, KnowledgeBaseEntry, Product, Store
from app.services.grounded_responder import _COLORS as _COLOR_WORDS
from app.services.product_resolver import focus_from_history
from app.services.sales_intent import (
    SalesIntent,
    detect_intent,
    is_catalog_listing,
    is_followup_reference,
    superlative_kind,
)
from app.services.semantic_index import (
    SOURCE_FAQ,
    SOURCE_KNOWLEDGE_BASE,
    SOURCE_PRODUCT,
    get_rag_settings,
    retrieve_semantic_matches,
)
from app.services.text_utils import (
    STOP_WORDS,
    chunk_text,
    content_tokens,
    extract_budget,
    fuzzy_match,
    NUMBER_WORD_TOKENS,
    normalize_text,
    stem_token,
)

logger = logging.getLogger(__name__)

MAX_RESULTS_PER_SOURCE = 3
MAX_PRODUCT_RESULTS = 5
MAX_LISTING_PRODUCTS = 8
MAX_CONTEXT_RESULTS = 7
MAX_PASSAGES_PER_ENTRY = 2
RELATIVE_SCORE_CUTOFF = 0.30
BM25_K1 = 1.4
BM25_B = 0.6
TITLE_BOOST = 2.5


def normalize_for_search(value: str) -> str:
    """Comparison-only version of text (display text is never modified)."""
    return normalize_text(value)


# --------------------------------------------------------------------------
# Domain vocabulary
# --------------------------------------------------------------------------


def _stems(words: str) -> frozenset[str]:
    return frozenset(
        stem_token(token) for word in words.split() for token in [normalize_text(word)] if token
    )


# Policy / store-information concepts.  A concept match is a strong signal even
# when the exact words differ ("ارسال" ↔ "تحویل", "refund" ↔ "مرجوعی").
_CONCEPT_ALIASES: dict[str, frozenset[str]] = {
    "delivery": _stems(
        "delivery deliver shipping ship shipped courier ارسال تحویل پست پیک فرستادن فرستاده میفرستید میفرستین "
        "حمل بارنامه تیپاکس"
    ),
    "return": _stems(
        "return returns returning refund refunded exchange مرجوع مرجوعی بازگشت بازگرداندن تعویض استرداد "
        "بازپرداخت عودت"
    ),
    "price": _stems("price prices pricing cost costs قیمت هزینه بها"),
    "stock": _stems("stock availability available inventory موجود موجودی ناموجود دردسترس"),
    "warranty": _stems("warranty guarantee گارانتی ضمانت ضمانتنامه"),
    "payment": _stems("payment pay installment installments cash card پرداخت درگاه اقساط قسطی نقدی کارت"),
    "contact": _stems("contact phone support email whatsapp telegram instagram تماس تلفن پشتیبانی ایمیل واتساپ تلگرام اینستاگرام"),
    "hours": _stems("hours open closed schedule ساعت ساعات تعطیل باز بسته"),
    "address": _stems("address location branch map آدرس نشانی مکان لوکیشن شعبه"),
    "discount": _stems("discount coupon sale offer off تخفیف حراج کوپن"),
}
_CONCEPT_PHRASES: dict[str, tuple[str, ...]] = {
    "delivery": ("می فرستید", "ارسال می کنید", "تحویل می دهید", "چند روزه می رسه", "کی می رسه"),
    "return": ("پس دادن", "پس بدهم", "پس بدم", "پس بدی", "برگردانم", "برگرداندن کالا", "پس میدم", "پس می دم"),
    "hours": ("ساعت کاری", "ساعات کاری", "ساعت کار", "کی باز", "تا ساعت"),
    "contact": ("شماره تماس", "شماره تلفن", "چطور تماس"),
}
# Concepts that describe a *product fact*; they alone never justify retrieving a
# record ("قیمت بیت کوین چنده؟" must not return the cheapest laptop).
_PRODUCT_FACT_CONCEPTS = frozenset({"price", "stock"})

_SYNONYM_GROUPS: dict[str, frozenset[str]] = {
    "shoe": _stems("کفش کتونی کتانی بوت صندل نیمبوت نیم بوت shoe shoes sneaker sneakers boot boots sandal footwear loafer"),
    "phone": _stems("گوشی موبایل همراه تلفنهمراه smartphone phone mobile cellphone iphone"),
    "laptop": _stems("لپتاپ لپ تاپ لپتب نوتبوک رایانه laptop notebook macbook ultrabook"),
    "shirt": _stems("پیراهن تیشرت تی شرت بلوز شومیز tshirt shirt tee blouse top"),
    "pants": _stems("شلوار شلوارک جین pants trousers jeans shorts"),
    "jacket": _stems("کاپشن ژاکت پالتو بارانی کت هودی سوییشرت jacket coat hoodie sweater sweatshirt"),
    "bag": _stems("کیف کوله چمدان bag backpack handbag purse suitcase"),
    "watch": _stems("مچی watch wristwatch smartwatch"),
    "headphone": _stems("هدفون هندزفری هدست ایرپاد ایرفون headphone headphones earphone earphones earbuds airpods headset"),
    "burger": _stems("برگر همبرگر چیزبرگر burger hamburger cheeseburger"),
    "pizza": _stems("پیتزا pizza"),
    "coffee": _stems("قهوه اسپرسو کاپوچینو لاته coffee espresso cappuccino latte"),
    "tea": _stems("چای دمنوش tea"),
    "dessert": _stems("دسر کیک شیرینی بستنی dessert cake sweet icecream pastry"),
    "food": _stems("غذا خوراک ناهار شام صبحانه food meal lunch dinner breakfast"),
    "drink": _stems("نوشیدنی آبمیوه شربت نوشابه drink beverage juice soda"),
    "tv": _stems("تلویزیون تیوی tv television"),
    "camera": _stems("دوربین camera"),
    "tablet": _stems("تبلت tablet ipad"),
    "perfume": _stems("عطر ادکلن پرفیوم perfume cologne fragrance"),
    "cream": _stems("کرم لوسیون مرطوبکننده cream lotion moisturizer"),
    "medicine": _stems("دارو قرص شربت مکمل ویتامین medicine pill tablet vitamin supplement"),
    "book": _stems("کتاب رمان book novel"),
    "toy": _stems("اسباببازی عروسک toy doll lego"),
}

_GENERIC_TOKENS = frozenset(
    _CONCEPT_ALIASES["price"]
    | _CONCEPT_ALIASES["stock"]
    | _stems(
        "محصول محصولات کالا کالاها جنس مدل نوع مورد گزینه آیتم عدد دانه تعداد سایز اندازه رنگ "
        "product products item items goods model type size color colour piece pieces unit units "
        "بدهم بدم بدیم نمیدم میدم کنم کنید کنیم دارید نمیکنه دارین چطوره چطور هستش مناسبه "
        "تومان تومن ریال"
    )
)

_STOCK_ONLY_FAMILY = _CONCEPT_ALIASES["price"] | _CONCEPT_ALIASES["stock"]


def _normalize_alias(text: str) -> str:
    return normalize_text(text)


@lru_cache(maxsize=1)
def _all_phrase_concepts() -> dict[str, tuple[str, ...]]:
    return {name: tuple(_normalize_alias(p) for p in phrases) for name, phrases in _CONCEPT_PHRASES.items()}


def concepts_in(text: str, tokens: Sequence[str] | None = None) -> set[str]:
    """Policy/product-fact concepts expressed in *text*."""
    normalized = normalize_text(text)
    token_set = set(tokens) if tokens is not None else set(content_tokens(text, keep_stop=True))
    found = {name for name, aliases in _CONCEPT_ALIASES.items() if token_set & aliases}
    for name, phrases in _all_phrase_concepts().items():
        if any(phrase in normalized for phrase in phrases):
            found.add(name)
    return found


def synonym_groups_in(tokens: Sequence[str]) -> set[str]:
    token_set = set(tokens)
    return {name for name, members in _SYNONYM_GROUPS.items() if token_set & members}


# --------------------------------------------------------------------------
# Documents and scoring
# --------------------------------------------------------------------------


@lru_cache(maxsize=30000)
def _cached_tokens(text: str) -> tuple[str, ...]:
    return tuple(content_tokens(text))


@dataclass
class _Doc:
    key: tuple[str, int]
    record: FAQ | KnowledgeBaseEntry | Product
    title: str
    body: str
    title_tokens: list[str]
    body_tokens: list[str]
    concepts: set[str]
    groups: set[str]
    tf: Counter = field(default_factory=Counter)
    length: float = 0.0
    passages: list[str] = field(default_factory=list)


def _category_names(store: Store, product: Product) -> str:
    wanted = set(product.category_ids or [])
    if not wanted:
        return ""
    names = []
    for item in store.categories or []:
        if isinstance(item, dict) and item.get("id") in wanted and item.get("name"):
            names.append(str(item["name"]))
    return " ".join(names)


def _attribute_text(product: Product) -> str:
    attrs = product.attributes or {}
    if not isinstance(attrs, dict):
        return ""
    parts: list[str] = []
    for key, value in attrs.items():
        if isinstance(value, (list, tuple)):
            value = " ".join(str(v) for v in value)
        if value in (None, "", False):
            continue
        parts.append(f"{key} {value}")
    return " ".join(parts)


def _build_doc(source_type: str, record, store: Store) -> _Doc:
    if source_type == SOURCE_FAQ:
        title, body = record.question or "", record.answer or ""
    elif source_type == SOURCE_KNOWLEDGE_BASE:
        title, body = record.title or "", record.content or ""
    else:
        title = record.name or ""
        body = " ".join(
            part
            for part in (
                record.description or "",
                record.size or "",
                record.color or "",
                _attribute_text(record),
                _category_names(store, record),
            )
            if part
        )
    title_tokens = list(_cached_tokens(title))
    body_tokens = list(_cached_tokens(body))
    all_tokens = title_tokens + body_tokens
    concepts = concepts_in(f"{title} {body}", all_tokens)
    groups = synonym_groups_in(all_tokens)
    doc = _Doc(
        key=(source_type, record.id),
        record=record,
        title=title,
        body=body,
        title_tokens=title_tokens,
        body_tokens=body_tokens,
        concepts=concepts,
        groups=groups,
    )
    tf: Counter = Counter()
    for token in title_tokens:
        tf[token] += TITLE_BOOST
    for token in body_tokens:
        tf[token] += 1.0
    for name in concepts:
        tf[f"__c_{name}"] += 1.0
    for name in groups:
        tf[f"__s_{name}"] += 1.0
    doc.tf = tf
    doc.length = float(len(title_tokens) * TITLE_BOOST + len(body_tokens)) or 1.0
    if source_type == SOURCE_KNOWLEDGE_BASE:
        doc.passages = chunk_text(body)
    return doc


class _Index:
    def __init__(self, docs: list[_Doc]):
        self.docs = docs
        self.df: Counter = Counter()
        for doc in docs:
            for term in doc.tf:
                self.df[term] += 1
        self.n = max(len(docs), 1)
        self.avgdl = (sum(doc.length for doc in docs) / len(docs)) if docs else 1.0
        self.vocab = {term for term in self.df if not term.startswith("__")}
        self.max_idf = self.idf_value(1)

    def idf_value(self, df: int) -> float:
        return math.log(1 + (self.n - df + 0.5) / (df + 0.5))

    def idf(self, term: str) -> float:
        df = self.df.get(term, 0)
        return self.idf_value(df) if df else self.max_idf


@dataclass
class _Query:
    meaningful: list[str]
    terms: dict[str, float]
    origin: dict[str, str]  # expanded term -> original query token
    concepts: set[str]
    groups: set[str]


def _build_query(question: str, index: _Index, budget_present: bool = False) -> _Query:
    tokens = content_tokens(question)
    if budget_present:
        # "زیر ۳ میلیون" describes a price range, not a product word.
        tokens = [t for t in tokens if not t.isdigit() and t not in NUMBER_WORD_TOKENS]
    meaningful = [t for t in dict.fromkeys(tokens) if t not in _GENERIC_TOKENS and t not in STOP_WORDS]
    terms: dict[str, float] = {}
    origin: dict[str, str] = {}
    for token in dict.fromkeys(tokens):
        terms[token] = max(terms.get(token, 0.0), 1.0)
        origin[token] = token
        if token in index.vocab or token in _GENERIC_TOKENS or token.isdigit():
            continue
        # Typos and transliteration noise.
        near = fuzzy_match(token, index.vocab)
        if near and near not in terms:
            terms[near] = 0.75
            origin[near] = token
        # Prefix / partial words: "sneak" ↔ "sneaker", "گلک" ↔ "گلکسی".
        if len(token) >= 4:
            for candidate in index.vocab:
                if candidate != token and candidate.startswith(token) and candidate not in terms:
                    terms[candidate] = 0.6
                    origin[candidate] = token
    concepts = concepts_in(question, tokens)
    groups = synonym_groups_in(tokens)
    for name in concepts:
        terms[f"__c_{name}"] = 1.6
    for name in groups:
        terms[f"__s_{name}"] = 0.7
    return _Query(meaningful=meaningful, terms=terms, origin=origin, concepts=concepts, groups=groups)


def _score_doc(doc: _Doc, query: _Query, index: _Index) -> tuple[float, set[str], set[str]]:
    """Return (score, matched original meaningful tokens, matched policy concepts)."""
    score = 0.0
    matched_tokens: set[str] = set()
    matched_concepts: set[str] = set()
    norm = 1 - BM25_B + BM25_B * (doc.length / index.avgdl)
    for term, weight in query.terms.items():
        tf = doc.tf.get(term)
        if not tf:
            continue
        saturation = tf * (BM25_K1 + 1) / (tf + BM25_K1 * norm)
        score += weight * index.idf(term) * saturation
        if term.startswith("__c_"):
            name = term[4:]
            if name not in _PRODUCT_FACT_CONCEPTS:
                matched_concepts.add(name)
        elif term.startswith("__s_"):
            members = _SYNONYM_GROUPS.get(term[4:], frozenset())
            matched_tokens.update(token for token in query.meaningful if token in members)
        else:
            original = query.origin.get(term, term)
            if original in query.meaningful:
                matched_tokens.add(original)
    return score, matched_tokens, matched_concepts


def _coverage(matched: set[str], query: _Query, index: _Index) -> float:
    total = sum(index.idf(token) for token in query.meaningful)
    if total <= 0:
        return 0.0
    return sum(index.idf(token) for token in matched) / total


def _accept(doc_matched: set[str], doc_concepts: set[str], query: _Query, index: _Index) -> bool:
    if doc_concepts:
        return True
    if not query.meaningful:
        return False
    if len(query.meaningful) == 1:
        return bool(doc_matched)
    if len(doc_matched) >= 2 and _coverage(doc_matched, query, index) >= 0.34:
        return True
    return _coverage(doc_matched, query, index) >= 0.5


# --------------------------------------------------------------------------
# Public data structures
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class RetrievedMatch:
    source_type: Literal["faq", "knowledge_base", "product"]
    record: FAQ | KnowledgeBaseEntry | Product
    lexical_score: float
    semantic_score: float
    hybrid_score: float
    passages: tuple[str, ...] = ()


@dataclass(frozen=True)
class RetrievedContext:
    store: Store
    faqs: list[FAQ]
    knowledge_entries: list[KnowledgeBaseEntry]
    products: list[Product]
    matches: list[RetrievedMatch] = field(default_factory=list)
    mode: str = "search"  # search | listing | focus | none
    intent: SalesIntent = SalesIntent.GENERAL
    focus_product: Product | None = None
    budget: tuple[int | None, int | None] = (None, None)

    @property
    def is_empty(self) -> bool:
        return not (self.faqs or self.knowledge_entries or self.products)


# --------------------------------------------------------------------------
# Conflict detection (kept: objective duplicate-record conflicts only)
# --------------------------------------------------------------------------


def _has_conflicting_information(context: RetrievedContext) -> bool:
    values_by_key: dict[tuple, set[str]] = {}
    for faq in context.faqs:
        values_by_key.setdefault(("faq", normalize_text(faq.question)), set()).add(
            normalize_text(faq.answer)
        )
    for entry in context.knowledge_entries:
        values_by_key.setdefault(("kb", normalize_text(entry.title)), set()).add(
            normalize_text(entry.content)
        )
    for product in context.products:
        key = (
            "product",
            normalize_text(product.name),
            normalize_text(product.size or ""),
            normalize_text(product.color or ""),
            json.dumps(product.attributes or {}, sort_keys=True, ensure_ascii=False),
        )
        values_by_key.setdefault(key, set()).add(f"{product.price}|{product.stock - product.reserved_stock}")
    return any(len(values) > 1 for values in values_by_key.values())


# --------------------------------------------------------------------------
# Retrieval
# --------------------------------------------------------------------------


def _available(product: Product) -> int:
    return (product.stock or 0) - (product.reserved_stock or 0)


def _within_budget(product: Product, budget: tuple[int | None, int | None]) -> bool:
    low, high = budget
    price = float(product.price)
    if low is not None and price < low:
        return False
    if high is not None and price > high:
        return False
    return True


def _listing_products(products: list[Product], question: str, budget) -> list[Product]:
    kind = superlative_kind(question)
    pool = [p for p in products if _within_budget(p, budget)]
    in_stock = [p for p in pool if _available(p) > 0] or pool
    if kind == "cheapest":
        ordered = sorted(in_stock, key=lambda p: (float(p.price), p.id))
    elif kind == "priciest":
        ordered = sorted(in_stock, key=lambda p: (-float(p.price), p.id))
    elif kind == "newest":
        ordered = sorted(in_stock, key=lambda p: -p.id)
    elif budget != (None, None):
        ordered = sorted(in_stock, key=lambda p: (float(p.price), p.id))
    else:
        ordered = sorted(in_stock, key=lambda p: p.id)
    limit = 3 if kind in {"cheapest", "priciest", "newest"} else MAX_LISTING_PRODUCTS
    return ordered[:limit]


def _best_passages(doc: _Doc, query: _Query, index: _Index) -> tuple[str, ...]:
    if not doc.passages or len(doc.body) <= 700:
        return ()
    scored = []
    for position, passage in enumerate(doc.passages):
        tokens = set(_cached_tokens(passage))
        score = sum(
            index.idf(term) * weight
            for term, weight in query.terms.items()
            if not term.startswith("__") and term in tokens
        )
        concepts = concepts_in(passage)
        score += 1.5 * len(concepts & query.concepts)
        scored.append((score, position, passage))
    scored.sort(key=lambda item: (-item[0], item[1]))
    best = [item for item in scored[:MAX_PASSAGES_PER_ENTRY] if item[0] > 0] or scored[:1]
    best.sort(key=lambda item: item[1])
    return tuple(passage for _, _, passage in best)


def _semantic_candidates(db: Session, store_id: int, question: str, records_by_key) -> dict[tuple[str, int], float]:
    try:
        matches = retrieve_semantic_matches(db, store_id, question)
    except Exception:  # noqa: BLE001 - semantic search is strictly optional
        logger.warning("Semantic retrieval raised; continuing lexically", exc_info=True)
        return {}
    return {
        (match.source_type, match.source_id): match.similarity
        for match in matches
        if (match.source_type, match.source_id) in records_by_key
    }


def retrieve_store_context(
    db: Session,
    store_id: int,
    question: str,
    history: Sequence[dict[str, str]] | None = None,
) -> RetrievedContext | None:
    store = db.query(Store).filter(Store.id == store_id).first()
    if store is None:
        return None

    intent = detect_intent(question, list(history) if history else None)
    if intent in {SalesIntent.GREETING, SalesIntent.THANKS}:
        return RetrievedContext(store, [], [], [], [], mode="none", intent=intent)

    faqs = db.query(FAQ).filter(FAQ.store_id == store_id, FAQ.is_active.is_(True)).order_by(FAQ.id).all()
    entries = (
        db.query(KnowledgeBaseEntry)
        .filter(KnowledgeBaseEntry.store_id == store_id, KnowledgeBaseEntry.is_active.is_(True))
        .order_by(KnowledgeBaseEntry.id)
        .all()
    )
    products = (
        db.query(Product)
        .filter(Product.store_id == store_id, Product.is_active.is_(True))
        .order_by(Product.id)
        .all()
    )

    docs = (
        [_build_doc(SOURCE_FAQ, record, store) for record in faqs]
        + [_build_doc(SOURCE_KNOWLEDGE_BASE, record, store) for record in entries]
        + [_build_doc(SOURCE_PRODUCT, record, store) for record in products]
    )
    index = _Index(docs)
    docs_by_key = {doc.key: doc for doc in docs}
    records_by_key = {doc.key: doc.record for doc in docs}
    budget = extract_budget(question)
    query = _build_query(question, index, budget != (None, None))

    # ---- lexical ranking -------------------------------------------------
    top_k = get_rag_settings().lexical_top_k
    lexical: dict[tuple[str, int], float] = {}
    for source_type in (SOURCE_FAQ, SOURCE_KNOWLEDGE_BASE, SOURCE_PRODUCT):
        ranked = []
        for doc in docs:
            if doc.key[0] != source_type:
                continue
            score, matched, concepts = _score_doc(doc, query, index)
            if score <= 0:
                continue
            if source_type == SOURCE_PRODUCT:
                # Products need a product-specific word, never a concept alone.
                if not matched:
                    continue
                title_set = set(doc.title_tokens)
                title_groups = synonym_groups_in(doc.title_tokens)
                title_hit = any(
                    token in title_set or any(token in _SYNONYM_GROUPS[g] for g in title_groups)
                    for token in matched
                )
                # A product whose *name* contains a query word is a real reference,
                # even inside a multi-topic question ("shipping returns phone").
                accepted = title_hit or _accept(matched, set(), query, index)
            else:
                accepted = _accept(matched, concepts, query, index)
            if accepted:
                ranked.append((score, doc.key))
        ranked.sort(key=lambda item: (-item[0], item[1][1]))
        limit = max(top_k, MAX_PRODUCT_RESULTS if source_type == SOURCE_PRODUCT else MAX_RESULTS_PER_SOURCE)
        if ranked:
            best = ranked[0][0]
            for score, key in ranked[:limit]:
                if score >= best * RELATIVE_SCORE_CUTOFF:
                    lexical[key] = score

    # ---- semantic ranking (optional) -------------------------------------
    semantic = _semantic_candidates(db, store_id, question, records_by_key)
    meaningful_set = set(query.meaningful)
    for key in list(semantic):
        if key[0] == SOURCE_PRODUCT:
            doc = docs_by_key[key]
            # Never let an unrelated product in through vectors alone.
            doc_tokens = set(doc.title_tokens) | set(doc.body_tokens)
            if not (meaningful_set & doc_tokens) and key not in lexical:
                del semantic[key]

    # ---- fusion ----------------------------------------------------------
    settings = get_rag_settings()
    max_lex = max(lexical.values(), default=1.0)
    fused: list[tuple[float, float, float, tuple[str, int]]] = []
    for key in set(lexical) | set(semantic):
        lex = lexical.get(key, 0.0)
        sem = semantic.get(key, 0.0)
        if semantic:
            hybrid = settings.lexical_weight * (lex / max_lex) + settings.semantic_weight * sem
        else:
            hybrid = lex / max_lex
        # Policy questions favour policy sources, product questions favour products.
        if intent == SalesIntent.STORE_INFO and key[0] != SOURCE_PRODUCT:
            hybrid *= 1.15
        elif intent in {SalesIntent.PRODUCT_INFO, SalesIntent.PRODUCT_SEARCH, SalesIntent.RECOMMENDATION,
                        SalesIntent.COMPARE} and key[0] == SOURCE_PRODUCT:
            hybrid *= 1.15
        fused.append((hybrid, lex, sem, key))
    fused.sort(key=lambda item: (-item[0], -item[1], item[3][1]))

    selected: list[RetrievedMatch] = []
    counts: dict[str, int] = {}
    for hybrid, lex, sem, key in fused:
        cap = MAX_PRODUCT_RESULTS if key[0] == SOURCE_PRODUCT else MAX_RESULTS_PER_SOURCE
        if counts.get(key[0], 0) >= cap:
            continue
        doc = docs_by_key[key]
        passages = _best_passages(doc, query, index) if key[0] == SOURCE_KNOWLEDGE_BASE else ()
        selected.append(RetrievedMatch(key[0], doc.record, lex, sem, hybrid, passages))
        counts[key[0]] = counts.get(key[0], 0) + 1
        if len(selected) >= MAX_CONTEXT_RESULTS:
            break

    mode = "search"
    focus_product: Product | None = None
    selected_products = [m for m in selected if m.source_type == SOURCE_PRODUCT]

    # ---- budget filter on named products --------------------------------
    if budget != (None, None) and selected_products:
        kept = [m for m in selected if m.source_type != SOURCE_PRODUCT or _within_budget(m.record, budget)]
        selected = kept
        selected_products = [m for m in selected if m.source_type == SOURCE_PRODUCT]

    # ---- follow-ups: «قیمتش چنده؟» --------------------------------------
    followup = is_followup_reference(question) or (
        not query.meaningful and intent in {SalesIntent.PRODUCT_INFO, SalesIntent.RECOMMENDATION}
    )
    wants_listing = is_catalog_listing(question) or superlative_kind(question) is not None
    # "رنگ آبی هم دارید؟" continues the previous product; "قیمت بیت کوین؟" does not:
    # every meaningful word must be a variant attribute (colour/size/number).
    attribute_words = {stem_token(normalize_text(word)) for word in _COLOR_WORDS}
    short_attribute_question = (
        intent == SalesIntent.PRODUCT_INFO
        and not selected_products
        and all(token in attribute_words or token.isdigit() for token in query.meaningful)
    )
    if history and not wants_listing and (followup or short_attribute_question) and not selected_products:
        resolution = focus_from_history(list(history), products)
        if resolution.product is not None:
            focus_product = resolution.product
            selected.insert(0, RetrievedMatch(SOURCE_PRODUCT, focus_product, 0.0, 0.0, 1.0))
            mode = "focus"
    elif history and followup and selected_products and not query.meaningful:
        resolution = focus_from_history(list(history), products)
        if resolution.product is not None and resolution.product.id not in {m.record.id for m in selected_products}:
            focus_product = resolution.product
            selected.insert(0, RetrievedMatch(SOURCE_PRODUCT, focus_product, 0.0, 0.0, 1.0))
            mode = "focus"

    # ---- catalog listing / superlative / budget-only --------------------
    listing_needed = wants_listing or (
        not selected
        and not query.meaningful
        and (budget != (None, None) or intent in {SalesIntent.PRODUCT_SEARCH, SalesIntent.RECOMMENDATION,
                                                  SalesIntent.PRODUCT_INFO, SalesIntent.COMPARE})
    )
    if listing_needed and products:
        listed = _listing_products(products, question, budget)
        if listed:
            selected = [m for m in selected if m.source_type != SOURCE_PRODUCT]
            for rank, product in enumerate(listed):
                selected.append(RetrievedMatch(SOURCE_PRODUCT, product, 0.0, 0.0, 1.0 - rank * 0.01))
            mode = "listing"

    return RetrievedContext(
        store=store,
        faqs=[m.record for m in selected if isinstance(m.record, FAQ)],
        knowledge_entries=[m.record for m in selected if isinstance(m.record, KnowledgeBaseEntry)],
        products=[m.record for m in selected if isinstance(m.record, Product)],
        matches=selected,
        mode=mode if selected else "none",
        intent=intent,
        focus_product=focus_product,
        budget=budget,
    )


# --------------------------------------------------------------------------
# Prompt formatting
# --------------------------------------------------------------------------


def _clean(value: object) -> str:
    return " ".join(str(value or "").replace("|", "/").split())


def format_product_line(product: Product) -> str:
    attributes = product.attributes if isinstance(product.attributes, dict) else {}
    attr_text = ", ".join(
        f"{_clean(k)}: {_clean(v)}" for k, v in attributes.items() if v not in (None, "", False)
    )
    parts = [
        f"id={product.id}",
        _clean(product.name),
        f"price={product.price}",
        f"stock={product.stock - product.reserved_stock}",
    ]
    if product.size:
        parts.append(f"size={_clean(product.size)}")
    if product.color:
        parts.append(f"color={_clean(product.color)}")
    if attr_text:
        parts.append(f"attributes={attr_text}")
    parts.append(f"description={_clean(product.description) or 'No description'}")
    return "- " + " | ".join(parts)


def format_context(context: RetrievedContext, max_chars: int = 6000) -> str:
    if context.is_empty:
        return "No matching information was found."

    header = [f"Store: {context.store.name}"]
    description = _clean(context.store.description)
    if description:
        header.append(f"About the store: {description[:300]}")
    sections = ["\n".join(header)]
    if _has_conflicting_information(context):
        sections.append(
            "Data quality notice: matching store records contain conflicting values. "
            "Do not choose one value; explain the uncertainty."
        )
    sections.append("Relevant store information (highest relevance first):")

    blocks: list[str] = []
    for match in context.matches:
        record = match.record
        if isinstance(record, FAQ):
            blocks.append(f"SOURCE: FAQ\nQ: {record.question}\nA: {record.answer}")
        elif isinstance(record, KnowledgeBaseEntry):
            content = " … ".join(match.passages) if match.passages else record.content
            blocks.append(f"SOURCE: KNOWLEDGE_BASE\nTitle: {record.title}\nContent: {content}")
        else:
            blocks.append(f"SOURCE: PRODUCT\n{format_product_line(record)}")

    text = "\n\n".join(sections)
    for position, block in enumerate(blocks):
        candidate = f"{text}\n\n{block}"
        if position > 0 and len(candidate) > max_chars:
            break
        text = candidate
    return text
