"""add account verification records

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
"""

from alembic import op
import sqlalchemy as sa


revision = "c4d5e6f7a8b9"
down_revision = "b3c4d5e6f7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("phone", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.create_index("ix_users_phone", ["phone"], unique=True)

    op.create_table(
        "verification_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("target", sa.String(length=255), nullable=False),
        sa.Column("code_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_verification_codes_user_id", "verification_codes", ["user_id"])
    op.create_index("ix_verification_codes_user_channel", "verification_codes", ["user_id", "channel"])


def downgrade() -> None:
    op.drop_index("ix_verification_codes_user_channel", table_name="verification_codes")
    op.drop_index("ix_verification_codes_user_id", table_name="verification_codes")
    op.drop_table("verification_codes")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_phone")
        batch_op.drop_column("is_verified")
        batch_op.drop_column("phone")