"""add user profile-completion fields and captcha challenges

Revision ID: a1b2c3d4e5f6
Revises: fa1b2c3d4e5f
"""

from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "fa1b2c3d4e5f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("national_id", sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column("business_address", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("business_phone", sa.String(length=50), nullable=True))
        batch_op.create_unique_constraint("uq_users_national_id", ["national_id"])
    op.create_index("ix_users_national_id", "users", ["national_id"])

    op.create_table(
        "captcha_challenges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("code_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_captcha_challenges_token", "captcha_challenges", ["token"])


def downgrade() -> None:
    op.drop_index("ix_captcha_challenges_token", table_name="captcha_challenges")
    op.drop_table("captcha_challenges")

    op.drop_index("ix_users_national_id", table_name="users")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("uq_users_national_id", type_="unique")
        batch_op.drop_column("business_phone")
        batch_op.drop_column("business_address")
        batch_op.drop_column("national_id")
