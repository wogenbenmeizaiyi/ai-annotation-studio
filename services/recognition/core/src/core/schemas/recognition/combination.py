from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db import Base
from core.schemas.recognition.model_config import RecognitionModelConfig


class RecognitionCombination(Base):
    """可复用的多模型综合检测配置。"""

    __tablename__ = "recognition_combinations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    project_name: Mapped[str] = mapped_column(String(255), index=True, default="通用")
    description: Mapped[str] = mapped_column(Text, default="")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    model_links: Mapped[list[RecognitionCombinationModel]] = relationship(
        back_populates="combination",
        cascade="all, delete-orphan",
        order_by="RecognitionCombinationModel.sort_order",
    )


class RecognitionCombinationModel(Base):
    """综合检测配置与模型配置的多对多关联。"""

    __tablename__ = "recognition_combination_models"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    combination_id: Mapped[int] = mapped_column(
        ForeignKey("recognition_combinations.id", ondelete="CASCADE"),
        index=True,
    )
    model_id: Mapped[int] = mapped_column(
        ForeignKey("recognition_model_configs.id"),
        index=True,
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    combination: Mapped[RecognitionCombination] = relationship(
        back_populates="model_links",
    )
    model: Mapped[RecognitionModelConfig] = relationship()
