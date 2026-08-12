import pytest

from core.mq.task_routing import (
    GPU_TASK_NAME,
    MULTIMODAL_QUEUE_NAME,
    MULTIMODAL_TASK_NAME,
    SAM_QUEUE_NAME,
    TASK_QUEUE_SPECS,
    UnsupportedDetectionType,
    YOLO_QUEUE_NAME,
    get_detection_method,
    get_task_queue_spec,
    normalize_detection_type,
    route_recognition_task,
)
from core.schemas.recognition import RecognitionMethod


@pytest.mark.parametrize(
    ("detection_type", "expected_method", "expected_key", "expected_task_name"),
    [
        (1, RecognitionMethod.YOLO_DETECTION, "yolo", GPU_TASK_NAME),
        (2, RecognitionMethod.YOLO_SEGMENTATION, "yolo", GPU_TASK_NAME),
        (3, RecognitionMethod.SAM_SEGMENTATION, "sam", GPU_TASK_NAME),
        (4, RecognitionMethod.MULTIMODAL, "multimodal", MULTIMODAL_TASK_NAME),
    ],
)
def test_detection_type_maps_to_expected_queue_and_task(
    detection_type: int,
    expected_method: RecognitionMethod,
    expected_key: str,
    expected_task_name: str,
) -> None:
    spec = get_task_queue_spec(detection_type)

    assert normalize_detection_type(detection_type) == detection_type
    assert get_detection_method(detection_type) is expected_method
    assert spec is TASK_QUEUE_SPECS[expected_key]
    assert detection_type in spec.detection_types
    assert spec.task_name == expected_task_name
    assert spec.queue_name == f"tasks.image.recognition.{expected_key}"
    assert spec.exchange_name == spec.queue_name
    assert spec.routing_key == spec.queue_name
    assert spec.dead_letter_exchange == f"{spec.queue_name}.dlx"
    assert spec.dead_letter_queue == f"{spec.queue_name}.dlq"
    assert spec.dead_letter_routing_key == spec.dead_letter_queue


def test_queue_specs_partition_all_supported_detection_types() -> None:
    assigned_types = [
        detection_type
        for spec in TASK_QUEUE_SPECS.values()
        for detection_type in spec.detection_types
    ]

    assert set(TASK_QUEUE_SPECS) == {"yolo", "sam", "multimodal"}
    assert sorted(assigned_types) == [1, 2, 3, 4]
    assert len(assigned_types) == len(set(assigned_types))


def test_queue_names_are_fixed_contracts() -> None:
    assert YOLO_QUEUE_NAME == "tasks.image.recognition.yolo"
    assert SAM_QUEUE_NAME == "tasks.image.recognition.sam"
    assert MULTIMODAL_QUEUE_NAME == "tasks.image.recognition.multimodal"


@pytest.mark.parametrize("detection_type", [0, 5, -1, None, "unknown"])
def test_invalid_detection_type_is_rejected(detection_type: object) -> None:
    with pytest.raises(UnsupportedDetectionType):
        normalize_detection_type(detection_type)
    with pytest.raises(UnsupportedDetectionType):
        get_detection_method(detection_type)
    with pytest.raises(UnsupportedDetectionType):
        get_task_queue_spec(detection_type)


@pytest.mark.parametrize("detection_type", [1, 2, 3, 4])
def test_celery_router_uses_payload_detection_type(detection_type: int) -> None:
    spec = get_task_queue_spec(detection_type)

    assert route_recognition_task(
        spec.task_name,
        (),
        {"detection_type": detection_type},
        {},
    ) == {
        "queue": spec.queue_name,
        "exchange": spec.exchange_name,
        "routing_key": spec.routing_key,
    }


def test_celery_router_rejects_task_name_and_type_mismatch() -> None:
    with pytest.raises(UnsupportedDetectionType):
        route_recognition_task(GPU_TASK_NAME, (), {"detection_type": 4}, {})
