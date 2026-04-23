from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.models.case_review import CaseReview, ReviewComment
from app.schemas.case_review import (
    AIReviewRequest,
    AIReviewResult,
    CaseReviewCreate,
    CaseReviewListResponse,
    CaseReviewResponse,
    CaseReviewStatusUpdate,
    ReviewCommentCreate,
    ReviewCommentResponse,
)
from app.services.case_review_service import CaseReviewService

router = APIRouter(prefix="/reviews", tags=["reviews"])
logger = logging.getLogger(__name__)


VALID_STATUSES = {"pending", "in_review", "approved", "needs_revision"}
VALID_DECISIONS = {"approved", "needs_revision"}


def _serialize_ai_details(result: AIReviewResult) -> str:
    return json.dumps(result.model_dump(by_alias=True), ensure_ascii=False)


def _serialize_ai_details_from_dict(data: dict) -> str:
    """将 dict 格式的 AI 评审结果序列化为 JSON 字符串"""
    import json as _json
    return _json.dumps(data, ensure_ascii=False)


def _deserialize_ai_details(raw: Optional[str]) -> Optional[AIReviewResult]:
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return AIReviewResult(**data)
    except (json.JSONDecodeError, TypeError):
        return None


def _review_to_response(review: CaseReview) -> CaseReviewResponse:
    comments = [
        ReviewCommentResponse(
            id=c.id,
            reviewId=c.review_id,
            author=c.author,
            content=c.content,
            caseId=c.case_id,
            caseTitle=c.case_title,
            parentCommentId=c.parent_comment_id,
            createdAt=c.created_at,
            updatedAt=c.updated_at,
        )
        for c in review.comments
    ]

    return CaseReviewResponse(
        id=review.id,
        generationId=review.generation_id,
        caseTitle=review.case_title,
        requirementText=review.requirement_text,
        generatedCases=review.generated_cases,
        reviewStatus=review.review_status,
        completenessScore=review.completeness_score,
        executabilityScore=review.executability_score,
        consistencyScore=review.consistency_score,
        redundancyScore=review.redundancy_score,
        coverageScore=review.coverage_score,
        overallScore=review.overall_score,
        aiReviewSummary=review.ai_review_summary,
        aiReviewDetails=_deserialize_ai_details(review.ai_review_details),
        reviewer=review.reviewer,
        reviewerComment=review.reviewer_comment,
        decision=review.decision,
        createdAt=review.created_at,
        updatedAt=review.updated_at,
        comments=comments,
    )


# ── Case Review CRUD ────────────────────────────────────────────────


