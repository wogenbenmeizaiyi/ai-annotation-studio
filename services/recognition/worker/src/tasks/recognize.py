"""识别任务的通用执行器兼容入口。

实际 Celery 任务分别在 ``tasks.gpu`` 和 ``tasks.multimodal`` 注册。
"""

from tasks.executor import (
    ImageProcessingRetriesExhausted,
    execute_recognition_task,
    retry_on_expected_route,
    validate_task_delivery,
)

__all__ = [
    "execute_recognition_task",
    "ImageProcessingRetriesExhausted",
    "retry_on_expected_route",
    "validate_task_delivery",
]
