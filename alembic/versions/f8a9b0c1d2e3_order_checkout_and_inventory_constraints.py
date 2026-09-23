"""scope order checkout attempts and enforce inventory invariants

Revision ID: f8a9b0c1d2e3
Revises: 2b3c4d5e6f7a
"""

from alembic import op
import sqlalchemy as sa


revision = "f8a9b0c1d2e3"
down_revision = "2b3c4d5e6f7a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_constraint("uq_orders_idempotency_key", type_="unique")
        batch_op.create_unique_constraint(
            "uq_orders_scoped_idempotency",
            ["store_id", "user_id", "guest_token", "idempotency_key"],
        )
    with op.batch_alter_table("conversations") as batch_op:
        batch_op.add_column(sa.Column("checkout_idempotency_key", sa.String(128), nullable=True))
    with op.batch_alter_table("products") as batch_op:
        batch_op.create_check_constraint("ck_products_stock_nonnegative", "stock >= 0")
        batch_op.create_check_constraint(
            "ck_products_reserved_stock_nonnegative",
            "reserved_stock >= 0",
        )


def downgrade() -> None:
    with op.batch_alter_table("products") as batch_op:
        batch_op.drop_constraint("ck_products_reserved_stock_nonnegative", type_="check")
        batch_op.drop_constraint("ck_products_stock_nonnegative", type_="check")
    with op.batch_alter_table("conversations") as batch_op:
        batch_op.drop_column("checkout_idempotency_key")
    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_constraint("uq_orders_scoped_idempotency", type_="unique")
        batch_op.create_unique_constraint("uq_orders_idempotency_key", ["idempotency_key"])