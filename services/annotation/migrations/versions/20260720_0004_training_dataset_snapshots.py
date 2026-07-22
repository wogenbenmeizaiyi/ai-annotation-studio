"""add reproducible training dataset snapshots

Revision ID: 20260720_0004
Revises: 20260720_0003
Create Date: 2026-07-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260720_0004"
down_revision: Union[str, None] = "20260720_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SNAPSHOT_COLUMNS = {
    "dataset_fingerprint": sa.Column(
        "dataset_fingerprint",
        sa.String(length=64),
        nullable=True,
        comment="训练数据集快照SHA256指纹",
    ),
    "dataset_yaml_path": sa.Column(
        "dataset_yaml_path",
        sa.String(length=1024),
        nullable=True,
        comment="本次训练固定使用的数据集YAML路径",
    ),
    "dataset_manifest_path": sa.Column(
        "dataset_manifest_path",
        sa.String(length=1024),
        nullable=True,
        comment="本次训练集/验证集划分清单路径",
    ),
}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_columns = {
        item["name"] for item in inspector.get_columns("train_tasks")
    }
    for name, column in SNAPSHOT_COLUMNS.items():
        if name not in existing_columns:
            op.add_column("train_tasks", column)

    existing_indexes = {
        item["name"] for item in sa.inspect(op.get_bind()).get_indexes("train_tasks")
    }
    if "ix_train_tasks_dataset_fingerprint" not in existing_indexes:
        op.create_index(
            "ix_train_tasks_dataset_fingerprint",
            "train_tasks",
            ["dataset_fingerprint"],
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_indexes = {
        item["name"] for item in inspector.get_indexes("train_tasks")
    }
    if "ix_train_tasks_dataset_fingerprint" in existing_indexes:
        op.drop_index("ix_train_tasks_dataset_fingerprint", table_name="train_tasks")

    existing_columns = {
        item["name"] for item in sa.inspect(op.get_bind()).get_columns("train_tasks")
    }
    for name in reversed(tuple(SNAPSHOT_COLUMNS)):
        if name in existing_columns:
            op.drop_column("train_tasks", name)
