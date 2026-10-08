"""add store review table

Revision ID: c8f1c2d3e4a5
Revises: a7b8c9d0e1f2
"""

from alembic import op
import sqlalchemy as sa


revision = "c8f1c2d3e4a5"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "store_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("store_reviews.id", ondelete="CASCADE"), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=True),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("is_approved", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "store_id", name="uq_store_review_user_store"),
        sa.UniqueConstraint("user_id", "product_id", name="uq_store_product_review_user_product"),
    )
    op.create_index("ix_store_reviews_user_id", "store_reviews", ["user_id"])
    op.create_index("ix_store_reviews_store_id", "store_reviews", ["store_id"])
    op.create_index("ix_store_reviews_product_id", "store_reviews", ["product_id"])
    op.create_index("ix_store_reviews_order_id", "store_reviews", ["order_id"])
    op.create_index("ix_store_reviews_parent_id", "store_reviews", ["parent_id"])
    op.create_index("ix_store_reviews_store_created", "store_reviews", ["store_id", "created_at"])
    op.create_index("ix_store_reviews_product_created", "store_reviews", ["product_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_store_reviews_product_created", table_name="store_reviews")
    op.drop_index("ix_store_reviews_store_created", table_name="store_reviews")
    op.drop_index("ix_store_reviews_parent_id", table_name="store_reviews")
    op.drop_index("ix_store_reviews_order_id", table_name="store_reviews")
    op.drop_index("ix_store_reviews_product_id", table_name="store_reviews")
    op.drop_index("ix_store_reviews_store_id", table_name="store_reviews")
    op.drop_index("ix_store_reviews_user_id", table_name="store_reviews")
    op.drop_table("store_reviews")
