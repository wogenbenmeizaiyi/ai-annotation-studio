"""create recognition schema

Revision ID: 20260710_0001
Revises:
Create Date: 2026-07-10 00:00:00
"""

from __future__ import annotations

from alembic import op

revision = "20260710_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS recognition_task_records (
        id SERIAL PRIMARY KEY,
        task_id VARCHAR(64) UNIQUE NOT NULL,
        status VARCHAR(32),
        callback_url VARCHAR(2048),
        request_payload JSONB NOT NULL,
        result_payload JSONB,
        callback_attempts INTEGER,
        last_callback_status_code INTEGER,
        last_callback_error TEXT,
        callback_started_at TIMESTAMP WITH TIME ZONE,
        completed_at TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
    );
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_recognition_task_records_task_id
    ON recognition_task_records (task_id);
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_recognition_task_records_status
    ON recognition_task_records (status);
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS recognition_image_results (
        id SERIAL PRIMARY KEY,
        task_id VARCHAR(64) NOT NULL
            REFERENCES recognition_task_records(task_id),
        image_index INTEGER NOT NULL,
        source_url TEXT NOT NULL,
        service VARCHAR(64) NOT NULL,
        detection_type VARCHAR(255) NOT NULL,
        image_key VARCHAR(1024) NOT NULL,
        coco_key VARCHAR(1024) NOT NULL,
        annotation_count INTEGER,
        result_payload JSONB NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
        CONSTRAINT uq_recognition_image_result UNIQUE (task_id, image_index)
    );
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_recognition_image_results_task_id
    ON recognition_image_results (task_id);
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_recognition_image_results_service
    ON recognition_image_results (service);
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_recognition_image_results_detection_type
    ON recognition_image_results (detection_type);
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS recognition_model_configs (
        id SERIAL PRIMARY KEY,
        uuid VARCHAR(64) UNIQUE NOT NULL,
        name VARCHAR(255) NOT NULL,
        detection_type INTEGER NOT NULL,
        prompt TEXT,
        model_file VARCHAR(255),
        storage_key VARCHAR(1024),
        is_deleted BOOLEAN DEFAULT false,
        project_name VARCHAR(255),
        description TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
    );
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_recognition_model_configs_uuid
    ON recognition_model_configs (uuid);
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_recognition_model_configs_name
    ON recognition_model_configs (name);
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_recognition_model_configs_detection_type
    ON recognition_model_configs (detection_type);
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_recognition_model_configs_project_name
    ON recognition_model_configs (project_name);
    """)

    op.execute("""
    ALTER TABLE recognition_model_configs
        ADD COLUMN IF NOT EXISTS prompt TEXT,
        ADD COLUMN IF NOT EXISTS model_file VARCHAR(255),
        ADD COLUMN IF NOT EXISTS storage_key VARCHAR(1024),
        ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT false;
    """)
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_recognition_model_configs_is_deleted
    ON recognition_model_configs (is_deleted);
    """)
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'recognition_model_configs'
                AND column_name = 'runtime_key'
        ) THEN
            EXECUTE $migration$
                UPDATE recognition_model_configs
                SET
                    prompt = CASE
                        WHEN detection_type IN (3, 4) THEN runtime_key
                        ELSE prompt
                    END,
                    model_file = CASE
                        WHEN detection_type IN (1, 2)
                            AND runtime_key IS NOT NULL
                            THEN runtime_key || '.pt'
                        WHEN detection_type = 3
                            THEN COALESCE(
                                NULLIF(display_model_name, ''),
                                'sam3'
                            ) || '.pt'
                        ELSE model_file
                    END,
                    storage_key = CASE
                        WHEN detection_type IN (1, 2)
                            AND runtime_key IS NOT NULL
                            THEN '平台/yolo/model/' || runtime_key || '.pt'
                        WHEN detection_type = 3
                            THEN '平台/sam/model/'
                                || COALESCE(
                                    NULLIF(display_model_name, ''),
                                    'sam3'
                                )
                                || '.pt'
                        ELSE storage_key
                    END,
                    is_deleted = CASE
                        WHEN enabled IS NULL THEN false
                        ELSE NOT enabled
                    END
            $migration$;
        END IF;
    END $$;
    """)
    op.execute("""
    ALTER TABLE recognition_model_configs
        DROP CONSTRAINT IF EXISTS uq_recognition_model_runtime_key,
        DROP COLUMN IF EXISTS runtime_key,
        DROP COLUMN IF EXISTS display_model_name,
        DROP COLUMN IF EXISTS enabled;
    """)
    op.execute("""
    UPDATE recognition_model_configs
    SET
        is_deleted = COALESCE(is_deleted, false),
        project_name = COALESCE(project_name, '通用'),
        description = COALESCE(description, '')
    WHERE is_deleted IS NULL
        OR project_name IS NULL
        OR description IS NULL;
    """)
    op.execute("""
    COMMENT ON TABLE recognition_task_records IS '识别任务回调记录表';
    COMMENT ON TABLE recognition_image_results IS '识别任务图片结果表';
    COMMENT ON TABLE recognition_model_configs IS '识别模型配置表';
    """)
    op.execute("""
    COMMENT ON COLUMN recognition_model_configs.uuid IS '对外模型或识别项UUID';
    COMMENT ON COLUMN recognition_model_configs.name IS '业务展示名称';
    COMMENT ON COLUMN recognition_model_configs.detection_type IS '识别类型';
    COMMENT ON COLUMN recognition_model_configs.prompt IS '提示词，YOLO模型可为空';
    COMMENT ON COLUMN recognition_model_configs.model_file IS '模型文件名，远端多模态可为空';
    COMMENT ON COLUMN recognition_model_configs.storage_key IS '模型在S3或MinIO中的完整对象Key，远端多模态可为空';
    COMMENT ON COLUMN recognition_model_configs.is_deleted IS '是否删除';
    COMMENT ON COLUMN recognition_model_configs.project_name IS '项目名称';
    COMMENT ON COLUMN recognition_model_configs.description IS '描述';
    COMMENT ON COLUMN recognition_model_configs.created_at IS '创建时间';
    COMMENT ON COLUMN recognition_model_configs.updated_at IS '更新时间';
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS recognition_model_configs;")
    op.execute("DROP TABLE IF EXISTS recognition_image_results;")
    op.execute("DROP TABLE IF EXISTS recognition_task_records;")
