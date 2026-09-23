from dataclasses import dataclass, field
import logging
import re
import unicodedata
from typing import Literal

from sqlalchemy.orm import Session

from app.db.models import FAQ, KnowledgeBaseEntry, Product, Store
from app.services.semantic_index import (
    SOURCE_FAQ,
    SOURCE_KNOWLEDGE_BASE,
    SOURCE_PRODUCT,
    get_rag_settings,
    retrieve_semantic_matches,
)


MAX_RESULTS_PER_SOURCE = 3
MAX_CONTEXT_RESULTS = 5
logger = logging.getLogger(__name__)
STOP_WORDS = {
    "a", "an", "and", "are", "about", "do", "does", "for", "how", "i",
    "is", "it", "of", "on", "or", "the", "this", "to", "what", "you",
    "from", "all", "previous", "ignore", "reveal", "data", "rules", "weather",
    "آیا", "است", "این", "با", "برای", "چه", "چطور", "چگونه", "در", "را",
    "درباره", "دارید", "من", "و", "یا", "یک", "اطلاعات", "می", "شود",
}


# Keep the original text on every model for display, but normalize a separate
# copy for matching.  These variants are common when Persian is entered from
# different keyboards or copied from another application.
_PERSIAN_TRANSLATION = str.maketrans(
    {
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "ة": "ه",
        "ۀ": "ه",
        "ؤ": "و",
        "أ": "ا",
        "إ": "ا",
        "ـ": "",
        "\u200c": " ",
        "\u200f": " ",
        "\u200e": " ",
        "۰": "0",
        "۱": "1",
        "۲": "2",
        "۳": "3",
        "۴": "4",
        "۵": "5",
        "۶": "6",
        "۷": "7",
        "۸": "8",
        "۹": "9",
        "٠": "0",
        "١": "1",
        "٢": "2",
        "٣": "3",
        "٤": "4",
        "٥": "5",
        "٦": "6",
        "٧": "7",
        "٨": "8",
        "٩": "9",
    }
)
_ARABIC_DIACRITICS = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670]")
_TOKEN_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)

# This is deliberately a small, store-domain vocabulary rather than a general
# semantic search system.  The synthetic tokens make common alternate wording
# match while preserving a transparent, deterministic ranking algorithm.
_CONCEPT_ALIASES = {
    "delivery": frozenset(
        {
            "delivery", "deliver", "shipping", "ship", "ارسال", "تحویل", "پست",
            "فرستادن", "فرستاده", "میفرستید", "میفرستین",
        }
    ),
    "return": frozenset(
        {
            "return", "returns", "returning", "refund", "refunded", "مرجوع",
            "مرجوعی", "بازگشت", "بازگرداندن", "پسدادن", "تعویض", "استرداد",
        }
    ),
    "price": frozenset(
        {"price", "prices", "pricing", "cost", "costs", "قیمت", "هزینه", "بها"}
    ),
    "stock": frozenset(
        {
            "stock", "availability", "available", "inventory", "موجود", "موجودی",
            "ناموجود", "دردسترس",
        }
    ),
}

_GENERIC_PRODUCT_CONCEPTS = {
    "__concept_price",
    "__concept_stock",
}
_GENERIC_PRODUCT_QUERY_TOKENS = frozenset(
    _GENERIC_PRODUCT_CONCEPTS
    | _CONCEPT_ALIASES["price"]
    | _CONCEPT_ALIASES["stock"]
)

_CONCEPT_PHRASES = {
    "delivery": ("می فرستید", "ارسال می کنید", "تحویل می دهید"),
    "return": ("پس دادن", "پس بدهم", "پس بدم", "برگردانم", "برگرداندن کالا"),
}
_RECOMMENDATION_TERMS = ("پیشنهاد", "recommend", "recommendation", "suggest", "best")


def normalize_for_search(value: str) -> str:
    """Return a comparison-only version of text without changing stored text."""
    normalized = unicodedata.normalize("NFKC", value).translate(_PERSIAN_TRANSLATION)
    normalized = _ARABIC_DIACRITICS.sub("", normalized)
    return normalized.casefold()


@dataclass(frozen=True)
class RetrievedMatch:
    source_type: Literal["faq", "knowledge_base", "product"]
    record: FAQ | KnowledgeBaseEntry | Product
    lexical_score: float
    semantic_score: float
    hybrid_score: float


