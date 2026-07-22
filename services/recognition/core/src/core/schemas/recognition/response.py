from dataclasses import dataclass, field

from core.schemas.recognition.coco import CocoAnnotation, CocoCategory, CocoImage


@dataclass
class RecognitionResponse:
    images: list[CocoImage] = field(default_factory=list)
    annotations: list[CocoAnnotation] = field(default_factory=list)
    categories: list[CocoCategory] = field(default_factory=list)
    image_key: str = ""
    coco_key: str = ""
    service: str = ""
    detection_type: str = ""
    extra: dict = field(default_factory=dict)
