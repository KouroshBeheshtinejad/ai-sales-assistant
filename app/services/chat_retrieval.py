from dataclasses import dataclass
import re

from sqlalchemy.orm import Session

from app.db.models import FAQ, KnowledgeBaseEntry, Product, Store


MAX_RESULTS_PER_SOURCE = 3
STOP_WORDS = {
    "a", "an", "and", "are", "about", "do", "does", "for", "how", "i",
    "is", "it", "of", "on", "or", "the", "this", "to", "what", "you",
    "آیا", "است", "این", "با", "برای", "چه", "چطور", "چگونه", "در", "را",
    "درباره", "دارید", "من", "و", "یا", "یک", "اطلاعات", "می", "شود",
}


@dataclass(frozen=True)
class RetrievedContext:
    store: Store
    faqs: list[FAQ]
    knowledge_entries: list[KnowledgeBaseEntry]
    products: list[Product]

    @property
    def is_empty(self) -> bool:
        return not (self.faqs or self.knowledge_entries or self.products)


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[\w]+", value.casefold())
        if len(token) > 1 and token not in STOP_WORDS
    }


def _rank(records, query: str, fields: tuple[str, ...]):
    query_tokens = _tokens(query)
    ranked = []
    for record in records:
        searchable = " ".join(str(getattr(record, field) or "") for field in fields)
        score = len(query_tokens & _tokens(searchable))
        if score:
            ranked.append((score, record))
    ranked.sort(key=lambda item: (-item[0], item[1].id))
    return [record for _, record in ranked[:MAX_RESULTS_PER_SOURCE]]


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

    return RetrievedContext(
        store=store,
        faqs=_rank(faqs, question, ("question", "answer")),
        knowledge_entries=_rank(knowledge_entries, question, ("title", "content")),
        products=_rank(products, question, ("name", "description")),
    )


def format_context(context: RetrievedContext, max_chars: int = 5000) -> str:
    if context.is_empty:
        return "No matching information was found."

    sections = [f"Store: {context.store.name}"]
    if context.faqs:
        sections.append(
            "FAQs:\n" + "\n".join(
                f"- Q: {faq.question}\n  A: {faq.answer}" for faq in context.faqs
            )
        )
    if context.knowledge_entries:
        sections.append(
            "Knowledge base:\n" + "\n".join(
                f"- {entry.title}: {entry.content}"
                for entry in context.knowledge_entries
            )
        )
    if context.products:
        sections.append(
            "Products:\n" + "\n".join(
                f"- {product.name}: {product.description or 'No description'}; "
                f"price={product.price}; stock={product.stock}"
                for product in context.products
            )
        )
    return "\n\n".join(sections)[:max_chars]
