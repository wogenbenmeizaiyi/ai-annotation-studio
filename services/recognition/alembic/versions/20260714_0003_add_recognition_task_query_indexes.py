"""add recognition task query indexes

Revision ID: 20260714_0003
Revises: 20260710_0002
Create Date: 2026-07-14
"""

from alembic import op


revision = "20260714_0003"
down_revision = "20260710_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_recognition_task_records_created_at
    ON recognition_task_records (created_at DESC);
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_recognition_task_records_status_created_at
    ON recognition_task_records (status, created_at DESC);
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_recognition_task_records_detection_type_created_at
    ON recognition_task_records
    ((request_payload ->> 'detection_type'), created_at DESC);
    """)
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_recognition_task_records_project_name_trgm
    ON recognition_task_records
    USING gin ((request_payload ->> 'project_name') gin_trgm_ops);
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_recognition_task_records_project_name_trgm;")
    op.execute(
        "DROP INDEX IF EXISTS ix_recognition_task_records_detection_type_created_at;"
    )
    op.execute("DROP INDEX IF EXISTS ix_recognition_task_records_status_created_at;")
    op.execute("DROP INDEX IF EXISTS ix_recognition_task_records_created_at;")
