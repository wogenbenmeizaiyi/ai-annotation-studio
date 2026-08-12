from core.mq import MULTIMODAL_TASK_NAME, celery_app
from engine.services.multimodal_service import MultimodalService
from tasks.executor import execute_recognition_task
from tasks.resources import wait_for_system_resources


@celery_app.task(
    name=MULTIMODAL_TASK_NAME,
    bind=True,
    default_retry_delay=30,
    max_retries=3,
)
def process_multimodal(self, **kwargs) -> dict:
    return execute_recognition_task(
        self,
        kwargs,
        service_factory=lambda _detection_type: MultimodalService(),
        allowed_detection_types=frozenset({4}),
        wait_for_resources=wait_for_system_resources,
    )
