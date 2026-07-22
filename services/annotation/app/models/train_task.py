from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Float,
    Boolean,
    Index,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.database import Base


class TrainTaskModel(Base):
    __tablename__ = "train_tasks"
    __table_args__ = (
        Index("ix_train_tasks_queue", "status", "priority", "queued_at", "id"),
        {"comment": "YOLO训练任务表"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="训练任务ID")
    task_id = Column(
        Integer,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联的标注任务ID",
    )
    parent_train_task_id = Column(
        Integer,
        ForeignKey("train_tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="本轮参数优化所依据的上一轮训练任务ID",
    )
    model_name = Column(String(255), default="yolov8m", comment="模型名称")
    status = Column(
        String(50),
        default="QUEUED",
        comment="训练状态: QUEUED/CLAIMED/RECOVERING/RUNNING/FINISHED/ERROR/CANCELLED",
    )
    pid = Column(Integer, nullable=True, comment="训练进程PID")
    progress = Column(Integer, default=0, comment="训练进度百分比")
    current_epoch = Column(Integer, default=0, comment="当前epoch")
    total_epochs = Column(Integer, default=0, comment="总epoch数")
    error_message = Column(Text, nullable=True, comment="错误信息")
    config_json = Column(Text, nullable=True, comment="训练配置JSON")
    log_path = Column(String(512), nullable=True, comment="训练日志路径")
    output_path = Column(String(512), nullable=True, comment="训练输出路径")
    priority = Column(Integer, nullable=False, default=0, comment="队列优先级")
    queued_at = Column(DateTime(timezone=True), nullable=True, comment="进入队列时间")
    started_at = Column(DateTime(timezone=True), nullable=True, comment="训练开始时间")
    finished_at = Column(DateTime(timezone=True), nullable=True, comment="训练结束时间")
    heartbeat_at = Column(DateTime(timezone=True), nullable=True, comment="Worker心跳时间")
    worker_id = Column(String(128), nullable=True, comment="领取任务的Worker标识")
    checkpoint_path = Column(
        String(1024), nullable=True, comment="断点文件路径"
    )
    dataset_fingerprint = Column(
        String(64), nullable=True, index=True, comment="训练数据集快照SHA256指纹"
    )
    dataset_yaml_path = Column(
        String(1024), nullable=True, comment="本次训练固定使用的数据集YAML路径"
    )
    dataset_manifest_path = Column(
        String(1024), nullable=True, comment="本次训练集/验证集划分清单路径"
    )
    attempt_count = Column(Integer, nullable=False, default=0, comment="执行次数")
    resume_count = Column(Integer, nullable=False, default=0, comment="断点恢复次数")
    is_deleted = Column(Boolean, default=False, comment="是否已删除")
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        comment="创建时间",
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="更新时间",
    )

    task = relationship("TaskModel", back_populates="train_tasks")
    metrics = relationship(
        "TrainingMetricModel",
        back_populates="train_task",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        import json

        config_val = None
        if self.config_json:
            try:
                config_val = json.loads(self.config_json)
            except (json.JSONDecodeError, TypeError):
                config_val = None

        return {
            "id": self.id,
            "task_id": self.task_id,
            "parent_train_task_id": self.parent_train_task_id,
            "model_name": self.model_name,
            "status": self.status,
            "pid": self.pid,
            "progress": self.progress,
            "current_epoch": self.current_epoch,
            "total_epochs": self.total_epochs,
            "error_message": self.error_message,
            "config": config_val,
            "log_path": self.log_path,
            "output_path": self.output_path,
            "priority": self.priority,
            "queued_at": self.queued_at.isoformat() if self.queued_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "heartbeat_at": self.heartbeat_at.isoformat() if self.heartbeat_at else None,
            "worker_id": self.worker_id,
            "checkpoint_path": self.checkpoint_path,
            "dataset_fingerprint": self.dataset_fingerprint,
            "dataset_yaml_path": self.dataset_yaml_path,
            "dataset_manifest_path": self.dataset_manifest_path,
            "attempt_count": self.attempt_count,
            "resume_count": self.resume_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
