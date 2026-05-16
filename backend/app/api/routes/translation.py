from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session
from typing_extensions import Annotated

from app.api.routes.generate import _parse_uploads
from app.db.session import get_db_session
from app.models.translation import RequirementTranslation
from app.schemas.translation import (
    TranslationListItem,
    TranslationListResponse,
    TranslationResponse,
    TranslationUpdateRequest,
)
from app.services.llm_client import build_llm_client
from app.services.translation_service import translate_requirements

router = APIRouter(tags=["translation"])
logger = logging.getLogger(__name__)


@router.post("/translations", response_model=TranslationResponse)
async def create_translation(
    requirement_text: Annotated[str, Form(alias="requirementText")] = "",
    model_key: Annotated[Optional[str], Form(alias="modelKey")] = None,
    document_files: Annotated[Optional[list[UploadFile]], File(alias="documentFiles")] = None,
    image_files: Annotated[Optional[list[UploadFile]], File(alias="imageFiles")] = None,
    db: Session = Depends(get_db_session),
) -> TranslationResponse:
    requirement_text = requirement_text.strip()
    document_contexts, _image_contexts = await _parse_uploads(document_files, image_files)

    if not requirement_text and not document_contexts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请至少填写需求描述或上传参考文档。",
        )

    try:
        llm_client = build_llm_client(model_key)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    try:
        translated_content = translate_requirements(
            llm_client, requirement_text, document_contexts
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except Exception as exc:
        logger.exception("[translation] LLM call failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="需求翻译调用失败，请稍后重试。",
        ) from exc

    record = RequirementTranslation(
        original_requirement_text=requirement_text,
        translated_content=translated_content,
        status="pending_review",
        model_name=llm_client.profile.model_name,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return TranslationResponse(
        id=record.id,
        originalRequirementText=record.original_requirement_text,
        translatedContent=record.translated_content,
        reviewedContent=record.reviewed_content,
        status=record.status,
        modelName=record.model_name,
        createdAt=record.created_at,
        updatedAt=record.updated_at,
    )


@router.get("/translations", response_model=TranslationListResponse)
def list_translations(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, alias="pageSize")] = 20,
    db: Session = Depends(get_db_session),
) -> TranslationListResponse:
    total = db.query(RequirementTranslation).count()
    records = (
        db.query(RequirementTranslation)
        .order_by(RequirementTranslation.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [
        TranslationListItem(
            id=r.id,
            requirementPreview=(
                r.original_requirement_text[:80] + "..."
                if len(r.original_requirement_text) > 80
                else r.original_requirement_text
            ),
            status=r.status,
            modelName=r.model_name,
            createdAt=r.created_at,
        )
        for r in records
    ]

    return TranslationListResponse(
        items=items,
        total=total,
        page=page,
        pageSize=page_size,
    )


@router.get("/translations/{translation_id}", response_model=TranslationResponse)
def get_translation(
    translation_id: str,
    db: Session = Depends(get_db_session),
) -> TranslationResponse:
    record = db.get(RequirementTranslation, translation_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="翻译记录不存在。",
        )

    return TranslationResponse(
        id=record.id,
        originalRequirementText=record.original_requirement_text,
        translatedContent=record.translated_content,
        reviewedContent=record.reviewed_content,
        status=record.status,
        modelName=record.model_name,
        createdAt=record.created_at,
        updatedAt=record.updated_at,
    )


@router.put("/translations/{translation_id}", response_model=TranslationResponse)
def update_translation(
    translation_id: str,
    request: TranslationUpdateRequest,
    db: Session = Depends(get_db_session),
) -> TranslationResponse:
    record = db.get(RequirementTranslation, translation_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="翻译记录不存在。",
        )

    record.reviewed_content = request.reviewed_content
    record.status = request.status
    record.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)

    return TranslationResponse(
        id=record.id,
        originalRequirementText=record.original_requirement_text,
        translatedContent=record.translated_content,
        reviewedContent=record.reviewed_content,
        status=record.status,
        modelName=record.model_name,
        createdAt=record.created_at,
        updatedAt=record.updated_at,
    )


@router.delete("/translations/{translation_id}", response_model=dict)
def delete_translation(
    translation_id: str,
    db: Session = Depends(get_db_session),
) -> dict:
    record = db.get(RequirementTranslation, translation_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="翻译记录不存在。",
        )

    db.delete(record)
    db.commit()
    return {"ok": True}
