"""bootstrap Alembic and add the persistent training queue

Revision ID: 20260720_0001
Revises:
Create Date: 2026-07-20
"""

from typing import Optional, Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260720_0001"
down_revision: Optional[str] = None
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


QUEUE_COLUMNS = {
    "priority": sa.Column(
        "priority", sa.Integer(), nullable=False, server_default="0", comment="队列优先级"
    ),
    "queued_at": sa.Column(
        "queued_at", sa.DateTime(timezone=True), nullable=True, comment="进入队列时间"
    ),
    "started_at": sa.Column(
        "started_at", sa.DateTime(timezone=True), nullable=True, comment="训练开始时间"
    ),
    "finished_at": sa.Column(
        "finished_at", sa.DateTime(timezone=True), nullable=True, comment="训练结束时间"
    ),
    "heartbeat_at": sa.Column(
        "heartbeat_at", sa.DateTime(timezone=True), nullable=True, comment="Worker心跳时间"
    ),
    "worker_id": sa.Column(
        "worker_id", sa.String(length=128), nullable=True, comment="领取任务的Worker标识"
    ),
    "checkpoint_path": sa.Column(
        "checkpoint_path", sa.String(length=1024), nullable=True, comment="断点文件路径"
    ),
    "attempt_count": sa.Column(
        "attempt_count", sa.Integer(), nullable=False, server_default="0", comment="执行次数"
    ),
    "resume_count": sa.Column(
        "resume_count", sa.Integer(), nullable=False, server_default="0", comment="断点恢复次数"
    ),
}


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {item["name"] for item in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()

    # 兼容没有使用迁移工具创建的既有数据库，也支持空数据库首次部署。
    from app.db.database import Base
    import app.models  # noqa: F401
    from app.models.training_metric import TrainingMetricModel  # noqa: F401

    Base.metadata.create_all(bind=bind)
    inspector = sa.inspect(bind)
    existing_columns = {item["name"] for item in inspector.get_columns("train_tasks")}
    for name, column in QUEUE_COLUMNS.items():
        if name not in existing_columns:
            op.add_column("train_tasks", column)

    op.execute(
        sa.text(
            "UPDATE train_tasks SET status = 'QUEUED', "
            "queued_at = COALESCE(queued_at, created_at, CURRENT_TIMESTAMP), "
            "worker_id = NULL, heartbeat_at = NULL "
            "WHERE status IN ('PENDING', 'RUNNING', 'CLAIMED', 'RECOVERING')"
        )
    )

    inspector = sa.inspect(bind)
    if "ix_train_tasks_queue" not in _index_names(inspector, "train_tasks"):
        op.create_index(
            "ix_train_tasks_queue",
            "train_tasks",
            ["status", "priority", "queued_at", "id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "ix_train_tasks_queue" in _index_names(inspector, "train_tasks"):
        op.drop_index("ix_train_tasks_queue", table_name="train_tasks")
    existing_columns = {item["name"] for item in inspector.get_columns("train_tasks")}
    for name in reversed(tuple(QUEUE_COLUMNS)):
        if name in existing_columns:
            op.drop_column("train_tasks", name)
