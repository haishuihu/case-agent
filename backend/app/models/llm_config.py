from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

if TYPE_CHECKING:
    pass


class LLMConfig(Base):
    """LLM 模型配置，支持 OpenAI 兼容 / Anthropic / Google AI 等多种 API 格式。"""
    __tablename__ = "llm_configs"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True, comment="归属用户ID（预留）")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="配置名称")
    provider: Mapped[str] = mapped_column(String(50), nullable=False, comment="供应商：openai/anthropic/google 等")
    api_format: Mapped[str] = mapped_column(
        String(20), nullable=False, default="openai_compatible",
        comment="API格式：openai_compatible / anthropic / google_ai"
    )
    base_url: Mapped[str] = mapped_column(String(500), nullable=False, comment="API Endpoint")
    api_key: Mapped[str] = mapped_column(String(500), nullable=False, comment="API 密钥")
    model_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="模型名称")
    max_output_tokens: Mapped[int] = mapped_column(Integer, default=131072, comment="最大输出Token数")
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=120, comment="请求超时秒数")
    supports_vision: Mapped[bool] = mapped_column(default=False, comment="是否支持视觉")
    supports_structured_output: Mapped[bool] = mapped_column(default=True, comment="是否支持结构化输出")
    extra_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="预留扩展配置")
    is_default: Mapped[bool] = mapped_column(default=False, comment="是否为默认配置")
    is_active: Mapped[bool] = mapped_column(default=True, comment="是否启用")
    display_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序权重")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )


class EmbeddingConfig(Base):
    """Embedding 模型配置。"""
    __tablename__ = "embedding_configs"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True, comment="归属用户ID（预留）")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="配置名称")
    provider: Mapped[str] = mapped_column(String(50), nullable=False, comment="供应商")
    api_format: Mapped[str] = mapped_column(
        String(20), nullable=False, default="openai_compatible",
        comment="API格式：openai_compatible / google_ai"
    )
    base_url: Mapped[str] = mapped_column(String(500), nullable=False, comment="API Endpoint")
    api_key: Mapped[str] = mapped_column(String(500), nullable=False, comment="API 密钥")
    model_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="Embedding 模型名称")
    dimensions: Mapped[int] = mapped_column(Integer, default=0, comment="向量维度（0=不指定）")
    extra_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="预留扩展配置")
    is_active: Mapped[bool] = mapped_column(default=True, comment="是否启用")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
