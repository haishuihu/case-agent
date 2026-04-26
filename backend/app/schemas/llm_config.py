from __future__ import annotations

from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, Field


# ---- LLM Config ----

class LLMConfigBase(BaseModel):
    model_config = {"populate_by_name": True}

    name: str = Field(..., max_length=100)
    provider: str = Field(..., max_length=50)
    api_format: str = Field(
        default="openai_compatible", alias="apiFormat", max_length=20,
        description="API格式：openai_compatible / anthropic / google_ai"
    )
    base_url: str = Field(..., alias="baseUrl", max_length=500)
    api_key: str = Field(..., alias="apiKey", max_length=500)
    model_name: str = Field(..., alias="modelName", max_length=200)
    max_output_tokens: int = Field(default=131072, alias="maxOutputTokens", ge=1, le=10_000_000)
    timeout_seconds: int = Field(default=120, alias="timeoutSeconds", ge=1, le=600)
    supports_vision: bool = Field(default=False, alias="supportsVision")
    supports_structured_output: bool = Field(default=True, alias="supportsStructuredOutput")
    extra_config: Optional[dict] = Field(default=None, alias="extraConfig")
    is_active: bool = Field(default=True, alias="isActive")
    display_order: int = Field(default=0, alias="displayOrder", ge=0)


class LLMConfigCreate(LLMConfigBase):
    is_default: bool = Field(default=False, alias="isDefault")


class LLMConfigUpdate(BaseModel):
    model_config = {"populate_by_name": True}

    name: Optional[str] = Field(default=None, max_length=100)
    provider: Optional[str] = Field(default=None, max_length=50)
    api_format: Optional[str] = Field(default=None, alias="apiFormat", max_length=20)
    base_url: Optional[str] = Field(default=None, alias="baseUrl", max_length=500)
    api_key: Optional[str] = Field(default=None, alias="apiKey", max_length=500)
    model_name: Optional[str] = Field(default=None, alias="modelName", max_length=200)
    max_output_tokens: Optional[int] = Field(default=None, alias="maxOutputTokens", ge=1, le=10_000_000)
    timeout_seconds: Optional[int] = Field(default=None, alias="timeoutSeconds", ge=1, le=600)
    supports_vision: Optional[bool] = Field(default=None, alias="supportsVision")
    supports_structured_output: Optional[bool] = Field(default=None, alias="supportsStructuredOutput")
    extra_config: Optional[dict] = Field(default=None, alias="extraConfig")
    is_active: Optional[bool] = Field(default=None, alias="isActive")
    is_default: Optional[bool] = Field(default=None, alias="isDefault")
    display_order: Optional[int] = Field(default=None, alias="displayOrder", ge=0)


class LLMConfigResponse(BaseModel):
    model_config = {"populate_by_name": True, "from_attributes": True}

    id: str
    user_id: Optional[str] = Field(default=None, alias="userId")
    name: str
    provider: str
    api_format: str = Field(alias="apiFormat")
    base_url: str = Field(alias="baseUrl")
    model_name: str = Field(alias="modelName")
    max_output_tokens: int = Field(alias="maxOutputTokens")
    timeout_seconds: int = Field(alias="timeoutSeconds")
    supports_vision: bool = Field(alias="supportsVision")
    supports_structured_output: bool = Field(alias="supportsStructuredOutput")
    extra_config: Optional[dict] = Field(default=None, alias="extraConfig")
    is_default: bool = Field(alias="isDefault")
    is_active: bool = Field(alias="isActive")
    display_order: int = Field(alias="displayOrder")
    created_at: datetime = Field(alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")

    def model_dump(self, **kwargs):
        kwargs.setdefault("exclude", set())
        kwargs["exclude"] = {*kwargs["exclude"], "api_key"}
        return super().model_dump(**kwargs)


# ---- Embedding Config ----

class EmbeddingConfigBase(BaseModel):
    model_config = {"populate_by_name": True}

    name: str = Field(..., max_length=100)
    provider: str = Field(..., max_length=50)
    api_format: str = Field(
        default="openai_compatible", alias="apiFormat", max_length=20,
        description="API格式：openai_compatible / google_ai"
    )
    base_url: str = Field(..., alias="baseUrl", max_length=500)
    api_key: str = Field(..., alias="apiKey", max_length=500)
    model_name: str = Field(..., alias="modelName", max_length=200)
    dimensions: int = Field(default=0, alias="dimensions", ge=0)
    extra_config: Optional[dict] = Field(default=None, alias="extraConfig")
    is_active: bool = Field(default=True, alias="isActive")


class EmbeddingConfigCreate(EmbeddingConfigBase):
    pass


class EmbeddingConfigUpdate(BaseModel):
    model_config = {"populate_by_name": True}

    name: Optional[str] = Field(default=None, max_length=100)
    provider: Optional[str] = Field(default=None, max_length=50)
    api_format: Optional[str] = Field(default=None, alias="apiFormat", max_length=20)
    base_url: Optional[str] = Field(default=None, alias="baseUrl", max_length=500)
    api_key: Optional[str] = Field(default=None, alias="apiKey", max_length=500)
    model_name: Optional[str] = Field(default=None, alias="modelName", max_length=200)
    dimensions: Optional[int] = Field(default=None, alias="dimensions", ge=0)
    extra_config: Optional[dict] = Field(default=None, alias="extraConfig")
    is_active: Optional[bool] = Field(default=None, alias="isActive")


class EmbeddingConfigResponse(BaseModel):
    model_config = {"populate_by_name": True, "from_attributes": True}

    id: str
    user_id: Optional[str] = Field(default=None, alias="userId")
    name: str
    provider: str
    api_format: str = Field(alias="apiFormat")
    base_url: str = Field(alias="baseUrl")
    model_name: str = Field(alias="modelName")
    dimensions: int = Field(alias="dimensions")
    extra_config: Optional[dict] = Field(default=None, alias="extraConfig")
    is_active: bool = Field(alias="isActive")
    created_at: datetime = Field(alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")

    def model_dump(self, **kwargs):
        kwargs.setdefault("exclude", set())
        kwargs["exclude"] = {*kwargs["exclude"], "api_key"}
        return super().model_dump(**kwargs)


class TestConnectionRequest(BaseModel):
    model_config = {"populate_by_name": True}

    provider: str
    api_format: str = Field(alias="apiFormat")
    base_url: str = Field(alias="baseUrl")
    api_key: str = Field(alias="apiKey")
    model_name: str = Field(alias="modelName")
    timeout_seconds: int = Field(default=30, alias="timeoutSeconds")


class TestConnectionResponse(BaseModel):
    ok: bool
    message: str


class MigrateStatusResponse(BaseModel):
    needs_migration: bool
    llm_configs_count: int
    embedding_configs_count: int
    env_has_llm_config: bool
    env_has_embedding_config: bool


class SetDefaultResponse(BaseModel):
    ok: bool
    message: str