@dataclass(frozen=True)
class RetrievedContext:
    store: Store
    faqs: list[FAQ]
    knowledge_entries: list[KnowledgeBaseEntry]
    products: list[Product]
    matches: list[RetrievedMatch] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (self.faqs or self.knowledge_entries or self.products)


def _tokens(value: str) -> set[str]:
    normalized = normalize_for_search(value)
    raw_tokens = set(_TOKEN_PATTERN.findall(normalized))
    lexical_tokens = {
        form
        for token in raw_tokens
        for form in _token_forms(token)
        if len(form) > 1 and form not in STOP_WORDS
    }
    concepts = {
        f"__concept_{name}"
        for name, aliases in _CONCEPT_ALIASES.items()
        if lexical_tokens & aliases
        or any(phrase in normalized for phrase in _CONCEPT_PHRASES.get(name, ()))
    }
    return lexical_tokens | concepts


def _token_forms(token: str) -> set[str]:
    """Add only common Persian inflection forms needed for word matching."""
    forms = {token}
    if len(token) > 4 and token.endswith("های"):
        forms.add(token[:-3])
    elif len(token) > 3 and token.endswith("ها"):
        forms.add(token[:-2])
    elif len(token) > 4 and token.endswith("ی"):
        forms.add(token[:-1])
    return forms


def _lexical_tokens(value: str) -> set[str]:
    return {token for token in _tokens(value) if not token.startswith("__concept_")}


def _searchable_text(record, fields: tuple[str, ...]) -> str:
    values = [str(getattr(record, field) or "") for field in fields]
    if isinstance(record, Product):
        # Product price and stock are database fields, not free text.  Adding
        # their labels lets a direct question such as "موجودی دارید؟" find
        # products while the formatted context still supplies the real values.
        values.extend(("price قیمت", "stock موجودی"))
    return " ".join(values)


def _lexical_score(record, query: str, fields: tuple[str, ...]) -> tuple[float, set[str]]:
    query_tokens = _tokens(query)
    record_tokens = _tokens(_searchable_text(record, fields))
    matches = query_tokens & record_tokens
    direct_matches = {token for token in matches if not token.startswith("__concept_")}
    concept_matches = matches - direct_matches
    score = len(direct_matches) + (2 * len(concept_matches))
    if isinstance(record, Product):
        name_matches = _lexical_tokens(query) & _lexical_tokens(record.name)
        # Exact product/model words should outrank generic policy records.
        if len(name_matches) >= 2:
            score += 4
    return float(score), matches


def _is_recommendation_query(question: str) -> bool:
    normalized_question = normalize_for_search(question)
    return any(term in normalized_question for term in _RECOMMENDATION_TERMS)


def _has_sufficient_lexical_match(
    matched_tokens: set[str], question: str, lexical_candidates: dict[tuple[str, int], object]
) -> bool:
    """Reject one-word incidental matches while preserving explicit recommendations."""
    if any(token.startswith("__concept_") for token in matched_tokens):
        return True
    matched_lexical_tokens = {
        token for token in matched_tokens if not token.startswith("__concept_")
    }
    if len(_lexical_tokens(question)) <= 2:
        return bool(matched_lexical_tokens)
    if len(matched_lexical_tokens) >= 2:
        return True
    return _is_recommendation_query(question) and any(
        source_type == SOURCE_PRODUCT for source_type, _ in lexical_candidates
    )


def _has_conflicting_information(context: RetrievedContext) -> bool:
    """Detect exact duplicate subjects with different active values.

    This intentionally catches only objective duplicate-record conflicts.  The
    model still receives all selected records and is instructed not to invent a
    resolution for subtler contradictions.
    """
    groups = (
        (context.faqs, "question", "answer"),
        (context.knowledge_entries, "title", "content"),
        (context.products, "name", "price"),
    )
    for records, key_field, value_field in groups:
        values_by_key: dict[str, set[str]] = {}
        for record in records:
            key = normalize_for_search(str(getattr(record, key_field) or ""))
            if isinstance(record, Product):
                value = f"{record.price}|{record.stock - record.reserved_stock}"
            else:
                value = str(getattr(record, value_field) or "").strip()
            values_by_key.setdefault(key, set()).add(value)
        if any(len(values) > 1 for values in values_by_key.values()):
            return True
    return False

