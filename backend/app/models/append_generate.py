from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AppendGenerateRecord(Base):
    """追加生成记录"""
    __tablename__ = "append_generate_records"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    existing_cases: Mapped[str] = mapped_column(Text, comment="已有用例内容")
    requirement_text: Mapped[str] = mapped_column(Text, comment="需求描述")
    model_name: Mapped[str] = mapped_column(String, comment="模型名称")
    appended_content: Mapped[str] = mapped_column(Text, comment="追加生成的用例内容(JSON)")
    total_count: Mapped[int] = mapped_column(Integer, default=0, comment="追加用例数量")
    client_model_key: Mapped[Optional[str]] = mapped_column(String, comment="客户端模型Key")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
