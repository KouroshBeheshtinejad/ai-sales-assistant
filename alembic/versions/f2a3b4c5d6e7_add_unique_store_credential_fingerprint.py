"""prevent cross-store reuse of payment credentials

Revision ID: f2a3b4c5d6e7
Revises: f0e1d2c3b4a5
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, Sequence[str], None] = "f0e1d2c3b4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "store_payment_accounts",
        sa.Column("credential_fingerprint", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "uq_store_payment_account_credential_fingerprint",
        "store_payment_accounts",
        ["credential_fingerprint"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_store_payment_account_credential_fingerprint",
        table_name="store_payment_accounts",
    )
    op.drop_column("store_payment_accounts", "credential_fingerprint")