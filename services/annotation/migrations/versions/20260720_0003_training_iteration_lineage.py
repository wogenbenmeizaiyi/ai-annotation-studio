"""add training optimization lineage

Revision ID: 20260720_0003
Revises: 20260720_0002
Create Date: 2026-07-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260720_0003"
down_revision: Union[str, None] = "20260720_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> set[str]:
    return {
        item["name"]
        for item in sa.inspect(op.get_bind()).get_columns(table_name)
    }


def _foreign_key_names(table_name: str) -> set[str]:
    return {
        item["name"]
        for item in sa.inspect(op.get_bind()).get_foreign_keys(table_name)
        if item.get("name")
    }


def _index_names(table_name: str) -> set[str]:
    return {
        item["name"]
        for item in sa.inspect(op.get_bind()).get_indexes(table_name)
        if item.get("name")
    }


def upgrade() -> None:
    if "parent_train_task_id" not in _column_names("train_tasks"):
        op.add_column(
            "train_tasks",
            sa.Column(
                "parent_train_task_id",
                sa.Integer(),
                nullable=True,
                comment="本轮参数优化所依据的上一轮训练任务ID",
            ),
        )
    if "fk_train_tasks_parent_train_task_id" not in _foreign_key_names("train_tasks"):
        op.create_foreign_key(
            "fk_train_tasks_parent_train_task_id",
            "train_tasks",
            "train_tasks",
            ["parent_train_task_id"],
            ["id"],
            ondelete="SET NULL",
        )
    if "ix_train_tasks_parent_train_task_id" not in _index_names("train_tasks"):
        op.create_index(
            "ix_train_tasks_parent_train_task_id",
            "train_tasks",
            ["parent_train_task_id"],
        )

    proposal_table = "agent_config_proposals"
    if "source_train_task_id" not in _column_names(proposal_table):
        op.add_column(
            proposal_table,
            sa.Column(
                "source_train_task_id",
                sa.Integer(),
                nullable=True,
                comment="生成优化草案所依据的上一轮训练任务ID",
            ),
        )
    if (
        "fk_agent_config_proposals_source_train_task_id"
        not in _foreign_key_names(proposal_table)
    ):
        op.create_foreign_key(
            "fk_agent_config_proposals_source_train_task_id",
            proposal_table,
            "train_tasks",
            ["source_train_task_id"],
            ["id"],
            ondelete="SET NULL",
        )
    if (
        "ix_agent_config_proposals_source_train_task_id"
        not in _index_names(proposal_table)
    ):
        op.create_index(
            "ix_agent_config_proposals_source_train_task_id",
            proposal_table,
            ["source_train_task_id"],
        )


def downgrade() -> None:
    proposal_table = "agent_config_proposals"
    if "ix_agent_config_proposals_source_train_task_id" in _index_names(proposal_table):
        op.drop_index(
            "ix_agent_config_proposals_source_train_task_id",
            table_name=proposal_table,
        )
    if (
        "fk_agent_config_proposals_source_train_task_id"
        in _foreign_key_names(proposal_table)
    ):
        op.drop_constraint(
            "fk_agent_config_proposals_source_train_task_id",
            proposal_table,
            type_="foreignkey",
        )
    if "source_train_task_id" in _column_names(proposal_table):
        op.drop_column(proposal_table, "source_train_task_id")

    if "ix_train_tasks_parent_train_task_id" in _index_names("train_tasks"):
        op.drop_index("ix_train_tasks_parent_train_task_id", table_name="train_tasks")
    if "fk_train_tasks_parent_train_task_id" in _foreign_key_names("train_tasks"):
        op.drop_constraint(
            "fk_train_tasks_parent_train_task_id",
            "train_tasks",
            type_="foreignkey",
        )
    if "parent_train_task_id" in _column_names("train_tasks"):
        op.drop_column("train_tasks", "parent_train_task_id")
