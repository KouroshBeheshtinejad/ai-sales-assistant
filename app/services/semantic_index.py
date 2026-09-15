"""Storage, synchronization, and retrieval for optional pgvector documents."""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import FAQ, KnowledgeBaseEntry, Product, SemanticDocument
from app.services.embedding_provider import (
    EmbeddingProviderError,
    get_embedding_provider,
    rag_is_enabled,
)


logger = logging.getLogger(__name__)

SOURCE_FAQ = "faq"
SOURCE_KNOWLEDGE_BASE = "knowledge_base"
SOURCE_PRODUCT = "product"
SourceType = Literal["faq", "knowledge_base", "product"]


@dataclass(frozen=True)
class RagSettings:
    enabled: bool
    lexical_top_k: int
    semantic_top_k: int
    semantic_threshold: float
    lexical_weight: float
    semantic_weight: float


@dataclass(frozen=True)
class SemanticMatch:
    source_type: SourceType
    source_id: int
    similarity: float


def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return max(minimum, min(maximum, value))


def _bounded_float(name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        return default
    return max(minimum, min(maximum, value))


def get_rag_settings() -> RagSettings:
    lexical_weight = _bounded_float("AI_RAG_LEXICAL_WEIGHT", 0.70, 0.0, 1.0)
    semantic_weight = _bounded_float("AI_RAG_SEMANTIC_WEIGHT", 0.30, 0.0, 1.0)
    total_weight = lexical_weight + semantic_weight
    if total_weight == 0:
        lexical_weight, semantic_weight = 0.70, 0.30
        total_weight = 1.0
    return RagSettings(
        enabled=rag_is_enabled(),
        lexical_top_k=_bounded_int("AI_RAG_LEXICAL_TOP_K", 3, 1, 10),
        semantic_top_k=_bounded_int("AI_RAG_SEMANTIC_TOP_K", 3, 1, 10),
        semantic_threshold=_bounded_float("AI_RAG_SEMANTIC_THRESHOLD", 0.72, -1.0, 1.0),
        lexical_weight=lexical_weight / total_weight,
        semantic_weight=semantic_weight / total_weight,
    )


def source_type_for(record: FAQ | KnowledgeBaseEntry | Product) -> SourceType:
    if isinstance(record, FAQ):
        return SOURCE_FAQ
    if isinstance(record, KnowledgeBaseEntry):
        return SOURCE_KNOWLEDGE_BASE
    if isinstance(record, Product):
        return SOURCE_PRODUCT
    raise TypeError(f"Unsupported semantic document source: {type(record)!r}")


def build_document_content(record: FAQ | KnowledgeBaseEntry | Product) -> str:
    """Build semantic text without copying transactional price or stock into the index."""
    source_type = source_type_for(record)
    if source_type == SOURCE_FAQ:
        return f"FAQ\nQuestion: {record.question}\nAnswer: {record.answer}"
    if source_type == SOURCE_KNOWLEDGE_BASE:
        return f"Knowledge base\nTitle: {record.title}\nContent: {record.content}"
    attributes = json.dumps(record.attributes or {}, ensure_ascii=False, sort_keys=True)
    return (
        f"Product\nName: {record.name}\nDescription: {record.description or ''}\n"
        f"Size: {record.size or ''}\nColor: {record.color or ''}\nAttributes: {attributes}"
    )


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def discard_semantic_document(
    db: Session, source_type: SourceType, source_id: int, store_id: int
) -> None:
    """Remove an index entry inside the caller's transaction before source changes."""
    (
        db.query(SemanticDocument)
        .filter(
            SemanticDocument.store_id == store_id,
            SemanticDocument.source_type == source_type,
            SemanticDocument.source_id == source_id,
        )
        .delete(synchronize_session=False)
    )


def safely_discard_semantic_document(
    db: Session, source_type: SourceType, source_id: int, store_id: int
) -> bool:
    try:
        discard_semantic_document(db, source_type, source_id, store_id)
        return True
    except SQLAlchemyError as exc:
        db.rollback()
        logger.warning("Semantic document could not be discarded: %s", exc)
        return False


def sync_semantic_document(db: Session, record: FAQ | KnowledgeBaseEntry | Product) -> bool:
    """Synchronously replace one document, leaving lexical retrieval available on failure."""
    settings = get_rag_settings()
    if not settings.enabled:
        return False
    source_type = source_type_for(record)
    content = build_document_content(record)
    content_hash = _content_hash(content)
    existing = (
        db.query(SemanticDocument)
        .filter(
            SemanticDocument.store_id == record.store_id,
            SemanticDocument.source_type == source_type,
            SemanticDocument.source_id == record.id,
        )
        .one_or_none()
    )
    if existing and existing.content_hash == content_hash and existing.is_active == record.is_active:
        return False

    if existing:
        db.delete(existing)
        db.flush()
    if not record.is_active:
        db.commit()
        return False

    try:
        embedding = get_embedding_provider().embed_documents([content])[0]
    except (EmbeddingProviderError, IndexError) as exc:
        # Any previous vector was removed before embedding so stale searchable
        # content cannot survive a failed update. Lexical retrieval still works.
        db.commit()
        logger.warning("Semantic document was not indexed: %s", exc)
        return False

    db.add(
        SemanticDocument(
            store_id=record.store_id,
            source_type=source_type,
            source_id=record.id,
            content_hash=content_hash,
            embedding=embedding,
            is_active=True,
        )
    )
    db.commit()
    return True


def safely_sync_semantic_document(db: Session, record: FAQ | KnowledgeBaseEntry | Product) -> bool:
    try:
        return sync_semantic_document(db, record)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.warning("Semantic document could not be synchronized: %s", exc)
        return False


def backfill_semantic_index(db: Session) -> int:
    """Index all existing records and remove documents with missing sources."""
    if not get_rag_settings().enabled:
        raise EmbeddingProviderError("Enable AI_RAG_ENABLED before running semantic backfill")

    records = [
        *db.query(FAQ).all(),
        *db.query(KnowledgeBaseEntry).all(),
        *db.query(Product).all(),
    ]
    expected_keys = {
        (source_type_for(record), record.store_id, record.id) for record in records
    }
    indexed_count = 0
    for record in records:
        indexed_count += int(safely_sync_semantic_document(db, record))

    stale_documents = [
        document
        for document in db.query(SemanticDocument).all()
        if (document.source_type, document.store_id, document.source_id) not in expected_keys
    ]
    for document in stale_documents:
        db.delete(document)
    if stale_documents:
        db.commit()
    return indexed_count


def _cosine_similarity(first: list[float], second: list[float]) -> float:
    numerator = sum(left * right for left, right in zip(first, second, strict=True))
    first_norm = math.sqrt(sum(value * value for value in first))
    second_norm = math.sqrt(sum(value * value for value in second))
    if not first_norm or not second_norm:
        return -1.0
    return numerator / (first_norm * second_norm)


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.10g}" for value in vector) + "]"


