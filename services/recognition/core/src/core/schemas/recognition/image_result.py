from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base


class RecognitionImageResult(Base):
    """识别任务下每张图片的最终结果记录。"""

    __tablename__ = "recognition_image_results"
    __table_args__ = (
        UniqueConstraint("task_id", "image_index", name="uq_recognition_image_result"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("recognition_task_records.task_id"),
        index=True,
    )
    image_index: Mapped[int] = mapped_column(Integer)
    source_url: Mapped[str] = mapped_column(Text)
    service: Mapped[str] = mapped_column(String(64), index=True)
    detection_type: Mapped[str] = mapped_column(String(255), index=True)
    image_key: Mapped[str] = mapped_column(String(1024))
    coco_key: Mapped[str] = mapped_column(String(1024))
    annotation_count: Mapped[int] = mapped_column(Integer, default=0)
    result_payload: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
