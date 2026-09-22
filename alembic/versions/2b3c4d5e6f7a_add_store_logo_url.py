"""add store logo URL

Revision ID: 2b3c4d5e6f7a
Revises: 1a2b3c4d5e6f
"""

from alembic import op
import sqlalchemy as sa


revision = "2b3c4d5e6f7a"
down_revision = "1a2b3c4d5e6f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("stores") as batch_op:
        batch_op.add_column(sa.Column("logo_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("stores") as batch_op:
        batch_op.drop_column("logo_url")