import logging
import uuid

from sqlalchemy.orm import Session

from core.mq import submit_recognition_task
from core.schemas.recognition import RecognitionTaskRecord
from core.schemas.task import RecognitionRecordedSubmitRequest

logger = logging.getLogger(__name__)


def submit_recorded_recognition(
    request: RecognitionRecordedSubmitRequest,
    db: Session,
) -> str:
    """保存任务记录，并用同一个 task_id 提交识别任务。"""
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

    submit_recognition_task(request.to_task_payload(), task_id=task_id)
    logger.info("recognition task submitted task_id=%s", task_id)

    logger.info(
        "db commit recognition task record succeeded id=%s task_id=%s status=pending",
        record.id,
        task_id,
    )
    return task_id
