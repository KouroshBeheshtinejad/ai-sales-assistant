"""Add home sections table

Revision ID: e9a0b1c2d3f4
Revises: fa1b2c3d4e5f
Create Date: 2026-10-05
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e9a0b1c2d3f4"
down_revision = "fa1b2c3d4e5f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "home_sections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("titles", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="stores"),
        sa.Column("business_types", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("background_color", sa.String(length=7), nullable=False, server_default="#f2f7f6"),
        sa.Column("item_limit", sa.Integer(), nullable=False, server_default="12"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("kind IN ('stores', 'products')", name="ck_home_sections_kind"),
        sa.CheckConstraint("item_limit >= 1 AND item_limit <= 24", name="ck_home_sections_item_limit"),
    )
    op.create_index("ix_home_sections_active_position", "home_sections", ["is_active", "position"])


def downgrade() -> None:
    op.drop_index("ix_home_sections_active_position", table_name="home_sections")
    op.drop_table("home_sections")