def _postgres_semantic_matches(
    db: Session,
    store_id: int,
    query_embedding: list[float],
    settings: RagSettings,
) -> list[SemanticMatch]:
    rows = db.execute(
        text(
            """
            SELECT source_type, source_id,
                   1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
            FROM semantic_documents
            WHERE store_id = :store_id AND is_active = true
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
            """
        ),
        {
            "embedding": _vector_literal(query_embedding),
            "store_id": store_id,
            "top_k": settings.semantic_top_k,
        },
    ).mappings()
    return [
        SemanticMatch(
            source_type=row["source_type"],
            source_id=row["source_id"],
            similarity=float(row["similarity"]),
        )
        for row in rows
        if float(row["similarity"]) >= settings.semantic_threshold
    ]


def _portable_semantic_matches(
    db: Session,
    store_id: int,
    query_embedding: list[float],
    settings: RagSettings,
) -> list[SemanticMatch]:
    matches = []
    documents = (
        db.query(SemanticDocument)
        .filter(SemanticDocument.store_id == store_id, SemanticDocument.is_active.is_(True))
        .all()
    )
    for document in documents:
        similarity = _cosine_similarity(query_embedding, document.embedding)
        if similarity >= settings.semantic_threshold:
            matches.append(
                SemanticMatch(
                    source_type=document.source_type,
                    source_id=document.source_id,
                    similarity=similarity,
                )
            )
    return sorted(matches, key=lambda item: item.similarity, reverse=True)[: settings.semantic_top_k]


def retrieve_semantic_matches(db: Session, store_id: int, question: str) -> list[SemanticMatch]:
    """Return scoped, thresholded semantic matches or an empty fallback result."""
    settings = get_rag_settings()
    if not settings.enabled:
        return []
    try:
        query_embedding = get_embedding_provider().embed_query(question)
        if db.bind is not None and db.bind.dialect.name == "postgresql":
            matches = _postgres_semantic_matches(db, store_id, query_embedding, settings)
        else:
            matches = _portable_semantic_matches(db, store_id, query_embedding, settings)
        logger.debug(
            "Semantic retrieval store_id=%s candidates=%s threshold=%s",
            store_id,
            len(matches),
            settings.semantic_threshold,
        )
        return matches
    except (EmbeddingProviderError, SQLAlchemyError, ValueError, TypeError) as exc:
        logger.warning("Semantic retrieval failed; falling back to lexical retrieval: %s", exc)
        return []


def main() -> None:
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        indexed_count = backfill_semantic_index(db)
        print(f"Indexed {indexed_count} semantic documents.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
