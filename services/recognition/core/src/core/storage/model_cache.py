import logging
import os
import uuid
from pathlib import Path

from core.config import config
from core.s3.s3_client import s3
from core.schemas.recognition import RecognitionModelConfig

logger = logging.getLogger(__name__)

MODEL_SUBDIRECTORY_BY_TYPE = {
    1: Path("yolo") / "detection",
    2: Path("yolo") / "segmentation",
    3: Path("sam"),
}
SAM_DEFAULT_MODEL_FILE = "sam3.pt"
SAM_DEFAULT_STORAGE_KEY = "平台/sam/model/sam3.pt"


class ModelUnavailableError(RuntimeError):
    """模型文件无法在本地缓存中就绪。"""


def get_local_model_path(model: RecognitionModelConfig) -> Path | None:
    """返回模型在共享本地缓存中的目标路径。"""
    if model.detection_type == 4:
        return None

    subdirectory = MODEL_SUBDIRECTORY_BY_TYPE.get(model.detection_type)
    if subdirectory is None:
        raise ModelUnavailableError(f"不支持的模型类型: {model.detection_type}")
    model_file = model.model_file
    if model.detection_type == 3:
        model_file = model_file or SAM_DEFAULT_MODEL_FILE
    if not model_file:
        raise ModelUnavailableError(f"模型未配置文件名: {model.uuid}")
    return Path(config.MODELS_DIR).resolve() / subdirectory / model_file


def ensure_model_available(model: RecognitionModelConfig) -> Path | None:
    """确保模型文件已存在于共享缓存；缺失时从 S3 下载。"""
    local_path = get_local_model_path(model)
    if local_path is None:
        return None
    if local_path.is_file():
        return local_path
    storage_key = model.storage_key
    if model.detection_type == 3:
        storage_key = storage_key or SAM_DEFAULT_STORAGE_KEY
    if not storage_key:
        raise ModelUnavailableError(f"模型本地不存在且未配置存储 Key: {model.uuid}")

    local_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = local_path.with_name(
        f".{local_path.name}.{uuid.uuid4().hex}.downloading"
    )
    try:
        logger.info(
            "downloading recognition model uuid=%s storage_key=%s target=%s",
            model.uuid,
            storage_key,
            local_path,
        )
        s3.download_file(config.S3_BUCKET, storage_key, str(temporary_path))
        os.replace(temporary_path, local_path)
    except Exception as exc:
        temporary_path.unlink(missing_ok=True)
        raise ModelUnavailableError(f"模型下载失败: {model.uuid}") from exc

    logger.info("recognition model cache ready uuid=%s path=%s", model.uuid, local_path)
    return local_path
