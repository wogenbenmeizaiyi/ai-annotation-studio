"""add protected platform owner

Revision ID: 20260724_0002
Revises: 20260723_0001
Create Date: 2026-07-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260724_0002"
down_revision = "20260723_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "auth_users",
        sa.Column(
            "is_platform_owner",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.execute(
        sa.text(
            """
            UPDATE auth_users
            SET is_platform_owner = true
            WHERE id = (
                SELECT id
                FROM auth_users
                WHERE role = 'super_admin' AND status = 'active'
                ORDER BY created_at ASC, id ASC
                LIMIT 1
            )
            """
        )
    )
    op.create_index(
        "uq_auth_users_single_platform_owner",
        "auth_users",
        ["is_platform_owner"],
        unique=True,
        postgresql_where=sa.text("is_platform_owner = true"),
    )
    op.create_check_constraint(
        "ck_auth_users_platform_owner_role",
        "auth_users",
        "NOT is_platform_owner OR role = 'super_admin'",
    )
    op.alter_column("auth_users", "is_platform_owner", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "ck_auth_users_platform_owner_role",
        "auth_users",
        type_="check",
    )
    op.drop_index("uq_auth_users_single_platform_owner", table_name="auth_users")
    op.drop_column("auth_users", "is_platform_owner")
