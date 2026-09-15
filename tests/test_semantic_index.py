from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import models
from app.db.database import Base
from app.services import semantic_index


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class FixedEmbeddingProvider:
    dimension = 384

    @staticmethod
    def _vector():
        return [1.0] + [0.0] * 383

    def embed_query(self, text):
        return self._vector()

    def embed_documents(self, texts):
        return [self._vector() for _ in texts]


def test_backfill_indexes_existing_records_and_removes_orphans(monkeypatch):
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        monkeypatch.setenv("AI_RAG_ENABLED", "true")
        monkeypatch.setattr(
            semantic_index,
            "get_embedding_provider",
            lambda: FixedEmbeddingProvider(),
        )

        user = models.User(email="rag-owner@example.com", password_hash="hash")
        db.add(user)
        db.flush()
        store = models.Store(name="RAG Store", owner_id=user.id)
        db.add(store)
        db.flush()
        active_faq = models.FAQ(
            store_id=store.id,
            question="What is shipping?",
            answer="Two days.",
            is_active=True,
        )
        inactive_faq = models.FAQ(
            store_id=store.id,
            question="Hidden question",
            answer="Hidden answer.",
            is_active=False,
        )
        db.add_all([active_faq, inactive_faq])
        db.flush()
        db.add(
            models.SemanticDocument(
                store_id=store.id,
                source_type=semantic_index.SOURCE_FAQ,
                source_id=999,
                content_hash="orphan",
                embedding=FixedEmbeddingProvider._vector(),
                is_active=True,
            )
        )
        db.commit()

        assert semantic_index.backfill_semantic_index(db) == 1
        documents = db.query(models.SemanticDocument).all()
        assert len(documents) == 1
        assert documents[0].source_id == active_faq.id

        matches = semantic_index.retrieve_semantic_matches(db, store.id, "shipping")
        assert [(match.source_type, match.source_id) for match in matches] == [
            (semantic_index.SOURCE_FAQ, active_faq.id)
        ]
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)