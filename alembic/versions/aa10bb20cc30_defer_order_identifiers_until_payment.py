"""defer public order identifiers until payment confirmation

Revision ID: aa10bb20cc30
Revises: fa1b2c3d4e5f
"""

from alembic import op
import sqlalchemy as sa


revision = "aa10bb20cc30"
down_revision = "fa1b2c3d4e5f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.alter_column("tracking_number", existing_type=sa.String(length=10), nullable=True)
        batch_op.alter_column("invoice_number", existing_type=sa.String(length=40), nullable=True)
        batch_op.add_column(sa.Column("paid_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_column("paid_at")
        batch_op.alter_column("invoice_number", existing_type=sa.String(length=40), nullable=False)
        batch_op.alter_column("tracking_number", existing_type=sa.String(length=10), nullable=False)