from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class QuickGenerateRecord(Base):
    __tablename__ = "quick_generate_records"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    requirement_text: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(nullable=False)
    output_content: Mapped[str] = mapped_column(Text, nullable=False)
    client_model_key: Mapped[Optional[str]] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
