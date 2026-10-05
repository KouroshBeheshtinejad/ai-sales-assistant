"""add per-store payment accounts and currency snapshots

Revision ID: e3f4a5b6c7d8
Revises: d7e8f9a0b1c2
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = "d7e8f9a0b1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("stores", sa.Column("country_code", sa.String(length=2), nullable=False, server_default="IR"))
    op.add_column("stores", sa.Column("currency", sa.String(length=3), nullable=False, server_default="IRT"))
    op.add_column("stores", sa.Column("payment_provider", sa.String(length=30), nullable=False, server_default="disabled"))
    op.add_column("orders", sa.Column("currency", sa.String(length=3), nullable=False, server_default="IRT"))

    op.create_table(
        "store_payment_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("external_account_id", sa.String(length=255), nullable=True),
        sa.Column("credential_reference", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("capabilities", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("provider_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("store_id", "provider", name="uq_store_payment_account_provider"),
    )
    op.create_index("ix_store_payment_accounts_store_id", "store_payment_accounts", ["store_id"])
    op.add_column("payments", sa.Column("provider_account_id", sa.Integer(), nullable=True))
    op.create_index("ix_payments_provider_account_id", "payments", ["provider_account_id"])
    op.add_column("payments", sa.Column("provider_context", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.create_foreign_key(
        "fk_payments_provider_account_id_store_payment_accounts",
        "payments",
        "store_payment_accounts",
        ["provider_account_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.add_column("payments", sa.Column("currency", sa.String(length=3), nullable=False, server_default="IRT"))
    op.create_table(
        "payment_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("transaction_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("provider_reference", sa.String(length=255), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("transaction_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("payment_id", "idempotency_key", name="uq_payment_transaction_idempotency"),
    )
    op.create_index("ix_payment_transactions_payment_id", "payment_transactions", ["payment_id"])
    op.create_index("ix_payment_transactions_provider_reference", "payment_transactions", ["provider_reference"])
    op.create_index("ix_payment_transactions_payment_status", "payment_transactions", ["payment_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_payment_transactions_payment_status", table_name="payment_transactions")
    op.drop_index("ix_payment_transactions_provider_reference", table_name="payment_transactions")
    op.drop_index("ix_payment_transactions_payment_id", table_name="payment_transactions")
    op.drop_table("payment_transactions")
    op.drop_column("payments", "provider_context")
    op.drop_column("payments", "currency")
    op.drop_constraint("fk_payments_provider_account_id_store_payment_accounts", "payments", type_="foreignkey")
    op.drop_index("ix_payments_provider_account_id", table_name="payments")
    op.drop_column("payments", "provider_account_id")
    op.drop_index("ix_store_payment_accounts_store_id", table_name="store_payment_accounts")
    op.drop_table("store_payment_accounts")
    op.drop_column("orders", "currency")
    op.drop_column("stores", "payment_provider")
    op.drop_column("stores", "currency")
    op.drop_column("stores", "country_code")