from core.schemas.recognition.coco import CocoAnnotation, CocoCategory, CocoImage
from core.schemas.recognition.combination import (
    RecognitionCombination,
    RecognitionCombinationModel,
)
from core.schemas.recognition.method import RecognitionMethod
from core.schemas.recognition.image_result import RecognitionImageResult
from core.schemas.recognition.request import RecognitionRequest
from core.schemas.recognition.response import RecognitionResponse
from core.schemas.recognition.raw_detection import RawDetection
from core.schemas.recognition.model_config import RecognitionModelConfig
from core.schemas.recognition.task_record import RecognitionTaskRecord

__all__ = [
    "CocoAnnotation",
    "CocoCategory",
    "CocoImage",
    "RecognitionCombination",
    "RecognitionCombinationModel",
    "RecognitionImageResult",
    "RecognitionMethod",
    "RecognitionModelConfig",
    "RecognitionRequest",
    "RecognitionResponse",
    "RawDetection",
    "RecognitionTaskRecord",
]
