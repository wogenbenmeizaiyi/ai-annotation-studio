from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base


class RecognitionTaskRecord(Base):
    """识别任务提交记录。"""

    __tablename__ = "recognition_task_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="pending")
    owner_subject_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    callback_url: Mapped[str] = mapped_column(String(2048))
    request_payload: Mapped[dict] = mapped_column(JSONB)
    result_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    callback_attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_callback_status_code: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    last_callback_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    callback_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
