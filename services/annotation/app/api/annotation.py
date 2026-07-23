from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import List, Optional, Union

from app.models.annotation import CocoAnnotation, CocoDataset, CocoCategory, CocoImage
from app.models.api_response import ApiResponse
from app.models.image import ImageModel
from app.services.image_store import ImageStore
from app.core.auth import get_request_auth, require_image_manager


router = APIRouter(prefix="/annotation", tags=["Annotation"])
image_store = ImageStore()


class UpdateAnnotationRequest(BaseModel):
    image_id: int
    cocoAnnotations: List[dict]


@router.get("/get_by_image")
def get_annotation_by_image(image_id: int):
    """
    根据图片ID获取标注信息
    """
    img = image_store.get_image_by_id(image_id)
    if not img:
        return ApiResponse.error_response(
            message=f"图片未找到: ID {image_id}", code=404
        )

    annotation_data = img.annotation_jsonb
    if isinstance(annotation_data, str):
        import json

        try:
            annotation_data = json.loads(annotation_data)
        except (json.JSONDecodeError, TypeError):
            annotation_data = None

    return ApiResponse.success_response(data=annotation_data)


@router.post("/update")
def update_annotation(req: UpdateAnnotationRequest, request: Request):
    """
    更新标注信息（覆盖写入）
    """
    require_image_manager(req.image_id, get_request_auth(request))
    img = image_store.get_image_by_id(req.image_id)
    if not img:
        return ApiResponse.error_response(
            message=f"图片未找到: ID {req.image_id}", code=404
        )

    db_annotation = img.annotation_jsonb
    if isinstance(db_annotation, str):
        import json

        try:
            db_annotation = json.loads(db_annotation)
        except (json.JSONDecodeError, TypeError):
            db_annotation = None

    if not db_annotation:
        return ApiResponse.error_response(message="该图片无标注数据基础结构", code=400)

    coco_annotations = []
    for ann_dict in req.cocoAnnotations:
        coco_annotations.append(CocoAnnotation.from_coco_dict(ann_dict))

    existing_dataset = CocoDataset.from_coco_dict(db_annotation)
    existing_dataset.annotations = coco_annotations

    updated_jsonb = existing_dataset.to_coco_dict()
    return image_store.update_annotation_jsonb(req.image_id, updated_jsonb)
