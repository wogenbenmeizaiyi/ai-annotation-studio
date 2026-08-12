import logging
import uuid

from sqlalchemy.orm import Session

from core.db import SessionLocal
from core.mq import submit_recognition_task
from core.mq.task_routing import normalize_detection_type
from core.schemas.recognition import RecognitionTaskRecord
from core.schemas.task import RecognitionRecordedSubmitRequest

logger = logging.getLogger(__name__)


class RecognitionTaskPublishError(RuntimeError):
    """任务记录已保存，但投递到 Broker 失败。"""


def _mark_publish_failed(
    task_id: str,
    record: RecognitionTaskRecord,
    db: Session,
    error: str,
) -> None:
    message = f"task publish failed: {error}"[:2000]
    record.status = "failed"
    record.last_callback_error = message
    try:
        db.commit()
        return
    except Exception:
        logger.exception(
            "failed to mark unpublished recognition task failed task_id=%s",
            task_id,
        )
        try:
            db.rollback()
        except Exception:
            logger.exception(
                "failed to rollback publish failure state task_id=%s",
                task_id,
            )

    retry_db = None
    try:
        retry_db = SessionLocal()
        retry_record = (
            retry_db.query(RecognitionTaskRecord)
            .filter(RecognitionTaskRecord.task_id == task_id)
            .one_or_none()
        )
        if retry_record is None:
            logger.error(
                "unpublished recognition task record not found task_id=%s",
                task_id,
            )
            return
        retry_record.status = "failed"
        retry_record.last_callback_error = message
        retry_db.commit()
    except Exception:
        if retry_db is not None:
            try:
                retry_db.rollback()
            except Exception:
                logger.exception(
                    "independent failure-state rollback failed task_id=%s",
                    task_id,
                )
        logger.exception(
            "independent failure-state update failed task_id=%s",
            task_id,
        )
    finally:
        if retry_db is not None:
            try:
                retry_db.close()
            except Exception:
                logger.exception(
                    "independent failure-state session close failed task_id=%s",
                    task_id,
                )


def submit_recorded_recognition(
    request: RecognitionRecordedSubmitRequest,
    db: Session,
) -> str:
    """保存任务记录，并用同一个 task_id 提交识别任务。"""
    request.detection_type = normalize_detection_type(request.detection_type)
    task_id = str(uuid.uuid4())
    logger.info(
        "submitting recognition task task_id=%s image_count=%s",
        task_id,
        len(request.images),
    )

    record = RecognitionTaskRecord(
        task_id=task_id,
        status="pending",
        callback_url=request.callback_url or "",
        request_payload=request.to_record_payload(),
    )

    db.add(record)
    logger.info(
        "db commit recognition task record started task_id=%s",
        task_id,
    )
    try:
        db.commit()
        db.refresh(record)
    except Exception:
        logger.exception("failed to save recognition task record task_id=%s", task_id)
        db.rollback()
        logger.info("db rollback recognition task record succeeded task_id=%s", task_id)
        raise

    try:
        submit_recognition_task(request.to_task_payload(), task_id=task_id)
    except Exception as exc:
        logger.exception("failed to publish recognition task task_id=%s", task_id)
        _mark_publish_failed(task_id, record, db, str(exc))
        raise RecognitionTaskPublishError(str(exc)) from exc
    logger.info("recognition task submitted task_id=%s", task_id)

    logger.info(
        "db commit recognition task record succeeded id=%s task_id=%s status=pending",
        record.id,
        task_id,
    )
    return task_id
