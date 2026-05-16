from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.models.auto_test import (
    ExecutionStatus,
    ResultStatus,
    TestCase,
    TestExecution,
    TestResult,
)
from app.schemas.auto_test import (
    DashboardStats,
    ExecutionCreateRequest,
    ExecutionDetailResponse,
    ExecutionResponse,
    ExecutionTrend,
    ExecutionUpdateRequest,
    FailureDistribution,
    RecentExecution,
    TestResultCreate,
    TestResultResponse,
)

router = APIRouter(tags=["auto-test"])


# ---- TestExecution CRUD ----

@router.get("/executions", response_model=list[ExecutionResponse])
def list_executions(
    plan_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    triggered_by: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db_session),
):
    query = db.query(TestExecution).filter(TestExecution.is_deleted == False)  # noqa: E712
    if plan_id:
        query = query.filter(TestExecution.plan_id == plan_id)
    if status:
        query = query.filter(TestExecution.status == status)
    if triggered_by:
        query = query.filter(TestExecution.triggered_by == triggered_by)
    
    executions = query.order_by(TestExecution.created_at.desc()).offset(skip).limit(limit).all()
    return [ExecutionResponse.model_validate(e) for e in executions]


@router.post("/executions", response_model=ExecutionResponse)
def create_execution(
    data: ExecutionCreateRequest,
    db: Session = Depends(get_db_session),
):
    name = data.name or f"执行 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    execution = TestExecution(
        plan_id=data.plan_id,
        suite_id=data.suite_id,
        name=name,
        status=ExecutionStatus.PENDING.value,
        case_ids=json.dumps(data.case_ids) if data.case_ids else None,
        context=json.dumps(data.context) if data.context else None,
        triggered_by=data.triggered_by,
        trigger_source=data.trigger_source or "manual",
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    return ExecutionResponse.model_validate(execution)


