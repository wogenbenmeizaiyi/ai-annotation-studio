"""初始化识别模型配置，并为 YOLO 模型复制 UUID 文件名副本。"""

import shutil
import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in ("core/src",):
    sys.path.insert(0, str(PROJECT_ROOT / path))

from core.db import Base, SessionLocal, engine  # noqa: E402
from core.schemas.recognition.model_config import RecognitionModelConfig  # noqa: E402

DEFAULT_PROJECT_NAME = "通用"
YOLO_MODEL_DIRS = (
    (1, PROJECT_ROOT / "models" / "yolo" / "detection"),
    (2, PROJECT_ROOT / "models" / "yolo" / "segmentation"),
)
STORAGE_KEY_PREFIX_BY_TYPE = {
    1: "平台/yolo/model",
    2: "平台/yolo/model",
    3: "平台/sam/model",
}
PROMPT_MODEL_CONFIGS = (
    (3, "sam3", "crack", "sam3.pt", "平台/sam/model/sam3.pt"),
    (4, "多模态", "穿着绿色反光衣的人", None, None),
    (4, "多模态", "带着黄色安全帽的人", None, None),
    (4, "多模态", "路面抛洒物", None, None),
    (4, "多模态", "坑洞", None, None),
)


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


def _upsert_config(
    *,
    db,
    uuid_value: str,
    name: str,
    detection_type: int,
    prompt: str | None = None,
    model_file: str | None = None,
    storage_key: str | None = None,
    project_name: str = DEFAULT_PROJECT_NAME,
    description: str = "",
) -> RecognitionModelConfig:
    row = (
        db.query(RecognitionModelConfig)
        .filter(RecognitionModelConfig.uuid == uuid_value)
        .first()
    )
    if row is None:
        row = (
            db.query(RecognitionModelConfig)
            .filter(
                RecognitionModelConfig.project_name == project_name,
                RecognitionModelConfig.detection_type == detection_type,
                RecognitionModelConfig.name == name,
                RecognitionModelConfig.prompt == prompt,
            )
            .first()
        )

    if row is None:
        row = RecognitionModelConfig(uuid=uuid_value)
        db.add(row)

    row.name = name
    row.detection_type = detection_type
    row.prompt = prompt
    row.model_file = model_file
    row.storage_key = storage_key
    row.project_name = project_name
    row.is_deleted = False
    row.description = description
    return row


def _seed_yolo_models(db) -> None:
    for detection_type, model_dir in YOLO_MODEL_DIRS:
        if not model_dir.exists():
            continue

        for model_file in sorted(model_dir.glob("*.pt")):
            original_name = model_file.stem
            if _is_uuid(original_name):
                existing = (
                    db.query(RecognitionModelConfig)
                    .filter(RecognitionModelConfig.uuid == original_name)
                    .first()
                )
                if existing is None:
                    model_file_name = model_file.name
                    _upsert_config(
                        db=db,
                        uuid_value=original_name,
                        name=original_name,
                        detection_type=detection_type,
                        model_file=model_file_name,
                        storage_key=(
                            f"{STORAGE_KEY_PREFIX_BY_TYPE[detection_type]}/"
                            f"{model_file_name}"
                        ),
                        description=f"YOLO model file: {model_file.name}",
                    )
                continue

            existing = (
                db.query(RecognitionModelConfig)
                .filter(
                    RecognitionModelConfig.project_name == DEFAULT_PROJECT_NAME,
                    RecognitionModelConfig.detection_type == detection_type,
                    RecognitionModelConfig.name == original_name,
                )
                .first()
            )
            if existing is not None:
                target_name = existing.model_file or f"{existing.uuid}.pt"
                target_file = model_file.with_name(target_name)
                if not target_file.exists():
                    shutil.copy2(model_file, target_file)
                    print(
                        f"copied YOLO model: {model_file.name} -> {target_file.name}"
                    )
                continue

            model_uuid = str(uuid.uuid4())
            model_file_name = f"{model_uuid}.pt"
            target_file = model_file.with_name(model_file_name)
            if target_file.exists():
                raise FileExistsError(f"target model file already exists: {target_file}")
            shutil.copy2(model_file, target_file)
            print(f"copied YOLO model: {model_file.name} -> {target_file.name}")

            _upsert_config(
                db=db,
                uuid_value=model_uuid,
                name=original_name,
                detection_type=detection_type,
                model_file=model_file_name,
                storage_key=(
                    f"{STORAGE_KEY_PREFIX_BY_TYPE[detection_type]}/"
                    f"{model_file_name}"
                ),
                description=f"YOLO model file: {target_file.name}",
            )


def _seed_prompt_models(db) -> None:
    for detection_type, name, prompt, model_file, storage_key in PROMPT_MODEL_CONFIGS:
        _upsert_config(
            db=db,
            uuid_value=str(uuid.uuid4()),
            name=name,
            detection_type=detection_type,
            prompt=prompt,
            model_file=model_file,
            storage_key=storage_key,
            description="prompt based recognition config",
        )


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        _seed_yolo_models(db)
        _seed_prompt_models(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print("recognition model configs seeded")


if __name__ == "__main__":
    main()
