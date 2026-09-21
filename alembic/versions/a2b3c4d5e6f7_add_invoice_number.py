"""add immutable invoice number to orders

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
"""

import secrets
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "a2b3c4d5e6f7"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.add_column(sa.Column("invoice_number", sa.String(length=40), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, created_at FROM orders ORDER BY id")).fetchall()
    used = set()
    for row in rows:
        date_value = row.created_at or datetime.now(timezone.utc).replace(tzinfo=None)
        while True:
            value = f"INV-{date_value:%Y%m%d}-{secrets.randbelow(1_000_000):06d}"
            if value not in used:
                used.add(value)
                break
        bind.execute(sa.text("UPDATE orders SET invoice_number = :value WHERE id = :order_id"), {"value": value, "order_id": row.id})

    with op.batch_alter_table("orders") as batch_op:
        batch_op.alter_column("invoice_number", existing_type=sa.String(length=40), nullable=False)
        batch_op.create_unique_constraint("uq_orders_invoice_number", ["invoice_number"])
        batch_op.create_index("ix_orders_invoice_number", ["invoice_number"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_index("ix_orders_invoice_number")
        batch_op.drop_constraint("uq_orders_invoice_number", type_="unique")
        batch_op.drop_column("invoice_number")