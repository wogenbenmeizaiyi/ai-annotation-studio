"""识别服务的惰性导出。

这里不在包导入时加载 GPU 库，使多模态 worker 可以使用轻量依赖启动。
"""

from importlib import import_module

from core.schemas.recognition import (
    RecognitionMethod,
    RecognitionRequest,
    RecognitionResponse,
)

_SERVICE_MODULES = {
    "BaseRecognitionService": "engine.services.base_service",
    "GpuRecognitionService": "engine.services.gpu_service",
    "MultimodalService": "engine.services.multimodal_service",
    "SamSegmentationService": "engine.services.sam_segmentation_service",
    "YoloDetectionService": "engine.services.yolo_detection_service",
    "YoloSegmentationService": "engine.services.yolo_segmentation_service",
}


def __getattr__(name: str):
    module_name = _SERVICE_MODULES.get(name)
    if module_name is None:
        raise AttributeError(name)
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


__all__ = [
    "BaseRecognitionService",
    "GpuRecognitionService",
    "MultimodalService",
    "RecognitionMethod",
    "RecognitionRequest",
    "RecognitionResponse",
    "SamSegmentationService",
    "YoloDetectionService",
    "YoloSegmentationService",
]
