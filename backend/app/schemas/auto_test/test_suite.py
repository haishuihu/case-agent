from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field, field_validator


# ---- TestSuite ----

class TestSuiteBase(BaseModel):
    name: str = Field(..., max_length=200, description="套件名称")
    description: Optional[str] = Field(default=None, description="套件描述")
    project_id: Optional[str] = Field(default=None, max_length=100, description="项目ID")
    is_active: bool = Field(default=True, description="是否启用")


class TestSuiteCreate(TestSuiteBase):
    pass


class TestSuiteUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = None
    project_id: Optional[str] = Field(default=None, max_length=100)
    is_active: Optional[bool] = None


class TestSuiteResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    name: str
    description: Optional[str] = None
    project_id: Optional[str] = None
    created_by: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None
    case_count: int = 0
    plan_count: int = 0


# ---- TestCase ----

class TestCaseBase(BaseModel):
    title: str = Field(..., max_length=300, description="用例标题")
    description: Optional[str] = Field(default=None, description="用例描述")
    case_type: str = Field(default="api", description="用例类型: api/ui/unit/integration")
    priority: int = Field(default=3, ge=1, le=5, description="优先级 1-5")
    tags: Optional[list[str]] = Field(default=None, description="标签列表")
    
    # API 测试字段
    method: Optional[str] = Field(default=None, max_length=10, description="HTTP方法")
    endpoint: Optional[str] = Field(default=None, max_length=500, description="API端点")
    headers: Optional[dict] = Field(default=None, description="请求头")
    request_body: Optional[dict] = Field(default=None, description="请求体")
    expected_status: Optional[int] = Field(default=200, description="预期状态码")
    expected_response: Optional[dict] = Field(default=None, description="预期响应")
    validation_rules: Optional[dict] = Field(default=None, description="验证规则")
    
    # UI 测试字段
    ui_selector: Optional[str] = Field(default=None, max_length=500, description="UI选择器")
    ui_action: Optional[str] = Field(default=None, max_length=50, description="UI动作")
    ui_expected: Optional[str] = Field(default=None, description="UI预期")
    
    # 其他
    test_data: Optional[dict] = Field(default=None, description="测试数据")
    extra_metadata: Optional[dict] = Field(default=None, description="扩展元数据")


class TestCaseCreate(TestCaseBase):
    suite_id: str = Field(..., description="所属套件ID")


class TestCaseUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=300)
    description: Optional[str] = None
    case_type: Optional[str] = None
    priority: Optional[int] = Field(default=None, ge=1, le=5)
    tags: Optional[list[str]] = None
    
    method: Optional[str] = None
    endpoint: Optional[str] = None
    headers: Optional[dict] = None
    request_body: Optional[dict] = None
    expected_status: Optional[int] = None
    expected_response: Optional[dict] = None
    validation_rules: Optional[dict] = None
    
    ui_selector: Optional[str] = None
    ui_action: Optional[str] = None
    ui_expected: Optional[str] = None
    
    test_data: Optional[dict] = None
    extra_metadata: Optional[dict] = None
    status: Optional[str] = None


class TestCaseResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    suite_id: str
    title: str
    description: Optional[str] = None
    case_type: str = "api"
    status: str = "active"
    priority: int = 3
    
    method: Optional[str] = None
    endpoint: Optional[str] = None
    headers: Optional[dict] = None
    request_body: Optional[dict] = None
    expected_status: Optional[int] = 200
    expected_response: Optional[dict] = None
    validation_rules: Optional[dict] = None
    
    ui_selector: Optional[str] = None
    ui_action: Optional[str] = None
    ui_expected: Optional[str] = None
    
    test_data: Optional[dict] = None
    extra_metadata: Optional[dict] = None
    tags: Optional[list[str]] = None
    current_version: int = 1
    
    created_at: datetime
    updated_at: Optional[datetime] = None


# ---- TestCaseTag ----

class TestCaseTagBase(BaseModel):
    name: str = Field(..., max_length=50, description="标签名称")
    color: str = Field(default="#0071e3", max_length=20, description="标签颜色")
    description: Optional[str] = Field(default=None, max_length=200, description="标签描述")


class TestCaseTagCreate(TestCaseTagBase):
    pass


class TestCaseTagResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    name: str
    color: str = "#0071e3"
    description: Optional[str] = None
    created_at: datetime


# ---- TestCaseVersion ----

class TestCaseVersionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    case_id: str
    version: int
    content: Optional[dict] = None
    change_summary: Optional[str] = None
    changed_by: Optional[str] = None
    created_at: datetime

    @field_validator("content", mode="before")
    @classmethod
    def parse_content(cls, v: Any) -> Any:
        if isinstance(v, str):
            return json.loads(v)
        return v
