"""create recognition combinations

Revision ID: 20260710_0002
Revises: 20260710_0001
Create Date: 2026-07-10 00:30:00
"""

from __future__ import annotations

from alembic import op

revision = "20260710_0002"
down_revision = "20260710_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE recognition_combinations (
        id SERIAL PRIMARY KEY,
        uuid VARCHAR(64) UNIQUE NOT NULL,
        name VARCHAR(255) NOT NULL,
        project_name VARCHAR(255) NOT NULL DEFAULT '通用',
        description TEXT NOT NULL DEFAULT '',
        is_deleted BOOLEAN NOT NULL DEFAULT false,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
    );
    """)
    op.execute("""
    CREATE INDEX ix_recognition_combinations_uuid
    ON recognition_combinations (uuid);
    CREATE INDEX ix_recognition_combinations_name
    ON recognition_combinations (name);
    CREATE INDEX ix_recognition_combinations_project_name
    ON recognition_combinations (project_name);
    CREATE INDEX ix_recognition_combinations_is_deleted
    ON recognition_combinations (is_deleted);
    """)
    op.execute("""
    CREATE TABLE recognition_combination_models (
        id SERIAL PRIMARY KEY,
        combination_id INTEGER NOT NULL
            REFERENCES recognition_combinations(id) ON DELETE CASCADE,
        model_id INTEGER NOT NULL REFERENCES recognition_model_configs(id),
        sort_order INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
        CONSTRAINT uq_recognition_combination_model
            UNIQUE (combination_id, model_id)
    );
    """)
    op.execute("""
    CREATE INDEX ix_recognition_combination_models_combination_id
    ON recognition_combination_models (combination_id);
    CREATE INDEX ix_recognition_combination_models_model_id
    ON recognition_combination_models (model_id);
    """)
    op.execute("""
    COMMENT ON TABLE recognition_combinations IS '可复用的多模型综合检测配置';
    COMMENT ON TABLE recognition_combination_models IS '综合检测配置与模型配置多对多关联表';
    """)


def downgrade() -> None:
    op.execute("DROP TABLE recognition_combination_models;")
    op.execute("DROP TABLE recognition_combinations;")
