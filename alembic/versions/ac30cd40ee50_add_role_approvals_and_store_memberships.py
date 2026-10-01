"""add account approvals and tenant-scoped store admin memberships

Revision ID: ac30cd40ee50
Revises: ab20bc30dd40
"""

from alembic import op
import sqlalchemy as sa


revision = "ac30cd40ee50"
down_revision = "ab20bc30dd40"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("role", existing_type=sa.String(length=20), type_=sa.String(length=30), server_default="store_owner")
        batch_op.add_column(sa.Column("approval_status", sa.String(length=20), nullable=False, server_default="active"))
        batch_op.create_index("ix_users_approval_status", ["approval_status"])
    op.execute("UPDATE users SET role = 'store_owner' WHERE role = 'seller'")
    op.create_table(
        "store_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False, server_default="store_admin"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("store_id", "user_id", name="uq_store_membership_user_store"),
    )
    op.create_index("ix_store_memberships_store_id", "store_memberships", ["store_id"])
    op.create_index("ix_store_memberships_user_id", "store_memberships", ["user_id"])
    op.create_index("ix_store_memberships_status", "store_memberships", ["status"])
    op.create_index("ix_store_memberships_user_status", "store_memberships", ["user_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_store_memberships_user_status", table_name="store_memberships")
    op.drop_index("ix_store_memberships_status", table_name="store_memberships")
    op.drop_index("ix_store_memberships_user_id", table_name="store_memberships")
    op.drop_index("ix_store_memberships_store_id", table_name="store_memberships")
    op.drop_table("store_memberships")
    op.execute("UPDATE users SET role = 'seller' WHERE role = 'store_owner'")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_approval_status")
        batch_op.drop_column("approval_status")
        batch_op.alter_column("role", existing_type=sa.String(length=30), type_=sa.String(length=20), server_default="seller")