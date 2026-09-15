"""add semantic document vector index

Revision ID: c3a0b8d9e2f1
Revises: 8cbb7b5c0d26
Create Date: 2026-09-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3a0b8d9e2f1"
down_revision: Union[str, Sequence[str], None] = "8cbb7b5c0d26"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE TABLE semantic_documents (
            id SERIAL PRIMARY KEY,
            store_id INTEGER NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
            source_type VARCHAR(32) NOT NULL,
            source_id INTEGER NOT NULL,
            content_hash VARCHAR(64) NOT NULL,
            embedding vector(384) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP NOT NULL DEFAULT now(),
            CONSTRAINT uq_semantic_document_source
                UNIQUE (store_id, source_type, source_id)
        )
        """
    )
    op.create_index(
        "ix_semantic_documents_store_active",
        "semantic_documents",
        ["store_id", "is_active"],
        unique=False,
    )
    op.create_index(
        "ix_semantic_documents_source",
        "semantic_documents",
        ["source_type", "source_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_semantic_documents_source", table_name="semantic_documents")
    op.drop_index("ix_semantic_documents_store_active", table_name="semantic_documents")
    op.drop_table("semantic_documents")
    # The extension is intentionally retained because it can be shared by
    # independent migrations or manually managed database objects.
