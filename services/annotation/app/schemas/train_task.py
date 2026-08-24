import logging
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class YoloTrainConfig(BaseModel):
    model: str = Field(default="yolo26n.pt", description="模型文件名")
    epochs: int = Field(default=100, ge=1)
    patience: int = Field(default=100, ge=0)
    batch: Union[int, float] = Field(default=16)
    imgsz: Union[int, List[int]] = Field(default=640)
    pretrained: Union[bool, str] = Field(default=True)
    optimizer: str = Field(default="auto")
    single_cls: bool = Field(default=False)
    classes: Optional[List[int]] = Field(default=None)
    rect: bool = Field(default=False)
    multi_scale: float = Field(default=0.0, ge=0)
    cos_lr: bool = Field(default=False)
    close_mosaic: int = Field(default=10, ge=0)
    fraction: float = Field(default=1.0, gt=0, le=1)
    freeze: Optional[Union[int, List[int]]] = Field(default=None)
    lr0: float = Field(default=0.01, gt=0)
    lrf: float = Field(default=0.01, ge=0)
    momentum: float = Field(default=0.937, ge=0)
    weight_decay: float = Field(default=0.0005, ge=0)
    warmup_epochs: float = Field(default=3.0, ge=0)
    warmup_momentum: float = Field(default=0.8, ge=0)
    warmup_bias_lr: float = Field(default=0.1, ge=0)
    box: float = Field(default=7.5, ge=0)
    cls: float = Field(default=0.5, ge=0)
    cls_pw: float = Field(default=0.0, ge=0)
    dfl: float = Field(default=1.5, ge=0)
    pose: float = Field(default=12.0, ge=0)
    kobj: float = Field(default=1.0, ge=0)
    rle: float = Field(default=1.0, ge=0)
    angle: float = Field(default=1.0, ge=0)
    nbs: int = Field(default=64, ge=1)
    overlap_mask: bool = Field(default=True)
    mask_ratio: int = Field(default=4, ge=1)
    dropout: float = Field(default=0.0, ge=0)
    val: bool = Field(default=True)

    # 数据增强参数
    hsv_h: float = Field(default=0.015, ge=0, le=1)
    hsv_s: float = Field(default=0.7, ge=0, le=1)
    hsv_v: float = Field(default=0.4, ge=0, le=1)
    degrees: float = Field(default=0.0, ge=0, le=180)
    translate: float = Field(default=0.1, ge=0, le=1)
    scale: float = Field(default=0.5, ge=0)
    shear: float = Field(default=0.0, ge=-180, le=180)
    perspective: float = Field(default=0.0, ge=0, le=0.001)
    flipud: float = Field(default=0.0, ge=0, le=1)
    fliplr: float = Field(default=0.5, ge=0, le=1)
    bgr: float = Field(default=0.0, ge=0, le=1)
    mosaic: float = Field(default=1.0, ge=0, le=1)
    mixup: float = Field(default=0.0, ge=0, le=1)
    cutmix: float = Field(default=0.0, ge=0, le=1)
    copy_paste: float = Field(default=0.0, ge=0, le=1)
    copy_paste_mode: str = Field(default="flip")
    auto_augment: str = Field(default="randaugment")
    erasing: float = Field(default=0.4, ge=0, le=1)
    augmentations: Optional[List[Dict[str, Any]]] = Field(default=None)

    val_split: float = Field(default=0.2, ge=0, le=1)

    def to_train_kwargs(
        self,
        data_path: str,
        project: str,
        name: str,
        exist_ok: bool,
        workers: int,
        supported_args: Optional[Set[str]] = None,
    ) -> Dict[str, Any]:
        """转换为 Ultralytics model.train 参数。"""
        kwargs = self.model_dump(exclude={"model", "val_split"}, exclude_none=True)
        kwargs["project"] = project
        kwargs["name"] = name
        kwargs["data"] = data_path
        kwargs["exist_ok"] = exist_ok
        kwargs["save"] = True
        kwargs["plots"] = False
        kwargs["verbose"] = False
        kwargs["workers"] = workers
        if supported_args is not None:
            unsupported_args = sorted(set(kwargs) - supported_args)
            if unsupported_args:
                logger.warning(f"忽略当前 Ultralytics 不支持的训练参数: {unsupported_args}")
                kwargs = {
                    key: value
                    for key, value in kwargs.items()
                    if key in supported_args
                }
        return kwargs

    class Config:
        extra = "forbid"


class CreateTaskRequest(BaseModel):
    task_name: str
    config: YoloTrainConfig = Field(default_factory=YoloTrainConfig)
    priority: int = Field(default=0, ge=-100, le=100)
    parent_train_task_id: Optional[int] = Field(default=None, ge=1)

    class Config:
        extra = "forbid"
