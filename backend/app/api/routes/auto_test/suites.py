from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.models.auto_test import TestCase, TestCaseTag, TestCaseVersion, TestSuite
from app.schemas.auto_test import (
    TestCaseCreate,
    TestCaseResponse,
    TestCaseTagCreate,
    TestCaseTagResponse,
    TestCaseUpdate,
    TestCaseVersionResponse,
    TestSuiteCreate,
    TestSuiteResponse,
    TestSuiteUpdate,
)
from app.services.auto_test.ai_recommender import AIRecommender

router = APIRouter(prefix="/auto-test", tags=["auto-test"])


# ---- TestSuite CRUD ----

@router.get("/suites", response_model=list[TestSuiteResponse])
def list_suites(
    project_id: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db_session),
):
    query = db.query(TestSuite).filter(TestSuite.is_deleted == False)  # noqa: E712
    if project_id:
        query = query.filter(TestSuite.project_id == project_id)
    if is_active is not None:
        query = query.filter(TestSuite.is_active == is_active)
    
    suites = query.order_by(TestSuite.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for suite in suites:
        case_count = db.query(TestCase).filter(TestCase.suite_id == suite.id).count()
        suite_data = TestSuiteResponse.model_validate(suite)
        suite_data.case_count = case_count
        result.append(suite_data)
    return result


@router.post("/suites", response_model=TestSuiteResponse)
def create_suite(
    data: TestSuiteCreate,
    created_by: Optional[str] = Query(None),
    db: Session = Depends(get_db_session),
):
    suite = TestSuite(
        name=data.name,
        description=data.description,
        project_id=data.project_id,
        created_by=created_by,
        is_active=data.is_active,
    )
    db.add(suite)
    db.commit()
    db.refresh(suite)
    return TestSuiteResponse.model_validate(suite)


@router.get("/suites/{suite_id}", response_model=TestSuiteResponse)
def get_suite(suite_id: str, db: Session = Depends(get_db_session)):
    suite = db.query(TestSuite).filter(TestSuite.id == suite_id, TestSuite.is_deleted == False).first()  # noqa: E712
    if not suite:
        raise HTTPException(status_code=404, detail="套件不存在")

    case_count = db.query(TestCase).filter(TestCase.suite_id == suite.id).count()
    suite_data = TestSuiteResponse.model_validate(suite)
    suite_data.case_count = case_count
    return suite_data


@router.put("/suites/{suite_id}", response_model=TestSuiteResponse)
def update_suite(
    suite_id: str,
    data: TestSuiteUpdate,
    db: Session = Depends(get_db_session),
):
    suite = db.query(TestSuite).filter(TestSuite.id == suite_id).first()
    if not suite:
        raise HTTPException(status_code=404, detail="套件不存在")
    
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(suite, key, value)
    
    db.commit()
    db.refresh(suite)
    return TestSuiteResponse.model_validate(suite)


@router.delete("/suites/{suite_id}")
def delete_suite(suite_id: str, db: Session = Depends(get_db_session)):
    suite = db.query(TestSuite).filter(TestSuite.id == suite_id, TestSuite.is_deleted == False).first()  # noqa: E712
    if not suite:
        raise HTTPException(status_code=404, detail="套件不存在")

    suite.is_deleted = True
    suite.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "套件已删除"}


# ---- TestCase CRUD ----

@router.get("/cases", response_model=list[TestCaseResponse])
def list_cases(
    suite_id: Optional[str] = Query(None),
    case_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db_session),
):
    query = db.query(TestCase).filter(TestCase.is_deleted == False)  # noqa: E712
    if suite_id:
        query = query.filter(TestCase.suite_id == suite_id)
    if case_type:
        query = query.filter(TestCase.case_type == case_type)
    if status:
        query = query.filter(TestCase.status == status)
    if priority:
        query = query.filter(TestCase.priority == priority)
    if search:
        query = query.filter(TestCase.title.ilike(f"%{search}%"))

    cases = query.order_by(TestCase.created_at.desc()).offset(skip).limit(limit).all()
    
    # Convert SQLAlchemy models to response format
    result = []
    for c in cases:
        case_data = {
            "id": c.id,
            "suite_id": c.suite_id,
            "title": c.title,
            "description": c.description,
            "case_type": c.case_type,
            "status": c.status,
            "priority": c.priority,
            "method": c.method,
            "endpoint": c.endpoint,
            "headers": json.loads(c.headers) if c.headers else None,
            "request_body": json.loads(c.request_body) if c.request_body else None,
            "expected_status": c.expected_status,
            "expected_response": json.loads(c.expected_response) if c.expected_response else None,
            "validation_rules": json.loads(c.validation_rules) if c.validation_rules else None,
            "ui_selector": c.ui_selector,
            "ui_action": c.ui_action,
            "ui_expected": c.ui_expected,
            "test_data": json.loads(c.test_data) if c.test_data else None,
            "extra_metadata": json.loads(c.extra_metadata) if c.extra_metadata else None,
            "tags": json.loads(c.tags) if c.tags else None,
            "current_version": c.current_version,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
        }
        result.append(TestCaseResponse.model_validate(case_data))
    return result


