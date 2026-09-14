"""add faq and knowledge base models

Revision ID: 8cbb7b5c0d26
Revises: 1c4d8a7b2e91
Create Date: 2026-09-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8cbb7b5c0d26"
down_revision: Union[str, Sequence[str], None] = "1c4d8a7b2e91"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "faqs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question", sa.String(length=500), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_faqs_is_active"), "faqs", ["is_active"], unique=False)
    op.create_index(op.f("ix_faqs_store_id"), "faqs", ["store_id"], unique=False)

    op.create_table(
        "knowledge_base_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_knowledge_base_entries_is_active"), "knowledge_base_entries", ["is_active"], unique=False)
    op.create_index(op.f("ix_knowledge_base_entries_store_id"), "knowledge_base_entries", ["store_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_knowledge_base_entries_store_id"), table_name="knowledge_base_entries")
    op.drop_index(op.f("ix_knowledge_base_entries_is_active"), table_name="knowledge_base_entries")
    op.drop_table("knowledge_base_entries")

    op.drop_index(op.f("ix_faqs_store_id"), table_name="faqs")
    op.drop_index(op.f("ix_faqs_is_active"), table_name="faqs")
    op.drop_table("faqs")
