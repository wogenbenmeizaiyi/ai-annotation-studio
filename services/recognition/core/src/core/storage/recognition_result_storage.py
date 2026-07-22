import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from core.schemas.recognition.image_result import RecognitionImageResult
from core.schemas.recognition.task_record import RecognitionTaskRecord

logger = logging.getLogger(__name__)


def get_recognition_task_record(
    task_id: str,
    db: Session,
) -> RecognitionTaskRecord | None:
    """查询识别任务记录。"""
    return (
        db.query(RecognitionTaskRecord)
        .filter(RecognitionTaskRecord.task_id == task_id)
        .one_or_none()
    )


def prepare_recognition_result_storage(task_id: str, db: Session) -> bool:
    """清理任务旧结果，为 worker 批量写入单图结果做准备。"""
    record = get_recognition_task_record(task_id, db)
    if record is None:
        logger.warning("recognition task record not found task_id=%s", task_id)
        return False

    deleted_count = db.query(RecognitionImageResult).filter(
        RecognitionImageResult.task_id == task_id
    ).delete(synchronize_session=False)
    record.status = "processing"
    record.result_payload = None
    record.completed_at = None
    record.last_callback_error = None
    record.last_callback_status_code = None
    db.commit()
    logger.info(
        "prepared recognition result storage task_id=%s deleted_count=%s",
        task_id,
        deleted_count,
    )
    return True


def save_recognition_image_result_batch(
    task_id: str,
    results: list[dict],
    db: Session,
    default_service: str,
    default_detection_type: str,
) -> int:
    """批量保存一批单图识别结果。"""
    rows = []
    for item in results:
        if not isinstance(item, dict):
            logger.warning("recognition result item is not object task_id=%s", task_id)
            continue

        image_index = item.get("image_index")
        if image_index is None:
            logger.warning("recognition result missing image_index task_id=%s", task_id)
            continue

        annotations = item.get("annotations", [])
        rows.append(
            RecognitionImageResult(
                task_id=task_id,
                image_index=image_index,
                source_url=item.get("url", ""),
                service=item.get("service") or default_service,
                detection_type=item.get("detection_type") or default_detection_type,
                image_key=item.get("image_key", ""),
                coco_key=item.get("coco_key", ""),
                annotation_count=(
                    len(annotations) if isinstance(annotations, list) else 0
                ),
                result_payload=_to_coco_payload(item),
            )
        )

    if not rows:
        return 0

    db.add_all(rows)
    db.commit()
    logger.info(
        "saved recognition image result batch task_id=%s batch_count=%s",
        task_id,
        len(rows),
    )
    return len(rows)


def complete_recognition_result_storage(
    task_id: str,
    payload: dict,
    db: Session,
) -> RecognitionTaskRecord | None:
    """标记任务识别完成，并保存轻量汇总信息。"""
    record = get_recognition_task_record(task_id, db)
    if record is None:
        logger.warning("recognition task record not found task_id=%s", task_id)
        return None

    now = datetime.now(UTC)
    record.result_payload = payload
    record.status = "success"
    record.completed_at = now
    record.callback_started_at = record.callback_started_at or now
    record.last_callback_error = None
    record.last_callback_status_code = None
    db.commit()
    logger.info("completed recognition result storage task_id=%s", task_id)
    return record


def fail_recognition_result_storage(
    task_id: str,
    error: str,
    db: Session,
) -> None:
    """标记任务识别失败，保留已写入的部分单图结果用于排查。"""
    record = get_recognition_task_record(task_id, db)
    if record is None:
        return

    record.status = "failed"
    record.last_callback_error = error[:2000]
    db.commit()
    logger.info("marked recognition result storage failed task_id=%s", task_id)


def save_recognition_result(payload: dict, db: Session) -> RecognitionTaskRecord | None:
    """兼容旧流程：保存完整 MQ 结果和每张图片结果。"""
    task_id = payload.get("task_id")
    if not task_id:
        logger.error("recognition result message missing task_id")
        return None

    record = get_recognition_task_record(task_id, db)
    if record is None:
        logger.warning("recognition task record not found task_id=%s", task_id)
        return None

    logger.info(
        "saving legacy recognition result task_id=%s result_count=%s",
        task_id,
        len(payload.get("results", [])) if isinstance(payload.get("results"), list) else 0,
    )
    prepare_recognition_result_storage(task_id, db)
    results = payload.get("results", [])
    if isinstance(results, list):
        indexed_results = []
        for index, item in enumerate(results):
            if isinstance(item, dict):
                indexed_item = dict(item)
                indexed_item["image_index"] = index
                indexed_results.append(indexed_item)
        save_recognition_image_result_batch(
            task_id,
            indexed_results,
            db,
            payload.get("service", ""),
            payload.get("prompt_or_model", ""),
        )
    return complete_recognition_result_storage(task_id, payload, db)


def load_recognition_result_payload(task_id: str, db: Session) -> dict | None:
    """从数据库重建回调使用的完整任务结果。"""
    record = get_recognition_task_record(task_id, db)
    if record is None:
        logger.warning("recognition task record not found task_id=%s", task_id)
        return None

    rows = (
        db.query(RecognitionImageResult)
        .filter(RecognitionImageResult.task_id == task_id)
        .order_by(RecognitionImageResult.image_index.asc())
        .all()
    )
    results = []
    for row in rows:
        result_payload = row.result_payload or {}
        results.append(
            {
                "url": row.source_url,
                "service": row.service,
                "detection_type": row.detection_type,
                "count": row.annotation_count,
                "image_key": row.image_key,
                "coco_key": row.coco_key,
                "images": result_payload.get("images", []),
                "annotations": result_payload.get("annotations", []),
                "categories": result_payload.get("categories", []),
            }
        )

    return {
        "task_id": task_id,
        "results": results,
    }


def _to_coco_payload(item: dict) -> dict:
    """从单张图片结果中提取最基础的 COCO 标注结构。"""
    return {
        "images": item.get("images", []),
        "annotations": item.get("annotations", []),
        "categories": item.get("categories", []),
    }
