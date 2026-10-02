"""add storefront categories and theme colors

Revision ID: d7e8f9a0b1c2
Revises: c6d7e8f9a0b1
Create Date: 2026-10-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d7e8f9a0b1c2"
down_revision: Union[str, Sequence[str], None] = "c6d7e8f9a0b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "stores",
        sa.Column("categories", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "stores",
        sa.Column("primary_color", sa.String(length=7), nullable=False, server_default="#0d8a85"),
    )
    op.add_column(
        "stores",
        sa.Column("secondary_color", sa.String(length=7), nullable=False, server_default="#f2f7f6"),
    )
    op.add_column(
        "products",
        sa.Column("category_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )


def downgrade() -> None:
    op.drop_column("products", "category_ids")
    op.drop_column("stores", "secondary_color")
    op.drop_column("stores", "primary_color")
    op.drop_column("stores", "categories")