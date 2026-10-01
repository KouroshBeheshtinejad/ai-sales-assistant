from sqlalchemy.orm import Session

from app.db.models import FAQ, KnowledgeBaseEntry, Store, User


def get_store_or_404(db: Session, store_id: int, user_id: int):
    user = db.get(User, user_id)
    filters = [Store.id == store_id]
    if user is None or user.role != "god":
        filters.append(Store.owner_id == user_id)
    store = db.query(Store).filter(*filters).first()
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
