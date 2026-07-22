from dataclasses import dataclass, field


@dataclass
class RawDetection:
    """模型推理得到的单个原始标注，不包含 COCO 分类信息。"""

    bbox: list[float]
    score: float
    segmentation: list[list[float]] = field(default_factory=list)
