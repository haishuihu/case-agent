from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---- TestExecution ----

class ExecutionCreateRequest(BaseModel):
    """触发测试执行请求"""
    suite_id: Optional[str] = Field(default=None, description="套件ID")
    plan_id: Optional[str] = Field(default=None, description="计划ID")
    case_ids: Optional[list[str]] = Field(default=None, description="指定用例ID列表")
    name: Optional[str] = Field(default=None, description="执行名称")
    context: Optional[dict] = Field(default=None, description="执行上下文")
    triggered_by: Optional[str] = Field(default=None, description="触发人")
    trigger_source: Optional[str] = Field(default=None, description="触发来源")


class ExecutionUpdateRequest(BaseModel):
    """更新执行状态请求"""
    status: Optional[str] = None
    total_cases: Optional[int] = None
    passed_count: Optional[int] = None
    failed_count: Optional[int] = None
    blocked_count: Optional[int] = None
    skipped_count: Optional[int] = None
    pass_rate: Optional[float] = None
    ai_summary: Optional[str] = None
    ai_recommendations: Optional[list[str]] = None


class ExecutionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    plan_id: Optional[str] = None
    suite_id: Optional[str] = None
    name: str
    status: str = "pending"
    
    total_cases: int = 0
    passed_count: int = 0
    failed_count: int = 0
    blocked_count: int = 0
    skipped_count: int = 0
    pass_rate: float = 0.0
    
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = 0
    
    triggered_by: Optional[str] = None
    trigger_source: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_recommendations: Optional[list[str]] = None
    
    created_at: datetime


class ExecutionDetailResponse(ExecutionResponse):
    """执行详情响应"""
    case_ids: Optional[list[str]] = None
    context: Optional[dict] = None
    results: list["TestResultResponse"] = []
    report_path: Optional[str] = None


# ---- TestResult ----

class TestResultBase(BaseModel):
    case_id: str = Field(..., description="用例ID")
    result: str = Field(default="pending", description="结果: pass/fail/blocked/skipped/pending")
    
    request_data: Optional[dict] = None
    response_data: Optional[dict] = None
    response_status: Optional[int] = None
    
    validation_details: Optional[dict] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    
    duration_ms: Optional[int] = Field(default=0, description="耗时(毫秒)")
    retry_count: int = Field(default=0, description="重试次数")
    
    ai_analysis: Optional[str] = None
    likely_root_cause: Optional[str] = None


class TestResultCreate(TestResultBase):
    execution_id: Optional[str] = Field(default=None, description="执行ID（可从路径参数获取）")


class TestResultResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    execution_id: str
    case_id: str
    result: str = "pending"
    
    request_data: Optional[dict] = None
    response_data: Optional[dict] = None
    response_status: Optional[int] = None
    
    validation_details: Optional[dict] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    
    screenshot_path: Optional[str] = None
    log_path: Optional[str] = None
    
    duration_ms: Optional[int] = 0
    executed_at: Optional[datetime] = None
    retry_count: int = 0
    
    ai_analysis: Optional[str] = None
    likely_root_cause: Optional[str] = None
    
    created_at: datetime
    
    # 扩展字段
    case_title: Optional[str] = None
    case_type: Optional[str] = None


# ---- Dashboard Stats ----

class DashboardStats(BaseModel):
    """仪表盘统计数据"""
    pending_count: int = 0
    running_count: int = 0
    today_pass_count: int = 0
    today_fail_count: int = 0
    today_total_cases: int = 0
    today_pass_rate: float = 0.0
    
    total_suites: int = 0
    total_cases: int = 0
    total_plans: int = 0
    total_executions: int = 0


class RecentExecution(BaseModel):
    """最近执行记录"""
    id: str
    name: str
    status: str
    total_cases: int
    passed_count: int
    failed_count: int
    pass_rate: float
    triggered_by: Optional[str] = None
    created_at: datetime
    duration_ms: Optional[int] = None


class ExecutionTrend(BaseModel):
    """执行趋势数据"""
    date: str
    total: int
    passed: int
    failed: int
    pass_rate: float


class FailureDistribution(BaseModel):
    """失败分布"""
    module: str
    count: int
    percentage: float
