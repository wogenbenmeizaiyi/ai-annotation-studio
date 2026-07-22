from enum import Enum


class RecognitionMethod(str, Enum):
    YOLO_DETECTION = "yolo_detection"
    YOLO_SEGMENTATION = "yolo_segmentation"
    SAM_SEGMENTATION = "sam_segmentation"
    MULTIMODAL = "multimodal"
