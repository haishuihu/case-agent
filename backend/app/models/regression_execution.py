from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    pass


class ExecutionStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"


class RegressionExecution(Base):
    """回归用例执行记录"""
    __tablename__ = "regression_executions"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    recommendation_id: Mapped[str] = mapped_column(
        ForeignKey("regression_recommendations.id", ondelete="CASCADE"), nullable=False,
        comment="关联回归推荐"
    )

    status: Mapped[str] = mapped_column(
        String(20), default=ExecutionStatus.NOT_STARTED.value,
        comment="执行状态: not_started/in_progress/passed/failed/blocked"
    )
    executed_by: Mapped[Optional[str]] = mapped_column(
        String(100), comment="执行人"
    )
    executed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), comment="执行时间"
    )
    actual_result: Mapped[Optional[str]] = mapped_column(
        Text, comment="实际结果"
    )
    comment: Mapped[Optional[str]] = mapped_column(
        Text, comment="备注"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    recommendation: Mapped["RegressionRecommendation"] = relationship(
        back_populates="execution"
    )
