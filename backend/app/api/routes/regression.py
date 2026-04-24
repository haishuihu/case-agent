from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.models.impact import ImpactAnalysis, RegressionRecommendation
from app.schemas.impact import (
    RegressionRecommendRequest,
    RegressionRecommendResponse,
    RegressionRecommendationResponse,
)
from app.services.regression_recommender import RegressionRecommender

router = APIRouter(prefix="/regression", tags=["regression"])
logger = logging.getLogger(__name__)


def _build_recommend_response(
    analysis_id: str,
    recommendations: list[RegressionRecommendation],
) -> RegressionRecommendResponse:
    """将 ORM 模型列表转换为分组响应"""
    must: list[RegressionRecommendationResponse] = []
    should: list[RegressionRecommendationResponse] = []
    could: list[RegressionRecommendationResponse] = []

    for rec in recommendations:
        item = RegressionRecommendationResponse(
            id=rec.id,
            caseId=rec.case_id or None,
            caseTitle=rec.case_title or None,
            priority=rec.priority,
            riskLevel=rec.risk_level,
            reason=rec.reason or None,
            estimatedMinutes=rec.estimated_minutes,
            category=rec.category,
            executionStatus=rec.execution.status if rec.execution else None,
        )
        if rec.priority == "must":
            must.append(item)
        elif rec.priority == "should":
            should.append(item)
        else:
            could.append(item)

    def total_mins(items: list[RegressionRecommendationResponse]) -> int:
        return sum(r.estimatedMinutes or 0 for r in items)

    return RegressionRecommendResponse(
        analysisId=analysis_id,
        mustRegress=must,
        shouldRegress=should,
        couldRegress=could,
        totalMustMinutes=total_mins(must),
        totalShouldMinutes=total_mins(should),
        totalCouldMinutes=total_mins(could),
    )


@router.post("/recommend", response_model=RegressionRecommendResponse)
def recommend_regression(
    request: RegressionRecommendRequest,
    db: Session = Depends(get_db_session),
) -> RegressionRecommendResponse:
    """
    获取回归推荐。

    优先从已有的分析记录中返回推荐；若 analysis_id 不存在，则基于
    submission_id 获取最新分析重新推荐。
    """
    if request.analysisId:
        analysis = db.get(ImpactAnalysis, request.analysisId)
    elif request.submissionId:
        analysis = (
            db.query(ImpactAnalysis)
            .filter(ImpactAnalysis.submission_id == request.submissionId)
            .order_by(ImpactAnalysis.created_at.desc())
            .first()
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="analysisId 或 submissionId 至少需要提供一个",
        )

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到影响分析记录，请先执行影响分析",
        )

    # 如果分析记录已有推荐结果，直接返回
    if analysis.recommendations:
        logger.info("[regression] returning cached recommendations for analysis=%s", analysis.id)
        return _build_recommend_response(analysis.id, analysis.recommendations)

    # 重新生成推荐
    recommender = RegressionRecommender()
    impacted = [
        {"module_name": m.module_name, "risk_level": m.risk_level, "module_type": m.module_type}
        for m in analysis.impacted_modules
    ]

    recs = recommender.recommend(
        impacted_modules=impacted,
        summary=analysis.impact_summary or "",
        recent_defects=None,
    )

    # 保存推荐结果
    for rec in recs:
        db.add(RegressionRecommendation(
            analysis_id=analysis.id,
            case_id=rec.get("case_id"),
            case_title=rec.get("case_title"),
            priority=rec.get("priority", "should"),
            risk_level=rec.get("risk_level", "medium"),
            reason=rec.get("reason"),
            estimated_minutes=rec.get("estimated_minutes"),
            category=rec.get("category"),
        ))

    db.commit()
    db.refresh(analysis)

    logger.info("[regression] generated %d recommendations for analysis=%s", len(recs), analysis.id)
    return _build_recommend_response(analysis.id, analysis.recommendations)


@router.get("/recommendations/{analysis_id}", response_model=RegressionRecommendResponse)
def get_recommendations(
    analysis_id: str,
    db: Session = Depends(get_db_session),
) -> RegressionRecommendResponse:
    """获取指定分析的回归推荐结果"""
    analysis = db.get(ImpactAnalysis, analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"影响分析 {analysis_id} 不存在",
        )
    return _build_recommend_response(analysis.id, analysis.recommendations)
