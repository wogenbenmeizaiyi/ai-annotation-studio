import io
import re
import uuid
import logging
from typing import List, Optional, Tuple
from PIL import Image
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.s3.s3_client import s3, s3_instance
from app.db.database import SessionLocal
from app.models.annotation import CocoDataset, CocoImage, CocoCategory
from app.models.api_response import ApiResponse
from app.models.image import ImageModel
from app.models.task import TaskModel, CategoryModel

logger = logging.getLogger(__name__)

S3_BUCKET = settings.S3_BUCKET_NAME
S3_URL_EXPIRES = settings.S3_URL_EXPIRES


def _generate_s3_key(task_name: str, file_name: str) -> str:
    return f"annotation/{task_name}/{file_name}"


def _detect_suffix(data: bytes) -> str:
    import imghdr

    img_type = imghdr.what(None, h=data)
    return f".{img_type}" if img_type else ".jpg"


def _presigned_url(s3_key: str) -> str:
    return s3_instance.generate_presigned_url(
        bucket=S3_BUCKET, key=s3_key, expires_in=S3_URL_EXPIRES
    )


def _to_dict_with_url(img_row: ImageModel) -> dict:
    data = img_row.to_dict()
    data["url"] = _presigned_url(img_row.s3_key)
    return data


def extract_number(name: str) -> int:
    match = re.search(r"\d+", name)
    return int(match.group()) if match else 0


class ImageStore:
    def upload_image(
        self,
        task_name: str,
        image_data: bytes,
        original_name: str,
        detection_type: str,
        categories: Optional[List[CocoCategory]] = None,
    ) -> ApiResponse:
        db: Session = SessionLocal()
        try:
            task = (
                db.query(TaskModel)
                .filter(TaskModel.name == task_name, TaskModel.is_deleted == False)
                .first()
            )
            if not task:
                return ApiResponse.error_response(
                    message=f"任务未找到: {task_name}", code=404
                )

            task_id = task.id

            image = Image.open(io.BytesIO(image_data))
            width, height = image.size
            file_size = len(image_data)

            suffix = _detect_suffix(image_data)
            file_name = f"{uuid.uuid4().hex[:16]}{suffix}"
            s3_key = _generate_s3_key(task_name, file_name)

            s3.put_object(
                Bucket=S3_BUCKET,
                Key=s3_key,
                Body=image_data,
                ContentType=f"image/{suffix.lstrip('.')}",
            )
            logger.info(f"图片上传RustFS成功: {s3_key}")

            coco_image = CocoImage(
                file_name=file_name,
                width=width,
                height=height,
            )
            coco_dataset = CocoDataset(
                categories=categories or [],
                images=[coco_image],
                annotations=[],
            )
            annotation_jsonb = coco_dataset.to_coco_dict()

            img_row = ImageModel(
                task_id=task_id,
                file_name=file_name,
                original_name=original_name,
                s3_key=s3_key,
                width=width,
                height=height,
                file_size=file_size,
                detection_type=detection_type,
                is_annotated=False,
                annotation_jsonb=annotation_jsonb,
            )
            db.add(img_row)
            db.commit()
            db.refresh(img_row)

            return ApiResponse.success_response(
                data=_to_dict_with_url(img_row),
                message="图片上传和COCO数据创建成功",
            )
        except Exception as e:
            db.rollback()
            logger.error(f"图片上传失败: {str(e)}")
            return ApiResponse.error_response(
                message=f"图片上传失败: {str(e)}", code=500
            )
        finally:
            db.close()

    # ------------------------
    # Read
    # ------------------------
    def get_image_with_url(self, image_id: int) -> Optional[dict]:
        db: Session = SessionLocal()
        try:
            img = (
                db.query(ImageModel)
                .filter(ImageModel.id == image_id, ImageModel.is_deleted == False)
                .first()
            )
            if not img:
                return None
            return _to_dict_with_url(img)
        finally:
            db.close()

    def get_image_list_by_task_name(self, task_name: str) -> List[dict]:
        db: Session = SessionLocal()
        try:
            task = (
                db.query(TaskModel)
                .filter(TaskModel.name == task_name, TaskModel.is_deleted == False)
                .first()
            )
            if not task:
                return []
            images = (
                db.query(ImageModel)
                .filter(ImageModel.task_id == task.id, ImageModel.is_deleted == False)
                .order_by(ImageModel.id)
                .all()
            )
            return [_to_dict_with_url(img) for img in images]
        finally:
            db.close()

    def get_images_by_task_name_paged(
        self, task_name: str, page: int, page_size: int
    ) -> Tuple[List[dict], int, int]:
        db: Session = SessionLocal()
        try:
            if page < 1:
                page = 1
            if page_size < 1:
                page_size = 20

            task = (
                db.query(TaskModel)
                .filter(TaskModel.name == task_name, TaskModel.is_deleted == False)
                .first()
            )
            if not task:
                return [], 0, 0

            query = (
                db.query(ImageModel)
                .filter(ImageModel.task_id == task.id, ImageModel.is_deleted == False)
                .order_by(ImageModel.id)
            )
            total = query.count()
            annotated_count = query.filter(ImageModel.is_annotated == True).count()
            images = query.offset((page - 1) * page_size).limit(page_size).all()

            return [_to_dict_with_url(img) for img in images], total, annotated_count
        finally:
            db.close()

    def get_image_by_id(self, image_id: int) -> Optional[ImageModel]:
        db: Session = SessionLocal()
        try:
            return (
                db.query(ImageModel)
                .filter(ImageModel.id == image_id, ImageModel.is_deleted == False)
                .first()
            )
        finally:
            db.close()

    # ------------------------
    # Update annotation
    # ------------------------
    def update_annotation_jsonb(
        self, image_id: int, annotation_jsonb: dict
    ) -> ApiResponse:
        db: Session = SessionLocal()
        try:
            img = (
                db.query(ImageModel)
                .filter(ImageModel.id == image_id, ImageModel.is_deleted == False)
                .first()
            )
            if not img:
                return ApiResponse.error_response(
                    message=f"图片未找到: ID {image_id}", code=404
                )

            img.annotation_jsonb = annotation_jsonb
            annotations_list = annotation_jsonb.get("annotations", [])
            img.is_annotated = len(annotations_list) > 0
            db.commit()
            db.refresh(img)

            return ApiResponse.success_response(
                data=_to_dict_with_url(img),
                message="标注更新成功",
            )
        except Exception as e:
            db.rollback()
            return ApiResponse.error_response(
                message=f"标注更新失败: {str(e)}", code=500
            )
        finally:
            db.close()

    # ------------------------
    # Delete (soft)
    # ------------------------
    def delete_image(self, image_id: int) -> ApiResponse:
        db: Session = SessionLocal()
        try:
            img = (
                db.query(ImageModel)
                .filter(ImageModel.id == image_id, ImageModel.is_deleted == False)
                .first()
            )
            if not img:
                return ApiResponse.error_response(
                    message=f"图片未找到: ID {image_id}", code=404
                )

            img.is_deleted = True
            from datetime import datetime, timezone

            img.updated_at = datetime.now(timezone.utc)
            db.commit()
            return ApiResponse.success_response(data=None, message="图片删除成功")
        except Exception as e:
            db.rollback()
            return ApiResponse.error_response(
                message=f"图片删除失败: {str(e)}", code=500
            )
        finally:
            db.close()
