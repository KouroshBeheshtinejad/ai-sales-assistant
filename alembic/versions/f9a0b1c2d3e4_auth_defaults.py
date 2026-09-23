"""align user verification default with the registration flow

Revision ID: f9a0b1c2d3e4
Revises: f8a9b0c1d2e3
"""

from alembic import op
import sqlalchemy as sa


revision = "f9a0b1c2d3e4"
down_revision = "f8a9b0c1d2e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "is_verified",
            existing_type=sa.Boolean(),
            server_default=sa.text("0"),
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "is_verified",
            existing_type=sa.Boolean(),
            server_default=sa.text("1"),
        )