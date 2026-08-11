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


def _column_names(inspector: sa.Inspector) -> set[str]:
    return {item["name"] for item in inspector.get_columns("tasks")}


def _index_names(inspector: sa.Inspector) -> set[str]:
    return {item["name"] for item in inspector.get_indexes("tasks")}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 首条 bootstrap 迁移会用当前 ORM 模型初始化全新数据库，因此新库中可能
    # 已经存在此列和索引；旧库升级时则由本迁移补齐。
    if "owner_subject_id" not in _column_names(inspector):
        op.add_column(
            "tasks",
            sa.Column(
                "owner_subject_id",
                sa.String(length=36),
                nullable=True,
                comment="创建者认证主体UUID",
            ),
        )

    inspector = sa.inspect(bind)
    if "ix_tasks_owner_subject_id" not in _index_names(inspector):
        op.create_index("ix_tasks_owner_subject_id", "tasks", ["owner_subject_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "ix_tasks_owner_subject_id" in _index_names(inspector):
        op.drop_index("ix_tasks_owner_subject_id", table_name="tasks")

    inspector = sa.inspect(bind)
    if "owner_subject_id" in _column_names(inspector):
        op.drop_column("tasks", "owner_subject_id")
