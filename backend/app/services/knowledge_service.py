from __future__ import annotations

import json
import logging
import re
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.generation import KnowledgeChunk, KnowledgeDocument
from app.services.embedding_client import (
    generate_embeddings,
    generate_single_embedding,
    is_embedding_available,
)

logger = logging.getLogger(__name__)

CHUNK_MAX_CHARS = 1500
CHUNK_OVERLAP_CHARS = 150


def _estimate_tokens(text: str) -> int:
    return max(len(text) // 3, 1)


def chunk_document_text(content: str) -> list[str]:
    paragraphs = re.split(r"\n{2,}", content.strip())
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current) + len(para) + 2 <= CHUNK_MAX_CHARS:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current)
            if len(para) > CHUNK_MAX_CHARS:
                for i in range(0, len(para), CHUNK_MAX_CHARS - CHUNK_OVERLAP_CHARS):
                    chunks.append(para[i : i + CHUNK_MAX_CHARS])
            else:
                overlap_text = current[-(CHUNK_OVERLAP_CHARS):] if current else ""
                current = f"{overlap_text}\n\n{para}" if overlap_text else para
                continue
            current = ""

    if current:
        chunks.append(current)

    return chunks if chunks else [content[:CHUNK_MAX_CHARS] or content]


def index_document(db: Session, doc: KnowledgeDocument) -> None:
    db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == doc.id).delete()
    db.flush()

    text_chunks = chunk_document_text(doc.content)
    logger.info("[knowledge] chunking doc=%s chunks=%d", doc.id, len(text_chunks))

    embeddings: Optional[list[list[float]]] = None
    if is_embedding_available():
        try:
            doc.embedding_status = "processing"
            db.flush()
            embeddings = generate_embeddings(text_chunks)
            doc.embedding_status = "completed"
        except Exception as exc:
            logger.warning("[knowledge] embedding failed for doc=%s: %s", doc.id, exc)
            doc.embedding_status = "failed"
    else:
        doc.embedding_status = "pending"

    for idx, chunk_text in enumerate(text_chunks):
        emb_json = json.dumps(embeddings[idx]) if embeddings and idx < len(embeddings) else None
        chunk = KnowledgeChunk(
            document_id=doc.id,
            chunk_index=idx,
            chunk_text=chunk_text,
            embedding=emb_json,
            token_count=_estimate_tokens(chunk_text),
        )
        db.add(chunk)

    db.commit()
    logger.info("[knowledge] indexed doc=%s status=%s", doc.id, doc.embedding_status)


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


def coarse_filter(
    db: Session,
    doc_types: Optional[list[str]] = None,
    module_keywords: Optional[list[str]] = None,
    limit: int = 50,
) -> list[KnowledgeDocument]:
    query = db.query(KnowledgeDocument).filter(KnowledgeDocument.status == "active")
    if doc_types:
        query = query.filter(KnowledgeDocument.doc_type.in_(doc_types))
    if module_keywords:
        conditions: list = []
        for kw in module_keywords:
            conditions.append(KnowledgeDocument.module_tags.contains(kw))
            conditions.append(KnowledgeDocument.title.ilike(f"%{kw}%"))
            conditions.append(KnowledgeDocument.content.ilike(f"%{kw}%"))
            if KnowledgeDocument.summary is not None:
                conditions.append(KnowledgeDocument.summary.ilike(f"%{kw}%"))
        query = query.filter(or_(*conditions))
    return (
        query.order_by(KnowledgeDocument.created_at.desc())
        .limit(limit)
        .all()
    )


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a < 1e-9 or norm_b < 1e-9:
        return 0.0
    return dot / (norm_a * norm_b)