@router.get("/executions/{execution_id}", response_model=ExecutionDetailResponse)
def get_execution(execution_id: str, db: Session = Depends(get_db_session)):
    execution = db.query(TestExecution).filter(TestExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    
    results = (
        db.query(TestResult)
        .filter(TestResult.execution_id == execution_id)
        .all()
    )
    
    result_responses = []
    for result in results:
        case = db.query(TestCase).filter(TestCase.id == result.case_id).first()
        result_data = TestResultResponse.model_validate(result)
        if case:
            result_data.case_title = case.title
            result_data.case_type = case.case_type
        result_responses.append(result_data)
    
    execution_data = ExecutionDetailResponse.model_validate(execution)
    execution_data.case_ids = json.loads(execution.case_ids) if execution.case_ids else []
    execution_data.context = json.loads(execution.context) if execution.context else {}
    execution_data.results = result_responses
    
    ai_recommendations = json.loads(execution.ai_recommendations) if execution.ai_recommendations else None
    execution_data.ai_recommendations = ai_recommendations
    
    return execution_data


@router.put("/executions/{execution_id}", response_model=ExecutionResponse)
def update_execution(
    execution_id: str,
    data: ExecutionUpdateRequest,
    db: Session = Depends(get_db_session),
):
    execution = db.query(TestExecution).filter(TestExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "ai_recommendations" and value:
            setattr(execution, key, json.dumps(value))
        else:
            setattr(execution, key, value)
    
    if data.status == ExecutionStatus.RUNNING.value and not execution.started_at:
        execution.started_at = datetime.utcnow()
    elif data.status in (ExecutionStatus.COMPLETED.value, ExecutionStatus.FAILED.value):
        execution.completed_at = datetime.utcnow()
        if execution.started_at:
            execution.duration_ms = int(
                (execution.completed_at - execution.started_at).total_seconds() * 1000
            )
    
    db.commit()
    db.refresh(execution)
    return ExecutionResponse.model_validate(execution)


@router.post("/executions/{execution_id}/start", response_model=ExecutionResponse)
def start_execution(execution_id: str, db: Session = Depends(get_db_session)):
    execution = db.query(TestExecution).filter(TestExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    
    execution.status = ExecutionStatus.RUNNING.value
    execution.started_at = datetime.utcnow()
    
    db.commit()
    db.refresh(execution)
    return ExecutionResponse.model_validate(execution)


@router.post("/executions/{execution_id}/complete", response_model=ExecutionResponse)
def complete_execution(
    execution_id: str,
    status: str = Query("completed"),
    db: Session = Depends(get_db_session),
):
    execution = db.query(TestExecution).filter(TestExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    
    execution.status = status
    execution.completed_at = datetime.utcnow()
    
    if execution.started_at:
        execution.duration_ms = int(
            (execution.completed_at - execution.started_at).total_seconds() * 1000
        )
    
    if execution.total_cases > 0:
        execution.pass_rate = round(execution.passed_count / execution.total_cases * 100, 2)
    
    db.commit()
    db.refresh(execution)
    return ExecutionResponse.model_validate(execution)


# ---- TestResult ----

@router.post("/executions/{execution_id}/results", response_model=TestResultResponse)
def create_result(
    execution_id: str,
    data: TestResultCreate,
    db: Session = Depends(get_db_session),
):
    execution = db.query(TestExecution).filter(TestExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    
    result = TestResult(
        execution_id=execution_id,
        case_id=data.case_id,
        result=data.result,
        request_data=json.dumps(data.request_data) if data.request_data else None,
        response_data=json.dumps(data.response_data) if data.response_data else None,
        response_status=data.response_status,
        validation_details=json.dumps(data.validation_details) if data.validation_details else None,
        error_message=data.error_message,
        stack_trace=data.stack_trace,
        duration_ms=data.duration_ms,
        retry_count=data.retry_count,
        ai_analysis=data.ai_analysis,
        likely_root_cause=data.likely_root_cause,
        executed_at=datetime.utcnow(),
    )
    db.add(result)
    
    if data.result == ResultStatus.PASS.value:
        execution.passed_count += 1
    elif data.result == ResultStatus.FAIL.value:
        execution.failed_count += 1
    elif data.result == ResultStatus.BLOCKED.value:
        execution.blocked_count += 1
    elif data.result == ResultStatus.SKIPPED.value:
        execution.skipped_count += 1
    
    execution.total_cases = (
        execution.passed_count + execution.failed_count + 
        execution.blocked_count + execution.skipped_count
    )
    if execution.total_cases > 0:
        execution.pass_rate = round(execution.passed_count / execution.total_cases * 100, 2)
    
    db.commit()
    db.refresh(result)
    return TestResultResponse.model_validate(result)


# ---- Dashboard ----

@router.get("/dashboard/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db_session)):
    today = datetime.now(timezone.utc).date()
    today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
    
    pending_count = (
        db.query(TestExecution)
        .filter(TestExecution.status == ExecutionStatus.PENDING.value)
        .count()
    )
    running_count = (
        db.query(TestExecution)
        .filter(TestExecution.status == ExecutionStatus.RUNNING.value)
        .count()
    )
    
    today_executions = (
        db.query(TestExecution)
        .filter(TestExecution.created_at >= today_start)
        .all()
    )
    today_pass = sum(e.passed_count for e in today_executions)
    today_fail = sum(e.failed_count for e in today_executions)
    today_total = sum(e.total_cases for e in today_executions)
    today_pass_rate = round(today_pass / today_total * 100, 2) if today_total > 0 else 0.0
    
    from app.models.auto_test import TestSuite, TestPlan
    
    return DashboardStats(
        pending_count=pending_count,
        running_count=running_count,
        today_pass_count=today_pass,
        today_fail_count=today_fail,
        today_total_cases=today_total,
        today_pass_rate=today_pass_rate,
        total_suites=db.query(TestSuite).count(),
        total_cases=db.query(TestCase).count(),
        total_plans=db.query(TestPlan).count(),
        total_executions=db.query(TestExecution).count(),
    )


@router.get("/dashboard/recent", response_model=list[RecentExecution])
def get_recent_executions(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db_session),
):
    executions = (
        db.query(TestExecution)
        .order_by(TestExecution.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        RecentExecution(
            id=e.id,
            name=e.name,
            status=e.status,
            total_cases=e.total_cases,
            passed_count=e.passed_count,
            failed_count=e.failed_count,
            pass_rate=e.pass_rate,
            triggered_by=e.triggered_by,
            created_at=e.created_at,
            duration_ms=e.duration_ms,
        )
        for e in executions
    ]


@router.get("/dashboard/trends", response_model=list[ExecutionTrend])
def get_execution_trends(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db_session),
):
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=days)
    
    trends = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        day_start = datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc)
        day_end = datetime.combine(date, datetime.max.time()).replace(tzinfo=timezone.utc)
        
        executions = (
            db.query(TestExecution)
            .filter(
                TestExecution.created_at >= day_start,
                TestExecution.created_at <= day_end,
            )
            .all()
        )
        
        total = sum(e.total_cases for e in executions)
        passed = sum(e.passed_count for e in executions)
        failed = sum(e.failed_count for e in executions)
        pass_rate = round(passed / total * 100, 2) if total > 0 else 0.0
        
        trends.append(
            ExecutionTrend(
                date=date.isoformat(),
                total=total,
                passed=passed,
                failed=failed,
                pass_rate=pass_rate,
            )
        )
    
    return trends


@router.get("/dashboard/failures", response_model=list[FailureDistribution])
def get_failure_distribution(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db_session),
):
    recent_results = (
        db.query(TestResult)
        .filter(TestResult.result == ResultStatus.FAIL.value)
        .join(TestExecution)
        .filter(
            TestExecution.created_at >= datetime.now(timezone.utc) - timedelta(days=7)
        )
        .all()
    )
    
    case_failures = {}
    for result in recent_results:
        case = db.query(TestCase).filter(TestCase.id == result.case_id).first()
        if case:
            suite_id = case.suite_id
            if suite_id not in case_failures:
                case_failures[suite_id] = 0
            case_failures[suite_id] += 1
    
    total_failures = len(recent_results)
    distributions = []
    
    for suite_id, count in sorted(case_failures.items(), key=lambda x: x[1], reverse=True)[:limit]:
        suite = db.query(TestSuite).filter(TestSuite.id == suite_id).first()
        distributions.append(
            FailureDistribution(
                module=suite.name if suite else "Unknown",
                count=count,
                percentage=round(count / total_failures * 100, 2) if total_failures > 0 else 0,
            )
        )
    
    return distributions


# ---- Retry Failed ----

@router.post("/executions/{execution_id}/retry-failed", response_model=ExecutionResponse)
def retry_failed_cases(
    execution_id: str,
    db: Session = Depends(get_db_session),
):
    execution = db.query(TestExecution).filter(TestExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    failed_results = (
        db.query(TestResult)
        .filter(
            TestResult.execution_id == execution_id,
            TestResult.result == ResultStatus.FAIL.value,
        )
        .all()
    )

    if not failed_results:
        raise HTTPException(status_code=400, detail="没有失败的用例需要重试")

    failed_case_ids = list(set(r.case_id for r in failed_results))
    new_execution = TestExecution(
        id=str(uuid4()),
        plan_id=execution.plan_id,
        suite_id=execution.suite_id,
        name=f"[重试] {execution.name}",
        status=ExecutionStatus.PENDING.value,
        case_ids=json.dumps(failed_case_ids),
        triggered_by="retry",
        trigger_source="manual",
    )
    db.add(new_execution)
    db.commit()
    db.refresh(new_execution)

    return ExecutionResponse.model_validate(new_execution)


# ---- Report Generation ----

@router.get("/executions/{execution_id}/report")
def get_execution_report(
    execution_id: str,
    db: Session = Depends(get_db_session),
):
    execution = db.query(TestExecution).filter(TestExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    results = (
        db.query(TestResult)
        .filter(TestResult.execution_id == execution_id)
        .all()
    )

    from app.services.auto_test.report_generator import generate_execution_report
    html = generate_execution_report(execution, results)

    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)


# ---- WebSocket Progress ----

@router.websocket("/executions/{execution_id}/ws")
async def execution_websocket(websocket: WebSocket, execution_id: str):
    await websocket.accept()

    db = next(get_db_session())
    try:
        execution = db.query(TestExecution).filter(TestExecution.id == execution_id).first()
        if not execution:
            await websocket.send_json({"type": "error", "message": "执行记录不存在"})
            await websocket.close()
            return

        prev_results_count = 0
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=5)
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                pass
            except (WebSocketDisconnect, Exception):
                break

            db.refresh(execution)
            results = (
                db.query(TestResult)
                .filter(TestResult.execution_id == execution_id)
                .order_by(TestResult.created_at.asc())
                .all()
            )

            if len(results) > prev_results_count:
                new_results = results[prev_results_count:]
                for r in new_results:
                    await websocket.send_json({
                        "type": "result",
                        "case_id": r.case_id,
                        "result": r.result,
                        "duration_ms": r.duration_ms,
                        "error_message": r.error_message[:200] if r.error_message else None,
                    })

                total = execution.total_cases or len(results)
                passed = execution.passed_count
                failed = execution.failed_count
                await websocket.send_json({
                    "type": "progress",
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "progress_pct": round((passed + failed) / total * 100, 1) if total > 0 else 0,
                })
                prev_results_count = len(results)

            if execution.status in (ExecutionStatus.COMPLETED.value, ExecutionStatus.FAILED.value, ExecutionStatus.CANCELLED.value):
                await websocket.send_json({
                    "type": "complete",
                    "status": execution.status,
                    "pass_rate": execution.pass_rate,
                    "duration_ms": execution.duration_ms,
                })
                break

        await websocket.close()
    finally:
        db.close()
