from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class GenerationRecord(Base):
    __tablename__ = "generation_records"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    requirement_text: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(nullable=False)
    prompt_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    output_markdown: Mapped[Optional[str]] = mapped_column(Text)
    raw_response: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(default="succeeded", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    progress_phase: Mapped[str] = mapped_column(default="", nullable=False)
    progress_detail: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    client_model_key: Mapped[Optional[str]] = mapped_column()
    cancel_requested: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    attachments: Mapped[list["GenerationAttachment"]] = relationship(
        back_populates="generation",
        cascade="all, delete-orphan",
    )


class GenerationAttachment(Base):
    __tablename__ = "generation_attachments"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    generation_id: Mapped[str] = mapped_column(ForeignKey("generation_records.id"), nullable=False)
    file_role: Mapped[str] = mapped_column(nullable=False)
    filename: Mapped[str] = mapped_column(nullable=False)
    content_type: Mapped[str] = mapped_column(nullable=False)
    extracted_content: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    generation: Mapped[GenerationRecord] = relationship(back_populates="attachments")


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(nullable=False)
    doc_type: Mapped[str] = mapped_column(nullable=False, default="other")
    module_tags: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(nullable=False, default="active")
    summary: Mapped[Optional[str]] = mapped_column(Text)
    structured_payload: Mapped[Optional[str]] = mapped_column(Text)
    source_filename: Mapped[Optional[str]] = mapped_column()
    embedding_status: Mapped[str] = mapped_column(default="pending")
    source_type: Mapped[str] = mapped_column(nullable=False, default="manual")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    document_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[str]] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    document: Mapped[KnowledgeDocument] = relationship(back_populates="chunks")
