"""add guest commerce identity

Revision ID: d4e7f6a1b2c3
Revises: 9d539be227e9
"""
from alembic import op
import sqlalchemy as sa

revision = "d4e7f6a1b2c3"
down_revision = "9d539be227e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("carts") as batch_op:
        batch_op.add_column(sa.Column("guest_token", sa.String(length=64), nullable=True))
        batch_op.create_index("ix_carts_guest_token", ["guest_token"], unique=False)
        batch_op.create_unique_constraint("uq_cart_guest_store", ["guest_token", "store_id"])
        batch_op.create_check_constraint(
            "ck_carts_identity",
            "(user_id IS NOT NULL) OR (guest_token IS NOT NULL)",
        )
        batch_op.alter_column("user_id", existing_type=sa.Integer(), nullable=True)

    with op.batch_alter_table("orders") as batch_op:
        batch_op.add_column(sa.Column("guest_token", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("idempotency_key", sa.String(length=128), nullable=True))
        batch_op.create_index("ix_orders_guest_token", ["guest_token"], unique=False)
        batch_op.create_index("ix_orders_idempotency_key", ["idempotency_key"], unique=False)
        batch_op.create_unique_constraint("uq_orders_idempotency_key", ["idempotency_key"])
        batch_op.create_check_constraint(
            "ck_orders_identity",
            "(user_id IS NOT NULL) OR (guest_token IS NOT NULL)",
        )
        batch_op.alter_column("user_id", existing_type=sa.Integer(), nullable=True)

    with op.batch_alter_table("conversations") as batch_op:
        batch_op.add_column(sa.Column("checkout_state", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("checkout_customer_name", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("checkout_customer_phone", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("checkout_customer_address", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("last_order_id", sa.Integer(), nullable=True))

    op.execute("UPDATE conversations SET checkout_state = 'idle' WHERE checkout_state IS NULL")
    with op.batch_alter_table("conversations") as batch_op:
        batch_op.alter_column("checkout_state", existing_type=sa.String(length=30), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("conversations") as batch_op:
        batch_op.drop_column("last_order_id")
        batch_op.drop_column("checkout_customer_address")
        batch_op.drop_column("checkout_customer_phone")
        batch_op.drop_column("checkout_customer_name")
        batch_op.drop_column("checkout_state")

    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_constraint("ck_orders_identity", type_="check")
        batch_op.drop_constraint("uq_orders_idempotency_key", type_="unique")
        batch_op.drop_index("ix_orders_idempotency_key")
        batch_op.drop_index("ix_orders_guest_token")
        batch_op.drop_column("idempotency_key")
        batch_op.drop_column("guest_token")
        batch_op.alter_column("user_id", existing_type=sa.Integer(), nullable=False)

    with op.batch_alter_table("carts") as batch_op:
        batch_op.drop_constraint("ck_carts_identity", type_="check")
        batch_op.drop_constraint("uq_cart_guest_store", type_="unique")
        batch_op.drop_index("ix_carts_guest_token")
        batch_op.drop_column("guest_token")
        batch_op.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
