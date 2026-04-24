from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.models.quick_generate import QuickGenerateRecord
from app.schemas.generate import (
    QuickHistoryClearResponse,
    QuickHistoryItem,
    QuickHistoryListResponse,
)

router = APIRouter(prefix="/api/v1/generate/quick", tags=["quick-generate"])


def _preview_requirement(text: str, max_len: int = 80) -> str:
    stripped = text.strip().replace("\n", " ").replace("\r", "")
    return stripped[:max_len] + ("..." if len(stripped) > max_len else "")


@router.get("/history", response_model=QuickHistoryListResponse)
def list_quick_history(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, alias="pageSize")] = 30,
    db: Session = Depends(get_db_session),
) -> QuickHistoryListResponse:
    q = db.query(QuickGenerateRecord).order_by(QuickGenerateRecord.created_at.desc())
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    items = [
        QuickHistoryItem(
            id=row.id,
            requirementPreview=_preview_requirement(row.requirement_text),
            outputContent=row.output_content,
            modelName=row.model_name,
            createdAt=row.created_at,
        )
        for row in rows
    ]
    return QuickHistoryListResponse(
        items=items, total=total, page=page, pageSize=page_size
    )


@router.delete("/history", response_model=QuickHistoryClearResponse)
def clear_quick_history(
    db: Session = Depends(get_db_session),
) -> QuickHistoryClearResponse:
    deleted_count = db.query(QuickGenerateRecord).delete()
    db.commit()
    return QuickHistoryClearResponse(ok=True, deletedCount=deleted_count)