@router.post("", response_model=CaseReviewResponse, status_code=status.HTTP_201_CREATED)
def create_review(
    payload: CaseReviewCreate,
    db: Session = Depends(get_db_session),
) -> CaseReviewResponse:
    """创建一条用例评审记录"""
    review = CaseReview(
        generation_id=payload.generation_id,
        case_title=payload.case_title,
        requirement_text=payload.requirement_text,
        generated_cases=payload.generated_cases,
        reviewer=payload.reviewer,
        review_status="pending",
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    logger.info("[review] created id=%s", review.id)
    return _review_to_response(review)


@router.get("", response_model=CaseReviewListResponse)
def list_reviews(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: Session = Depends(get_db_session),
) -> CaseReviewListResponse:
    """获取评审列表"""
    q = db.query(CaseReview)
    if status_filter:
        if status_filter not in VALID_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的状态值。可选值: {', '.join(VALID_STATUSES)}",
            )
        q = q.filter(CaseReview.review_status == status_filter)

    total = q.count()
    rows = (
        q.order_by(CaseReview.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [_review_to_response(r) for r in rows]
    return CaseReviewListResponse(items=items, total=total, page=page, pageSize=page_size)


@router.get("/{review_id}", response_model=CaseReviewResponse)
def get_review(
    review_id: str,
    db: Session = Depends(get_db_session),
) -> CaseReviewResponse:
    """获取评审详情"""
    review = db.get(CaseReview, review_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评审记录不存在")
    return _review_to_response(review)


@router.patch("/{review_id}", response_model=CaseReviewResponse)
def update_review_status(
    review_id: str,
    payload: CaseReviewStatusUpdate,
    db: Session = Depends(get_db_session),
) -> CaseReviewResponse:
    """更新评审状态和人工意见"""
    review = db.get(CaseReview, review_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评审记录不存在")

    if payload.review_status is not None:
        if payload.review_status not in VALID_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的状态值。可选值: {', '.join(VALID_STATUSES)}",
            )
        review.review_status = payload.review_status

    if payload.decision is not None:
        if payload.decision not in VALID_DECISIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的决定值。可选值: {', '.join(VALID_DECISIONS)}",
            )
        review.decision = payload.decision

    if payload.reviewer is not None:
        review.reviewer = payload.reviewer
    if payload.reviewer_comment is not None:
        review.reviewer_comment = payload.reviewer_comment

    db.commit()
    db.refresh(review)
    logger.info("[review] updated id=%s status=%s", review.id, review.review_status)
    return _review_to_response(review)


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_review(
    review_id: str,
    db: Session = Depends(get_db_session),
) -> None:
    """删除评审记录"""
    review = db.get(CaseReview, review_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评审记录不存在")
    db.delete(review)
    db.commit()
    logger.info("[review] deleted id=%s", review_id)


# ── Review Comments ────────────────────────────────────────────────


@router.post("/{review_id}/comments", response_model=ReviewCommentResponse, status_code=status.HTTP_201_CREATED)
def add_comment(
    review_id: str,
    payload: ReviewCommentCreate,
    db: Session = Depends(get_db_session),
) -> ReviewCommentResponse:
    """为评审添加评论（行内意见）"""
    review = db.get(CaseReview, review_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评审记录不存在")

    if payload.parent_comment_id:
        parent = db.get(ReviewComment, payload.parent_comment_id)
        if not parent or parent.review_id != review_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="父评论不存在或不属于该评审",
            )

    comment = ReviewComment(
        review_id=review_id,
        author=payload.author,
        content=payload.content,
        case_id=payload.case_id,
        case_title=payload.case_title,
        parent_comment_id=payload.parent_comment_id,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    logger.info("[review] added comment id=%s to review_id=%s", comment.id, review_id)

    return ReviewCommentResponse(
        id=comment.id,
        reviewId=comment.review_id,
        author=comment.author,
        content=comment.content,
        caseId=comment.case_id,
        caseTitle=comment.case_title,
        parentCommentId=comment.parent_comment_id,
        createdAt=comment.created_at,
        updatedAt=comment.updated_at,
    )


@router.get("/{review_id}/comments", response_model=list[ReviewCommentResponse])
def list_comments(
    review_id: str,
    db: Session = Depends(get_db_session),
) -> list[ReviewCommentResponse]:
    """获取评审的所有评论"""
    review = db.get(CaseReview, review_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评审记录不存在")

    return [
        ReviewCommentResponse(
            id=c.id,
            reviewId=c.review_id,
            author=c.author,
            content=c.content,
            caseId=c.case_id,
            caseTitle=c.case_title,
            parentCommentId=c.parent_comment_id,
            createdAt=c.created_at,
            updatedAt=c.updated_at,
        )
        for c in review.comments
    ]


@router.delete("/{review_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_comment(
    review_id: str,
    comment_id: str,
    db: Session = Depends(get_db_session),
) -> None:
    """删除评论"""
    review = db.get(CaseReview, review_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评审记录不存在")

    comment = db.get(ReviewComment, comment_id)
    if not comment or comment.review_id != review_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评论不存在")

    db.delete(comment)
    db.commit()
    logger.info("[review] deleted comment id=%s", comment_id)


# ── AI Review ──────────────────────────────────────────────────────


@router.post("/ai-review", response_model=CaseReviewResponse, status_code=status.HTTP_201_CREATED)
def run_ai_review(
    payload: AIReviewRequest,
    db: Session = Depends(get_db_session),
) -> CaseReviewResponse:
    """创建评审记录并执行 AI 评审"""
    review = CaseReview(
        generation_id=payload.generation_id,
        case_title=payload.case_title,
        requirement_text=payload.requirement_text,
        generated_cases=payload.generated_cases,
        review_status="in_review",
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    try:
        service = CaseReviewService()
        ai_result = service.run_ai_review(
            requirement_text=payload.requirement_text or "",
            generated_cases=payload.generated_cases or "",
            model_key=payload.model_key,
        )

        review.completeness_score = ai_result["dimensions"][0]["score"] if len(ai_result["dimensions"]) > 0 else None
        review.executability_score = ai_result["dimensions"][1]["score"] if len(ai_result["dimensions"]) > 1 else None
        review.consistency_score = ai_result["dimensions"][2]["score"] if len(ai_result["dimensions"]) > 2 else None
        review.redundancy_score = ai_result["dimensions"][3]["score"] if len(ai_result["dimensions"]) > 3 else None
        review.coverage_score = ai_result["dimensions"][4]["score"] if len(ai_result["dimensions"]) > 4 else None
        review.overall_score = ai_result["overall_score"]
        review.ai_review_summary = f"综合评分: {ai_result['overall_score']}/100，建议关注: {'; '.join(ai_result['suggestions'][:3])}"
        review.ai_review_details = _serialize_ai_details_from_dict(ai_result)
        review.review_status = "in_review"

    except Exception as exc:
        logger.warning("[review] AI review failed for id=%s: %s", review.id, exc)
        review.ai_review_summary = "AI 评审执行失败，请稍后重试"
        review.review_status = "pending"

    db.commit()
    db.refresh(review)
    logger.info("[review] AI review completed for id=%s overall=%s", review.id, review.overall_score)
    return _review_to_response(review)