@router.post("/cases", response_model=TestCaseResponse)
def create_case(data: TestCaseCreate, db: Session = Depends(get_db_session)):
    suite = db.query(TestSuite).filter(TestSuite.id == data.suite_id).first()
    if not suite:
        raise HTTPException(status_code=404, detail="套件不存在")
    
    case = TestCase(
        suite_id=data.suite_id,
        title=data.title,
        description=data.description,
        case_type=data.case_type,
        priority=data.priority,
        method=data.method,
        endpoint=data.endpoint,
        headers=json.dumps(data.headers) if data.headers else None,
        request_body=json.dumps(data.request_body) if data.request_body else None,
        expected_status=data.expected_status,
        expected_response=json.dumps(data.expected_response) if data.expected_response else None,
        validation_rules=json.dumps(data.validation_rules) if data.validation_rules else None,
        ui_selector=data.ui_selector,
        ui_action=data.ui_action,
        ui_expected=data.ui_expected,
        test_data=json.dumps(data.test_data) if data.test_data else None,
        extra_metadata=json.dumps(data.extra_metadata) if data.extra_metadata else None,
        tags=json.dumps(data.tags) if data.tags else None,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    
    # Convert to response format
    case_data = {
        "id": case.id,
        "suite_id": case.suite_id,
        "title": case.title,
        "description": case.description,
        "case_type": case.case_type,
        "status": case.status,
        "priority": case.priority,
        "method": case.method,
        "endpoint": case.endpoint,
        "headers": json.loads(case.headers) if case.headers else None,
        "request_body": json.loads(case.request_body) if case.request_body else None,
        "expected_status": case.expected_status,
        "expected_response": json.loads(case.expected_response) if case.expected_response else None,
        "validation_rules": json.loads(case.validation_rules) if case.validation_rules else None,
        "ui_selector": case.ui_selector,
        "ui_action": case.ui_action,
        "ui_expected": case.ui_expected,
        "test_data": json.loads(case.test_data) if case.test_data else None,
        "extra_metadata": json.loads(case.extra_metadata) if case.extra_metadata else None,
        "tags": json.loads(case.tags) if case.tags else None,
        "current_version": case.current_version,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
    }
    return TestCaseResponse.model_validate(case_data)


@router.get("/cases/{case_id}", response_model=TestCaseResponse)
def get_case(case_id: str, db: Session = Depends(get_db_session)):
    case = db.query(TestCase).filter(TestCase.id == case_id, TestCase.is_deleted == False).first()  # noqa: E712
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")

    # Convert to response format
    case_data = {
        "id": case.id,
        "suite_id": case.suite_id,
        "title": case.title,
        "description": case.description,
        "case_type": case.case_type,
        "status": case.status,
        "priority": case.priority,
        "method": case.method,
        "endpoint": case.endpoint,
        "headers": json.loads(case.headers) if case.headers else None,
        "request_body": json.loads(case.request_body) if case.request_body else None,
        "expected_status": case.expected_status,
        "expected_response": json.loads(case.expected_response) if case.expected_response else None,
        "validation_rules": json.loads(case.validation_rules) if case.validation_rules else None,
        "ui_selector": case.ui_selector,
        "ui_action": case.ui_action,
        "ui_expected": case.ui_expected,
        "test_data": json.loads(case.test_data) if case.test_data else None,
        "extra_metadata": json.loads(case.extra_metadata) if case.extra_metadata else None,
        "tags": json.loads(case.tags) if case.tags else None,
        "current_version": case.current_version,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
    }
    return TestCaseResponse.model_validate(case_data)


@router.put("/cases/{case_id}", response_model=TestCaseResponse)
def update_case(
    case_id: str,
    data: TestCaseUpdate,
    db: Session = Depends(get_db_session),
):
    case = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")
    
    update_data = data.model_dump(exclude_unset=True, by_alias=False)
    
    for key, value in update_data.items():
        if key in ("headers", "request_body", "expected_response", "validation_rules", "test_data", "extra_metadata", "tags"):
            setattr(case, key, json.dumps(value) if value else None)
        else:
            setattr(case, key, value)
    
    db.commit()
    db.refresh(case)
    
    # Convert to response format
    case_data = {
        "id": case.id,
        "suite_id": case.suite_id,
        "title": case.title,
        "description": case.description,
        "case_type": case.case_type,
        "status": case.status,
        "priority": case.priority,
        "method": case.method,
        "endpoint": case.endpoint,
        "headers": json.loads(case.headers) if case.headers else None,
        "request_body": json.loads(case.request_body) if case.request_body else None,
        "expected_status": case.expected_status,
        "expected_response": json.loads(case.expected_response) if case.expected_response else None,
        "validation_rules": json.loads(case.validation_rules) if case.validation_rules else None,
        "ui_selector": case.ui_selector,
        "ui_action": case.ui_action,
        "ui_expected": case.ui_expected,
        "test_data": json.loads(case.test_data) if case.test_data else None,
        "extra_metadata": json.loads(case.extra_metadata) if case.extra_metadata else None,
        "tags": json.loads(case.tags) if case.tags else None,
        "current_version": case.current_version,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
    }
    return TestCaseResponse.model_validate(case_data)


@router.delete("/cases/{case_id}")
def delete_case(case_id: str, db: Session = Depends(get_db_session)):
    case = db.query(TestCase).filter(TestCase.id == case_id, TestCase.is_deleted == False).first()  # noqa: E712
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")

    case.is_deleted = True
    case.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "用例已删除"}


