import statistics
from collections import Counter
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.image import ImageModel
from app.models.task import CategoryModel, TaskModel
from app.services.agent.config_policy import available_models


class TrainingContextService:
    def build(self, task_name: str) -> Dict[str, Any]:
        db: Session = SessionLocal()
        try:
            task = (
                db.query(TaskModel)
                .filter(TaskModel.name == task_name, TaskModel.is_deleted == False)
                .first()
            )
            if not task:
                raise ValueError(f"标注任务不存在: {task_name}")

            categories = (
                db.query(CategoryModel)
                .filter(CategoryModel.task_id == task.id)
                .order_by(CategoryModel.id)
                .all()
            )
            images = (
                db.query(ImageModel)
                .filter(ImageModel.task_id == task.id, ImageModel.is_deleted == False)
                .all()
            )

            class_counts: Counter[int] = Counter()
            object_area_ratios = []
            annotation_count = 0
            empty_annotated_images = 0
            for image in images:
                payload = image.annotation_jsonb if isinstance(image.annotation_jsonb, dict) else {}
                annotations = payload.get("annotations", []) if payload else []
                if image.is_annotated and not annotations:
                    empty_annotated_images += 1
                for annotation in annotations:
                    annotation_count += 1
                    category_id = annotation.get("category_id")
                    if isinstance(category_id, int):
                        class_counts[category_id] += 1
                    area = annotation.get("area")
                    if not isinstance(area, (int, float)):
                        bbox = annotation.get("bbox") or []
                        if len(bbox) >= 4:
                            area = float(bbox[2]) * float(bbox[3])
                    image_area = max(1, int(image.width or 0) * int(image.height or 0))
                    if isinstance(area, (int, float)) and area >= 0:
                        object_area_ratios.append(float(area) / image_area)

            small = sum(1 for value in object_area_ratios if value < 0.01)
            medium = sum(1 for value in object_area_ratios if 0.01 <= value < 0.1)
            large = sum(1 for value in object_area_ratios if value >= 0.1)
            denominator = max(1, len(object_area_ratios))
            category_names = {category.id: category.name for category in categories}

            return {
                "task_id": task.id,
                "task_name": task.name,
                "detection_type": task.detection_type,
                "description": task.description,
                "categories": [
                    {**category.to_dict(), "yolo_class_index": index}
                    for index, category in enumerate(categories)
                ],
                "yolo_class_ids": list(range(len(categories))),
                "image_count": len(images),
                "annotated_image_count": sum(1 for image in images if image.is_annotated),
                "empty_annotated_image_count": empty_annotated_images,
                "annotation_count": annotation_count,
                "median_width": (
                    int(statistics.median([image.width for image in images])) if images else 0
                ),
                "median_height": (
                    int(statistics.median([image.height for image in images])) if images else 0
                ),
                "class_distribution": {
                    category_names.get(category_id, str(category_id)): count
                    for category_id, count in sorted(class_counts.items())
                },
                "object_size_distribution": {
                    "small_ratio": round(small / denominator, 4),
                    "medium_ratio": round(medium / denominator, 4),
                    "large_ratio": round(large / denominator, 4),
                },
                "available_models": available_models(),
            }
        finally:
            db.close()
