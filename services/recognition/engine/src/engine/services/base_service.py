import gc
from abc import ABC, abstractmethod

import io
import json

from PIL import Image
import torch

from core.config import config
from core.s3.s3_client import s3
from core.schemas.recognition import (
    CocoAnnotation,
    CocoCategory,
    CocoImage,
    RawDetection,
    RecognitionMethod,
    RecognitionRequest,
    RecognitionResponse,
)


class BaseRecognitionService(ABC):
    method: RecognitionMethod

    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @abstractmethod
    async def recognize(self, request: RecognitionRequest) -> RecognitionResponse: ...

    def release_resources(self) -> None:
        """释放仅适用于短生命周期直连请求的模型与 CUDA 缓存。"""
        self._release_model_resources()
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def _release_model_resources(self) -> None:
        """子类按需清除自身持有的模型引用。"""

    def build_coco_response(
        self,
        request: RecognitionRequest,
        image: Image.Image,
        detections: list[RawDetection],
        image_id: str,
        image_ext: str,
        storage_namespace: str,
    ) -> RecognitionResponse:
        """将统一的原始推理结果转换为单图 COCO 响应并持久化到 S3。"""
        width, height = image.size
        file_name = f"{image_id}.{image_ext}"
        category_name = request.extra.get("category_name") or request.detection_type
        storage_namespace = request.extra.get("category_name") or storage_namespace
        categories = (
            [
                CocoCategory(
                    id=1,
                    name=category_name,
                    supercategory=category_name,
                )
            ]
            if detections
            else []
        )
        annotations = [
            CocoAnnotation(
                id=index,
                image_id=1,
                category_id=1,
                bbox=detection.bbox,
                score=detection.score,
                segmentation=detection.segmentation,
                iscrowd=0,
            )
            for index, detection in enumerate(detections, start=1)
        ]

        image_buffer = io.BytesIO()
        image.save(image_buffer, format="JPEG")
        image_key = self.upload_to_s3(
            request.project_name,
            image_buffer.getvalue(),
            f"{storage_namespace}/image/{file_name}",
        )
        response = RecognitionResponse(
            images=[CocoImage(id=1, file_name=file_name, width=width, height=height)],
            annotations=annotations,
            categories=categories,
            image_key=image_key,
            service=self._name,
            detection_type=request.detection_type,
        )
        response.coco_key = self.upload_coco_json(
            request.project_name,
            response,
            storage_namespace,
            image_id,
            image_ext,
        )
        return response

    @staticmethod
    def serialize_response(response: RecognitionResponse) -> dict:
        return {
            "service": response.service,
            "detection_type": response.detection_type,
            "count": len(response.annotations),
            "url": response.extra.get("url"),
            "image_key": response.image_key,
            "coco_key": response.coco_key,
            "images": [
                {
                    "id": img.id,
                    "file_name": img.file_name,
                    "width": img.width,
                    "height": img.height,
                }
                for img in response.images
            ],
            "annotations": [
                {
                    "id": ann.id,
                    "image_id": ann.image_id,
                    "category_id": ann.category_id,
                    "bbox": ann.bbox,
                    "score": ann.score,
                    "segmentation": ann.segmentation,
                }
                for ann in response.annotations
            ],
            "categories": [
                {"id": cat.id, "name": cat.name, "supercategory": cat.supercategory}
                for cat in response.categories
            ],
        }

    @staticmethod
    def upload_to_s3(
        project_name: str, file_data: bytes | io.BytesIO, object_name: str
    ) -> str:
        """
        上传数据到 S3，返回访问路径 (不包含 endpoint)。
        适用于上传标注后的图片数据流 (bytes / BytesIO)。
        """
        if isinstance(file_data, bytes):
            file_data = io.BytesIO(file_data)

        if hasattr(file_data, "seek"):
            file_data.seek(0)

        bucket = config.S3_BUCKET
        s3.upload_fileobj(file_data, bucket, f"{project_name}/{object_name}")
        return f"{bucket}/{project_name}/{object_name}"

    @staticmethod
    def upload_coco_json(
        project_name: str,
        response: RecognitionResponse,
        detection_type: str,
        image_id: str,
        ext: str,
    ) -> str:
        """上传 COCO 格式的 JSON 到 S3"""
        coco_data = {
            "images": [
                {
                    "id": img.id,
                    "file_name": img.file_name,
                    "width": img.width,
                    "height": img.height,
                }
                for img in response.images
            ],
            "annotations": [
                {
                    "id": ann.id,
                    "image_id": ann.image_id,
                    "category_id": ann.category_id,
                    "bbox": ann.bbox,
                    "score": ann.score,
                    "segmentation": ann.segmentation,
                    "iscrowd": ann.iscrowd,
                }
                for ann in response.annotations
            ],
            "categories": [
                {"id": cat.id, "name": cat.name, "supercategory": cat.supercategory}
                for cat in response.categories
            ],
        }
        json_bytes = json.dumps(coco_data, ensure_ascii=False, indent=2).encode("utf-8")
        return BaseRecognitionService.upload_to_s3(
            project_name,
            json_bytes,
            f"{detection_type}/json/{image_id}.json",
        )
