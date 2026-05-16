from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.models.auto_test import (
    ExecutionStatus,
    ScheduleType,
    TestCase,
    TestExecution,
    TestPlan,
    TestSuite,
    TriggerConfig,
    TriggerType,
)
from app.schemas.auto_test import (
    GitWebhookPayload,
    RegressionRecommendItem,
    RegressionRecommendRequest,
    RegressionRecommendResponse,
    TestPlanCreate,
    TestPlanResponse,
    TestPlanUpdate,
    TriggerConfigCreate,
    TriggerConfigResponse,
    TriggerConfigUpdate,
    WebhookPayload,
)

router = APIRouter(tags=["auto-test"])


# ---- TestPlan CRUD ----

@router.get("/plans", response_model=list[TestPlanResponse])
def list_plans(
    suite_id: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db_session),
):
    query = db.query(TestPlan).filter(TestPlan.is_deleted == False)  # noqa: E712
    if suite_id:
        query = query.filter(TestPlan.suite_id == suite_id)
    if is_active is not None:
        query = query.filter(TestPlan.is_active == is_active)
    
    plans = query.order_by(TestPlan.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for plan in plans:
        execution_count = db.query(TestExecution).filter(TestExecution.plan_id == plan.id).count()
        last_execution = (
            db.query(TestExecution)
            .filter(TestExecution.plan_id == plan.id)
            .order_by(TestExecution.created_at.desc())
            .first()
        )
        plan_data = TestPlanResponse.model_validate(plan)
        plan_data.execution_count = execution_count
        plan_data.last_execution_at = last_execution.created_at if last_execution else None
        plan_data.last_execution_status = last_execution.status if last_execution else None
        result.append(plan_data)
    return result


@router.post("/plans", response_model=TestPlanResponse)
def create_plan(data: TestPlanCreate, db: Session = Depends(get_db_session)):
    suite = db.query(TestSuite).filter(TestSuite.id == data.suite_id).first()
    if not suite:
        raise HTTPException(status_code=404, detail="套件不存在")
    
    plan = TestPlan(
        suite_id=data.suite_id,
        name=data.name,
        description=data.description,
        schedule_type=data.schedule_type,
        schedule_config=json.dumps(data.schedule_config) if data.schedule_config else None,
        auto_execute=data.auto_execute,
        notification_config=json.dumps(data.notification_config) if data.notification_config else None,
        case_filter=json.dumps(data.case_filter) if data.case_filter else None,
        execution_config=json.dumps(data.execution_config) if data.execution_config else None,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return TestPlanResponse.model_validate(plan)


@router.get("/plans/{plan_id}", response_model=TestPlanResponse)
def get_plan(plan_id: str, db: Session = Depends(get_db_session)):
    plan = db.query(TestPlan).filter(TestPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")
    
    execution_count = db.query(TestExecution).filter(TestExecution.plan_id == plan.id).count()
    last_execution = (
        db.query(TestExecution)
        .filter(TestExecution.plan_id == plan.id)
        .order_by(TestExecution.created_at.desc())
        .first()
    )
    plan_data = TestPlanResponse.model_validate(plan)
    plan_data.execution_count = execution_count
    plan_data.last_execution_at = last_execution.created_at if last_execution else None
    plan_data.last_execution_status = last_execution.status if last_execution else None
    return plan_data


@router.put("/plans/{plan_id}", response_model=TestPlanResponse)
def update_plan(
    plan_id: str,
    data: TestPlanUpdate,
    db: Session = Depends(get_db_session),
):
    plan = db.query(TestPlan).filter(TestPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key in ("schedule_config", "notification_config", "case_filter", "execution_config"):
            setattr(plan, key, json.dumps(value) if value else None)
        else:
            setattr(plan, key, value)
    
    db.commit()
    db.refresh(plan)
    return TestPlanResponse.model_validate(plan)


@router.delete("/plans/{plan_id}")
def delete_plan(plan_id: str, db: Session = Depends(get_db_session)):
    plan = db.query(TestPlan).filter(TestPlan.id == plan_id, TestPlan.is_deleted == False).first()  # noqa: E712
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")

    plan.is_deleted = True
    plan.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "计划已删除"}


# ---- TriggerConfig CRUD ----

@router.get("/plans/{plan_id}/triggers", response_model=list[TriggerConfigResponse])
def list_triggers(plan_id: str, db: Session = Depends(get_db_session)):
    triggers = (
        db.query(TriggerConfig)
        .filter(TriggerConfig.plan_id == plan_id)
        .order_by(TriggerConfig.created_at.desc())
        .all()
    )
    return [TriggerConfigResponse.model_validate(t) for t in triggers]


@router.post("/plans/{plan_id}/triggers", response_model=TriggerConfigResponse)
def create_trigger(
    plan_id: str,
    data: TriggerConfigCreate,
    db: Session = Depends(get_db_session),
):
    plan = db.query(TestPlan).filter(TestPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")
    
    import secrets
    trigger = TriggerConfig(
        plan_id=plan_id,
        trigger_type=data.trigger_type,
        name=data.name,
        config=json.dumps(data.config) if data.config else None,
        enabled=data.enabled,
        secret_key=secrets.token_hex(16),
    )
    db.add(trigger)
    db.commit()
    db.refresh(trigger)
    return TriggerConfigResponse.model_validate(trigger)


@router.put("/triggers/{trigger_id}", response_model=TriggerConfigResponse)
def update_trigger(
    trigger_id: str,
    data: TriggerConfigUpdate,
    db: Session = Depends(get_db_session),
):
    trigger = db.query(TriggerConfig).filter(TriggerConfig.id == trigger_id).first()
    if not trigger:
        raise HTTPException(status_code=404, detail="触发器不存在")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "config":
            setattr(trigger, key, json.dumps(value) if value else None)
        else:
            setattr(trigger, key, value)
    
    db.commit()
    db.refresh(trigger)
    return TriggerConfigResponse.model_validate(trigger)


@router.delete("/triggers/{trigger_id}")
def delete_trigger(trigger_id: str, db: Session = Depends(get_db_session)):
    trigger = db.query(TriggerConfig).filter(TriggerConfig.id == trigger_id).first()
    if not trigger:
        raise HTTPException(status_code=404, detail="触发器不存在")
    
    db.delete(trigger)
    db.commit()
    return {"message": "触发器已删除"}


def _verify_webhook_secret(trigger: TriggerConfig, secret: str | None) -> bool:
    """Verify webhook secret if configured."""
    if not trigger.secret_key:
        return True
    if not secret:
        return False
    return secret == trigger.secret_key


def _resolve_plan_cases(db: Session, plan: TestPlan) -> list[str]:
    """Resolve case IDs for a plan based on its case_filter."""
    case_filter = json.loads(plan.case_filter) if plan.case_filter else {}
    query = db.query(TestCase).filter(
        TestCase.suite_id == plan.suite_id,
        TestCase.status == "active",
    )
    priority = case_filter.get("priority")
    if priority:
        query = query.filter(TestCase.priority >= priority)
    case_type = case_filter.get("case_type")
    if case_type:
        query = query.filter(TestCase.case_type == case_type)
    limit = case_filter.get("limit", 50)
    cases = query.order_by(TestCase.priority.desc()).limit(limit).all()
    return [c.id for c in cases]


def _create_execution_for_trigger(
    db: Session,
    plan: TestPlan,
    case_ids: list[str],
    name: str,
    triggered_by: str,
    trigger_source: str,
    auto_start: bool = True,
) -> TestExecution:
    execution = TestExecution(
        id=str(uuid4()),
        plan_id=plan.id,
        suite_id=plan.suite_id,
        name=name,
        status=ExecutionStatus.RUNNING.value if auto_start else ExecutionStatus.PENDING.value,
        case_ids=json.dumps(case_ids),
        triggered_by=triggered_by,
        trigger_source=trigger_source,
        started_at=datetime.utcnow() if auto_start else None,
    )
    db.add(execution)
    return execution


# ---- Git Webhook ----

@router.post("/webhooks/git")
def git_webhook(
    payload: GitWebhookPayload,
    db: Session = Depends(get_db_session),
):
    triggers = (
        db.query(TriggerConfig)
        .filter(
            TriggerConfig.trigger_type == "git_push",
            TriggerConfig.enabled == True,
        )
        .all()
    )

    triggered_plans = []
    triggered_executions = []
    for trigger in triggers:
        config = json.loads(trigger.config or "{}")
        branches = config.get("branches", [])
        if not branches or not payload.branch or payload.branch not in branches:
            continue

        if not _verify_webhook_secret(trigger, payload.secret):
            continue

        plan = db.query(TestPlan).filter(TestPlan.id == trigger.plan_id).first()
        if not plan or not plan.is_active:
            continue

        trigger.last_triggered_at = datetime.utcnow()
        case_ids = _resolve_plan_cases(db, plan)
        execution = _create_execution_for_trigger(
            db, plan, case_ids,
            name=f"Git Push: {payload.branch} ({payload.commit_sha[:7] if payload.commit_sha else 'unknown'})",
            triggered_by="git",
            trigger_source="git_push",
        )
        triggered_executions.append(execution.id)
        triggered_plans.append({
            "plan_id": plan.id,
            "plan_name": plan.name,
            "trigger_id": trigger.id,
            "execution_id": execution.id,
        })

    db.commit()

    return {
        "message": "Webhook received",
        "triggered_plans": triggered_plans,
        "executions_created": len(triggered_executions),
        "branch": payload.branch,
        "commit_sha": payload.commit_sha,
    }


# ---- Generic Webhooks (CICD / API / Schedule) ----

@router.post("/webhooks/{trigger_type}")
def generic_webhook(
    trigger_type: str,
    payload: WebhookPayload,
    db: Session = Depends(get_db_session),
):
    valid_types = ["cicd", "api_call", "schedule"]
    if trigger_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"不支持的触发类型: {trigger_type}")

    triggers = (
        db.query(TriggerConfig)
        .filter(
            TriggerConfig.trigger_type == trigger_type,
            TriggerConfig.enabled == True,
        )
        .all()
    )

    triggered = []
    for trigger in triggers:
        if not _verify_webhook_secret(trigger, payload.secret):
            continue

        plan = db.query(TestPlan).filter(TestPlan.id == trigger.plan_id).first()
        if not plan or not plan.is_active:
            continue

        trigger.last_triggered_at = datetime.utcnow()
        case_ids = _resolve_plan_cases(db, plan)
        execution = _create_execution_for_trigger(
            db, plan, case_ids,
            name=f"[{trigger_type}] {plan.name}",
            triggered_by=trigger_type,
            trigger_source=trigger_type,
        )
        triggered.append({
            "plan_id": plan.id,
            "plan_name": plan.name,
            "trigger_id": trigger.id,
            "execution_id": execution.id,
        })

    db.commit()

    return {
        "message": f"Webhook ({trigger_type}) received",
        "triggered": triggered,
    }


# ---- Regression Recommendation ----

@router.post("/recommend", response_model=RegressionRecommendResponse)
def get_regression_recommendation(
    data: RegressionRecommendRequest,
    db: Session = Depends(get_db_session),
):
    from app.services.auto_test.ai_recommender import AIRecommender

    recommender = AIRecommender(db)
    recommendations, summary = recommender.recommend(
        changed_files=data.changed_files,
        diff_content=data.diff_content,
        module_names=data.module_names,
        max_cases=data.max_cases,
    )

    if data.include_ai_recommendation:
        changed_modules = list(set(
            (data.module_names or []) +
            (recommender.analyze_changed_modules(data.changed_files or []) if data.changed_files else []) +
            (recommender.parse_diff_for_modules(data.diff_content or "") if data.diff_content else [])
        ))
        for item in recommendations:
            if not item.ai_reasoning:
                case = db.query(TestCase).filter(TestCase.id == item.case_id).first()
                if case:
                    item.ai_reasoning = recommender.get_ai_reasoning(case, changed_modules)

    total_duration = sum(r.estimated_duration_ms or 0 for r in recommendations)

    return RegressionRecommendResponse(
        total_recommended=len(recommendations),
        total_estimated_duration_ms=total_duration,
        recommendations=recommendations,
        summary=summary,
    )
