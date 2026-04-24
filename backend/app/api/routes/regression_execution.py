from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.models.impact import RegressionRecommendation
from app.models.regression_execution import RegressionExecution, ExecutionStatus
from app.schemas.impact import ExecutionUpdateRequest, ExecutionUpdateResponse

router = APIRouter(prefix="/regression", tags=["regression-execution"])
logger = logging.getLogger(__name__)

VALID_STATUSES = {s.value for s in ExecutionStatus}


@router.post(
    "/recommendations/{recommendation_id}/execute",
    response_model=ExecutionUpdateResponse,
    status_code=status.HTTP_200_OK,
)
def update_execution_status(
    recommendation_id: str,
    request: ExecutionUpdateRequest,
    db: Session = Depends(get_db_session),
) -> ExecutionUpdateResponse:
    """
    更新回归推荐用例的执行状态。

    若该推荐尚未有执行记录则创建，否则更新。
    """
    rec = db.get(RegressionRecommendation, recommendation_id)
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"回归推荐 {recommendation_id} 不存在",
        )

    if request.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的执行状态。可选值: {', '.join(sorted(VALID_STATUSES))}",
        )

    execution = rec.execution
    if execution is None:
        execution = RegressionExecution(
            recommendation_id=recommendation_id,
            status=request.status,
            executed_by=request.executedBy,
            executed_at=datetime.now(timezone.utc),
            actual_result=request.actualResult,
            comment=request.comment,
        )
        db.add(execution)
        logger.info("[regression-exec] created execution id=%s for recommendation=%s", execution.id, recommendation_id)
    else:
        execution.status = request.status
        execution.executed_by = request.executedBy
        execution.executed_at = datetime.now(timezone.utc)
        execution.actual_result = request.actualResult
        execution.comment = request.comment
        logger.info("[regression-exec] updated execution id=%s status=%s", execution.id, request.status)

    db.commit()
    db.refresh(execution)

    return ExecutionUpdateResponse(
        id=execution.id,
        recommendationId=execution.recommendation_id,
        status=execution.status,
        executedBy=execution.executed_by,
        executedAt=execution.executed_at,
        actualResult=execution.actual_result,
        comment=execution.comment,
    )


@router.get(
    "/recommendations/{recommendation_id}/execute",
    response_model=ExecutionUpdateResponse,
    status_code=status.HTTP_200_OK,
)
def get_execution_status(
    recommendation_id: str,
    db: Session = Depends(get_db_session),
) -> ExecutionUpdateResponse:
    """获取指定回归推荐用例的执行状态。"""
    rec = db.get(RegressionRecommendation, recommendation_id)
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"回归推荐 {recommendation_id} 不存在",
        )

    execution = rec.execution
    if execution is None:
        return ExecutionUpdateResponse(
            id="",
            recommendationId=recommendation_id,
            status=ExecutionStatus.NOT_STARTED.value,
            executedBy=None,
            executedAt=None,
            actualResult=None,
            comment=None,
        )

    return ExecutionUpdateResponse(
        id=execution.id,
        recommendationId=execution.recommendation_id,
        status=execution.status,
        executedBy=execution.executed_by,
        executedAt=execution.executed_at,
        actualResult=execution.actual_result,
        comment=execution.comment,
    )