def _filter_weak_product_candidates(
    candidates: dict[tuple[str, int], tuple[float, set[str]]],
    query_tokens: set[str],
    records_by_key: dict[tuple[str, int], object],
) -> dict[tuple[str, int], tuple[float, set[str]]]:
    """
    Prevent generic price/stock concepts from making unrelated products
    eligible for retrieval.
    """
    filtered: dict[tuple[str, int], tuple[float, set[str]]] = {}

    meaningful_query_tokens = query_tokens - _GENERIC_PRODUCT_QUERY_TOKENS

    for key, (score, matched_tokens) in candidates.items():
        record = records_by_key.get(key)

        if not isinstance(record, Product):
            filtered[key] = (score, matched_tokens)
            continue

        product_text = " ".join(
            str(value)
            for value in (
                getattr(record, "name", ""),
                getattr(record, "description", ""),
            )
            if value
        )

        product_tokens = _tokens(product_text)

        if meaningful_query_tokens & product_tokens:
            filtered[key] = (score, matched_tokens)

    return filtered


def _filter_semantic_product_candidates(
    candidates: dict[tuple[str, int], float],
    query_tokens: set[str],
    records_by_key: dict[tuple[str, int], object],
) -> dict[tuple[str, int], float]:
    """
    Prevent unrelated products from entering the final context through
    semantic retrieval alone.

    FAQ and Knowledge Base semantic retrieval remain unaffected.
    """
    filtered: dict[tuple[str, int], float] = {}
    meaningful_query_tokens = query_tokens - _GENERIC_PRODUCT_QUERY_TOKENS

    for key, score in candidates.items():
        record = records_by_key.get(key)
        if record is None:
            continue
        if not isinstance(record, Product):
            filtered[key] = score
            continue

        product_tokens = _tokens(
            " ".join(
                str(value)
                for value in (
                    getattr(record, "name", ""),
                    getattr(record, "description", ""),
                )
                if value
            )
        )

        if meaningful_query_tokens & product_tokens:
            filtered[key] = score

    return filtered

