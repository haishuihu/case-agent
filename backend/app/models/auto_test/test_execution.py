from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    pass


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ResultStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    PENDING = "pending"


class TestExecution(Base):
    """测试执行记录"""
    __tablename__ = "test_executions"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    plan_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("test_plans.id", ondelete="SET NULL"), nullable=True,
        comment="关联测试计划"
    )
    suite_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("test_suites.id", ondelete="SET NULL"), nullable=True,
        comment="关联测试套件"
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="执行名称")
    status: Mapped[str] = mapped_column(
        String(20), default=ExecutionStatus.PENDING.value,
        comment="执行状态: pending/running/completed/failed/cancelled"
    )

    # 执行的用例ID列表 (JSON)
    case_ids: Mapped[Optional[str]] = mapped_column(
        Text, comment="执行的用例ID列表 JSON"
    )

    # 执行上下文
    context: Mapped[Optional[str]] = mapped_column(
        Text, comment="执行上下文 JSON (触发源、参数等)"
    )

    # 统计信息
    total_cases: Mapped[int] = mapped_column(default=0, comment="总用例数")
    passed_count: Mapped[int] = mapped_column(default=0, comment="通过数")
    failed_count: Mapped[int] = mapped_column(default=0, comment="失败数")
    blocked_count: Mapped[int] = mapped_column(default=0, comment="阻塞数")
    skipped_count: Mapped[int] = mapped_column(default=0, comment="跳过数")
    pass_rate: Mapped[float] = mapped_column(default=0.0, comment="通过率")

    # 执行时间
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), comment="开始时间"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), comment="完成时间"
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(default=0, comment="执行耗时(毫秒)")

    # 触发信息
    triggered_by: Mapped[Optional[str]] = mapped_column(
        String(100), comment="触发人: user/git/cicd/api"
    )
    trigger_source: Mapped[Optional[str]] = mapped_column(
        String(50), comment="触发来源: manual/git_push/schedule/cicd"
    )

    # AI 分析结果
    ai_summary: Mapped[Optional[str]] = mapped_column(
        Text, comment="AI 执行摘要"
    )
    ai_recommendations: Mapped[Optional[str]] = mapped_column(
        Text, comment="AI 改进建议 JSON"
    )

    # 报告文件路径
    report_path: Mapped[Optional[str]] = mapped_column(
        String(500), comment="报告文件路径"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    plan: Mapped[Optional["TestPlan"]] = relationship(back_populates="executions")
    results: Mapped[list["TestResult"]] = relationship(
        back_populates="execution", cascade="all, delete-orphan"
    )


class TestResult(Base):
    """测试结果"""
    __tablename__ = "test_results"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    execution_id: Mapped[str] = mapped_column(
        ForeignKey("test_executions.id", ondelete="CASCADE"), nullable=False
    )
    case_id: Mapped[str] = mapped_column(
        ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False
    )

    result: Mapped[str] = mapped_column(
        String(20), default=ResultStatus.PENDING.value,
        comment="结果: pass/fail/blocked/skipped/pending"
    )

    # 响应信息
    request_data: Mapped[Optional[str]] = mapped_column(
        Text, comment="实际请求数据"
    )
    response_data: Mapped[Optional[str]] = mapped_column(
        Text, comment="实际响应数据"
    )
    response_status: Mapped[Optional[int]] = mapped_column(
        default=0, comment="实际响应状态码"
    )

    # 验证结果
    validation_details: Mapped[Optional[str]] = mapped_column(
        Text, comment="验证详情 JSON"
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text, comment="错误信息"
    )
    stack_trace: Mapped[Optional[str]] = mapped_column(
        Text, comment="堆栈信息"
    )

    # 截图/日志
    screenshot_path: Mapped[Optional[str]] = mapped_column(
        String(500), comment="截图路径"
    )
    log_path: Mapped[Optional[str]] = mapped_column(
        String(500), comment="日志路径"
    )

    # 时间
    duration_ms: Mapped[Optional[int]] = mapped_column(default=0, comment="耗时(毫秒)")
    executed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), comment="执行时间"
    )

    # 重试次数
    retry_count: Mapped[int] = mapped_column(default=0, comment="重试次数")

    # AI 分析
    ai_analysis: Mapped[Optional[str]] = mapped_column(
        Text, comment="AI 分析结果"
    )
    likely_root_cause: Mapped[Optional[str]] = mapped_column(
        Text, comment="可能的根因"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    execution: Mapped["TestExecution"] = relationship(back_populates="results")
    test_case: Mapped["TestCase"] = relationship(back_populates="results")
