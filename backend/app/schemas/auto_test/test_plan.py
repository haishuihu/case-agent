from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---- TestPlan ----

class TestPlanBase(BaseModel):
    name: str = Field(..., max_length=200, description="计划名称")
    description: Optional[str] = Field(default=None, description="计划描述")
    schedule_type: str = Field(default="manual", description="调度类型: manual/cron/event")
    schedule_config: Optional[dict] = Field(default=None, description="调度配置")
    auto_execute: bool = Field(default=False, description="是否自动执行")
    notification_config: Optional[dict] = Field(default=None, description="通知配置")
    case_filter: Optional[dict] = Field(default=None, description="用例筛选条件")
    execution_config: Optional[dict] = Field(default=None, description="执行配置")


class TestPlanCreate(TestPlanBase):
    suite_id: str = Field(..., description="所属套件ID")


class TestPlanUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = None
    schedule_type: Optional[str] = None
    schedule_config: Optional[dict] = None
    auto_execute: Optional[bool] = None
    notification_config: Optional[dict] = None
    case_filter: Optional[dict] = None
    execution_config: Optional[dict] = None
    is_active: Optional[bool] = None


class TestPlanResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    suite_id: str
    name: str
    description: Optional[str] = None
    schedule_type: str = "manual"
    schedule_config: Optional[dict] = None
    auto_execute: bool = False
    notification_config: Optional[dict] = None
    case_filter: Optional[dict] = None
    execution_config: Optional[dict] = None
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # 扩展字段
    execution_count: int = 0
    last_execution_at: Optional[datetime] = None
    last_execution_status: Optional[str] = None


# ---- TriggerConfig ----

class TriggerConfigBase(BaseModel):
    trigger_type: str = Field(..., description="触发类型: git_push/schedule/api/cicd/submission")
    name: Optional[str] = Field(default=None, max_length=100, description="触发器名称")
    config: Optional[dict] = Field(default=None, description="触发器配置")
    enabled: bool = Field(default=True, description="是否启用")


class TriggerConfigCreate(TriggerConfigBase):
    plan_id: Optional[str] = Field(default=None, description="关联计划ID（可从路径参数获取）")


class TriggerConfigUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    config: Optional[dict] = None
    enabled: Optional[bool] = None


class TriggerConfigResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    plan_id: str
    trigger_type: str
    name: Optional[str] = None
    config: Optional[dict] = None
    enabled: bool = True
    last_triggered_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# ---- Git Webhook Payload ----

class GitWebhookPayload(BaseModel):
    """Git Webhook 接收的数据"""
    event: str = Field(..., description="事件类型: push/pull_request等")
    branch: Optional[str] = Field(default=None, description="分支名")
    commit_sha: Optional[str] = Field(default=None, description="提交SHA")
    commit_message: Optional[str] = Field(default=None, description="提交信息")
    author: Optional[str] = Field(default=None, description="提交者")
    changed_files: Optional[list[str]] = Field(default=None, description="变更文件列表")
    diff_content: Optional[str] = Field(default=None, description="Diff内容")

    # 用于签名验证
    signature: Optional[str] = Field(default=None, description="Webhook签名")
    secret: Optional[str] = Field(default=None, description="密钥(可选)")


class WebhookPayload(BaseModel):
    """通用 Webhook 接收的数据"""
    event: str = Field(..., description="事件类型")
    data: Optional[dict] = Field(default=None, description="事件数据")
    branch: Optional[str] = Field(default=None)
    secret: Optional[str] = Field(default=None)


class RegressionRecommendRequest(BaseModel):
    """回归推荐请求"""
    changed_files: Optional[list[str]] = Field(default=None, description="变更文件列表")
    diff_content: Optional[str] = Field(default=None, description="Git Diff内容")
    module_names: Optional[list[str]] = Field(default=None, description="影响的模块名")
    submission_id: Optional[str] = Field(default=None, description="关联提测ID")
    max_cases: int = Field(default=50, ge=1, le=200, description="最大推荐用例数")
    include_ai_recommendation: bool = Field(default=True, description="是否包含AI推荐理由")


class RegressionRecommendItem(BaseModel):
    """推荐的回归用例项"""
    case_id: str
    case_title: str
    priority: int
    score: float
    reason: str
    ai_reasoning: Optional[str] = None
    estimated_duration_ms: Optional[int] = None


class RegressionRecommendResponse(BaseModel):
    """回归推荐响应"""
    total_recommended: int
    total_estimated_duration_ms: int
    recommendations: list[RegressionRecommendItem]
    summary: str
