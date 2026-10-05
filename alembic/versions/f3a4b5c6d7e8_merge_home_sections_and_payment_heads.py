"""merge home sections and payment credential heads

Revision ID: f3a4b5c6d7e8
Revises: e9a0b1c2d3f4, f2a3b4c5d6e7
"""

from alembic import op
import sqlalchemy as sa


revision = "f3a4b5c6d7e8"
down_revision = ("e9a0b1c2d3f4", "f2a3b4c5d6e7")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
