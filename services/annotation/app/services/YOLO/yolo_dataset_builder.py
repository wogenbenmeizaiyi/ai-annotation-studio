import hashlib
import json
import logging
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import yaml
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.s3.s3_client import s3
from app.db.database import SessionLocal
from app.models.annotation import CocoAnnotation, CocoDataset
from app.models.image import ImageModel
from app.models.task import CategoryModel, TaskModel

logger = logging.getLogger(__name__)

S3_BUCKET = settings.S3_BUCKET_NAME
TRAIN_DATA_DIR = Path(settings.TRAIN_DATA_DIR)
DATASET_SNAPSHOT_VERSION = 1


@dataclass(frozen=True)
class DatasetImageRecord:
    image_id: int
    file_name: str
    s3_key: str
    width: int
    height: int
    yolo_lines: Tuple[str, ...]


@dataclass(frozen=True)
class DatasetBuildResult:
    fingerprint: str
    yaml_path: Path
    manifest: Dict
    reused: bool


def coco_ann_to_yolo_line(
    ann: CocoAnnotation,
    img_width: int,
    img_height: int,
    cat_id_to_yolo_idx: Optional[Dict[int, int]] = None,
) -> str:
    def clamp(v: float) -> float:
        return max(0.0, min(1.0, v))

    if ann.segmentation:
        polygon = ann.segmentation[0]
        if len(polygon) < 6:
            return ""
        yolo_cls = (
            cat_id_to_yolo_idx.get(ann.category_id, ann.category_id)
            if cat_id_to_yolo_idx
            else ann.category_id
        )
        norm_points = []
        for i in range(0, len(polygon), 2):
            x = clamp(polygon[i] / img_width)
            y = clamp(polygon[i + 1] / img_height)
            norm_points.append(f"{x:.6f} {y:.6f}")
        return f"{yolo_cls} " + " ".join(norm_points)

    if not ann.bbox:
        return ""

    x, y, w, h = ann.bbox
    x_center = clamp((x + w / 2) / img_width)
    y_center = clamp((y + h / 2) / img_height)
    w_norm = clamp(w / img_width)
    h_norm = clamp(h / img_height)

    yolo_cls = (
        cat_id_to_yolo_idx.get(ann.category_id, ann.category_id)
        if cat_id_to_yolo_idx
        else ann.category_id
    )

    return f"{yolo_cls} {x_center:.6f} {y_center:.6f} {w_norm:.6f} {h_norm:.6f}"


