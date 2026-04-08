from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class KnowledgeDocumentCreate(BaseModel):
    title: str
    doc_type: str = Field(default="other", alias="docType")
    module_tags: list[str] = Field(default_factory=list, alias="moduleTags")
    content: str
    structured_payload: Optional[dict[str, object]] = Field(
        default=None, alias="structuredPayload"
    )

    model_config = {"populate_by_name": True}


class KnowledgeDocumentUpdate(BaseModel):
    title: Optional[str] = None
    doc_type: Optional[str] = Field(default=None, alias="docType")
    module_tags: Optional[list[str]] = Field(default=None, alias="moduleTags")
    status: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    structured_payload: Optional[dict[str, object]] = Field(
        default=None, alias="structuredPayload"
    )

    model_config = {"populate_by_name": True}


class KnowledgeChunkItem(BaseModel):
    id: str
    chunk_index: int = Field(alias="chunkIndex")
    chunk_text: str = Field(alias="chunkText")
    token_count: int = Field(alias="tokenCount")
    has_embedding: bool = Field(alias="hasEmbedding")

    model_config = {"populate_by_name": True}


class KnowledgeDocumentItem(BaseModel):
    id: str
    title: str
    doc_type: str = Field(alias="docType")
    module_tags: list[str] = Field(default_factory=list, alias="moduleTags")
    status: str
    summary: Optional[str] = None
    source_type: str = Field(alias="sourceType")
    source_filename: Optional[str] = Field(default=None, alias="sourceFilename")
    embedding_status: str = Field(alias="embeddingStatus")
    created_at: datetime = Field(alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")
    chunk_count: int = Field(default=0, alias="chunkCount")

    model_config = {"populate_by_name": True}


class KnowledgeDocumentDetail(KnowledgeDocumentItem):
    content: str
    structured_payload: Optional[dict[str, object]] = Field(
        default=None, alias="structuredPayload"
    )
    chunks: list[KnowledgeChunkItem] = Field(default_factory=list)


class KnowledgeDocumentListResponse(BaseModel):
    items: list[KnowledgeDocumentItem]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")

    model_config = {"populate_by_name": True}


class KnowledgeSearchRequest(BaseModel):
    query: str
    doc_types: Optional[list[str]] = Field(default=None, alias="docTypes")
    module_tags: Optional[list[str]] = Field(default=None, alias="moduleTags")
    top_k: int = Field(default=5, alias="topK")

    model_config = {"populate_by_name": True}


class KnowledgeSearchResultItem(BaseModel):
    document_id: str = Field(alias="documentId")
    title: str
    doc_type: str = Field(alias="docType")
    summary: Optional[str] = None
    relevance_score: float = Field(alias="relevanceScore")
    match_source: str = Field(alias="matchSource")

    model_config = {"populate_by_name": True}


class KnowledgeSearchResponse(BaseModel):
    results: list[KnowledgeSearchResultItem]


class KnowledgeStatsResponse(BaseModel):
    total_documents: int = Field(alias="totalDocuments")
    active_documents: int = Field(alias="activeDocuments")
    type_counts: dict[str, int] = Field(default_factory=dict, alias="typeCounts")
    embedding_counts: dict[str, int] = Field(
        default_factory=dict, alias="embeddingCounts"
    )
    total_chunks: int = Field(default=0, alias="totalChunks")

    model_config = {"populate_by_name": True}
