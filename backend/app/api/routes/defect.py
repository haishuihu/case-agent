from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.models.defect import Defect
from app.schemas.defect import (
    DefectCreate,
    DefectFromExecution,
    DefectListResponse,
    DefectResponse,
    DefectUpdate,
)
from app.services.execution_tracker import ExecutionTracker

router = APIRouter(prefix="/defects", tags=["defects"])
logger = logging.getLogger(__name__)

VALID_SEVERITIES = {"critical", "high", "medium", "low"}
VALID_PRIORITIES = {"high", "medium", "low"}
VALID_STATUSES = {"open", "in_progress", "resolved", "closed"}


def _defect_to_response(defect: Defect) -> DefectResponse:
    attachments = []
    if defect.attachments:
        try:
            attachments = json.loads(defect.attachments)
        except json.JSONDecodeError:
            pass

    return DefectResponse(
        id=defect.id,
        submissionId=defect.submission_id,
        recommendationId=defect.recommendation_id,
        executionId=defect.execution_id,
        title=defect.title,
        description=defect.description,
        severity=defect.severity,
        priority=defect.priority,
        status=defect.status,
        environment=defect.environment,
        browser=defect.browser,
        rootCause=defect.root_cause,
        attachments=attachments,
        creator=defect.creator,
        assignee=defect.assignee,
        createdAt=defect.created_at,
        updatedAt=defect.updated_at,
        resolvedAt=defect.resolved_at,
    )


@router.post("", response_model=DefectResponse, status_code=status.HTTP_201_CREATED)
def create_defect(
    payload: DefectCreate,
    db: Session = Depends(get_db_session),
) -> DefectResponse:
    """创建缺陷记录"""
    if payload.severity not in VALID_SEVERITIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的严重程度。可选值: {', '.join(VALID_SEVERITIES)}",
        )

    attachments_json = json.dumps(payload.attachments or [], ensure_ascii=False) if hasattr(payload, 'attachments') else None

    defect = Defect(
        submission_id=payload.submission_id,
        recommendation_id=payload.recommendation_id,
        execution_id=payload.execution_id,
        title=payload.title,
        description=payload.description,
        severity=payload.severity,
        priority=payload.priority,
        status="open",
        environment=payload.environment,
        browser=payload.browser,
        root_cause=payload.root_cause,
        attachments=attachments_json,
        creator=payload.creator,
        assignee=payload.assignee,
    )
    db.add(defect)
    db.commit()
    db.refresh(defect)
    logger.info("[defect] created id=%s", defect.id)
    return _defect_to_response(defect)


@router.post("/from-execution", response_model=DefectResponse, status_code=status.HTTP_201_CREATED)
def create_defect_from_execution(
    payload: DefectFromExecution,
    db: Session = Depends(get_db_session),
) -> DefectResponse:
    """
    从执行失败的用例一键创建缺陷。

    自动带入：关联用例、失败步骤、预期结果、实际结果。
    """
    tracker = ExecutionTracker()
    try:
        result = tracker.create_defect_from_execution(
            execution_id=payload.execution_id,
            title=payload.title,
            description=payload.description,
            severity=payload.severity,
            priority=payload.priority,
            creator=payload.creator,
            db=db,
        )
        defect = db.get(Defect, result["id"])
        return _defect_to_response(defect)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("", response_model=DefectListResponse)
def list_defects(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    submission_id: Optional[str] = Query(default=None, alias="submissionId"),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    severity_filter: Optional[str] = Query(default=None, alias="severity"),
    db: Session = Depends(get_db_session),
) -> DefectListResponse:
    """获取缺陷列表"""
    q = db.query(Defect)

    if submission_id:
        q = q.filter(Defect.submission_id == submission_id)
    if status_filter:
        if status_filter not in VALID_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的状态值。可选值: {', '.join(VALID_STATUSES)}",
            )
        q = q.filter(Defect.status == status_filter)
    if severity_filter:
        if severity_filter not in VALID_SEVERITIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的严重程度值。可选值: {', '.join(VALID_SEVERITIES)}",
            )
        q = q.filter(Defect.severity == severity_filter)

    total = q.count()
    rows = (
        q.order_by(Defect.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [_defect_to_response(r) for r in rows]
    return DefectListResponse(items=items, total=total, page=page, pageSize=page_size)


@router.get("/{defect_id}", response_model=DefectResponse)
def get_defect(
    defect_id: str,
    db: Session = Depends(get_db_session),
) -> DefectResponse:
    """获取缺陷详情"""
    defect = db.get(Defect, defect_id)
    if not defect:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="缺陷不存在")
    return _defect_to_response(defect)


@router.patch("/{defect_id}", response_model=DefectResponse)
def update_defect(
    defect_id: str,
    payload: DefectUpdate,
    db: Session = Depends(get_db_session),
) -> DefectResponse:
    """更新缺陷"""
    defect = db.get(Defect, defect_id)
    if not defect:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="缺陷不存在")

    if payload.status is not None:
        if payload.status not in VALID_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的状态值。可选值: {', '.join(VALID_STATUSES)}",
            )
        defect.status = payload.status
        if payload.status == "resolved":
            defect.resolved_at = datetime.now(timezone.utc)

    if payload.severity is not None:
        defect.severity = payload.severity
    if payload.priority is not None:
        defect.priority = payload.priority
    if payload.title is not None:
        defect.title = payload.title
    if payload.description is not None:
        defect.description = payload.description
    if payload.environment is not None:
        defect.environment = payload.environment
    if payload.browser is not None:
        defect.browser = payload.browser
    if payload.root_cause is not None:
        defect.root_cause = payload.root_cause
    if payload.assignee is not None:
        defect.assignee = payload.assignee
    if payload.attachments is not None:
        defect.attachments = json.dumps(payload.attachments, ensure_ascii=False)

    db.commit()
    db.refresh(defect)
    logger.info("[defect] updated id=%s status=%s", defect.id, defect.status)
    return _defect_to_response(defect)


@router.delete("/{defect_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_defect(
    defect_id: str,
    db: Session = Depends(get_db_session),
) -> None:
    """删除缺陷"""
    defect = db.get(Defect, defect_id)
    if not defect:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="缺陷不存在")
    db.delete(defect)
    db.commit()
    logger.info("[defect] deleted id=%s", defect_id)
