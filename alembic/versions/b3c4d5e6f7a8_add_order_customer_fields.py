"""add structured customer fields to orders

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
"""

from alembic import op
import sqlalchemy as sa


revision = "b3c4d5e6f7a8"
down_revision = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.add_column(sa.Column("customer_first_name", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("customer_last_name", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("customer_email", sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_column("customer_email")
        batch_op.drop_column("customer_last_name")
        batch_op.drop_column("customer_first_name")