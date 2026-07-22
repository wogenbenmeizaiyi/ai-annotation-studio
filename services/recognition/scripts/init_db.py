"""数据库建表脚本 - 首次运行。"""

import sys
from pathlib import Path

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in ("core/src",):
    sys.path.insert(0, str(PROJECT_ROOT / path))

from core.db import Base, engine  # noqa: E402
from core.schemas.recognition.image_result import RecognitionImageResult  # noqa: E402
from core.schemas.recognition.model_config import RecognitionModelConfig  # noqa: E402
from core.schemas.recognition.task_record import RecognitionTaskRecord  # noqa: E402

_MODELS = (RecognitionTaskRecord, RecognitionImageResult, RecognitionModelConfig)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        conn.execute(
            text("""
            COMMENT ON TABLE recognition_task_records IS '识别任务回调记录表';
            COMMENT ON TABLE recognition_image_results IS '识别任务图片结果表';
            COMMENT ON TABLE recognition_model_configs IS '识别模型配置表';
            """)
        )
        conn.execute(
            text("""
            COMMENT ON COLUMN recognition_task_records.id IS '记录ID';
            COMMENT ON COLUMN recognition_task_records.task_id IS 'Celery任务ID';
            COMMENT ON COLUMN recognition_task_records.status IS '任务状态';
            COMMENT ON COLUMN recognition_task_records.callback_url IS '回调地址';
            COMMENT ON COLUMN recognition_task_records.request_payload IS '原始请求参数';
            COMMENT ON COLUMN recognition_task_records.result_payload IS '识别结果消息';
            COMMENT ON COLUMN recognition_task_records.callback_attempts IS '回调尝试次数';
            COMMENT ON COLUMN recognition_task_records.last_callback_status_code IS '最后一次回调HTTP状态码';
            COMMENT ON COLUMN recognition_task_records.last_callback_error IS '最后一次回调错误信息';
            COMMENT ON COLUMN recognition_task_records.callback_started_at IS '首次开始回调时间';
            COMMENT ON COLUMN recognition_task_records.completed_at IS '任务最终完成时间';
            COMMENT ON COLUMN recognition_task_records.created_at IS '创建时间';
            COMMENT ON COLUMN recognition_task_records.updated_at IS '更新时间';
            """)
        )
        conn.execute(
            text("""
            COMMENT ON COLUMN recognition_image_results.id IS '记录ID';
            COMMENT ON COLUMN recognition_image_results.task_id IS 'Celery任务ID';
            COMMENT ON COLUMN recognition_image_results.image_index IS '任务内图片序号';
            COMMENT ON COLUMN recognition_image_results.source_url IS '原始图片URL';
            COMMENT ON COLUMN recognition_image_results.service IS '服务枚举';
            COMMENT ON COLUMN recognition_image_results.detection_type IS '检测类型或模型/提示词';
            COMMENT ON COLUMN recognition_image_results.image_key IS '识别图片S3 Key';
            COMMENT ON COLUMN recognition_image_results.coco_key IS 'COCO结果JSON S3 Key';
            COMMENT ON COLUMN recognition_image_results.annotation_count IS '识别结果数量';
            COMMENT ON COLUMN recognition_image_results.result_payload IS '单张图片COCO标注结果';
            COMMENT ON COLUMN recognition_image_results.created_at IS '创建时间';
            """)
        )
        conn.execute(
            text("""
            COMMENT ON COLUMN recognition_model_configs.id IS '记录ID';
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
        )
        conn.commit()

    print("数据库表创建完成")


if __name__ == "__main__":
    init_db()
