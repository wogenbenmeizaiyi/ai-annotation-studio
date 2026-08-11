import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.core.config import settings
from app.schemas.train_task import YoloTrainConfig


def available_models() -> List[str]:
    model_dir = Path(settings.YOLO_MODEL_DIR)
    if not model_dir.is_absolute():
        model_dir = Path.cwd() / model_dir
    if not model_dir.exists():
        return []
    return sorted(path.name for path in model_dir.glob("*.pt") if path.is_file())


def validate_training_config(
    raw_config: Dict[str, Any],
    category_ids: List[int],
) -> Tuple[YoloTrainConfig, List[str]]:
    config = YoloTrainConfig.model_validate(raw_config)
    errors: List[str] = []

    if config.epochs > 1000:
        errors.append("epochs不能大于1000")
    if config.patience > config.epochs:
        errors.append("patience不能大于epochs")
    if isinstance(config.batch, int) and not (config.batch == -1 or 1 <= config.batch <= 256):
        errors.append("整数batch必须是-1或在1到256之间")
    if isinstance(config.batch, float) and not (config.batch == -1 or 0 < config.batch <= 1):
        errors.append("浮点batch只允许-1或0到1之间的自动显存比例")

    sizes = config.imgsz if isinstance(config.imgsz, list) else [config.imgsz]
    if not sizes or len(sizes) > 2 or any(not 320 <= value <= 2048 for value in sizes):
        errors.append("imgsz必须是320到2048之间的整数，最多包含宽高两个值")
    if config.lr0 > 1:
        errors.append("lr0不能大于1")
    if config.lrf > 1:
        errors.append("lrf不能大于1")
    if not 0.01 <= config.val_split <= 0.5:
        errors.append("val_split必须在0.01到0.5之间")
    if config.close_mosaic > config.epochs:
        errors.append("close_mosaic不能大于epochs")
    if config.classes is not None:
        unknown = sorted(set(config.classes) - set(category_ids))
        if unknown:
            errors.append(f"classes包含当前任务不存在的类别ID: {unknown}")

    models = available_models()
    if models and config.model not in models:
        errors.append(f"model必须来自服务端模型白名单: {models}")
    if Path(config.model).is_absolute() or ".." in Path(config.model).parts:
        errors.append("model不能使用绝对路径或父目录路径")

    if errors:
        raise ValueError("；".join(errors))
    return config, build_resource_warnings(config)


def build_resource_warnings(config: YoloTrainConfig) -> List[str]:
    warnings: List[str] = []
    sizes = config.imgsz if isinstance(config.imgsz, list) else [config.imgsz]
    max_size = max(sizes)
    if max_size >= 1280:
        warnings.append("输入尺寸较高，可能显著增加显存占用和训练时间")
    if isinstance(config.batch, int) and max_size >= 960 and config.batch >= 16:
        warnings.append("高分辨率配合较大batch可能导致显存不足")
    if config.epochs >= 500:
        warnings.append("训练轮数较高，请关注过拟合和GPU占用时间")
    return warnings


def canonical_config(config: YoloTrainConfig) -> str:
    return json.dumps(
        config.model_dump(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
