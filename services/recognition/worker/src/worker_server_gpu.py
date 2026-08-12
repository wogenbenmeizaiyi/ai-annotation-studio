import logging

from celery.signals import worker_ready

from core.mq import MULTIMODAL_TASK_NAME, celery_app
from core.mq.task_infra import ensure_task_infra
from tasks import gpu as _gpu_tasks  # noqa: F401
from tasks.rejected import register_rejected_tasks

register_rejected_tasks((MULTIMODAL_TASK_NAME,))

logger = logging.getLogger(__name__)


@worker_ready.connect
def declare_task_infra(**_kwargs) -> None:
    try:
        ensure_task_infra()
    except Exception:
        logger.exception("failed to declare task RabbitMQ infrastructure")
        raise


if __name__ == "__main__":
    celery_app.start()
