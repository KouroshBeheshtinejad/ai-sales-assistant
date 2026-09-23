"""make stock total inventory and enforce reservation invariant

Revision ID: fa1b2c3d4e5f
Revises: f9a0b1c2d3e4
"""

from alembic import op
import sqlalchemy as sa


revision = "fa1b2c3d4e5f"
down_revision = "f9a0b1c2d3e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("UPDATE products SET stock = stock + reserved_stock"))
    with op.batch_alter_table("products") as batch_op:
        batch_op.create_check_constraint(
            "ck_products_reserved_lte_stock",
            "reserved_stock <= stock",
        )


def downgrade() -> None:
    with op.batch_alter_table("products") as batch_op:
        batch_op.drop_constraint("ck_products_reserved_lte_stock", type_="check")