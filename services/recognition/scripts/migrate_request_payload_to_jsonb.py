"""将 recognition_task_records.request_payload 从 json 转为 jsonb。"""

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
            ALTER COLUMN request_payload TYPE jsonb
            USING request_payload::jsonb;
            """)
        )
        conn.commit()

    print("request_payload 已转换为 jsonb")


if __name__ == "__main__":
    migrate()
