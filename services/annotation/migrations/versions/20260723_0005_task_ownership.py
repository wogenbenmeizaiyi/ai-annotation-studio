"""add task ownership

Revision ID: 20260723_0005
Revises: 20260720_0004
Create Date: 2026-07-23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260723_0005"
down_revision: Union[str, None] = "20260720_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column(
            "owner_subject_id",
            sa.String(length=36),
            nullable=True,
            comment="创建者认证主体UUID",
        ),
    )
    op.create_index("ix_tasks_owner_subject_id", "tasks", ["owner_subject_id"])


def downgrade() -> None:
    op.drop_index("ix_tasks_owner_subject_id", table_name="tasks")
    op.drop_column("tasks", "owner_subject_id")
