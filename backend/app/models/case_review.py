from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    pass


class CaseReview(Base):
    """用例评审记录"""
    __tablename__ = "case_reviews"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    generation_id: Mapped[Optional[str]] = mapped_column(
        String(100), comment="关联的生成记录ID"
    )
    case_title: Mapped[Optional[str]] = mapped_column(String(200), comment="用例标题")
    requirement_text: Mapped[Optional[str]] = mapped_column(Text, comment="需求文本")
    generated_cases: Mapped[Optional[str]] = mapped_column(Text, comment="生成的用例内容(Markdown)")

    review_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending",
        comment="评审状态: pending/in_review/approved/needs_revision"
    )

    # AI 评审维度评分（0-100）
    completeness_score: Mapped[Optional[int]] = mapped_column(comment="完整性评分(0-100)")
    executability_score: Mapped[Optional[int]] = mapped_column(comment="可执行性评分(0-100)")
    consistency_score: Mapped[Optional[int]] = mapped_column(comment="一致性评分(0-100)")
    redundancy_score: Mapped[Optional[int]] = mapped_column(comment="冗余性评分(0-100)")
    coverage_score: Mapped[Optional[int]] = mapped_column(comment="覆盖率评分(0-100)")

    overall_score: Mapped[Optional[int]] = mapped_column(comment="综合评分(0-100)")
    ai_review_summary: Mapped[Optional[str]] = mapped_column(Text, comment="AI评审摘要")
    ai_review_details: Mapped[Optional[str]] = mapped_column(Text, comment="AI评审详细结果(JSON)")

    reviewer: Mapped[Optional[str]] = mapped_column(String(100), comment="评审人")
    reviewer_comment: Mapped[Optional[str]] = mapped_column(Text, comment="人工评审意见")
    decision: Mapped[Optional[str]] = mapped_column(String(20), comment="最终决定: approved/needs_revision")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    comments: Mapped[list["ReviewComment"]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )


class ReviewComment(Base):
    """评审评论（行内意见）"""
    __tablename__ = "review_comments"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    review_id: Mapped[str] = mapped_column(
        ForeignKey("case_reviews.id", ondelete="CASCADE"), nullable=False
    )

    author: Mapped[Optional[str]] = mapped_column(String(100), comment="评论人")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="评论内容")

    # 关联的用例元素（用于行内评论定位）
    case_id: Mapped[Optional[str]] = mapped_column(String(100), comment="关联用例ID")
    case_title: Mapped[Optional[str]] = mapped_column(String(200), comment="关联用例标题")

    parent_comment_id: Mapped[Optional[str]] = mapped_column(
        String(100), comment="父评论ID（用于回复链）"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    review: Mapped["CaseReview"] = relationship(back_populates="comments")