def embedding_rerank(
    query_embedding: list[float],
    candidate_doc_ids: list[str],
    db: Session,
    top_k: int = 8,
) -> list[tuple[str, float]]:
    if not candidate_doc_ids:
        return []

    chunks = (
        db.query(KnowledgeChunk)
        .filter(
            KnowledgeChunk.document_id.in_(candidate_doc_ids),
            KnowledgeChunk.embedding.isnot(None),
        )
        .all()
    )

    doc_best: dict[str, float] = {}
    for chunk in chunks:
        try:
            chunk_vec = json.loads(chunk.embedding)
        except (json.JSONDecodeError, TypeError):
            continue
        similarity = _cosine_similarity(query_embedding, chunk_vec)
        doc_best[chunk.document_id] = max(doc_best.get(chunk.document_id, 0.0), similarity)

    ranked = sorted(doc_best.items(), key=lambda x: x[1], reverse=True)[:top_k]
    return ranked


def hybrid_search(
    db: Session,
    query: str,
    doc_types: Optional[list[str]] = None,
    module_tags: Optional[list[str]] = None,
    top_k: int = 8,
) -> list[tuple[KnowledgeDocument, float, str]]:
    keywords = module_tags or []
    if not keywords:
        keywords = [w.strip() for w in re.split(r"[\s,，;；、]+", query) if len(w.strip()) >= 2]
    if query.strip() not in keywords:
        keywords.append(query.strip())

    candidates = coarse_filter(db, doc_types=doc_types, module_keywords=keywords)
    if not candidates:
        return []

    candidate_map = {d.id: d for d in candidates}

    if is_embedding_available():
        try:
            query_embedding = generate_single_embedding(query)
            ranked = embedding_rerank(query_embedding, list(candidate_map.keys()), db, top_k)
            results: list[tuple[KnowledgeDocument, float, str]] = []
            for doc_id, score in ranked:
                if doc_id in candidate_map:
                    results.append((candidate_map[doc_id], score, "embedding"))
            remaining = [d for d in candidates if d.id not in {r[0].id for r in results}]
            for d in remaining[:max(0, top_k - len(results))]:
                results.append((d, 0.0, "tag"))
            return results[:top_k]
        except Exception as exc:
            logger.warning("[knowledge] embedding search failed, falling back to tag-only: %s", exc)

    return [(d, 0.0, "tag") for d in candidates[:top_k]]


# ---------------------------------------------------------------------------
# Retrieve knowledge context for prompt injection
# ---------------------------------------------------------------------------


def retrieve_knowledge_for_generation(
    db: Session,
    requirement_text: str,
    module_names: Optional[list[str]] = None,
    top_k: int = 6,
) -> list[tuple[KnowledgeDocument, float, str]]:
    keywords = module_names or []
    text_keywords = [w.strip() for w in re.split(r"[\s,，;；、]+", requirement_text) if len(w.strip()) >= 2]
    keywords = list(set(keywords + text_keywords[:10]))

    candidates = coarse_filter(db, module_keywords=keywords, limit=30)
    if not candidates:
        logger.warning(
            "[knowledge] no candidates found for requirement_text=%r module_names=%r keywords=%r",
            requirement_text[:100], module_names, keywords
        )
        return []

    candidate_map = {d.id: d for d in candidates}

    if is_embedding_available():
        try:
            query_embedding = generate_single_embedding(requirement_text[:2000])
            ranked = embedding_rerank(query_embedding, list(candidate_map.keys()), db, top_k)
            results = [(candidate_map[did], score, "embedding") for did, score in ranked if did in candidate_map]
            if not results:
                logger.warning(
                    "[knowledge] embedding rerank returned empty for requirement_text=%r, "
                    "candidates=%d embedding_available=%s",
                    requirement_text[:100], len(candidates), is_embedding_available()
                )
            return results[:top_k]
        except Exception as exc:
            logger.warning("[knowledge] retrieval embedding failed: %s", exc)

    results = [(d, 0.0, "tag") for d in candidates[:top_k]]
    if not results:
        logger.warning(
            "[knowledge] no results for requirement_text=%r module_names=%r, "
            "candidates=%d embedding_available=%s",
            requirement_text[:100], module_names, len(candidates), is_embedding_available()
        )
    return results
