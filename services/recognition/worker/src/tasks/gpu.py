from core.mq import GPU_TASK_NAME, celery_app
from engine.services.sam_segmentation_service import SamSegmentationService
from engine.services.yolo_detection_service import YoloDetectionService
from engine.services.yolo_segmentation_service import YoloSegmentationService
from tasks.gpu_resources import release_gpu_cache, wait_for_gpu_resources
from tasks.executor import execute_recognition_task


def _create_gpu_service(detection_type: int):
    factories = {
        1: YoloDetectionService,
        2: YoloSegmentationService,
        3: SamSegmentationService,
    }
    return factories[detection_type]()


@celery_app.task(
    name=GPU_TASK_NAME,
    bind=True,
    default_retry_delay=30,
    max_retries=3,
)
def process_gpu(self, **kwargs) -> dict:
    return execute_recognition_task(
        self,
        kwargs,
        service_factory=_create_gpu_service,
        allowed_detection_types=frozenset({1, 2, 3}),
        wait_for_resources=wait_for_gpu_resources,
        cleanup=release_gpu_cache,
    )
