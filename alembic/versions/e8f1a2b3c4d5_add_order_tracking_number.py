"""add immutable customer order tracking number

Revision ID: e8f1a2b3c4d5
Revises: d4e7f6a1b2c3
"""

import secrets

from alembic import op
import sqlalchemy as sa


revision = "e8f1a2b3c4d5"
down_revision = "d4e7f6a1b2c3"
branch_labels = None
depends_on = None


def _tracking_number(used: set[str]) -> str:
    while True:
        value = str(secrets.randbelow(9_000_000_000) + 1_000_000_000)
        if value not in used:
            used.add(value)
            return value


def upgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.add_column(sa.Column("tracking_number", sa.String(length=10), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id FROM orders ORDER BY id")).fetchall()
    used: set[str] = set()
    for row in rows:
        bind.execute(
            sa.text("UPDATE orders SET tracking_number = :tracking_number WHERE id = :order_id"),
            {"tracking_number": _tracking_number(used), "order_id": row.id},
        )

    with op.batch_alter_table("orders") as batch_op:
        batch_op.alter_column(
            "tracking_number",
            existing_type=sa.String(length=10),
            nullable=False,
        )
        batch_op.create_unique_constraint("uq_orders_tracking_number", ["tracking_number"])
        batch_op.create_index("ix_orders_tracking_number", ["tracking_number"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_index("ix_orders_tracking_number")
        batch_op.drop_constraint("uq_orders_tracking_number", type_="unique")
        batch_op.drop_column("tracking_number")