from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from celery.exceptions import Reject

from core.mq.task_routing import get_task_queue_spec
from tasks import recognize
from tasks import executor


def _task(routing_key: str, retries: int = 0):
    return SimpleNamespace(
        request=SimpleNamespace(
            id="task-123",
            retries=retries,
            delivery_info={"routing_key": routing_key},
        ),
        max_retries=3,
        retry=Mock(),
        update_state=Mock(),
    )


@pytest.mark.parametrize(
    ("detection_type", "allowed_types"),
    [(1, {1, 2, 3}), (2, {1, 2, 3}), (3, {1, 2, 3}), (4, {4})],
)
def test_worker_accepts_only_matching_routing_key(
    detection_type: int,
    allowed_types: set[int],
) -> None:
    spec = get_task_queue_spec(detection_type)

    recognize.validate_task_delivery(
        _task(spec.routing_key),
        detection_type,
        frozenset(allowed_types),
    )


def test_worker_rejects_task_sent_to_wrong_resource_pool() -> None:
    task = _task(get_task_queue_spec(4).routing_key)

    with pytest.raises(Reject) as error:
        recognize.validate_task_delivery(task, 1, frozenset({1, 2, 3}))

    assert error.value.requeue is False


def test_worker_rejects_matching_type_on_wrong_routing_key() -> None:
    task = _task(get_task_queue_spec(1).routing_key)

    with pytest.raises(Reject) as error:
        recognize.validate_task_delivery(task, 3, frozenset({1, 2, 3}))

    assert error.value.requeue is False


def test_retry_preserves_original_route() -> None:
    spec = get_task_queue_spec(3)
    task = _task(spec.routing_key)
    failure = RuntimeError("temporary failure")

    recognize.retry_on_expected_route(task, failure, spec)

    task.retry.assert_called_once_with(
        exc=failure,
        queue=spec.queue_name,
        exchange=spec.exchange_name,
        routing_key=spec.routing_key,
    )


def test_terminal_failure_before_db_open_marks_record_failed(monkeypatch) -> None:
    task = _task(get_task_queue_spec(4).routing_key, retries=3)
    mark_failed = Mock()
    monkeypatch.setattr(executor, "mark_task_failed", mark_failed)

    with pytest.raises(Reject) as error:
        executor.execute_recognition_task(
            task,
            {
                "task_id": "task-123",
                "detection_type": 4,
                "text": "prompt",
                "images": [],
            },
            service_factory=Mock(),
            allowed_detection_types=frozenset({4}),
            wait_for_resources=Mock(),
        )

    assert error.value.requeue is False
    mark_failed.assert_called_once_with("task-123", "images is required")


def test_retry_publish_failure_marks_record_failed(monkeypatch) -> None:
    spec = get_task_queue_spec(4)
    task = _task(spec.routing_key)
    task.retry.side_effect = Reject("broker unavailable", requeue=False)
    mark_failed = Mock()
    monkeypatch.setattr(executor, "mark_task_failed", mark_failed)

    with pytest.raises(Reject):
        executor.execute_recognition_task(
            task,
            {
                "task_id": "task-123",
                "detection_type": 4,
                "text": "prompt",
                "images": ["https://images.example.test/example.jpg"],
            },
            service_factory=Mock(side_effect=RuntimeError("temporary failure")),
            allowed_detection_types=frozenset({4}),
            wait_for_resources=Mock(),
        )

    mark_failed.assert_called_once_with("task-123", "('broker unavailable', False)")


def test_failure_state_error_does_not_replace_delivery_reject(monkeypatch) -> None:
    task = _task(get_task_queue_spec(4).routing_key)
    monkeypatch.setattr(executor, "SessionLocal", Mock(side_effect=RuntimeError("db down")))

    with pytest.raises(Reject) as error:
        executor.execute_recognition_task(
            task,
            {"task_id": "task-123", "detection_type": 1, "images": ["x"]},
            service_factory=Mock(),
            allowed_detection_types=frozenset({4}),
            wait_for_resources=Mock(),
        )

    assert error.value.requeue is False
