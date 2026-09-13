"""add business type and product attributes

Revision ID: 1c4d8a7b2e91
Revises: 07e9f889dcf9
Create Date: 2026-09-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1c4d8a7b2e91"
down_revision: Union[str, Sequence[str], None] = "07e9f889dcf9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "stores",
        sa.Column(
            "business_type",
            sa.String(length=100),
            nullable=False,
            server_default="clothing",
        ),
    )
    op.create_index(
        op.f("ix_stores_business_type"),
        "stores",
        ["business_type"],
        unique=False,
    )
    op.add_column(
        "products",
        sa.Column("attributes", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("products", "attributes")
    op.drop_index(op.f("ix_stores_business_type"), table_name="stores")
    op.drop_column("stores", "business_type")