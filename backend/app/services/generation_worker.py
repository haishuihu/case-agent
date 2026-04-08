"""Background generation task: runs LLM pipeline in a thread and persists progress to DB."""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.generation import GenerationRecord
from app.services.file_parser import DocumentContext, ImageContext
from app.services.llm_client import build_llm_client

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _elapsed_since_started(record: GenerationRecord) -> int:
    if not record.started_at:
        return 0
    start = record.started_at
    if start.tzinfo is None:
        from datetime import datetime as dt

        delta = dt.utcnow() - start
    else:
        delta = _utcnow() - start
    return int(max(0.0, delta.total_seconds()))


def persist_progress(db: Session, task_id: str, payload: dict[str, object]) -> None:
    record = db.get(GenerationRecord, task_id)
    if not record:
        return
    extra_elapsed = _elapsed_since_started(record)
    record.progress_phase = str(payload.get("currentPhase", ""))
    record.progress_detail = json.dumps(
        {
            "phases": payload.get("phases", []),
            "progress": payload.get("progress", 0.0),
            "phaseLabel": payload.get("phaseLabel", ""),
            "elapsedSeconds": extra_elapsed,
        },
        ensure_ascii=False,
    )
    db.commit()


def run_generation_task(
    task_id: str,
    requirement_text: str,
    document_contexts: list[DocumentContext],
    image_contexts: list[ImageContext],
    model_key: Optional[str],
) -> None:
    db = SessionLocal()
    try:
        record = db.get(GenerationRecord, task_id)
        if not record or record.status != "running":
            return

        # 复用主 db session 进行进度更新和取消检查
        # 避免每次回调都创建新的 SessionLocal
        _db_for_progress = db

        def progress_callback(payload: dict[str, object]) -> None:
            try:
                persist_progress(_db_for_progress, task_id, payload)
                _db_for_progress.commit()
            except Exception as exc:
                logger.warning("[progress-callback] persist failed: %s", exc)
                try:
                    _db_for_progress.rollback()
                except Exception:
                    pass

        def cancel_check() -> bool:
            # 直接使用已经 commit 过的 db session 查询最新状态
            # 注意：这里需要刷新以获取其他线程/连接的更新
            try:
                _db_for_progress.refresh(record)
                return bool(record.cancel_requested)
            except Exception:
                # 如果 refresh 失败，说明 session 可能已过期，直接再查一次
                r = _db_for_progress.get(GenerationRecord, task_id)
                return bool(r and r.cancel_requested)

        try:
            llm_client = build_llm_client(model_key)
        except ValueError as exc:
            record.status = "failed"
            record.error_message = str(exc)
            record.progress_phase = "failed"
            db.commit()
            return

        try:
            result = llm_client.generate_test_cases(
                requirement_text=requirement_text,
                document_contexts=document_contexts,
                image_contexts=image_contexts,
                db_session=db,
                progress_callback=progress_callback,
                cancel_check=cancel_check,
            )
        except RuntimeError as exc:
            if "取消" in str(exc):
                record = db.get(GenerationRecord, task_id)
                if record:
                    record.status = "cancelled"
                    record.error_message = str(exc)
                    record.progress_phase = "cancelled"
                    db.commit()
                return
            raise
        except ValueError as exc:
            record = db.get(GenerationRecord, task_id)
            if record:
                record.status = "failed"
                record.error_message = str(exc)
                record.progress_phase = "failed"
                db.commit()
            return
        except Exception:
            logger.exception("generation task failed task_id=%s", task_id)
            record = db.get(GenerationRecord, task_id)
            if record:
                record.status = "failed"
                record.error_message = "生成失败，请稍后重试。"
                record.progress_phase = "failed"
                db.commit()
            return

        record = db.get(GenerationRecord, task_id)
        if not record:
            return
        record.output_markdown = result.markdown
        record.raw_response = result.raw_response
        record.prompt_snapshot = result.prompt_snapshot
        record.model_name = result.model_name
        record.status = "succeeded"
        record.progress_phase = "done"
        done_elapsed = _elapsed_since_started(record)
        record.progress_detail = json.dumps(
            {
                "phases": [],
                "progress": 1.0,
                "phaseLabel": "完成",
                "elapsedSeconds": done_elapsed,
            },
            ensure_ascii=False,
        )
        record.error_message = None
        db.commit()
    finally:
        db.close()


def spawn_generation_thread(
    task_id: str,
    requirement_text: str,
    document_contexts: list[DocumentContext],
    image_contexts: list[ImageContext],
    model_key: Optional[str],
) -> None:
    thread = threading.Thread(
        target=run_generation_task,
        args=(task_id, requirement_text, document_contexts, image_contexts, model_key),
        name=f"gen-{task_id[:8]}",
        daemon=True,
    )
    thread.start()
