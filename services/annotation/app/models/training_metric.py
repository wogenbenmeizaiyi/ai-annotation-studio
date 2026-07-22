from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    Boolean,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.database import Base


class TrainingMetricModel(Base):
    __tablename__ = "training_metrics"
    __table_args__ = {"comment": "YOLO训练每轮指标表"}

    id = Column(Integer, primary_key=True, autoincrement=True, comment="记录ID")
    train_task_id = Column(
        Integer,
        ForeignKey("train_tasks.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联的训练任务ID",
    )
    epoch = Column(Integer, nullable=False, comment="当前轮次(从1开始)")
    time_cost = Column(Float, nullable=True, comment="本轮耗时(秒)")

    # 训练损失
    train_box_loss = Column(Float, nullable=True, comment="训练box损失")
    train_seg_loss = Column(Float, nullable=True, comment="训练mask分割损失")
    train_cls_loss = Column(Float, nullable=True, comment="训练分类损失")
    train_dfl_loss = Column(Float, nullable=True, comment="训练DFL损失")

    # 验证损失
    val_box_loss = Column(Float, nullable=True, comment="验证box损失")
    val_seg_loss = Column(Float, nullable=True, comment="验证mask分割损失")
    val_cls_loss = Column(Float, nullable=True, comment="验证分类损失")
    val_dfl_loss = Column(Float, nullable=True, comment="验证DFL损失")

    # 评估指标
    precision = Column(Float, nullable=True, comment="精确率")
    recall = Column(Float, nullable=True, comment="召回率")
    map50 = Column(Float, nullable=True, comment="mAP@0.5")
    map50_95 = Column(Float, nullable=True, comment="mAP@0.5:0.95")
    mask_precision = Column(Float, nullable=True, comment="Mask精确率")
    mask_recall = Column(Float, nullable=True, comment="Mask召回率")
    mask_map50 = Column(Float, nullable=True, comment="Mask mAP@0.5")
    mask_map50_95 = Column(Float, nullable=True, comment="Mask mAP@0.5:0.95")
    fitness = Column(Float, nullable=True, comment="Ultralytics综合适应度")
    per_class_metrics = Column(JSONB, nullable=True, comment="逐类别Box和Mask评估指标")

    # 学习率
    lr_pg0 = Column(Float, nullable=True, comment="学习率参数组0")
    lr_pg1 = Column(Float, nullable=True, comment="学习率参数组1")
    lr_pg2 = Column(Float, nullable=True, comment="学习率参数组2")

    is_best = Column(Boolean, default=False, comment="是否为最优轮次")
    is_deleted = Column(Boolean, default=False, comment="是否已逻辑删除")
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        comment="创建时间",
    )

    train_task = relationship("TrainTaskModel", back_populates="metrics")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "train_task_id": self.train_task_id,
            "epoch": self.epoch,
            "time_cost": self.time_cost,
            "train_box_loss": self.train_box_loss,
            "train_seg_loss": self.train_seg_loss,
            "train_cls_loss": self.train_cls_loss,
            "train_dfl_loss": self.train_dfl_loss,
            "val_box_loss": self.val_box_loss,
            "val_seg_loss": self.val_seg_loss,
            "val_cls_loss": self.val_cls_loss,
            "val_dfl_loss": self.val_dfl_loss,
            "precision": self.precision,
            "recall": self.recall,
            "map50": self.map50,
            "map50_95": self.map50_95,
            "mask_precision": self.mask_precision,
            "mask_recall": self.mask_recall,
            "mask_map50": self.mask_map50,
            "mask_map50_95": self.mask_map50_95,
            "fitness": self.fitness,
            "per_class_metrics": self.per_class_metrics,
            "lr_pg0": self.lr_pg0,
            "lr_pg1": self.lr_pg1,
            "lr_pg2": self.lr_pg2,
            "is_best": self.is_best,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
