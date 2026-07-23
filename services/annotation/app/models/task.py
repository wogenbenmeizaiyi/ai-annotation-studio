from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.database import Base


class TaskModel(Base):
    __tablename__ = "tasks"
    __table_args__ = {"comment": "标注任务表"}

    id = Column(Integer, primary_key=True, autoincrement=True, comment="任务ID")
    name = Column(String(255), unique=True, nullable=False, comment="任务名称")
    description = Column(Text, default="", comment="任务描述")
    detection_type = Column(String(100), nullable=False, comment="检测类型")
    owner_subject_id = Column(
        String(36), nullable=True, index=True, comment="创建者认证主体UUID"
    )
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

    categories = relationship(
        "CategoryModel", back_populates="task", cascade="all, delete-orphan"
    )
    images = relationship(
        "ImageModel", back_populates="task", cascade="all, delete-orphan"
    )
    train_tasks = relationship(
        "TrainTaskModel", back_populates="task", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "detection_type": self.detection_type,
            "description": self.description,
            "owner_subject_id": self.owner_subject_id,
            "categories": [c.to_dict() for c in self.categories],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CategoryModel(Base):
    __tablename__ = "categories"
    __table_args__ = {"comment": "标注任务类别表"}

    id = Column(Integer, primary_key=True, autoincrement=True, comment="类别ID")
    task_id = Column(
        Integer,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属任务ID",
    )
    name = Column(String(255), nullable=False, comment="类别名称")
    supercategory = Column(String(255), default="", comment="父类别名称")

    task = relationship("TaskModel", back_populates="categories")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "supercategory": self.supercategory,
        }
