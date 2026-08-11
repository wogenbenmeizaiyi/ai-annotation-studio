from pathlib import Path

from fastapi import APIRouter

from core.schemas.dictionary import (
    ServiceTypeItem,
    ServiceTypeListResponse,
    YoloModelListResponse,
)
from core.schemas.recognition import RecognitionMethod

router = APIRouter(tags=["dict"])

_SERVICE_TYPE_DESCRIPTIONS = {
    RecognitionMethod.YOLO_DETECTION: "YOLO 目标检测",
    RecognitionMethod.YOLO_SEGMENTATION: "YOLO 图像分割",
    RecognitionMethod.SAM_SEGMENTATION: "SAM 图像分割",
    RecognitionMethod.MULTIMODAL: "多模态识别",
}

_SERVICE_TYPE_IDS = {
    RecognitionMethod.YOLO_DETECTION: 1,
    RecognitionMethod.YOLO_SEGMENTATION: 2,
    RecognitionMethod.SAM_SEGMENTATION: 3,
    RecognitionMethod.MULTIMODAL: 4,
}


@router.get("/services")
async def get_service_types() -> ServiceTypeListResponse:
    """获取所有可用的识别服务类型"""
    services = [
        ServiceTypeItem(
            id=_SERVICE_TYPE_IDS[method],
            name=method.value,
            description=_SERVICE_TYPE_DESCRIPTIONS[method],
        )
        for method in RecognitionMethod
    ]
    return ServiceTypeListResponse(services=services)


@router.get("/models/yolo")
async def get_yolo_models() -> YoloModelListResponse:
    """获取所有可用的 YOLO 模型名称（检测 + 分割）"""
    base_path = Path("models/yolo")

    detection_dir = base_path / "detection"
    detection_models = (
        sorted([p.stem for p in detection_dir.glob("*.pt") if p.is_file()])
        if detection_dir.exists()
        else []
    )

    segmentation_dir = base_path / "segmentation"
    segmentation_models = (
        sorted([p.stem for p in segmentation_dir.glob("*.pt") if p.is_file()])
        if segmentation_dir.exists()
        else []
    )

    return YoloModelListResponse(
        detection=detection_models,
        segmentation=segmentation_models,
    )
