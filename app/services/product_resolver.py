"""Resolve which product a customer is talking about.

Used by the commerce flow (add to cart) and by retrieval (follow-up questions
such as «قیمتش چنده؟»).  Matching is typo tolerant and understands ordinals
(«اولین محصول»), colour/size hints and conversation history.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

from app.db.models import Product
from app.services.sales_intent import extract_ordinal
from app.services.text_utils import (
    content_tokens,
    edit_ratio,
    normalize_text,
    split_sentences,
    split_tokens,
)

STRONG_SCORE = 8.0


@dataclass(frozen=True)
class ProductMatch:
    product: Product
    score: float
    coverage: float


@dataclass
class Resolution:
    product: Product | None = None
    candidates: list[Product] = field(default_factory=list)
    source: str = "none"  # question | history | ordinal | none

    @property
    def ambiguous(self) -> bool:
        return self.product is None and len(self.candidates) > 1


def _product_tokens(product: Product) -> list[str]:
    return content_tokens(product.name or "")


def _extra_tokens(product: Product) -> set[str]:
    values = [product.color or "", product.size or ""]
    attrs = product.attributes or {}
    if isinstance(attrs, dict):
        values.extend(str(value) for value in attrs.values() if isinstance(value, (str, int, float)))
    return set(content_tokens(" ".join(values)))


def score_product(query_tokens: Sequence[str], text_norm: str, product: Product) -> ProductMatch | None:
    name_norm = normalize_text(product.name or "")
    if not name_norm:
        return None
    if name_norm in text_norm:
        return ProductMatch(product, 100.0, 1.0)
    name_tokens = _product_tokens(product)
    if not name_tokens:
        return None
    query_set = set(query_tokens)
    matched = 0
    for token in name_tokens:
        if token in query_set:
            matched += 1
        elif len(token) >= 4 and any(len(q) >= 4 and edit_ratio(token, q) >= 0.82 for q in query_set):
            matched += 0.85
    if matched == 0:
        return None
    coverage = matched / len(name_tokens)
    score = coverage * 8 + matched
    extras = _extra_tokens(product)
    score += 1.5 * len(extras & query_set)
    return ProductMatch(product, score, coverage)


def match_products(text: str, products: Iterable[Product]) -> list[ProductMatch]:
    """Rank products by how well *text* refers to them (best first)."""
    text_norm = normalize_text(text)
    query_tokens = content_tokens(text)
    matches = []
    for product in products:
        match = score_product(query_tokens, text_norm, product)
        if match is None:
            continue
        # A single shared word out of a long product name is not a reference.
        name_len = len(_product_tokens(product))
        if match.score < 100 and name_len >= 3 and match.coverage < 0.5:
            continue
        matches.append(match)
    matches.sort(key=lambda item: (-item.score, item.product.id))
    return matches


def _pick(matches: list[ProductMatch]) -> Resolution:
    if not matches:
        return Resolution()
    top = matches[0]
    ties = [m for m in matches if abs(m.score - top.score) < 0.5]
    if len(ties) > 1:
        return Resolution(candidates=[m.product for m in ties][:5], source="question")
    return Resolution(product=top.product, candidates=[top.product], source="question")


def products_mentioned_in(text: str, products: Sequence[Product]) -> list[Product]:
    """Products explicitly named (strong match) in one message."""
    return [m.product for m in match_products(text, products) if m.score >= STRONG_SCORE or m.coverage >= 0.99]


def focus_from_history(
    history: Sequence[dict[str, str]] | None,
    products: Sequence[Product],
    *,
    window: int = 10,
) -> Resolution:
    """Most recent unambiguous product mentioned in the conversation."""
    if not history:
        return Resolution()
    for message in reversed(list(history)[-window:]):
        content = message.get("content") or ""
        if not content:
            continue
        mentioned = products_mentioned_in(content, products)
        if message.get("role") == "assistant" and len(mentioned) > 1:
            # The assistant listed several products: no single one is in focus.
            continue
        if len(mentioned) >= 1:
            ties = mentioned[:1] if message.get("role") == "user" or len(mentioned) == 1 else []
            if ties:
                return Resolution(product=ties[0], candidates=[ties[0]], source="history")
    return Resolution()


def resolve_product_reference(
    question: str,
    products: Sequence[Product],
    history: Sequence[dict[str, str]] | None = None,
) -> Resolution:
    """Resolve the product the customer means right now."""
    if not products:
        return Resolution()

    ordinal = extract_ordinal(question)
    noun_tokens = set(split_tokens(question))
    if ordinal is not None and not (
        noun_tokens & {"محصول", "کالا", "مورد", "گزینه", "product", "item", "one", "option", "اولی", "دومی", "سومی", "آخری"}
    ):
        ordinal = None
    from_question = _pick(match_products(question, products))
    if from_question.product is not None or from_question.ambiguous:
        return from_question

    if ordinal is not None:
        ordered = sorted(products, key=lambda item: item.id)
        index = ordinal - 1 if ordinal > 0 else len(ordered) - 1
        if 0 <= index < len(ordered):
            return Resolution(product=ordered[index], candidates=[ordered[index]], source="ordinal")

    return focus_from_history(history, products)


def sentences_with(text: str, tokens: set[str]) -> list[str]:
    return [s for s in split_sentences(text) if tokens & set(content_tokens(s))]
