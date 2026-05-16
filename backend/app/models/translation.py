from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class RequirementTranslation(Base):
    __tablename__ = "requirement_translations"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    original_requirement_text: Mapped[str] = mapped_column(Text, nullable=False)
    translated_content: Mapped[str] = mapped_column(Text, nullable=False)
    reviewed_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(default="pending_review", nullable=False)
    model_name: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
