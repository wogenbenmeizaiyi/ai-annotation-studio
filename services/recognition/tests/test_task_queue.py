from unittest.mock import Mock

import pytest

from core.mq import task_queue
from core.mq.task_routing import get_task_queue_spec
from core.schemas.task import RecognitionTaskPayload


@pytest.mark.parametrize("detection_type", [1, 2, 3, 4])
def test_submit_recognition_task_uses_explicit_route(
    monkeypatch,
    detection_type: int,
) -> None:
    send_task = Mock(return_value=object())
    monkeypatch.setattr(task_queue.celery_app, "send_task", send_task)
    payload = RecognitionTaskPayload(
        detection_type=detection_type,
        text="test-model-or-prompt",
        images=["https://images.example.test/example.jpg"],
        project_name="test-project",
    )

    result = task_queue.submit_recognition_task(payload, task_id="task-123")

    spec = get_task_queue_spec(detection_type)
    assert result is send_task.return_value
    send_task.assert_called_once_with(
        spec.task_name,
        task_id="task-123",
        kwargs=payload.to_dict(),
        queue=spec.queue_name,
        exchange=spec.exchange_name,
        routing_key=spec.routing_key,
    )


def test_submit_recognition_task_rejects_invalid_type_before_publish(
    monkeypatch,
) -> None:
    send_task = Mock()
    monkeypatch.setattr(task_queue.celery_app, "send_task", send_task)
    payload = RecognitionTaskPayload(detection_type=99, images=["https://example.test/a"])

    with pytest.raises(ValueError):
        task_queue.submit_recognition_task(payload)

    send_task.assert_not_called()
