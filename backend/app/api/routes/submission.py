from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.models.submission import Submission, SubmissionChecklist
from app.schemas.submission import (
    ChecklistCheckRequest,
    ChecklistItemResponse,
    GenerateChecklistRequest,
    GenerateChecklistResponse,
    SubmissionCreate,
    SubmissionItem,
    SubmissionListResponse,
    SubmissionUpdate,
)
from app.services.checklist_generator import ChecklistGenerator
from app.services.impact_analyzer import ImpactAnalyzer

router = APIRouter(prefix="/submissions", tags=["submissions"])
logger = logging.getLogger(__name__)


def _serialize_modules(modules: Optional[list[str]]) -> Optional[str]:
    if modules is None:
        return None
    return json.dumps(modules, ensure_ascii=False)


def _deserialize_modules(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _submission_to_item(submission: Submission) -> SubmissionItem:
    checklists = [
        ChecklistItemResponse(
            id=c.id,
            item=c.item,
            checkMethod=c.check_method or "",
            passCriteria=c.pass_criteria or "",
            riskLevel=c.risk_level,
            category=c.category,
            isChecked=c.is_checked,
            checkResult=c.check_result,
            checkedBy=c.checked_by,
            checkedAt=c.checked_at,
            isAiGenerated=c.is_ai_generated,
        )
        for c in submission.checklists
    ]

    gate_result = None
    if submission.gate_result:
        try:
            gate_result = json.loads(submission.gate_result)
        except json.JSONDecodeError:
            pass

    return SubmissionItem(
        id=submission.id,
        version=submission.version,
        submissionType=submission.submission_type,
        requirementId=submission.requirement_id,
        requirementLink=submission.requirement_link,
        changeDescription=submission.change_description,
        affectedModules=_deserialize_modules(submission.affected_modules),
        changeType=submission.change_type,
        selfTestPassed=submission.self_test_passed,
        selfTestCaseCount=submission.self_test_case_count,
        selfTestCoverage=submission.self_test_coverage,
        selfTestConclusion=submission.self_test_conclusion,
        smokeTestResult=submission.smoke_test_result,
        blockingIssueCount=submission.blocking_issue_count,
        status=submission.status,
        gateResult=gate_result,
        gateRejectReason=submission.gate_reject_reason,
        gitDiff=submission.git_diff,
        gitCommitHash=submission.git_commit_hash,
        branchName=submission.branch_name,
        submitter=submission.submitter,
        reviewedBy=submission.reviewed_by,
        createdAt=submission.created_at,
        updatedAt=submission.updated_at,
        checklists=checklists,
    )


@router.post("", response_model=SubmissionItem, status_code=status.HTTP_201_CREATED)
def create_submission(
    payload: SubmissionCreate,
    db: Session = Depends(get_db_session),
) -> SubmissionItem:
    """创建提测申请"""
    submission = Submission(
        version=payload.version,
        submission_type=payload.submission_type,
        requirement_id=payload.requirement_id,
        requirement_link=payload.requirement_link,
        change_description=payload.change_description,
        affected_modules=_serialize_modules(payload.affected_modules),
        change_type=payload.change_type,
        self_test_passed=payload.self_test_passed,
        self_test_case_count=payload.self_test_case_count,
        self_test_coverage=payload.self_test_coverage,
        self_test_conclusion=payload.self_test_conclusion,
        smoke_test_result=payload.smoke_test_result,
        blocking_issue_count=payload.blocking_issue_count,
        git_diff=payload.git_diff,
        git_commit_hash=payload.git_commit_hash,
        branch_name=payload.branch_name,
        submitter=payload.submitter,
        status="pending",
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    logger.info("[submission] created id=%s version=%s", submission.id, submission.version)
    return _submission_to_item(submission)


@router.get("", response_model=SubmissionListResponse)
def list_submissions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: Session = Depends(get_db_session),
) -> SubmissionListResponse:
    """获取提测申请列表"""
    query = db.query(Submission)

    if status_filter:
        query = query.filter(Submission.status == status_filter)

    total = query.count()
    submissions = (
        query.order_by(Submission.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [_submission_to_item(s) for s in submissions]
    return SubmissionListResponse(
        items=items,
        total=total,
        page=page,
        pageSize=page_size,
    )


@router.get("/{submission_id}", response_model=SubmissionItem)
def get_submission(
    submission_id: str,
    db: Session = Depends(get_db_session),
) -> SubmissionItem:
    """获取提测申请详情"""
    submission = db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提测申请不存在")
    return _submission_to_item(submission)


@router.patch("/{submission_id}", response_model=SubmissionItem)
def update_submission(
    submission_id: str,
    payload: SubmissionUpdate,
    db: Session = Depends(get_db_session),
) -> SubmissionItem:
    """更新提测申请"""
    submission = db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提测申请不存在")

    if payload.status is not None:
        submission.status = payload.status
    if payload.self_test_passed is not None:
        submission.self_test_passed = payload.self_test_passed
    if payload.self_test_case_count is not None:
        submission.self_test_case_count = payload.self_test_case_count
    if payload.self_test_coverage is not None:
        submission.self_test_coverage = payload.self_test_coverage
    if payload.self_test_conclusion is not None:
        submission.self_test_conclusion = payload.self_test_conclusion
    if payload.smoke_test_result is not None:
        submission.smoke_test_result = payload.smoke_test_result
    if payload.blocking_issue_count is not None:
        submission.blocking_issue_count = payload.blocking_issue_count
    if payload.gate_result is not None:
        submission.gate_result = payload.gate_result
    if payload.gate_reject_reason is not None:
        submission.gate_reject_reason = payload.gate_reject_reason
    if payload.reviewed_by is not None:
        submission.reviewed_by = payload.reviewed_by
    if payload.submitter is not None:
        submission.submitter = payload.submitter

    db.commit()
    db.refresh(submission)

    logger.info("[submission] updated id=%s", submission.id)
    return _submission_to_item(submission)


@router.delete("/{submission_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_submission(
    submission_id: str,
    db: Session = Depends(get_db_session),
) -> None:
    """删除提测申请"""
    submission = db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提测申请不存在")

    db.delete(submission)
    db.commit()
    logger.info("[submission] deleted id=%s", submission_id)


@router.post("/checklist/generate", response_model=GenerateChecklistResponse)
def generate_checklist(
    payload: GenerateChecklistRequest,
    db: Session = Depends(get_db_session),
) -> GenerateChecklistResponse:
    """AI生成提测Checklist"""
    submission = db.get(Submission, payload.submission_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提测申请不存在")

    generator = ChecklistGenerator()
    result = generator.generate(
        change_description=payload.change_description,
        affected_modules=payload.affected_modules,
        git_diff=payload.git_diff or "",
        recent_defects=payload.recent_defects,
    )

    saved_checklists = []
    for item in result.get("checklists", []):
        checklist = SubmissionChecklist(
            submission_id=submission.id,
            item=item.get("item", ""),
            check_method=item.get("method", ""),
            pass_criteria=item.get("pass_criteria", ""),
            risk_level=item.get("risk_level", "medium"),
            category=item.get("category", "general"),
            is_ai_generated=True,
        )
        db.add(checklist)
        saved_checklists.append(item)

    submission.gate_result = json.dumps({
        "summary": result.get("summary", ""),
        "suggestions": result.get("suggestions", []),
        "high_risk_areas": result.get("high_risk_areas", []),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }, ensure_ascii=False)

    db.commit()

    logger.info("[submission] generated %d checklists for id=%s", len(saved_checklists), submission.id)

    return GenerateChecklistResponse(
        checklists=[
            {
                "item": c.get("item", ""),
                "method": c.get("method", ""),
                "pass_criteria": c.get("pass_criteria", ""),
                "risk_level": c.get("risk_level", "medium"),
                "category": c.get("category", "general"),
            }
            for c in saved_checklists
        ],
        summary=result.get("summary", ""),
        suggestions=result.get("suggestions", []),
        highRiskAreas=result.get("high_risk_areas", []),
    )


@router.post("/checklist/check")
def check_checklist(
    payload: ChecklistCheckRequest,
    db: Session = Depends(get_db_session),
) -> dict[str, object]:
    """更新Checklist检查状态"""
    checklist = db.get(SubmissionChecklist, payload.checklist_id)
    if not checklist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist项不存在")

    checklist.is_checked = payload.is_checked
    checklist.check_result = payload.check_result
    checklist.checked_by = payload.checked_by
    checklist.checked_at = datetime.now(timezone.utc)

    db.commit()

    all_checked = (
        db.query(SubmissionChecklist)
        .filter(
            SubmissionChecklist.submission_id == checklist.submission_id,
            SubmissionChecklist.risk_level == "high",
            SubmissionChecklist.is_checked == False,
        )
        .count()
    ) == 0

    submission = db.get(Submission, checklist.submission_id)
    if submission:
        if all_checked:
            submission.status = "self_test_passed"
        elif submission.status == "pending":
            submission.status = "self_test"
        db.commit()

    return {
        "ok": True,
        "high_risk_all_checked": all_checked,
        "checklist_id": checklist.id,
        "is_checked": checklist.is_checked,
    }


@router.post("/checklist/impact")
def analyze_impact(
    git_diff: str = Query(..., description="Git Diff内容"),
    affected_modules: str = Query(default="", description="影响模块，逗号分隔"),
    db: Session = Depends(get_db_session),
) -> dict[str, object]:
    """分析代码变更影响（使用与 /impact-analysis 相同的分析引擎）"""
    modules_list = [m.strip() for m in affected_modules.split(",") if m.strip()]

    analyzer = ImpactAnalyzer()
    result = analyzer.analyze(
        git_diff=git_diff,
        affected_modules=modules_list,
    )

    # 转换为与原接口兼容的简化格式
    return {
        "impacted_modules": [m["module_name"] for m in result["impacted_modules"]],
        "indirect_impacts": result.get("indirect_impacts", []),
        "data_flow_impacts": result.get("data_flow_impacts", []),
        "api_breaking_changes": result.get("api_breaking_changes", []),
        "risk_points": result.get("risk_points", []),
        "confidence_level": result.get("confidence_level", "medium"),
    }


@router.get("/{submission_id}/checklist", response_model=list[ChecklistItemResponse])
def get_submission_checklists(
    submission_id: str,
    db: Session = Depends(get_db_session),
) -> list[ChecklistItemResponse]:
    """获取提测申请的Checklist"""
    submission = db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提测申请不存在")

    return [
        ChecklistItemResponse(
            id=c.id,
            item=c.item,
            checkMethod=c.check_method or "",
            passCriteria=c.pass_criteria or "",
            riskLevel=c.risk_level,
            category=c.category,
            isChecked=c.is_checked,
            checkResult=c.check_result,
            checkedBy=c.checked_by,
            checkedAt=c.checked_at,
            isAiGenerated=c.is_ai_generated,
        )
        for c in submission.checklists
    ]
