"""add store contact and location fields

Revision ID: a7b8c9d0e1f2
Revises: f0b1c2d3e4a5
"""

from alembic import op
import sqlalchemy as sa


revision = "a7b8c9d0e1f2"
down_revision = "f0b1c2d3e4a5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("stores", sa.Column("contact_phone", sa.String(length=50), nullable=True))
    op.add_column("stores", sa.Column("address", sa.Text(), nullable=True))
    op.add_column("stores", sa.Column("location_name", sa.String(length=255), nullable=True))
    op.add_column("stores", sa.Column("latitude", sa.Numeric(precision=10, scale=6), nullable=True))
    op.add_column("stores", sa.Column("longitude", sa.Numeric(precision=10, scale=6), nullable=True))
    op.add_column("stores", sa.Column("location_url", sa.String(length=500), nullable=True))
    op.add_column("stores", sa.Column("store_hours", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("stores", "store_hours")
    op.drop_column("stores", "location_url")
    op.drop_column("stores", "longitude")
    op.drop_column("stores", "latitude")
    op.drop_column("stores", "location_name")
    op.drop_column("stores", "address")
    op.drop_column("stores", "contact_phone")