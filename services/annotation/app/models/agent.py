"""YOLO Agent 会话、消息与训练草案模型。"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.database import Base


class AgentSessionModel(Base):
    __tablename__ = "agent_sessions"
    __table_args__ = {"comment": "YOLO Agent对话会话表"}

    id = Column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="Agent会话ID"
    )
    task_id = Column(
        Integer,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联标注任务ID",
    )
    train_task_id = Column(
        Integer,
        ForeignKey("train_tasks.id", ondelete="SET NULL"),
        nullable=True,
        comment="关联训练任务ID，参数模式为空",
    )
    mode = Column(String(32), nullable=False, default="config", comment="会话模式")
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="创建时间",
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="更新时间",
    )

    messages = relationship(
        "AgentMessageModel",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    proposals = relationship(
        "AgentConfigProposalModel",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class AgentMessageModel(Base):
    __tablename__ = "agent_messages"
    __table_args__ = {"comment": "YOLO Agent消息表"}

    id = Column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="消息ID"
    )
    session_id = Column(
        String(36),
        ForeignKey("agent_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属Agent会话ID",
    )
    role = Column(String(24), nullable=False, comment="消息角色")
    content = Column(Text, nullable=False, comment="消息正文")
    structured_json = Column(Text, nullable=True, comment="结构化响应JSON")
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="创建时间",
    )

    session = relationship("AgentSessionModel", back_populates="messages")


class AgentConfigProposalModel(Base):
    __tablename__ = "agent_config_proposals"
    __table_args__ = {"comment": "YOLO Agent训练参数草案表"}

    id = Column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="训练草案ID"
    )
    session_id = Column(
        String(36),
        ForeignKey("agent_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属Agent会话ID",
    )
    task_id = Column(
        Integer,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联标注任务ID",
    )
    source_train_task_id = Column(
        Integer,
        ForeignKey("train_tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="生成优化草案所依据的上一轮训练任务ID",
    )
    config_json = Column(Text, nullable=False, comment="完整训练参数JSON")
    config_hash = Column(String(64), nullable=False, comment="规范化参数SHA256")
    changes_json = Column(Text, nullable=False, default="[]", comment="参数变化JSON")
    warnings_json = Column(Text, nullable=False, default="[]", comment="风险提示JSON")
    status = Column(
        String(32), nullable=False, default="DRAFT", index=True, comment="草案状态"
    )
    confirmation_token_hash = Column(String(64), nullable=True, comment="确认令牌SHA256")
    confirmation_expires_at = Column(
        DateTime(timezone=True), nullable=True, comment="确认令牌过期时间"
    )
    confirmed_at = Column(DateTime(timezone=True), nullable=True, comment="用户确认时间")
    confirmation_used = Column(
        Boolean, nullable=False, default=False, comment="确认令牌是否已经使用"
    )
    train_task_id = Column(
        Integer,
        ForeignKey("train_tasks.id", ondelete="SET NULL"),
        nullable=True,
        comment="启动后的训练任务ID",
    )
    error_message = Column(Text, nullable=True, comment="启动失败信息")
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="创建时间",
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="更新时间",
    )

    session = relationship("AgentSessionModel", back_populates="proposals")


class AgentTrainingAnalysisModel(Base):
    __tablename__ = "agent_training_analyses"
    __table_args__ = {"comment": "YOLO训练完成后自动分析结果表"}

    id = Column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="自动分析ID"
    )
    train_task_id = Column(
        Integer,
        ForeignKey("train_tasks.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="关联训练任务ID，每个任务仅一条自动分析",
    )
    status = Column(
        String(32), nullable=False, default="PENDING", index=True, comment="分析状态"
    )
    analyzer_version = Column(String(32), nullable=True, comment="确定性分析器版本")
    model_name = Column(String(255), nullable=True, comment="生成总结使用的模型")
    analysis_json = Column(Text, nullable=True, comment="确定性指标分析JSON")
    model_result_json = Column(Text, nullable=True, comment="大模型结构化分析结果JSON")
    error_message = Column(Text, nullable=True, comment="自动分析失败信息")
    started_at = Column(DateTime(timezone=True), nullable=True, comment="分析开始时间")
    completed_at = Column(DateTime(timezone=True), nullable=True, comment="分析完成时间")
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="创建时间",
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="更新时间",
    )
