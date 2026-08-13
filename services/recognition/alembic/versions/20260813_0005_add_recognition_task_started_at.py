"""add recognition task started_at

Revision ID: 20260813_0005
Revises: 20260723_0004
Create Date: 2026-08-13
"""

import sqlalchemy as sa
from alembic import op


revision = "20260813_0005"
down_revision = "20260723_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "recognition_task_records",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "COMMENT ON COLUMN recognition_task_records.started_at "
        "IS 'worker 开始处理任务的时刻'"
    )


def downgrade() -> None:
    op.drop_column("recognition_task_records", "started_at")
