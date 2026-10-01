"""add user roles and merge outstanding migration heads

Revision ID: ab20bc30dd40
Revises: aa10bb20cc30, a1b2c3d4e5f6
"""

from alembic import op
import sqlalchemy as sa


revision = "ab20bc30dd40"
down_revision = ("aa10bb20cc30", "a1b2c3d4e5f6")
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("role", sa.String(length=20), nullable=False, server_default="seller"))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("role")