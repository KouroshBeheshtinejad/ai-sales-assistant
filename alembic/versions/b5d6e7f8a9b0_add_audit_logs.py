"""add audit logs

Revision ID: b5d6e7f8a9b0
Revises: ac30cd40ee50
"""

from alembic import op
import sqlalchemy as sa


revision = "b5d6e7f8a9b0"
down_revision = "ac30cd40ee50"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=120), nullable=True),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("stores.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("before_state", sa.JSON(), nullable=True),
        sa.Column("after_state", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_store_id", "audit_logs", ["store_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_store_created", "audit_logs", ["store_id", "created_at"])
    op.create_index("ix_audit_logs_actor_created", "audit_logs", ["actor_user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_actor_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_store_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_store_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")