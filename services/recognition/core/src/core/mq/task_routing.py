from dataclasses import dataclass

from core.schemas.recognition import RecognitionMethod

GPU_TASK_NAME = "recognition.process_gpu"
MULTIMODAL_TASK_NAME = "recognition.process_multimodal"
YOLO_QUEUE_NAME = "tasks.image.recognition.yolo"
SAM_QUEUE_NAME = "tasks.image.recognition.sam"
MULTIMODAL_QUEUE_NAME = "tasks.image.recognition.multimodal"


class UnsupportedDetectionType(ValueError):
    """识别类型不受支持。"""


@dataclass(frozen=True)
class TaskQueueSpec:
    key: str
    detection_types: tuple[int, ...]
    task_name: str
    queue_name: str
    exchange_name: str
    routing_key: str
    dead_letter_exchange: str
    dead_letter_queue: str
    dead_letter_routing_key: str


def _build_spec(
    key: str,
    detection_types: tuple[int, ...],
    task_name: str,
    queue_name: str,
) -> TaskQueueSpec:
    return TaskQueueSpec(
        key=key,
        detection_types=detection_types,
        task_name=task_name,
        queue_name=queue_name,
        exchange_name=queue_name,
        routing_key=queue_name,
        dead_letter_exchange=f"{queue_name}.dlx",
        dead_letter_queue=f"{queue_name}.dlq",
        dead_letter_routing_key=f"{queue_name}.dlq",
    )


TASK_QUEUE_SPECS: dict[str, TaskQueueSpec] = {
    "yolo": _build_spec("yolo", (1, 2), GPU_TASK_NAME, YOLO_QUEUE_NAME),
    "sam": _build_spec("sam", (3,), GPU_TASK_NAME, SAM_QUEUE_NAME),
    "multimodal": _build_spec(
        "multimodal",
        (4,),
        MULTIMODAL_TASK_NAME,
        MULTIMODAL_QUEUE_NAME,
    ),
}

_METHOD_BY_TYPE = {
    1: RecognitionMethod.YOLO_DETECTION,
    2: RecognitionMethod.YOLO_SEGMENTATION,
    3: RecognitionMethod.SAM_SEGMENTATION,
    4: RecognitionMethod.MULTIMODAL,
}
_TYPE_BY_METHOD = {method: value for value, method in _METHOD_BY_TYPE.items()}


def normalize_detection_type(value: object) -> int:
    """将整数、数字字符串或旧枚举值统一为 1–4。"""
    if isinstance(value, bool):
        raise UnsupportedDetectionType(f"Unsupported detection_type: {value!r}")
    if isinstance(value, RecognitionMethod):
        return _TYPE_BY_METHOD[value]
    if isinstance(value, int):
        detection_type = value
    elif isinstance(value, str):
        normalized = value.strip()
        if normalized.isdecimal():
            detection_type = int(normalized)
        else:
            try:
                detection_type = _TYPE_BY_METHOD[RecognitionMethod(normalized)]
            except (ValueError, KeyError) as exc:
                raise UnsupportedDetectionType(
                    f"Unsupported detection_type: {value!r}"
                ) from exc
    else:
        raise UnsupportedDetectionType(f"Unsupported detection_type: {value!r}")
    if detection_type not in _METHOD_BY_TYPE:
        raise UnsupportedDetectionType(
            f"Unsupported detection_type: {detection_type!r}"
        )
    return detection_type


def get_detection_method(value: object) -> RecognitionMethod:
    return _METHOD_BY_TYPE[normalize_detection_type(value)]


def get_task_queue_spec(value: object) -> TaskQueueSpec:
    detection_type = normalize_detection_type(value)
    for spec in TASK_QUEUE_SPECS.values():
        if detection_type in spec.detection_types:
            return spec
    raise UnsupportedDetectionType(f"Unsupported detection_type: {value!r}")


def route_recognition_task(
    name: str,
    _args: tuple,
    kwargs: dict,
    _options: dict,
    **_route_kwargs,
) -> dict[str, str] | None:
    """为非 API 调用者也按 detection_type 选择确定路由。"""
    if name not in {GPU_TASK_NAME, MULTIMODAL_TASK_NAME}:
        return None
    spec = get_task_queue_spec(kwargs.get("detection_type"))
    if spec.task_name != name:
        raise UnsupportedDetectionType(
            f"Task {name!r} does not support detection_type "
            f"{kwargs.get('detection_type')!r}"
        )
    return {
        "queue": spec.queue_name,
        "exchange": spec.exchange_name,
        "routing_key": spec.routing_key,
    }
