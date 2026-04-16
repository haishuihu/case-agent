from __future__ import annotations

import json
import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.models.generation import KnowledgeChunk, KnowledgeDocument
from app.schemas.knowledge import (
    KnowledgeChunkItem,
    KnowledgeDocumentCreate,
    KnowledgeDocumentDetail,
    KnowledgeDocumentItem,
    KnowledgeDocumentListResponse,
    KnowledgeDocumentUpdate,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSearchResultItem,
    KnowledgeStatsResponse,
)
from app.services.file_parser import parse_document_upload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def _serialize_module_tags(tags: Optional[list[str]]) -> Optional[str]:
    if tags is None:
        return None
    return json.dumps(tags, ensure_ascii=False)


def _deserialize_module_tags(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _parse_structured_payload(raw: Optional[str]) -> Optional[dict[str, object]]:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except (json.JSONDecodeError, TypeError):
        return None


def _doc_to_item(doc: KnowledgeDocument, chunk_count: int = 0) -> KnowledgeDocumentItem:
    return KnowledgeDocumentItem(
        id=doc.id,
        title=doc.title,
        docType=doc.doc_type,
        moduleTags=_deserialize_module_tags(doc.module_tags),
        status=doc.status,
        summary=doc.summary,
        sourceType=doc.source_type,
        sourceFilename=doc.source_filename,
        embeddingStatus=doc.embedding_status,
        createdAt=doc.created_at,
        updatedAt=doc.updated_at,
        chunkCount=chunk_count,
    )


def _doc_to_detail(doc: KnowledgeDocument) -> KnowledgeDocumentDetail:
    chunk_items = [
        KnowledgeChunkItem(
            id=c.id,
            chunkIndex=c.chunk_index,
            chunkText=c.chunk_text,
            tokenCount=c.token_count,
            hasEmbedding=c.embedding is not None,
        )
        for c in sorted(doc.chunks, key=lambda x: x.chunk_index)
    ]
    return KnowledgeDocumentDetail(
        id=doc.id,
        title=doc.title,
        docType=doc.doc_type,
        moduleTags=_deserialize_module_tags(doc.module_tags),
        status=doc.status,
        summary=doc.summary,
        sourceType=doc.source_type,
        sourceFilename=doc.source_filename,
        embeddingStatus=doc.embedding_status,
        createdAt=doc.created_at,
        updatedAt=doc.updated_at,
        chunkCount=len(chunk_items),
        content=doc.content,
        structuredPayload=_parse_structured_payload(doc.structured_payload),
        chunks=chunk_items,
    )


@router.post("/documents", response_model=KnowledgeDocumentItem, status_code=status.HTTP_201_CREATED)
def create_document(
    payload: KnowledgeDocumentCreate,
    db: Session = Depends(get_db_session),
) -> KnowledgeDocumentItem:
    if not payload.title.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="标题不能为空。")
    if not payload.content.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="内容不能为空。")

    doc = KnowledgeDocument(
        title=payload.title.strip(),
        doc_type=payload.doc_type,
        module_tags=_serialize_module_tags(payload.module_tags),
        source_type="manual",
        content=payload.content.strip(),
        structured_payload=json.dumps(payload.structured_payload, ensure_ascii=False)
        if payload.structured_payload
        else None,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    from app.services.knowledge_service import index_document
    index_document(db, doc)

    logger.info("[knowledge] created and indexed document id=%s title=%s", doc.id, doc.title)
    return _doc_to_item(doc)


@router.post("/documents/upload", response_model=KnowledgeDocumentItem, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: Annotated[str, Query()] = "",
    doc_type: Annotated[str, Query(alias="docType")] = "other",
    module_tags: Annotated[str, Query(alias="moduleTags")] = "",
    db: Session = Depends(get_db_session),
) -> KnowledgeDocumentItem:
    parsed = await parse_document_upload(file)

    effective_title = title.strip() or parsed.filename
    tags_list: list[str] = []
    if module_tags.strip():
        tags_list = [t.strip() for t in module_tags.split(",") if t.strip()]

    doc = KnowledgeDocument(
        title=effective_title,
        doc_type=doc_type,
        module_tags=_serialize_module_tags(tags_list),
        source_type="upload",
        source_filename=parsed.filename,
        content=parsed.extracted_text,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    from app.services.knowledge_service import index_document
    index_document(db, doc)

    logger.info("[knowledge] uploaded and indexed document id=%s filename=%s", doc.id, parsed.filename)
    return _doc_to_item(doc)


@router.get("/documents", response_model=KnowledgeDocumentListResponse)
def list_documents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    doc_type: Optional[str] = Query(default=None, alias="docType"),
    doc_status: Optional[str] = Query(default=None, alias="status"),
    search: Optional[str] = Query(default=None),
    db: Session = Depends(get_db_session),
) -> KnowledgeDocumentListResponse:
    query = db.query(KnowledgeDocument)

    if doc_type:
        query = query.filter(KnowledgeDocument.doc_type == doc_type)
    if doc_status:
        query = query.filter(KnowledgeDocument.status == doc_status)
    if search:
        keyword = f"%{search}%"
        query = query.filter(
            KnowledgeDocument.title.ilike(keyword)
            | KnowledgeDocument.content.ilike(keyword)
            | KnowledgeDocument.module_tags.ilike(keyword)
        )

    total = query.count()
    docs = (
        query.order_by(KnowledgeDocument.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    doc_ids = [d.id for d in docs]
    chunk_counts: dict[str, int] = {}
    if doc_ids:
        rows = (
            db.query(KnowledgeChunk.document_id, sa_func.count(KnowledgeChunk.id))
            .filter(KnowledgeChunk.document_id.in_(doc_ids))
            .group_by(KnowledgeChunk.document_id)
            .all()
        )
        chunk_counts = {row[0]: row[1] for row in rows}

    items = [_doc_to_item(d, chunk_counts.get(d.id, 0)) for d in docs]
    return KnowledgeDocumentListResponse(
        items=items, total=total, page=page, pageSize=page_size
    )


@router.get("/documents/{document_id}", response_model=KnowledgeDocumentDetail)
def get_document(
    document_id: str,
    db: Session = Depends(get_db_session),
) -> KnowledgeDocumentDetail:
    doc = db.get(KnowledgeDocument, document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识文档不存在。")
    return _doc_to_detail(doc)


@router.put("/documents/{document_id}", response_model=KnowledgeDocumentItem)
def update_document(
    document_id: str,
    payload: KnowledgeDocumentUpdate,
    db: Session = Depends(get_db_session),
) -> KnowledgeDocumentItem:
    doc = db.get(KnowledgeDocument, document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识文档不存在。")

    if payload.title is not None:
        doc.title = payload.title.strip()
    if payload.doc_type is not None:
        doc.doc_type = payload.doc_type
    if payload.module_tags is not None:
        doc.module_tags = _serialize_module_tags(payload.module_tags)
    if payload.status is not None:
        doc.status = payload.status
    if payload.summary is not None:
        doc.summary = payload.summary
    if payload.content is not None:
        doc.content = payload.content.strip()
        doc.embedding_status = "pending"
        db.flush()
        from app.services.knowledge_service import index_document
        index_document(db, doc)
        db.refresh(doc)
    if payload.structured_payload is not None:
        doc.structured_payload = json.dumps(payload.structured_payload, ensure_ascii=False)

    db.commit()
    db.refresh(doc)
    logger.info("[knowledge] updated document id=%s", doc.id)
    return _doc_to_item(doc)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_document(
    document_id: str,
    db: Session = Depends(get_db_session),
) -> None:
    doc = db.get(KnowledgeDocument, document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识文档不存在。")
    db.delete(doc)
    db.commit()
    logger.info("[knowledge] deleted document id=%s", document_id)


@router.post("/search", response_model=KnowledgeSearchResponse)
def search_knowledge(
    payload: KnowledgeSearchRequest,
    db: Session = Depends(get_db_session),
) -> KnowledgeSearchResponse:
    from app.services.knowledge_service import hybrid_search

    results = hybrid_search(
        db=db,
        query=payload.query,
        doc_types=payload.doc_types,
        module_tags=payload.module_tags,
        top_k=payload.top_k,
    )
    items = [
        KnowledgeSearchResultItem(
            documentId=doc.id,
            title=doc.title,
            docType=doc.doc_type,
            summary=doc.summary,
            relevanceScore=round(score, 4),
            matchSource=source,
        )
        for doc, score, source in results
    ]
    return KnowledgeSearchResponse(results=items)


@router.post("/documents/{document_id}/reindex", response_model=KnowledgeDocumentItem)
def reindex_document(
    document_id: str,
    db: Session = Depends(get_db_session),
) -> KnowledgeDocumentItem:
    doc = db.get(KnowledgeDocument, document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识文档不存在。")

    from app.services.knowledge_service import index_document

    index_document(db, doc)
    db.refresh(doc)
    logger.info("[knowledge] reindexed document id=%s status=%s", doc.id, doc.embedding_status)
    return _doc_to_item(doc, len(doc.chunks))


@router.get("/stats", response_model=KnowledgeStatsResponse)
def get_stats(
    db: Session = Depends(get_db_session),
) -> KnowledgeStatsResponse:
    total = db.query(sa_func.count(KnowledgeDocument.id)).scalar() or 0
    active = (
        db.query(sa_func.count(KnowledgeDocument.id))
        .filter(KnowledgeDocument.status == "active")
        .scalar()
        or 0
    )
    type_rows = (
        db.query(KnowledgeDocument.doc_type, sa_func.count(KnowledgeDocument.id))
        .group_by(KnowledgeDocument.doc_type)
        .all()
    )
    type_counts = {row[0]: row[1] for row in type_rows}

    emb_rows = (
        db.query(KnowledgeDocument.embedding_status, sa_func.count(KnowledgeDocument.id))
        .group_by(KnowledgeDocument.embedding_status)
        .all()
    )
    embedding_counts = {row[0]: row[1] for row in emb_rows}

    total_chunks = db.query(sa_func.count(KnowledgeChunk.id)).scalar() or 0

    return KnowledgeStatsResponse(
        totalDocuments=total,
        activeDocuments=active,
        typeCounts=type_counts,
        embeddingCounts=embedding_counts,
        totalChunks=total_chunks,
    )
