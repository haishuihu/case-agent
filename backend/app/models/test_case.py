from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class GeneratedTestCase(Base):
    __tablename__ = "test_case_items"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    generation_task_id: Mapped[str] = mapped_column(
        ForeignKey("generation_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(4), default="P2", nullable=False)
    module: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    confirmation_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(10), default="ai", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
