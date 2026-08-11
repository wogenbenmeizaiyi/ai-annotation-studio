"""为识别任务记录表补充回调消费字段。"""

import sys
from pathlib import Path

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in ("core/src",):
    sys.path.insert(0, str(PROJECT_ROOT / path))

from core.db import engine  # noqa: E402


def migrate() -> None:
    with engine.connect() as conn:
        conn.execute(
            text("""
            ALTER TABLE recognition_task_records
                ADD COLUMN IF NOT EXISTS result_payload jsonb,
                ADD COLUMN IF NOT EXISTS callback_attempts integer NOT NULL DEFAULT 0,
                ADD COLUMN IF NOT EXISTS last_callback_status_code integer,
                ADD COLUMN IF NOT EXISTS last_callback_error text,
                ADD COLUMN IF NOT EXISTS callback_started_at timestamptz,
                ADD COLUMN IF NOT EXISTS completed_at timestamptz;
            """)
        )
        conn.execute(
            text("""
            COMMENT ON COLUMN recognition_task_records.result_payload IS '识别结果消息';
            COMMENT ON COLUMN recognition_task_records.callback_attempts IS '回调尝试次数';
            COMMENT ON COLUMN recognition_task_records.last_callback_status_code IS '最后一次回调HTTP状态码';
            COMMENT ON COLUMN recognition_task_records.last_callback_error IS '最后一次回调错误信息';
            COMMENT ON COLUMN recognition_task_records.callback_started_at IS '首次开始回调时间';
            COMMENT ON COLUMN recognition_task_records.completed_at IS '任务最终完成时间';
            """)
        )
        conn.commit()

    print("识别任务回调字段迁移完成")


if __name__ == "__main__":
    migrate()
