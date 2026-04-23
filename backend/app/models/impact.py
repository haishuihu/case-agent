from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    pass


class ImpactAnalysis(Base):
    """影响分析记录"""
    __tablename__ = "impact_analyses"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    submission_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("submissions.id", ondelete="SET NULL"), nullable=True,
        comment="关联提测申请"
    )

    git_diff: Mapped[Optional[str]] = mapped_column(Text, comment="Git Diff内容")
    changed_files: Mapped[Optional[str]] = mapped_column(Text, comment="变更文件JSON数组")
    added_lines: Mapped[int] = mapped_column(Integer, default=0, comment="新增行数")
    deleted_lines: Mapped[int] = mapped_column(Integer, default=0, comment="删除行数")
    modified_functions: Mapped[Optional[str]] = mapped_column(Text, comment="修改函数JSON数组")

    impact_summary: Mapped[Optional[str]] = mapped_column(Text, comment="影响摘要")
    confidence_level: Mapped[str] = mapped_column(
        String(20), default="low",
        comment="置信度: high/medium/low"
    )
    status: Mapped[str] = mapped_column(
        String(20), default="completed",
        comment="状态: pending/completed/failed"
    )
    analyzed_by: Mapped[Optional[str]] = mapped_column(String(100), comment="分析人")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    impacted_modules: Mapped[list["ImpactedModule"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    recommendations: Mapped[list["RegressionRecommendation"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )


class ImpactedModule(Base):
    """受影响模块"""
    __tablename__ = "impacted_modules"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("impact_analyses.id", ondelete="CASCADE"), nullable=False
    )

    module_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="模块名称")
    module_type: Mapped[str] = mapped_column(
        String(20), default="direct",
        comment="类型: direct/indirect/api"
    )
    risk_level: Mapped[str] = mapped_column(
        String(10), default="medium",
        comment="风险等级: high/medium/low"
    )
    impact_description: Mapped[Optional[str]] = mapped_column(Text, comment="影响描述")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    analysis: Mapped["ImpactAnalysis"] = relationship(back_populates="impacted_modules")


class RegressionRecommendation(Base):
    """回归推荐"""
    __tablename__ = "regression_recommendations"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("impact_analyses.id", ondelete="CASCADE"), nullable=False
    )

    case_id: Mapped[Optional[str]] = mapped_column(String(100), comment="关联用例ID")
    case_title: Mapped[Optional[str]] = mapped_column(String(200), comment="用例标题")
    priority: Mapped[str] = mapped_column(
        String(20), default="should",
        comment="优先级: must/should/could"
    )
    risk_level: Mapped[str] = mapped_column(
        String(10), default="medium",
        comment="风险等级: high/medium/low"
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, comment="推荐原因")
    estimated_minutes: Mapped[Optional[int]] = mapped_column(Integer, comment="预估分钟数")
    category: Mapped[Optional[str]] = mapped_column(String(50), comment="用例分类")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    analysis: Mapped["ImpactAnalysis"] = relationship(back_populates="recommendations")
    execution: Mapped[Optional["RegressionExecution"]] = relationship(
        back_populates="recommendation", uselist=False
    )
