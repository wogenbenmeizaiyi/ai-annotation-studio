from celery.result import AsyncResult

from core.config import config
from core.mq.celery_app import celery_app
from core.schemas.task import RecognitionTaskPayload


def submit_recognition_task(
    payload: RecognitionTaskPayload,
    task_id: str | None = None,
) -> AsyncResult:
    """提交识别任务，API 层不直接依赖 worker task 实现。"""
    return celery_app.send_task(
        config.RECOGNIZE_IMAGE_TASK_NAME,
        task_id=task_id,
        kwargs=payload.to_dict(),
        queue=config.QUEUE_NAME,
        routing_key=config.QUEUE_NAME,
    )


def get_recognition_task_result(task_id: str) -> AsyncResult:
    """查询识别任务在 Celery backend 中的状态。"""
    return AsyncResult(task_id, app=celery_app)
