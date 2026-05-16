from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TranslationCreateRequest(BaseModel):
    """Request to create a new translation (used internally, not exposed as Pydantic)."""
    pass


class TranslationResponse(BaseModel):
    id: str
    original_requirement_text: str = Field(alias="originalRequirementText")
    translated_content: str = Field(alias="translatedContent")
    reviewed_content: Optional[str] = Field(default=None, alias="reviewedContent")
    status: str
    model_name: str = Field(alias="modelName")
    created_at: datetime = Field(alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")

    model_config = {"populate_by_name": True}


class TranslationListItem(BaseModel):
    id: str
    requirement_preview: str = Field(alias="requirementPreview")
    status: str
    model_name: str = Field(alias="modelName")
    created_at: datetime = Field(alias="createdAt")

    model_config = {"populate_by_name": True}


class TranslationListResponse(BaseModel):
    items: list[TranslationListItem]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")

    model_config = {"populate_by_name": True}


class TranslationUpdateRequest(BaseModel):
    reviewed_content: str = Field(alias="reviewedContent")
    status: str = "reviewed"

    model_config = {"populate_by_name": True}
