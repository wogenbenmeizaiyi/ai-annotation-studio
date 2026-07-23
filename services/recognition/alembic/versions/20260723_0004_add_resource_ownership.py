"""add resource ownership

Revision ID: 20260723_0004
Revises: 20260714_0003
Create Date: 2026-07-23
"""

import sqlalchemy as sa
from alembic import op


revision = "20260723_0004"
down_revision = "20260714_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "recognition_task_records",
        sa.Column("owner_subject_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        "ix_recognition_task_records_owner_subject_id",
        "recognition_task_records",
        ["owner_subject_id"],
    )
    op.add_column(
        "recognition_model_configs",
        sa.Column("owner_subject_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        "ix_recognition_model_configs_owner_subject_id",
        "recognition_model_configs",
        ["owner_subject_id"],
    )
    op.add_column(
        "recognition_combinations",
        sa.Column("owner_subject_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        "ix_recognition_combinations_owner_subject_id",
        "recognition_combinations",
        ["owner_subject_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_recognition_combinations_owner_subject_id",
        table_name="recognition_combinations",
    )
    op.drop_column("recognition_combinations", "owner_subject_id")
    op.drop_index(
        "ix_recognition_model_configs_owner_subject_id",
        table_name="recognition_model_configs",
    )
    op.drop_column("recognition_model_configs", "owner_subject_id")
    op.drop_index(
        "ix_recognition_task_records_owner_subject_id",
        table_name="recognition_task_records",
    )
    op.drop_column("recognition_task_records", "owner_subject_id")
