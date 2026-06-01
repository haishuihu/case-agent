from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.generation import GenerationRecord
from app.models.test_case import TestCase
from app.schemas.testcase import (
    GenerationMetadata,
    TestCaseCreate,
    TestCaseItem,
    TestCaseListResponse,
    TestCaseUpdate,
)


def _migrate_cases_from_raw(db: Session, task_id: str) -> list[TestCase]:
    """Extract cases from raw_response JSON and insert into test_case_items table."""
    record = db.query(GenerationRecord).filter(GenerationRecord.id == task_id).first()
    if not record or not record.raw_response:
        return []

    try:
        data = json.loads(record.raw_response)
    except json.JSONDecodeError:
        return []

    cases_data: list[dict] = data.get("cases", []) if isinstance(data, dict) else []
    if not cases_data:
        return []

    cases = []
    for i, case_data in enumerate(cases_data):
        tc = TestCase(
            generation_task_id=task_id,
            summary=case_data.get("summary", ""),
            priority=case_data.get("priority", "P2"),
            module=case_data.get("module", ""),
            category=case_data.get("category", ""),
            confirmation_note=case_data.get("confirmationNote"),
            source="ai",
            sort_order=i,
        )
        db.add(tc)
        cases.append(tc)

    db.commit()
    return cases


def _build_metadata(cases: list[TestCase]) -> GenerationMetadata:
    """Rebuild GenerationMetadata from current test_case_items rows."""
    total = len(cases)
    category_counts: dict[str, int] = {}
    module_counts: dict[str, int] = {}
    priority_counts: dict[str, int] = {}

    for tc in cases:
        cat = tc.category or "其他"
        mod = tc.module or "未分组"
        pri = tc.priority or "P2"
        category_counts[cat] = category_counts.get(cat, 0) + 1
        module_counts[mod] = module_counts.get(mod, 0) + 1
        priority_counts[pri] = priority_counts.get(pri, 0) + 1

    return GenerationMetadata(
        caseCount=total,
        categoryCounts=category_counts,
        moduleCounts=module_counts,
        priorityCounts=priority_counts,
        reviewQuestions=[],
        warnings=[],
        truncated=False,
        incompleteCategories=[],
    )


def get_or_migrate_cases(db: Session, task_id: str) -> list[TestCase]:
    """Return active cases for a task. Migrate from raw_response on first access."""
    existing = (
        db.query(TestCase)
        .filter(
            TestCase.generation_task_id == task_id,
            TestCase.is_deleted == False,
        )
        .first()
    )

    if existing is not None:
        return (
            db.query(TestCase)
            .filter(TestCase.generation_task_id == task_id, TestCase.is_deleted == False)
            .order_by(TestCase.sort_order)
            .all()
        )

    return _migrate_cases_from_raw(db, task_id)


def list_cases(db: Session, task_id: str) -> TestCaseListResponse:
    cases = get_or_migrate_cases(db, task_id)
    items = [_case_to_item(tc) for tc in cases]
    metadata = _build_metadata(cases)
    return TestCaseListResponse(cases=items, metadata=metadata)


def _case_to_item(tc: TestCase) -> TestCaseItem:
    return TestCaseItem(
        id=tc.id,
        summary=tc.summary,
        priority=tc.priority,
        module=tc.module,
        category=tc.category,
        confirmationNote=tc.confirmation_note,
        source=tc.source,
        updatedAt=tc.updated_at.isoformat() if tc.updated_at else None,
    )


def create_case(db: Session, task_id: str, data: TestCaseCreate) -> TestCaseItem:
    # Ensure migration happened
    get_or_migrate_cases(db, task_id)

    max_order = (
        db.query(TestCase.sort_order)
        .filter(TestCase.generation_task_id == task_id)
        .order_by(TestCase.sort_order.desc())
        .first()
    )
    next_order = (max_order[0] + 1) if max_order else 0

    tc = TestCase(
        generation_task_id=task_id,
        summary=data.summary,
        priority=data.priority,
        module=data.module,
        category=data.category,
        source=data.source,
        sort_order=next_order,
    )
    db.add(tc)
    db.commit()
    db.refresh(tc)
    return _case_to_item(tc)


def update_case(db: Session, case_id: str, data: TestCaseUpdate) -> TestCaseItem:
    tc = (
        db.query(TestCase)
        .filter(TestCase.id == case_id, TestCase.is_deleted == False)
        .first()
    )
    if not tc:
        raise ValueError(f"TestCase {case_id} not found")

    if data.summary is not None:
        tc.summary = data.summary
    if data.priority is not None:
        tc.priority = data.priority
    if data.module is not None:
        tc.module = data.module
    if data.category is not None:
        tc.category = data.category

    db.commit()
    db.refresh(tc)
    return _case_to_item(tc)


def soft_delete_case(db: Session, case_id: str) -> bool:
    tc = (
        db.query(TestCase)
        .filter(TestCase.id == case_id, TestCase.is_deleted == False)
        .first()
    )
    if not tc:
        return False
    tc.is_deleted = True
    db.commit()
    return True


def batch_soft_delete(db: Session, case_ids: list[str]) -> int:
    count = (
        db.query(TestCase)
        .filter(TestCase.id.in_(case_ids), TestCase.is_deleted == False)
        .update({"is_deleted": True}, synchronize_session="fetch")
    )
    db.commit()
    return count
