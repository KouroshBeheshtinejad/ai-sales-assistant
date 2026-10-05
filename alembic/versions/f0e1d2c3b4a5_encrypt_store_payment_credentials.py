"""store encrypted payment credentials

Revision ID: f0e1d2c3b4a5
Revises: e3f4a5b6c7d8
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f0e1d2c3b4a5"
down_revision: Union[str, Sequence[str], None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "store_payment_accounts",
        sa.Column("credential_ciphertext", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("store_payment_accounts", "credential_ciphertext")