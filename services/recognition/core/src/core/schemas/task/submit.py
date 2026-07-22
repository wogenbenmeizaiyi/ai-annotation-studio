from dataclasses import dataclass, field


@dataclass
class RecognitionTaskPayload:
    """提交给识别 worker 的任务参数。"""

    detection_type: int
    text: str = ""
    category_name: str = ""
    images: list[str] = field(default_factory=list)
    project_name: str = "通用"

    @staticmethod
    def from_dict(data: dict) -> "RecognitionTaskPayload":
        return RecognitionTaskPayload(
            detection_type=data.get("detection_type"),
            text=data.get("text", ""),
            category_name=data.get("category_name", ""),
            images=data.get("images", []),
            project_name=data.get("project_name") or "通用",
        )

    def to_dict(self) -> dict:
        return {
            "detection_type": self.detection_type,
            "text": self.text,
            "category_name": self.category_name,
            "images": self.images,
            "project_name": self.project_name,
        }


@dataclass
class RecognitionSubmitRequest:
    """识别接口请求参数。后续回调、凭证等接口字段放在这里。"""

    detection_type: int
    text: str = ""
    category_name: str = ""
    images: list[str] = field(default_factory=list)
    project_name: str = "通用"

    def to_task_payload(self) -> RecognitionTaskPayload:
        return RecognitionTaskPayload(
            detection_type=self.detection_type,
            text=self.text,
            category_name=self.category_name,
            images=self.images,
            project_name=self.project_name,
        )


@dataclass
class RecognitionRecordedSubmitRequest:
    """会写入任务记录的识别接口请求参数。"""

    detection_type: int
    callback_url: str = ""
    text: str = ""
    category_name: str = ""
    images: list[str] = field(default_factory=list)
    project_name: str = "通用"

    def to_task_payload(self) -> RecognitionTaskPayload:
        return RecognitionTaskPayload(
            detection_type=self.detection_type,
            text=self.text,
            category_name=self.category_name,
            images=self.images,
            project_name=self.project_name,
        )

    def to_record_payload(self) -> dict:
        return {
            "detection_type": self.detection_type,
            "text": self.text,
            "category_name": self.category_name,
            "images": self.images,
            "project_name": self.project_name,
        }


@dataclass
class TypedRecognitionSubmitRequest:
    """固定识别类型的识别接口请求参数。"""

    text: str = ""
    images: list[str] = field(default_factory=list)
    project_name: str = "通用"
    callback_url: str = ""

    def to_recorded_request(
        self,
        detection_type: int,
    ) -> RecognitionRecordedSubmitRequest:
        return RecognitionRecordedSubmitRequest(
            detection_type=detection_type,
            callback_url=self.callback_url,
            text=self.text,
            category_name="",
            images=self.images,
            project_name=self.project_name,
        )
