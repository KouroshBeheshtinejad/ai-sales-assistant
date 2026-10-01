"""extend conversations for customer support

Revision ID: c6d7e8f9a0b1
Revises: b5d6e7f8a9b0
"""

from alembic import op
import sqlalchemy as sa


revision = "c6d7e8f9a0b1"
down_revision = "b5d6e7f8a9b0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("conversations") as batch_op:
        batch_op.alter_column("store_id", existing_type=sa.Integer(), nullable=True)
        batch_op.add_column(sa.Column("kind", sa.String(length=20), nullable=False, server_default="sales"))
        batch_op.add_column(sa.Column("support_status", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("priority", sa.String(length=20), nullable=False, server_default="normal"))
        batch_op.add_column(sa.Column("assigned_to", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_conversations_assigned_to_users",
            "users",
            ["assigned_to"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_conversations_kind", ["kind"])
        batch_op.create_index("ix_conversations_support_status", ["support_status"])
        batch_op.create_index("ix_conversations_assigned_to", ["assigned_to"])


def downgrade() -> None:
    with op.batch_alter_table("conversations") as batch_op:
        batch_op.drop_index("ix_conversations_assigned_to")
        batch_op.drop_index("ix_conversations_support_status")
        batch_op.drop_index("ix_conversations_kind")
        batch_op.drop_constraint("fk_conversations_assigned_to_users", type_="foreignkey")
        batch_op.drop_column("assigned_to")
        batch_op.drop_column("priority")
        batch_op.drop_column("support_status")
        batch_op.drop_column("kind")
        batch_op.alter_column("store_id", existing_type=sa.Integer(), nullable=False)