from dataclasses import dataclass, field


@dataclass
class CocoAnnotation:
    id: int
    image_id: int
    category_id: int
    bbox: list[float]
    iscrowd: int = 0
    segmentation: list[list[float]] = field(default_factory=list)
    score: float = 0.0


@dataclass
class CocoCategory:
    id: int
    name: str
    supercategory: str = ""


@dataclass
class CocoImage:
    id: int
    file_name: str
    width: int
    height: int
