"""add detection and segmentation evaluation metrics

Revision ID: 20260720_0002
Revises: 20260720_0001
Create Date: 2026-07-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260720_0002"
down_revision: Union[str, None] = "20260720_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


METRIC_COLUMNS = {
    "train_seg_loss": sa.Column(
        "train_seg_loss", sa.Float(), nullable=True, comment="训练mask分割损失"
    ),
    "val_seg_loss": sa.Column(
        "val_seg_loss", sa.Float(), nullable=True, comment="验证mask分割损失"
    ),
    "mask_precision": sa.Column(
        "mask_precision", sa.Float(), nullable=True, comment="Mask精确率"
    ),
    "mask_recall": sa.Column(
        "mask_recall", sa.Float(), nullable=True, comment="Mask召回率"
    ),
    "mask_map50": sa.Column(
        "mask_map50", sa.Float(), nullable=True, comment="Mask mAP@0.5"
    ),
    "mask_map50_95": sa.Column(
        "mask_map50_95", sa.Float(), nullable=True, comment="Mask mAP@0.5:0.95"
    ),
    "fitness": sa.Column(
        "fitness", sa.Float(), nullable=True, comment="Ultralytics综合适应度"
    ),
    "per_class_metrics": sa.Column(
        "per_class_metrics",
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
        comment="逐类别Box和Mask评估指标",
    ),
}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {
        item["name"] for item in inspector.get_columns("training_metrics")
    }
    for name, column in METRIC_COLUMNS.items():
        if name not in existing_columns:
            op.add_column("training_metrics", column)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {
        item["name"] for item in inspector.get_columns("training_metrics")
    }
    for name in reversed(tuple(METRIC_COLUMNS)):
        if name in existing_columns:
            op.drop_column("training_metrics", name)
