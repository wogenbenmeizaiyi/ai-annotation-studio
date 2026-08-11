from pydantic import BaseModel, Field


class ServiceTypeItem(BaseModel):
    """服务类型项"""

    id: int = Field(description="枚举数字")
    name: str = Field(description="英文标识")
    description: str = Field(description="中文说明")


class ServiceTypeListResponse(BaseModel):
    """服务类型列表响应"""

    services: list[ServiceTypeItem] = Field(description="可用的服务类型列表")


class YoloModelItem(BaseModel):
    """YOLO 模型项"""

    name: str = Field(description="模型名称（不含 .pt 后缀）")
    type: str = Field(description="模型类型: detection / segmentation")


class YoloModelListResponse(BaseModel):
    """YOLO 模型列表响应"""

    detection: list[str] = Field(description="检测模型名称列表")
    segmentation: list[str] = Field(description="分割模型名称列表")
