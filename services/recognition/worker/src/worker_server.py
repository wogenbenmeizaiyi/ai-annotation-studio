import logging

from celery.signals import worker_ready

from core.mq import celery_app
from core.mq.task_infra import ensure_task_infra

logger = logging.getLogger(__name__)


@worker_ready.connect
def declare_task_infra(**kwargs) -> None:
    """Worker 启动后主动声明任务 DLQ，便于 RabbitMQ 管理台可见。"""
    try:
        ensure_task_infra()
    except Exception:
        logger.exception("failed to declare task RabbitMQ infrastructure")
        raise

if __name__ == "__main__":
    celery_app.start()
