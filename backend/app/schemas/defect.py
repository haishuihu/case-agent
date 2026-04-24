from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DefectCreate(BaseModel):
    """创建缺陷"""
    submission_id: Optional[str] = Field(None, alias="submissionId", description="关联提测申请ID")
    recommendation_id: Optional[str] = Field(None, alias="recommendationId", description="关联回归推荐ID")
    execution_id: Optional[str] = Field(None, alias="executionId", description="关联执行记录ID")
    title: str = Field(..., description="缺陷标题")
    description: Optional[str] = Field(None, description="缺陷描述")
    severity: str = Field(default="medium", description="严重程度: critical/high/medium/low")
    priority: str = Field(default="medium", description="优先级: high/medium/low")
    environment: Optional[str] = Field(None, description="环境")
    browser: Optional[str] = Field(None, description="浏览器/客户端")
    root_cause: Optional[str] = Field(None, alias="rootCause", description="根因分析")
    attachments: Optional[list[str]] = Field(None, description="附件路径列表")
    creator: Optional[str] = Field(None, description="创建人")
    assignee: Optional[str] = Field(None, description="指派给")

    model_config = {"populate_by_name": True}


class DefectUpdate(BaseModel):
    """更新缺陷"""
    title: Optional[str] = Field(None, description="缺陷标题")
    description: Optional[str] = Field(None, description="缺陷描述")
    severity: Optional[str] = Field(None, description="严重程度")
    priority: Optional[str] = Field(None, description="优先级")
    status: Optional[str] = Field(None, description="缺陷状态: open/in_progress/resolved/closed")
    environment: Optional[str] = Field(None, description="环境")
    browser: Optional[str] = Field(None, description="浏览器/客户端")
    root_cause: Optional[str] = Field(None, alias="rootCause", description="根因分析")
    attachments: Optional[list[str]] = Field(None, description="附件路径列表")
    assignee: Optional[str] = Field(None, description="指派给")


class DefectResponse(BaseModel):
    """缺陷详情"""
    id: str
    submission_id: Optional[str] = Field(None, alias="submissionId")
    recommendation_id: Optional[str] = Field(None, alias="recommendationId")
    execution_id: Optional[str] = Field(None, alias="executionId")
    title: str
    description: Optional[str] = None
    severity: str
    priority: str
    status: str
    environment: Optional[str] = None
    browser: Optional[str] = None
    root_cause: Optional[str] = Field(None, alias="rootCause")
    attachments: list[str] = Field(default_factory=list)
    creator: Optional[str] = None
    assignee: Optional[str] = None
    created_at: datetime = Field(alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")
    resolved_at: Optional[datetime] = Field(None, alias="resolvedAt")

    model_config = {"populate_by_name": True}


class DefectListResponse(BaseModel):
    """缺陷列表响应"""
    items: list[DefectResponse]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")

    model_config = {"populate_by_name": True}


class DefectFromExecution(BaseModel):
    """从执行失败一键创建缺陷"""
    execution_id: str = Field(..., alias="executionId", description="执行记录ID")
    title: Optional[str] = Field(None, description="缺陷标题（不填则自动生成）")
    description: Optional[str] = Field(None, description="缺陷描述")
    severity: str = Field(default="medium", description="严重程度")
    priority: str = Field(default="medium", description="优先级")
    creator: Optional[str] = Field(None, description="创建人")

    model_config = {"populate_by_name": True}
