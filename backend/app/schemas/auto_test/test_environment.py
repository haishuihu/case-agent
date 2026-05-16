from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class EnvironmentCreate(BaseModel):
    name: str = Field(..., max_length=100, description="环境名称")
    base_url: Optional[str] = Field(default=None, max_length=500, description="基础URL")
    description: Optional[str] = Field(default=None, max_length=500)
    variables: Optional[dict] = Field(default=None, description="环境变量")
    is_active: bool = Field(default=True)


class EnvironmentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    base_url: Optional[str] = Field(default=None, max_length=500)
    description: Optional[str] = Field(default=None, max_length=500)
    variables: Optional[dict] = Field(default=None)
    is_active: Optional[bool] = None


class EnvironmentResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    name: str
    base_url: Optional[str] = None
    description: Optional[str] = None
    variables: Optional[dict] = None
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None

    @field_validator("variables", mode="before")
    @classmethod
    def parse_variables(cls, v: Any) -> Any:
        if isinstance(v, str):
            return json.loads(v)
        return v
