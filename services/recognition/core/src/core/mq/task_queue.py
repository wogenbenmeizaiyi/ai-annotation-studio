from celery.result import AsyncResult

from core.mq.celery_app import celery_app
from core.mq.task_routing import get_task_queue_spec
from core.schemas.task import RecognitionTaskPayload


def submit_recognition_task(
    payload: RecognitionTaskPayload,
    task_id: str | None = None,
) -> AsyncResult:
    """提交识别任务，API 层不直接依赖 worker task 实现。"""
    spec = get_task_queue_spec(payload.detection_type)
    return celery_app.send_task(
        spec.task_name,
        task_id=task_id,
        kwargs=payload.to_dict(),
        queue=spec.queue_name,
        exchange=spec.exchange_name,
        routing_key=spec.routing_key,
    )


def get_recognition_task_result(task_id: str) -> AsyncResult:
    """查询识别任务在 Celery backend 中的状态。"""
    return AsyncResult(task_id, app=celery_app)