def _dataset_fingerprint(
    task_id: int,
    val_split: float,
    categories: List[Dict],
    records: List[DatasetImageRecord],
) -> str:
    payload = {
        "version": DATASET_SNAPSHOT_VERSION,
        "task_id": task_id,
        "val_split": format(val_split, ".8f"),
        "categories": categories,
        "images": [
            {
                "id": item.image_id,
                "file_name": item.file_name,
                "s3_key": item.s3_key,
                "width": item.width,
                "height": item.height,
                "labels": list(item.yolo_lines),
            }
            for item in sorted(records, key=lambda value: value.image_id)
        ],
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _split_records(
    records: List[DatasetImageRecord],
    task_id: int,
    val_split: float,
) -> Tuple[Set[int], Set[int]]:
    ranked = sorted(
        records,
        key=lambda item: (
            hashlib.sha256(
                f"{DATASET_SNAPSHOT_VERSION}:{task_id}:{item.image_id}:{item.file_name}".encode(
                    "utf-8"
                )
            ).hexdigest(),
            item.image_id,
        ),
    )
    if len(ranked) <= 1 or val_split <= 0:
        return {item.image_id for item in ranked}, set()

    val_count = int(len(ranked) * val_split + 0.5)
    val_count = min(max(val_count, 1), len(ranked) - 1)
    val_ids = {item.image_id for item in ranked[:val_count]}
    train_ids = {item.image_id for item in ranked[val_count:]}
    return train_ids, val_ids


class YoloDatasetBuilder:
    def build(self, task_name: str, val_split: float = 0.2) -> DatasetBuildResult:
        db: Session = SessionLocal()
        try:
            task = (
                db.query(TaskModel)
                .filter(TaskModel.name == task_name, TaskModel.is_deleted == False)
                .first()
            )
            if not task:
                raise ValueError(f"标注任务不存在: {task_name}")

            images = (
                db.query(ImageModel)
                .filter(ImageModel.task_id == task.id, ImageModel.is_deleted == False)
                .order_by(ImageModel.id)
                .all()
            )
            categories = (
                db.query(CategoryModel)
                .filter(CategoryModel.task_id == task.id)
                .order_by(CategoryModel.id)
                .all()
            )
            if not images:
                raise ValueError("当前任务没有可用于训练的图片")

            cat_id_to_yolo_idx = {
                category.id: index for index, category in enumerate(categories)
            }
            category_manifest = [
                {
                    "id": category.id,
                    "yolo_id": cat_id_to_yolo_idx[category.id],
                    "name": category.name,
                    "supercategory": category.supercategory,
                }
                for category in categories
            ]
            records = self._build_records(images, cat_id_to_yolo_idx)
            if not records:
                raise ValueError("当前任务没有包含有效标注的图片")
            if len(records) < 2 and val_split > 0:
                raise ValueError("启用验证集时至少需要2张包含有效标注的图片")

            fingerprint = _dataset_fingerprint(
                task.id,
                val_split,
                category_manifest,
                records,
            )
            train_ids, val_ids = _split_records(records, task.id, val_split)
            snapshot_root = TRAIN_DATA_DIR / task_name / "datasets"
            snapshot_dir = snapshot_root / fingerprint
            yaml_path = snapshot_dir / "data.yaml"
            manifest_path = snapshot_dir / "manifest.json"
            existing_manifest = self._read_complete_manifest(
                manifest_path,
                yaml_path,
                fingerprint,
            )
            if existing_manifest is not None:
                logger.info(
                    "复用YOLO数据集快照: task_id=%s fingerprint=%s",
                    task.id,
                    fingerprint,
                )
                return DatasetBuildResult(
                    fingerprint=fingerprint,
                    yaml_path=yaml_path,
                    manifest=existing_manifest,
                    reused=True,
                )

            snapshot_root.mkdir(parents=True, exist_ok=True)
            temp_dir = snapshot_root / f".{fingerprint}.tmp-{uuid.uuid4().hex}"
            try:
                manifest = self._write_snapshot(
                    temp_dir,
                    snapshot_dir,
                    task.id,
                    val_split,
                    fingerprint,
                    records,
                    train_ids,
                    val_ids,
                    category_manifest,
                )
                if snapshot_dir.exists():
                    shutil.rmtree(snapshot_dir)
                temp_dir.replace(snapshot_dir)
            except Exception:
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                raise

            logger.info(
                "创建YOLO数据集快照: task_id=%s fingerprint=%s train=%s val=%s",
                task.id,
                fingerprint,
                len(train_ids),
                len(val_ids),
            )
            return DatasetBuildResult(
                fingerprint=fingerprint,
                yaml_path=yaml_path,
                manifest=manifest,
                reused=False,
            )
        finally:
            db.close()

    @staticmethod
    def _build_records(
        images: List[ImageModel],
        cat_id_to_yolo_idx: Dict[int, int],
    ) -> List[DatasetImageRecord]:
        records = []
        for image in images:
            annotation_data = image.annotation_jsonb
            if not annotation_data:
                continue
            if isinstance(annotation_data, str):
                try:
                    annotation_data = json.loads(annotation_data)
                except (json.JSONDecodeError, TypeError):
                    continue
            if not isinstance(annotation_data, dict):
                continue

            dataset = CocoDataset.from_coco_dict(annotation_data)
            lines = tuple(
                sorted(
                    line
                    for annotation in dataset.annotations
                    if (
                        line := coco_ann_to_yolo_line(
                            annotation,
                            image.width,
                            image.height,
                            cat_id_to_yolo_idx,
                        )
                    )
                )
            )
            if lines:
                records.append(
                    DatasetImageRecord(
                        image_id=image.id,
                        file_name=image.file_name,
                        s3_key=image.s3_key,
                        width=image.width,
                        height=image.height,
                        yolo_lines=lines,
                    )
                )
        return records

    @staticmethod
    def _read_complete_manifest(
        manifest_path: Path,
        yaml_path: Path,
        fingerprint: str,
    ) -> Optional[Dict]:
        if not manifest_path.is_file() or not yaml_path.is_file():
            return None
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if manifest.get("fingerprint") != fingerprint or not manifest.get("complete"):
            return None
        snapshot_dir = manifest_path.parent
        for split in ("train", "val"):
            for item in manifest.get(split, []):
                snapshot_name = item.get("snapshot_file_name")
                if not snapshot_name:
                    return None
                image_path = snapshot_dir / "images" / split / snapshot_name
                label_path = snapshot_dir / "labels" / split / f"{Path(snapshot_name).stem}.txt"
                if not image_path.is_file() or not label_path.is_file():
                    return None
        return manifest

    @staticmethod
    def _write_snapshot(
        snapshot_dir: Path,
        published_snapshot_dir: Path,
        task_id: int,
        val_split: float,
        fingerprint: str,
        records: List[DatasetImageRecord],
        train_ids: Set[int],
        val_ids: Set[int],
        categories: List[Dict],
    ) -> Dict:
        directories = {
            "train_images": snapshot_dir / "images" / "train",
            "val_images": snapshot_dir / "images" / "val",
            "train_labels": snapshot_dir / "labels" / "train",
            "val_labels": snapshot_dir / "labels" / "val",
        }
        for directory in directories.values():
            directory.mkdir(parents=True, exist_ok=True)

        train_manifest = []
        val_manifest = []
        for record in sorted(records, key=lambda value: value.image_id):
            split = "train" if record.image_id in train_ids else "val"
            safe_name = Path(record.file_name).name
            snapshot_name = f"{record.image_id}_{safe_name}"
            stem = Path(snapshot_name).stem
            image_path = directories[f"{split}_images"] / snapshot_name
            label_path = directories[f"{split}_labels"] / f"{stem}.txt"
            try:
                image_bytes = s3.get_object(Bucket=S3_BUCKET, Key=record.s3_key)["Body"].read()
            except Exception as exc:
                raise RuntimeError(f"下载训练图片失败: {record.file_name}") from exc
            image_path.write_bytes(image_bytes)
            label_path.write_text("\n".join(record.yolo_lines), encoding="utf-8")
            item = {
                "image_id": record.image_id,
                "source_file_name": record.file_name,
                "snapshot_file_name": snapshot_name,
                "s3_key": record.s3_key,
            }
            (train_manifest if split == "train" else val_manifest).append(item)

        names = {item["yolo_id"]: item["name"] for item in categories}
        yaml_data = {
            "path": str(published_snapshot_dir.resolve()),
            "train": "images/train",
            "val": "images/val",
            "nc": len(names),
            "names": names,
        }
        (snapshot_dir / "data.yaml").write_text(
            yaml.dump(yaml_data, allow_unicode=True),
            encoding="utf-8",
        )
        manifest = {
            "version": DATASET_SNAPSHOT_VERSION,
            "complete": True,
            "fingerprint": fingerprint,
            "task_id": task_id,
            "val_split": val_split,
            "image_count": len(records),
            "train_count": len(train_manifest),
            "val_count": len(val_manifest),
            "categories": categories,
            "train": train_manifest,
            "val": val_manifest,
        }
        (snapshot_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return manifest
