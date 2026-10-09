"""remove obsolete store location fields

Revision ID: e91f2a3b4c5d
Revises: c8f1c2d3e4a5
"""

from alembic import op
import sqlalchemy as sa


revision = "e91f2a3b4c5d"
down_revision = "c8f1c2d3e4a5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("stores", "location_url")
    op.drop_column("stores", "location_name")


def downgrade() -> None:
    op.add_column("stores", sa.Column("location_name", sa.String(length=255), nullable=True))
    op.add_column("stores", sa.Column("location_url", sa.String(length=500), nullable=True))