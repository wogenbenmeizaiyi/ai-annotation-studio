import logging
from collections.abc import Iterable

from celery.exceptions import Reject

from core.mq import celery_app
from tasks.executor import mark_task_failed

logger = logging.getLogger(__name__)


def register_rejected_tasks(task_names: Iterable[str]) -> None:
    """Register lightweight guards for task types this worker must never execute."""

    for task_name in task_names:
        if task_name in celery_app.tasks:
            continue

        def reject_wrong_worker(
            task,
            _guarded_task_name: str = task_name,
            **kwargs,
        ) -> None:
            task_id = kwargs.get("task_id") or task.request.id
            reason = (
                f"Task {_guarded_task_name!r} was delivered to the wrong worker pool"
            )
            logger.error("%s task_id=%s", reason, task_id)
            mark_task_failed(task_id, reason)
            raise Reject(reason, requeue=False)

        celery_app.task(name=task_name, bind=True)(reject_wrong_worker)
