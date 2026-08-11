"""create authentication schema

Revision ID: 20260723_0001
Revises:
Create Date: 2026-07-23
"""

from alembic import op
import sqlalchemy as sa


revision = "20260723_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("username_normalized", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("token_version", sa.Integer(), nullable=False),
        sa.Column("must_change_password", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(length=36), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username_normalized"),
    )
    op.create_index("ix_auth_users_role", "auth_users", ["role"])
    op.create_index("ix_auth_users_status", "auth_users", ["status"])
    op.create_index(
        "ix_auth_users_username_normalized", "auth_users", ["username_normalized"], unique=True
    )

    op.create_table(
        "auth_refresh_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["auth_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "ix_auth_refresh_sessions_expires_at", "auth_refresh_sessions", ["expires_at"]
    )
    op.create_index(
        "ix_auth_refresh_sessions_token_hash",
        "auth_refresh_sessions",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_auth_refresh_sessions_user_id", "auth_refresh_sessions", ["user_id"]
    )

    op.create_table(
        "auth_audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("actor_id", sa.String(length=36), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("target_id", sa.String(length=100), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auth_audit_logs_action", "auth_audit_logs", ["action"])
    op.create_index("ix_auth_audit_logs_actor_id", "auth_audit_logs", ["actor_id"])
    op.create_index("ix_auth_audit_logs_created_at", "auth_audit_logs", ["created_at"])
    op.create_index("ix_auth_audit_logs_target_id", "auth_audit_logs", ["target_id"])


def downgrade() -> None:
    op.drop_table("auth_audit_logs")
    op.drop_table("auth_refresh_sessions")
    op.drop_table("auth_users")
