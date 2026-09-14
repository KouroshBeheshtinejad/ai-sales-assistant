from sqlalchemy.orm import Session

from app.db.models import FAQ, KnowledgeBaseEntry, Store


def get_store_or_404(db: Session, store_id: int, user_id: int):
    store = (
        db.query(Store)
        .filter(
            Store.id == store_id,
            Store.owner_id == user_id,
        )
        .first()
    )
    if store is None:
        raise ValueError("Store not found")
    return store


def get_faq_for_store_or_404(db: Session, store_id: int, faq_id: int, user_id: int) -> FAQ:
    store = get_store_or_404(db, store_id, user_id)
    faq = (
        db.query(FAQ)
        .filter(
            FAQ.id == faq_id,
            FAQ.store_id == store.id,
        )
        .first()
    )
    if faq is None:
        raise ValueError("FAQ not found")
    return faq


def get_knowledge_for_store_or_404(db: Session, store_id: int, knowledge_id: int, user_id: int) -> KnowledgeBaseEntry:
    store = get_store_or_404(db, store_id, user_id)
    entry = (
        db.query(KnowledgeBaseEntry)
        .filter(
            KnowledgeBaseEntry.id == knowledge_id,
            KnowledgeBaseEntry.store_id == store.id,
        )
        .first()
    )
    if entry is None:
        raise ValueError("Knowledge entry not found")
    return entry
