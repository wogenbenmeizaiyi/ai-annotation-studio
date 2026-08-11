import json
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Boolean,
    BigInteger,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.database import Base


class ImageModel(Base):
    __tablename__ = "images"
    __table_args__ = {"comment": "任务图片表"}

    id = Column(Integer, primary_key=True, autoincrement=True, comment="图片ID")
    task_id = Column(
        Integer,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属任务ID",
    )
    file_name = Column(String(255), nullable=False, comment="图片文件名")
    original_name = Column(String(255), default="", comment="原始上传文件名")
    s3_key = Column(String(512), nullable=False, comment="S3存储路径")
    width = Column(Integer, default=0, comment="图片宽度(px)")
    height = Column(Integer, default=0, comment="图片高度(px)")
    file_size = Column(BigInteger, default=0, comment="文件大小(bytes)")
    detection_type = Column(String(100), nullable=False, comment="检测类型")
    is_annotated = Column(Boolean, default=False, comment="是否已标注")
    is_deleted = Column(Boolean, default=False, comment="是否已删除")
    annotation_jsonb = Column(JSONB, nullable=True, comment="COCO标注数据(JSONB)")
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

    task = relationship("TaskModel", back_populates="images")

    def to_dict(self) -> dict:
        annotation_data = None
        if self.annotation_jsonb:
            if isinstance(self.annotation_jsonb, dict):
                annotation_data = self.annotation_jsonb
            elif isinstance(self.annotation_jsonb, str):
                try:
                    annotation_data = json.loads(self.annotation_jsonb)
                except (json.JSONDecodeError, TypeError):
                    annotation_data = None

        return {
            "id": self.id,
            "task_id": self.task_id,
            "file_name": self.file_name,
            "original_name": self.original_name,
            "s3_key": self.s3_key,
            "width": self.width,
            "height": self.height,
            "file_size": self.file_size,
            "detection_type": self.detection_type,
            "is_annotated": self.is_annotated,
            "annotation_jsonb": annotation_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
