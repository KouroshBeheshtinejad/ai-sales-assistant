"""add home section decoration and hand-picked items

Revision ID: f0b1c2d3e4a5
Revises: f3a4b5c6d7e8
Create Date: 2026-10-06
"""

from alembic import op
import sqlalchemy as sa


revision = "f0b1c2d3e4a5"
down_revision = "f3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("home_sections") as batch:
        batch.add_column(sa.Column("background_color_2", sa.String(length=7), nullable=False, server_default=""))
        batch.add_column(sa.Column("pattern", sa.String(length=12), nullable=False, server_default="none"))
        batch.add_column(sa.Column("edge", sa.String(length=12), nullable=False, server_default="straight"))
        batch.add_column(sa.Column("card_style", sa.String(length=12), nullable=False, server_default="solid"))
        batch.add_column(sa.Column("icon", sa.String(length=8), nullable=False, server_default=""))
        batch.add_column(sa.Column("subtitle", sa.String(length=160), nullable=False, server_default=""))
        batch.add_column(sa.Column("subtitles", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
        batch.add_column(sa.Column("show_all_link", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.add_column(sa.Column("pinned_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
        batch.add_column(sa.Column("fill_random", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.create_check_constraint(
            "ck_home_sections_pattern",
            "pattern IN ('none', 'dots', 'grid', 'diagonal', 'waves', 'zellij')",
        )
        batch.create_check_constraint("ck_home_sections_edge", "edge IN ('straight', 'wave', 'curve')")
        batch.create_check_constraint("ck_home_sections_card_style", "card_style IN ('solid', 'glass')")


def downgrade() -> None:
    with op.batch_alter_table("home_sections") as batch:
        batch.drop_constraint("ck_home_sections_card_style", type_="check")
        batch.drop_constraint("ck_home_sections_edge", type_="check")
        batch.drop_constraint("ck_home_sections_pattern", type_="check")
        for column in (
            "fill_random",
            "pinned_ids",
            "show_all_link",
            "subtitles",
            "subtitle",
            "icon",
            "card_style",
            "edge",
            "pattern",
            "background_color_2",
        ):
            batch.drop_column(column)