# ---- TestCaseTags ----

@router.get("/tags", response_model=list[TestCaseTagResponse])
def list_tags(db: Session = Depends(get_db_session)):
    tags = db.query(TestCaseTag).order_by(TestCaseTag.name).all()
    return [TestCaseTagResponse.model_validate(t) for t in tags]


@router.post("/tags", response_model=TestCaseTagResponse)
def create_tag(data: TestCaseTagCreate, db: Session = Depends(get_db_session)):
    existing = db.query(TestCaseTag).filter(TestCaseTag.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="标签已存在")
    
    tag = TestCaseTag(
        name=data.name,
        color=data.color,
        description=data.description,
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return TestCaseTagResponse.model_validate(tag)


@router.delete("/tags/{tag_id}")
def delete_tag(tag_id: str, db: Session = Depends(get_db_session)):
    tag = db.query(TestCaseTag).filter(TestCaseTag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")
    
    db.delete(tag)
    db.commit()
    return {"message": "标签已删除"}


# ---- TestCaseVersions ----

@router.get("/cases/{case_id}/versions", response_model=list[TestCaseVersionResponse])
def list_case_versions(case_id: str, db: Session = Depends(get_db_session)):
    case = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")
    
    from app.models.auto_test import TestCaseVersion
    versions = (
        db.query(TestCaseVersion)
        .filter(TestCaseVersion.case_id == case_id)
        .order_by(TestCaseVersion.version.desc())
        .all()
    )
    return [TestCaseVersionResponse.model_validate(v) for v in versions]


# ---- Case Version Diff & Restore ----

@router.get("/cases/{case_id}/versions/diff")
def diff_case_versions(
    case_id: str,
    v1: int = Query(..., description="第一个版本号"),
    v2: int = Query(..., description="第二个版本号"),
    db: Session = Depends(get_db_session),
):
    case = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")

    ver1 = (
        db.query(TestCaseVersion)
        .filter(TestCaseVersion.case_id == case_id, TestCaseVersion.version == v1)
        .first()
    )
    ver2 = (
        db.query(TestCaseVersion)
        .filter(TestCaseVersion.case_id == case_id, TestCaseVersion.version == v2)
        .first()
    )

    if not ver1 or not ver2:
        raise HTTPException(status_code=404, detail="版本不存在")

    content1 = json.loads(ver1.content) if ver1.content else {}
    content2 = json.loads(ver2.content) if ver2.content else {}

    diff = {}
    all_keys = set(content1.keys()) | set(content2.keys())
    for key in all_keys:
        val1 = content1.get(key)
        val2 = content2.get(key)
        if val1 != val2:
            diff[key] = {"v1": val1, "v2": val2}

    return {
        "case_id": case_id,
        "v1": v1,
        "v2": v2,
        "diff": diff,
    }


@router.post("/cases/{case_id}/versions/{version_id}/restore", response_model=TestCaseResponse)
def restore_case_version(
    case_id: str,
    version_id: str,
    changed_by: str = Query("system"),
    db: Session = Depends(get_db_session),
):
    case = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")

    target_version = (
        db.query(TestCaseVersion)
        .filter(TestCaseVersion.id == version_id, TestCaseVersion.case_id == case_id)
        .first()
    )
    if not target_version:
        raise HTTPException(status_code=404, detail="版本不存在")

    content = json.loads(target_version.content) if target_version.content else {}
    for key, value in content.items():
        if hasattr(case, key):
            setattr(case, key, value)

    case.current_version += 1
    new_version = TestCaseVersion(
        id=str(uuid4()),
        case_id=case.id,
        version=case.current_version,
        content=target_version.content,
        change_summary=f"恢复到版本 {target_version.version}",
        changed_by=changed_by,
    )
    db.add(new_version)
    db.commit()
    db.refresh(case)

    return _case_to_response(case)


# ---- Case Clone ----

@router.post("/cases/{case_id}/clone", response_model=TestCaseResponse)
def clone_case(
    case_id: str,
    suffix: str = Query(" (副本)", description="标题后缀"),
    db: Session = Depends(get_db_session),
):
    case = db.query(TestCase).filter(TestCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")

    new_case = TestCase(
        suite_id=case.suite_id,
        title=f"{case.title}{suffix}",
        description=case.description,
        case_type=case.case_type,
        status="draft",
        priority=case.priority,
        method=case.method,
        endpoint=case.endpoint,
        headers=case.headers,
        request_body=case.request_body,
        expected_status=case.expected_status,
        expected_response=case.expected_response,
        validation_rules=case.validation_rules,
        ui_selector=case.ui_selector,
        ui_action=case.ui_action,
        ui_expected=case.ui_expected,
        test_data=case.test_data,
        extra_metadata=case.extra_metadata,
        tags=case.tags,
    )
    db.add(new_case)
    db.commit()
    db.refresh(new_case)

    return _case_to_response(new_case)


# ---- Batch Import ----

@router.post("/cases/import/csv", response_model=list[TestCaseResponse])
def import_cases_csv(
    suite_id: str = Query(..., description="目标套件ID"),
    file: UploadFile = None,
    db: Session = Depends(get_db_session),
):
    suite = db.query(TestSuite).filter(TestSuite.id == suite_id).first()
    if not suite:
        raise HTTPException(status_code=404, detail="套件不存在")

    content = file.file.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    created = []
    for row in reader:
        case = TestCase(
            suite_id=suite_id,
            title=row.get("title", row.get("标题", "")),
            description=row.get("description", row.get("描述", "")),
            case_type=row.get("case_type", row.get("类型", "api")),
            priority=int(row.get("priority", row.get("优先级", "3"))),
            method=row.get("method", row.get("方法", "")),
            endpoint=row.get("endpoint", row.get("端点", "")),
            expected_status=int(row.get("expected_status", row.get("预期状态码", "200"))),
            tags=json.dumps([t.strip() for t in row.get("tags", row.get("标签", "")).split(",") if t.strip()]) if row.get("tags") or row.get("标签") else None,
        )
        db.add(case)
        created.append(case)

    db.commit()
    for c in created:
        db.refresh(c)

    result = []
    for c in created:
        case_data = _build_case_data(c)
        result.append(TestCaseResponse.model_validate(case_data))
    return result


# ---- Batch Export ----

@router.get("/cases/export")
def export_cases(
    suite_id: Optional[str] = Query(None),
    format: str = Query("csv", description="导出格式: csv, json"),
    db: Session = Depends(get_db_session),
):
    query = db.query(TestCase)
    if suite_id:
        query = query.filter(TestCase.suite_id == suite_id)
    cases = query.order_by(TestCase.created_at.desc()).all()

    if format == "json":
        data = [_build_case_data(c) for c in cases]
        json_bytes = json.dumps(data, ensure_ascii=False, indent=2, default=str).encode("utf-8")
        return StreamingResponse(
            io.BytesIO(json_bytes),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=test_cases.json"},
        )

    # Default CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["title", "description", "case_type", "priority", "method", "endpoint", "expected_status", "status", "tags"])
    for case in cases:
        tags_str = ",".join(json.loads(case.tags)) if case.tags else ""
        writer.writerow([
            case.title, case.description or "", case.case_type, case.priority,
            case.method or "", case.endpoint or "", case.expected_status,
            case.status, tags_str,
        ])

    csv_bytes = output.getvalue().encode("utf-8-sig")
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=test_cases.csv"},
    )


# ---- AI 转换：从生成用例到 UI 自动化 ----

@router.post("/cases/convert-from-generation", response_model=list[TestCaseResponse])
def convert_from_generation(
    generation_id: str = Query(..., description="生成记录ID"),
    suite_id: str = Query(..., description="目标套件ID"),
    case_ids: Optional[str] = Query(None, description="要转换的用例ID列表，逗号分隔。不传则转换全部"),
    base_url: Optional[str] = Query(None, description="目标站点地址，如 https://staging.example.com"),
    db: Session = Depends(get_db_session),
):
    suite = db.query(TestSuite).filter(TestSuite.id == suite_id).first()
    if not suite:
        raise HTTPException(status_code=404, detail="套件不存在")

    from app.models.generation import GenerationRecord
    gen = db.query(GenerationRecord).filter(GenerationRecord.id == generation_id).first()
    if not gen:
        raise HTTPException(status_code=404, detail="生成记录不存在")
    if not gen.raw_response:
        raise HTTPException(status_code=400, detail="生成记录中没有结构化数据")

    from app.services.testcase_parser import load_generation_snapshot
    cases, _metadata = load_generation_snapshot(gen.raw_response, gen.output_markdown or "")

    if case_ids:
        selected_ids = set(case_ids.split(","))
        cases = [c for c in cases if c.caseId in selected_ids]

    if not cases:
        raise HTTPException(status_code=400, detail="没有可转换的用例")

    from app.services.auto_test.case_converter import convert_cases_to_ui, build_case_from_ui_step
    converted_list = convert_cases_to_ui(cases)

    created = []
    for i, converted in enumerate(converted_list):
        if i >= len(cases):
            break
        case_data = build_case_from_ui_step(converted, suite_id, cases[i], base_url)
        case = TestCase(
            suite_id=case_data["suite_id"],
            title=case_data["title"],
            description=case_data["description"],
            case_type=case_data["case_type"],
            priority=case_data["priority"],
            ui_selector=case_data["ui_selector"],
            ui_action=case_data["ui_action"],
            ui_expected=case_data["ui_expected"],
            tags=json.dumps(case_data.get("tags")),
            test_data=json.dumps(case_data.get("test_data")),
            extra_metadata=json.dumps(case_data.get("extra_metadata")),
        )
        db.add(case)
        created.append(case)

    db.commit()
    for c in created:
        db.refresh(c)

    result = []
    for c in created:
        case_data = _build_case_data(c)
        result.append(TestCaseResponse.model_validate(case_data))
    return result


# ---- Helpers ----

def _build_case_data(case: TestCase) -> dict:
    return {
        "id": case.id,
        "suite_id": case.suite_id,
        "title": case.title,
        "description": case.description,
        "case_type": case.case_type,
        "status": case.status,
        "priority": case.priority,
        "method": case.method,
        "endpoint": case.endpoint,
        "headers": json.loads(case.headers) if case.headers else None,
        "request_body": json.loads(case.request_body) if case.request_body else None,
        "expected_status": case.expected_status,
        "expected_response": json.loads(case.expected_response) if case.expected_response else None,
        "validation_rules": json.loads(case.validation_rules) if case.validation_rules else None,
        "ui_selector": case.ui_selector,
        "ui_action": case.ui_action,
        "ui_expected": case.ui_expected,
        "test_data": json.loads(case.test_data) if case.test_data else None,
        "extra_metadata": json.loads(case.extra_metadata) if case.extra_metadata else None,
        "tags": json.loads(case.tags) if case.tags else None,
        "current_version": case.current_version,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
    }


def _case_to_response(case: TestCase) -> TestCaseResponse:
    return TestCaseResponse.model_validate(_build_case_data(case))
