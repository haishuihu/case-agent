from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    pass


class Submission(Base):
    """提测申请"""
    __tablename__ = "submissions"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))

    version: Mapped[str] = mapped_column(String(100), nullable=False, comment="提测版本")
    submission_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="feature",
        comment="提测类型: feature/bugfix/urgent"
    )
    requirement_id: Mapped[Optional[str]] = mapped_column(String(100), comment="关联需求ID")
    requirement_link: Mapped[Optional[str]] = mapped_column(Text, comment="需求链接")

    change_description: Mapped[str] = mapped_column(Text, nullable=False, comment="变更描述")
    affected_modules: Mapped[Optional[str]] = mapped_column(Text, comment="影响模块(JSON数组)")
    change_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="modified",
        comment="变更类型: added/modified/deleted"
    )

    self_test_passed: Mapped[bool] = mapped_column(default=False, comment="自测是否通过")
    self_test_case_count: Mapped[int] = mapped_column(Integer, default=0, comment="自测用例数")
    self_test_coverage: Mapped[Optional[int]] = mapped_column(Integer, comment="自测覆盖率(%)")
    self_test_conclusion: Mapped[Optional[str]] = mapped_column(Text, comment="自测结论")

    smoke_test_result: Mapped[str] = mapped_column(
        String(20), default="not_executed",
        comment="冒烟测试结果: passed/failed/not_executed"
    )
    blocking_issue_count: Mapped[int] = mapped_column(Integer, default=0, comment="阻塞问题数")

    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending",
        comment="状态: pending/self_test/self_test_passed/gate_passed/gate_rejected"
    )
    gate_result: Mapped[Optional[str]] = mapped_column(Text, comment="门禁结果(JSON)")
    gate_reject_reason: Mapped[Optional[str]] = mapped_column(Text, comment="门禁拒绝原因")

    git_diff: Mapped[Optional[str]] = mapped_column(Text, comment="Git Diff内容")
    git_commit_hash: Mapped[Optional[str]] = mapped_column(String(100), comment="Git提交Hash")
    branch_name: Mapped[Optional[str]] = mapped_column(String(200), comment="分支名")

    submitter: Mapped[Optional[str]] = mapped_column(String(100), comment="提交人")
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(100), comment="审核人")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    checklists: Mapped[list["SubmissionChecklist"]] = relationship(
        back_populates="submission",
        cascade="all, delete-orphan"
    )


class SubmissionChecklist(Base):
    """提测Checklist"""
    __tablename__ = "submission_checklists"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    submission_id: Mapped[str] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False
    )

    item: Mapped[str] = mapped_column(Text, nullable=False, comment="检查项")
    check_method: Mapped[str] = mapped_column(Text, comment="检查方法")
    pass_criteria: Mapped[str] = mapped_column(Text, comment="通过标准")
    risk_level: Mapped[str] = mapped_column(
        String(10), default="medium",
        comment="风险等级: high/medium/low"
    )
    category: Mapped[str] = mapped_column(String(50), default="general", comment="分类")

    is_checked: Mapped[bool] = mapped_column(default=False, comment="是否已检查")
    check_result: Mapped[Optional[str]] = mapped_column(Text, comment="检查结果")
    checked_by: Mapped[Optional[str]] = mapped_column(String(100), comment="检查人")
    checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    is_ai_generated: Mapped[bool] = mapped_column(default=True, comment="是否AI生成")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    submission: Mapped[Submission] = relationship(back_populates="checklists")
