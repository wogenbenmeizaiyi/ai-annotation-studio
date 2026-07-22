from pydantic import BaseModel, Field


class TaskProgress(BaseModel, frozen=True):
    """任务处理进度信息"""

    processed: int = Field(description="已处理的图片数量")
    total: int = Field(description="图片总数")
    percent: float = Field(description="处理进度百分比 (0-100)")


class TaskResult(BaseModel, frozen=True):
    """识别任务执行结果"""

    task_id: str = Field(description="任务唯一标识")
    detection_type: str = Field(description="识别类型 (如 multimodal, yolo_detection)")
    prompt_or_model: str = Field(description="提示词或模型名称")
    image_count: int = Field(description="成功处理的图片数量")
    results: list[dict] = Field(description="每张图片的 COCO 格式识别结果列表")
    progress: TaskProgress = Field(description="任务进度信息")


class RecognitionStatus(BaseModel, frozen=True):
    """识别任务 API 统一响应"""

    task_id: str = Field(description="任务唯一标识")
    status: str = Field(description="任务状态: pending / processing / success / failed")
    result: TaskResult | None = Field(
        default=None, description="任务结果 (仅 status=success 时有值)"
    )
    progress: TaskProgress | None = Field(
        default=None, description="任务进度 (仅 status=processing/failed 时有值)"
    )
    error: str | None = Field(
        default=None, description="错误信息 (仅 status=failed 时有值)"
    )

    def to_response(self) -> dict:
        """转为 API 响应 dict，排除 None 字段"""
        return self.model_dump(mode="json", exclude_none=True)