def retrieve_store_context(db: Session, store_id: int, question: str) -> RetrievedContext | None:
    store = db.query(Store).filter(Store.id == store_id).first()
    if store is None:
        return None

    faqs = (
        db.query(FAQ)
        .filter(FAQ.store_id == store_id, FAQ.is_active.is_(True))
        .all()
    )

    knowledge_entries = (
        db.query(KnowledgeBaseEntry)
        .filter(
            KnowledgeBaseEntry.store_id == store_id,
            KnowledgeBaseEntry.is_active.is_(True),
        )
        .all()
    )

    products = (
        db.query(Product)
        .filter(Product.store_id == store_id, Product.is_active.is_(True))
        .all()
    )

    records_by_source = (
        (SOURCE_FAQ, faqs, ("question", "answer")),
        (SOURCE_KNOWLEDGE_BASE, knowledge_entries, ("title", "content")),
        (SOURCE_PRODUCT, products, ("name", "description")),
    )

    records_by_key = {
        (source_type, record.id): record
        for source_type, records, _ in records_by_source
        for record in records
    }

    # Normalize/tokenize the query once and reuse it for
    # lexical and semantic product relevance checks.
    query_tokens = _tokens(question)

    # ---------------------------------------------------------
    # Lexical retrieval
    # ---------------------------------------------------------

    lexical_candidates: dict[
        tuple[str, int],
        tuple[float, set[str]],
    ] = {}

    matched_tokens: set[str] = set()

    for source_type, records, fields in records_by_source:
        ranked_records = []

        for record in records:
            score, record_matches = _lexical_score(
                record,
                question,
                fields,
            )

            if score:
                ranked_records.append(
                    (score, record, record_matches)
                )

        ranked_records.sort(
            key=lambda item: (-item[0], item[1].id)
        )

        for score, record, record_matches in ranked_records[
            : get_rag_settings().lexical_top_k
        ]:
            lexical_candidates[
                (source_type, record.id)
            ] = (
                score,
                record_matches,
            )

    # ---------------------------------------------------------
    # Product relevance gate
    #
    # Prevent:
    # "قیمت بیت کوین چنده؟"
    #
    # from retrieving:
    # "لپ تاپ تستی"
    #
    # merely because all products contain generic price/stock
    # concepts.
    # ---------------------------------------------------------

    lexical_candidates = _filter_weak_product_candidates(
        lexical_candidates,
        query_tokens,
        records_by_key,
    )

    # Rebuild matched_tokens ONLY from the filtered candidates.
    # This prevents an unrelated product from making lexical
    # retrieval globally "sufficient".
    for _, record_matches in lexical_candidates.values():
        matched_tokens.update(record_matches)

    lexical_is_sufficient = _has_sufficient_lexical_match(
        matched_tokens,
        question,
        lexical_candidates,
    )

    # ---------------------------------------------------------
    # Semantic retrieval
    # ---------------------------------------------------------

    semantic_candidates = {
        (match.source_type, match.source_id): match.similarity
        for match in retrieve_semantic_matches(
            db,
            store_id,
            question,
        )
        if (match.source_type, match.source_id) in records_by_key
    }

    # Do not allow an unrelated product to enter context through
    # semantic retrieval alone.
    #
    # FAQ and Knowledge Base semantic matches are unaffected.
    semantic_candidates = _filter_semantic_product_candidates(
        semantic_candidates,
        query_tokens,
        records_by_key,
    )

    # ---------------------------------------------------------
    # If lexical retrieval is not sufficiently grounded,
    # discard lexical candidates.
    # ---------------------------------------------------------

    if not lexical_is_sufficient:
        lexical_candidates = {}

    # ---------------------------------------------------------
    # Hybrid ranking
    # ---------------------------------------------------------

    settings = get_rag_settings()

    candidate_keys = (
        set(lexical_candidates)
        | set(semantic_candidates)
    )

    max_lexical_score = max(
        (
            score
            for score, _ in lexical_candidates.values()
        ),
        default=1.0,
    )

    ranked_matches: list[RetrievedMatch] = []

    for source_type, source_id in candidate_keys:
        record = records_by_key[
            (source_type, source_id)
        ]

        lexical_score = lexical_candidates.get(
            (source_type, source_id),
            (0.0, set()),
        )[0]

        semantic_score = semantic_candidates.get(
            (source_type, source_id),
            0.0,
        )

        hybrid_score = (
            settings.lexical_weight
            * (lexical_score / max_lexical_score)
            + settings.semantic_weight
            * semantic_score
        )

        ranked_matches.append(
            RetrievedMatch(
                source_type=source_type,
                record=record,
                lexical_score=lexical_score,
                semantic_score=semantic_score,
                hybrid_score=hybrid_score,
            )
        )

    ranked_matches.sort(
        key=lambda match: (
            -match.hybrid_score,
            -match.lexical_score,
            match.record.id,
        )
    )

    # ---------------------------------------------------------
    # Limit final context
    # ---------------------------------------------------------

    selected_matches: list[RetrievedMatch] = []
    source_counts: dict[str, int] = {}

    for match in ranked_matches:
        if (
            source_counts.get(match.source_type, 0)
            >= MAX_RESULTS_PER_SOURCE
        ):
            continue

        selected_matches.append(match)

        source_counts[match.source_type] = (
            source_counts.get(match.source_type, 0) + 1
        )

        if len(selected_matches) == MAX_CONTEXT_RESULTS:
            break

    logger.debug(
        "Hybrid retrieval store_id=%s lexical_candidates=%s "
        "semantic_candidates=%s final_candidates=%s",
        store_id,
        len(lexical_candidates),
        len(semantic_candidates),
        len(selected_matches),
    )

    return RetrievedContext(
        store=store,
        faqs=[
            match.record
            for match in selected_matches
            if isinstance(match.record, FAQ)
        ],
        knowledge_entries=[
            match.record
            for match in selected_matches
            if isinstance(match.record, KnowledgeBaseEntry)
        ],
        products=[
            match.record
            for match in selected_matches
            if isinstance(match.record, Product)
        ],
        matches=selected_matches,
    )


def format_context(context: RetrievedContext, max_chars: int = 5000) -> str:
    if context.is_empty:
        return "No matching information was found."

    sections = [f"Store: {context.store.name}"]
    if _has_conflicting_information(context):
        sections.append(
            "Data quality notice: matching store records contain conflicting values. "
            "Do not choose one value; explain the uncertainty."
        )
    sections.append("Relevant store information (highest relevance first):")
    for match in context.matches:
        if isinstance(match.record, FAQ):
            sections.append(
                f"SOURCE: FAQ\nQ: {match.record.question}\nA: {match.record.answer}"
            )
        elif isinstance(match.record, KnowledgeBaseEntry):
            sections.append(
                f"SOURCE: KNOWLEDGE_BASE\nTitle: {match.record.title}\n"
                f"Content: {match.record.content}"
            )
        else:
            sections.append(
                f"SOURCE: PRODUCT\n- {match.record.name}: "
                f"{match.record.description or 'No description'}; "
                f"price={match.record.price}; stock={match.record.stock - match.record.reserved_stock}"
            )
    return "\n\n".join(sections)[:max_chars]
