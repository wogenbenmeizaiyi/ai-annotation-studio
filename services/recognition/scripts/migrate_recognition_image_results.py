"""创建识别任务图片结果表。"""

import sys
from pathlib import Path

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in ("core/src",):
    sys.path.insert(0, str(PROJECT_ROOT / path))

from core.db import Base, engine  # noqa: E402
from core.schemas.recognition.image_result import RecognitionImageResult  # noqa: E402
from core.schemas.recognition.task_record import RecognitionTaskRecord  # noqa: E402

_MODELS = (RecognitionTaskRecord, RecognitionImageResult)


def migrate() -> None:
    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        conn.execute(
            text("""
            COMMENT ON TABLE recognition_image_results IS '识别任务图片结果表';
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
        conn.commit()

    print("识别任务图片结果表创建完成")


if __name__ == "__main__":
    migrate()
