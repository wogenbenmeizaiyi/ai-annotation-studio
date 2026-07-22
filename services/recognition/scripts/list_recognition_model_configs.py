"""列出识别模型配置。"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in ("core/src",):
    sys.path.insert(0, str(PROJECT_ROOT / path))

from core.db import SessionLocal  # noqa: E402
from core.schemas.recognition.model_config import RecognitionModelConfig  # noqa: E402


def main() -> None:
    db = SessionLocal()
    try:
        rows = (
            db.query(RecognitionModelConfig)
            .order_by(
                RecognitionModelConfig.detection_type,
                RecognitionModelConfig.name,
                RecognitionModelConfig.created_at,
            )
            .all()
        )
        print(f"count={len(rows)}")
        for row in rows:
            print(
                row.id,
                row.uuid,
                row.name,
                row.detection_type,
                row.prompt,
                row.model_file,
                row.storage_key,
                row.is_deleted,
                row.project_name,
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
