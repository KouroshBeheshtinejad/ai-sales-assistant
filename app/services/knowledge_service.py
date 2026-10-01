from sqlalchemy.orm import Session

from app.db.models import FAQ, KnowledgeBaseEntry, Store, User
from app.security.policies import has_store_permission


def get_store_or_404(
    db: Session,
    store_id: int,
    user_id: int,
    permission: str = "store.read",
):
    user = db.get(User, user_id)
    if user is None or not has_store_permission(db, user, store_id, permission):
        raise ValueError("Store not found")
    return db.get(Store, store_id)


def get_faq_for_store_or_404(
    db: Session,
    store_id: int,
    faq_id: int,
    user_id: int,
    permission: str = "faq.read",
) -> FAQ:
    get_store_or_404(db, store_id, user_id, permission)
    faq = (
        db.query(FAQ)
        .filter(
            FAQ.id == faq_id,
            FAQ.store_id == store_id,
        )
        .first()
    )
    if faq is None:
        raise ValueError("FAQ not found")
    return faq


def get_knowledge_for_store_or_404(
    db: Session,
    store_id: int,
    knowledge_id: int,
    user_id: int,
    permission: str = "knowledge.read",
) -> KnowledgeBaseEntry:
    get_store_or_404(db, store_id, user_id, permission)
    entry = (
        db.query(KnowledgeBaseEntry)
        .filter(
            KnowledgeBaseEntry.id == knowledge_id,
            KnowledgeBaseEntry.store_id == store_id,
        )
        .first()
    )
    if entry is None:
        raise ValueError("Knowledge entry not found")
    return entry
