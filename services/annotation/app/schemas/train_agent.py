from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.train_task import YoloTrainConfig


class AgentChatRequest(BaseModel):
    session_id: Optional[str] = None
    task_name: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1, max_length=10000)
    current_config: Optional[Dict[str, Any]] = None
    train_task_id: Optional[int] = None

    class Config:
        extra = "forbid"


class ConfigChange(BaseModel):
    field: str
    before: Any = None
    after: Any = None
    reason: str


class AgentModelResult(BaseModel):
    reply: str = Field(min_length=1)
    config_patch: Dict[str, Any] = Field(default_factory=dict)
    changes: List[ConfigChange] = Field(default_factory=list)
    questions: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    ready_to_apply: bool = False

    class Config:
        extra = "forbid"


class AgentChatData(BaseModel):
    session_id: str
    mode: str
    reply: str
    proposal_id: Optional[str] = None
    config: Optional[YoloTrainConfig] = None
    changes: List[ConfigChange] = Field(default_factory=list)
    questions: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    ready_to_apply: bool = False
    analysis: Optional[Dict[str, Any]] = None


class ConfirmProposalRequest(BaseModel):
    expected_config: Dict[str, Any]

    class Config:
        extra = "forbid"


class StartProposalRequest(BaseModel):
    confirmation_token: str = Field(min_length=32, max_length=512)

    class Config:
        extra = "forbid"


class CreateOptimizationProposalRequest(BaseModel):
    instruction: str = Field(
        default="基于本次训练报告生成下一轮优化训练参数草案",
        min_length=1,
        max_length=5000,
    )

    class Config:
        extra = "forbid"
