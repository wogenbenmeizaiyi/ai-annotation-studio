from dataclasses import dataclass, field
from typing import Any


@dataclass
class RecognitionRequest:
    image_path: str | None = None
    image_data: bytes | None = None
    detection_type: str = ""
    project_name: str = "通用"
    confidence: float = 0.5
    extra: dict[str, Any] = field(default_factory=dict)
