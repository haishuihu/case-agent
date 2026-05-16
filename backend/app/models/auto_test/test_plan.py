from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    pass


class ScheduleType(str, Enum):
    MANUAL = "manual"
    CRON = "cron"
    EVENT = "event"


class TriggerType(str, Enum):
    GIT_PUSH = "git_push"
    SCHEDULE = "schedule"
    API_CALL = "api_call"
    CICD = "cicd"
    SUBMISSION = "submission"


class TestPlan(Base):
    """测试计划"""
    __tablename__ = "test_plans"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    suite_id: Mapped[str] = mapped_column(
        ForeignKey("test_suites.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="计划名称")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="计划描述")

    # 调度配置
    schedule_type: Mapped[str] = mapped_column(
        String(20), default=ScheduleType.MANUAL.value,
        comment="调度类型: manual/cron/event"
    )
    schedule_config: Mapped[Optional[str]] = mapped_column(
        Text, comment="调度配置 JSON (cron表达式等)"
    )
    auto_execute: Mapped[bool] = mapped_column(default=False, comment="是否自动执行")

    # 通知配置
    notification_config: Mapped[Optional[str]] = mapped_column(
        Text, comment="通知配置 JSON"
    )

    # 执行配置
    case_filter: Mapped[Optional[str]] = mapped_column(
        Text, comment="用例筛选条件 JSON"
    )
    execution_config: Mapped[Optional[str]] = mapped_column(
        Text, comment="执行配置 JSON (并发数、重试等)"
    )

    is_active: Mapped[bool] = mapped_column(default=True, comment="是否启用")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    suite: Mapped["TestSuite"] = relationship(back_populates="test_plans")
    executions: Mapped[list["TestExecution"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )
    triggers: Mapped[list["TriggerConfig"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )


class TriggerConfig(Base):
    """触发器配置"""
    __tablename__ = "trigger_configs"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    plan_id: Mapped[str] = mapped_column(
        ForeignKey("test_plans.id", ondelete="CASCADE"), nullable=False
    )

    trigger_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="触发类型: git_push/schedule/api/cicd/submission"
    )
    name: Mapped[str] = mapped_column(String(100), comment="触发器名称")
    config: Mapped[Optional[str]] = mapped_column(Text, comment="触发器配置 JSON")
    enabled: Mapped[bool] = mapped_column(default=True, comment="是否启用")
    secret_key: Mapped[Optional[str]] = mapped_column(String(200), comment="Webhook密钥")
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), comment="最后触发时间"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    plan: Mapped["TestPlan"] = relationship(back_populates="triggers")
