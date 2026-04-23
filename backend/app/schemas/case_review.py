from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Request Schemas ──────────────────────────────────────────────


class ReviewCommentCreate(BaseModel):
    """创建评审评论"""
    author: Optional[str] = Field(None, description="评论人")
    content: str = Field(..., description="评论内容")
    case_id: Optional[str] = Field(None, description="关联用例ID（用于行内评论）")
    case_title: Optional[str] = Field(None, description="关联用例标题")
    parent_comment_id: Optional[str] = Field(None, alias="parentCommentId", description="父评论ID")

    model_config = {"populate_by_name": True}


class CaseReviewCreate(BaseModel):
    """创建用例评审"""
    generation_id: Optional[str] = Field(None, alias="generationId", description="关联生成记录ID")
    case_title: Optional[str] = Field(None, alias="caseTitle", description="用例标题")
    requirement_text: Optional[str] = Field(None, alias="requirementText", description="需求文本")
    generated_cases: Optional[str] = Field(None, alias="generatedCases", description="生成的用例(Markdown)")
    reviewer: Optional[str] = Field(None, description="评审人")

    model_config = {"populate_by_name": True}


class CaseReviewStatusUpdate(BaseModel):
    """更新评审状态"""
    review_status: Optional[str] = Field(None, alias="reviewStatus")
    decision: Optional[str] = Field(None, description="最终决定: approved/needs_revision")
    reviewer: Optional[str] = Field(None, description="评审人")
    reviewer_comment: Optional[str] = Field(None, alias="reviewerComment", description="人工评审意见")

    model_config = {"populate_by_name": True}


class AIReviewRequest(BaseModel):
    """发起 AI 评审请求"""
    generation_id: Optional[str] = Field(None, alias="generationId", description="关联生成记录ID")
    case_title: Optional[str] = Field(None, alias="caseTitle", description="用例标题")
    requirement_text: Optional[str] = Field(None, alias="requirementText", description="需求文本")
    generated_cases: Optional[str] = Field(None, alias="generatedCases", description="生成的用例(Markdown)")
    model_key: Optional[str] = Field(None, alias="modelKey", description="模型Key")

    model_config = {"populate_by_name": True}


# ── Response Schemas ─────────────────────────────────────────────


class AIReviewDimension(BaseModel):
    """AI 评审维度评分"""
    dimension: str = Field(..., description="维度名称")
    label: str = Field(..., description="维度标签")
    score: int = Field(..., ge=0, le=100, description="评分 0-100")
    description: str = Field(..., description="评分说明")


class AIReviewIssue(BaseModel):
    """AI 评审问题项"""
    type: str = Field(..., description="问题类型")
    severity: str = Field(..., description="严重程度: high/medium/low")
    description: str = Field(..., description="问题描述")
    recommendation: Optional[str] = Field(None, description="建议")


class AIReviewResult(BaseModel):
    """AI 评审结果"""
    overall_score: int = Field(..., ge=0, le=100, alias="overallScore")
    dimensions: list[AIReviewDimension]
    issues: list[AIReviewIssue] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class ReviewCommentResponse(BaseModel):
    """评审评论响应"""
    id: str
    review_id: str = Field(alias="reviewId")
    author: Optional[str] = None
    content: str
    case_id: Optional[str] = Field(None, alias="caseId")
    case_title: Optional[str] = Field(None, alias="caseTitle")
    parent_comment_id: Optional[str] = Field(None, alias="parentCommentId")
    created_at: datetime = Field(alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")

    model_config = {"populate_by_name": True}


class CaseReviewResponse(BaseModel):
    """用例评审详情"""
    id: str
    generation_id: Optional[str] = Field(None, alias="generationId")
    case_title: Optional[str] = Field(None, alias="caseTitle")
    requirement_text: Optional[str] = Field(None, alias="requirementText")
    generated_cases: Optional[str] = Field(None, alias="generatedCases")
    review_status: str = Field(alias="reviewStatus")
    completeness_score: Optional[int] = Field(None, alias="completenessScore")
    executability_score: Optional[int] = Field(None, alias="executabilityScore")
    consistency_score: Optional[int] = Field(None, alias="consistencyScore")
    redundancy_score: Optional[int] = Field(None, alias="redundancyScore")
    coverage_score: Optional[int] = Field(None, alias="coverageScore")
    overall_score: Optional[int] = Field(None, alias="overallScore")
    ai_review_summary: Optional[str] = Field(None, alias="aiReviewSummary")
    ai_review_details: Optional[AIReviewResult] = Field(None, alias="aiReviewDetails")
    reviewer: Optional[str] = None
    reviewer_comment: Optional[str] = Field(None, alias="reviewerComment")
    decision: Optional[str] = None
    created_at: datetime = Field(alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")
    comments: list[ReviewCommentResponse] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class CaseReviewListResponse(BaseModel):
    """评审列表响应"""
    items: list[CaseReviewResponse]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")

    model_config = {"populate_by_name": True}
