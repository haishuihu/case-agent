from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.generation import GenerationAttachment, GenerationRecord
from app.schemas.generate import (
    GenerateResponse,
    RequirementSummaryResponse,
    ReviewModuleItem,
    ReviewResponse,
    TaskListItem,
    TaskListResponse,
    TaskStatusResponse,
    TaskSubmitResponse,
)
from app.schemas.model import ModelOption
from app.services.file_parser import DocumentContext, ImageContext, parse_document_upload, parse_image_upload
from app.services.llm_client import LLMClient, build_llm_client
from app.services.model_registry import list_model_profiles
from app.services.generation_worker import _elapsed_since_started, spawn_generation_thread
from app.services.testcase_exporter import (
    _build_filename,
    _content_disposition,
    build_csv_bytes,
    build_skill_template_markdown,
    build_xlsx_bytes,
)
from app.services.testcase_parser import load_generation_snapshot

router = APIRouter(tags=["generate"])


def _preview_requirement(text: Optional[str], max_len: int = 80) -> str:
    if not text or not str(text).strip():
        return "（无需求摘要）"
    t = str(text).strip().replace("\n", " ")
    if len(t) <= max_len:
        return t
    return t[:max_len] + "…"


def _extract_case_count_from_raw(raw_response: Optional[str]) -> Optional[int]:
    if not raw_response:
        return None
    try:
        data = json.loads(raw_response)
        meta = data.get("metadata") or {}
        if "caseCount" in meta:
            return int(meta["caseCount"])
        if "case_count" in meta:
            return int(meta["case_count"])
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    return None


def _build_generate_response_from_record(record: GenerationRecord) -> GenerateResponse:
    try:
        cases, metadata = load_generation_snapshot(
            raw_response=record.raw_response or "",
            markdown=record.output_markdown or "",
        )
    except Exception:
        cases = []
        metadata = GenerationMetadata(
            caseCount=0,
            categoryCounts={},
            warnings=["加载历史记录时发生错误"],
            truncated=False,
            incompleteCategories=[],
        )
    return GenerateResponse(
        generationId=record.id,
        markdown=record.output_markdown or "",
        modelName=record.model_name,
        attachmentCount=len(record.attachments),
        createdAt=record.created_at,
        cases=cases,
        metadata=metadata,
    )


def _task_status_response(record: GenerationRecord) -> TaskStatusResponse:
    detail: dict[str, object] = {}
    if record.progress_detail:
        try:
            parsed = json.loads(record.progress_detail)
            if isinstance(parsed, dict):
                detail = parsed
        except json.JSONDecodeError:
            detail = {}

    phases_obj = detail.get("phases", [])
    phases: list[dict[str, object]] = phases_obj if isinstance(phases_obj, list) else []

    progress = float(detail.get("progress", 0.0))
    phase_label = str(detail.get("phaseLabel", ""))
    elapsed = int(detail.get("elapsedSeconds", 0))
    if record.started_at and record.status == "running":
        elapsed = _elapsed_since_started(record)

    if record.status == "succeeded":
        progress = 1.0

    result: Optional[GenerateResponse] = None
    if record.status == "succeeded" and record.output_markdown and record.raw_response:
        result = _build_generate_response_from_record(record)

    preview = _preview_requirement(record.requirement_text)
    case_count = _extract_case_count_from_raw(record.raw_response) if record.status == "succeeded" else None

    return TaskStatusResponse(
        taskId=record.id,
        status=record.status,
        currentPhase=record.progress_phase or "",
        phaseLabel=phase_label,
        progress=progress,
        phases=phases,
        elapsedSeconds=elapsed,
        result=result,
        errorMessage=record.error_message,
        requirementPreview=preview,
        caseCount=case_count,
    )


@router.get("/models", response_model=list[ModelOption])
def list_models() -> list[ModelOption]:
    items: list[ModelOption] = []
    for profile in list_model_profiles():
        label = profile.label
        if not profile.api_key.strip():
            label = f"{profile.label}（未配置 API Key）"
        items.append(
            ModelOption(
                key=profile.key,
                label=label,
                provider=profile.provider,
                modelName=profile.model_name,
                supportsVision=profile.supports_vision,
                supportsStructuredOutput=profile.supports_structured_output,
            )
        )
    return items


async def _parse_uploads(
    document_files: Optional[list[UploadFile]],
    image_files: Optional[list[UploadFile]],
) -> tuple[list[DocumentContext], list[ImageContext]]:
    settings = get_settings()
    document_files = document_files or []
    image_files = image_files or []
    if len(document_files) + len(image_files) > settings.max_upload_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"附件数量不能超过 {settings.max_upload_files} 个。",
        )

    document_contexts: list[DocumentContext] = []
    for upload in document_files:
        document_contexts.append(await parse_document_upload(upload))

    total_document_chars = sum(len(d.extracted_text) for d in document_contexts)
    if total_document_chars > settings.max_total_document_chars:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="参考文档文本总长度过大，请减少上传内容后重试。",
        )

    image_contexts: list[ImageContext] = []
    for upload in image_files:
        image_contexts.append(await parse_image_upload(upload))

    return document_contexts, image_contexts


@router.post("/generate/review", response_model=ReviewResponse)
async def review_requirement(
    requirement_text: Annotated[str, Form(...)],
    model_key: Annotated[Optional[str], Form(alias="modelKey")] = None,
    document_files: Annotated[Optional[list[UploadFile]], File(alias="documentFiles")] = None,
    image_files: Annotated[Optional[list[UploadFile]], File(alias="imageFiles")] = None,
) -> ReviewResponse:
    """Phase 1 only: review requirements and decompose into modules."""
    try:
        llm_client = build_llm_client(model_key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    requirement_text = requirement_text.strip()
    if not requirement_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="需求描述不能为空。")

    document_contexts, _image_contexts = await _parse_uploads(document_files, image_files)

    try:
        from app.services.testcase_generator import TestCaseGenerator
        generator = TestCaseGenerator(llm_client)
        review = generator._phase1_review(requirement_text, document_contexts)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="需求评审调用失败，请稍后重试。") from exc

    return ReviewResponse(
        modules=[
            ReviewModuleItem(
                id=m.id,
                name=m.name,
                description=m.description,
                subFeatures=m.sub_features,
            )
            for m in review.modules
        ],
        questions=review.questions,
        businessRules=review.business_rules,
        dataConstraints=review.data_constraints,
        modelName=llm_client.profile.model_name,
    )


@router.post("/generate/summary", response_model=RequirementSummaryResponse)
async def summarize_requirement(
    requirement_text: Annotated[str, Form()] = "",
    model_key: Annotated[Optional[str], Form(alias="modelKey")] = None,
    document_files: Annotated[Optional[list[UploadFile]], File(alias="documentFiles")] = None,
    image_files: Annotated[Optional[list[UploadFile]], File(alias="imageFiles")] = None,
) -> RequirementSummaryResponse:
    requirement_text = requirement_text.strip()
    document_contexts, image_contexts = await _parse_uploads(document_files, image_files)
    if not requirement_text and not document_contexts and not image_contexts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请至少填写需求摘要或上传参考文件。",
        )

    try:
        llm_client = build_llm_client(model_key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        summary = llm_client.summarize_requirement_from_files(
            requirement_text=requirement_text,
            document_contexts=document_contexts,
            image_contexts=image_contexts,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="需求摘要提炼失败，请稍后重试。",
        ) from exc

    return RequirementSummaryResponse(
        summaryText=str(summary["summary_text"]),
        modules=list(summary["modules"]),
        businessRules=list(summary["business_rules"]),
        dataConstraints=list(summary["data_constraints"]),
        openQuestions=list(summary["open_questions"]),
        modelName=str(summary["model_name"]),
    )


@router.post("/generate", response_model=GenerateResponse)
async def generate_testcases(
    requirement_text: Annotated[str, Form(...)],
    model_key: Annotated[Optional[str], Form(alias="modelKey")] = None,
    document_files: Annotated[Optional[list[UploadFile]], File(alias="documentFiles")] = None,
    image_files: Annotated[Optional[list[UploadFile]], File(alias="imageFiles")] = None,
    db: Session = Depends(get_db_session),
) -> GenerateResponse:
    try:
        llm_client = build_llm_client(model_key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    profile = llm_client.profile
    requirement_text = requirement_text.strip()
    if not requirement_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="需求描述不能为空。")

    document_contexts, image_contexts = await _parse_uploads(document_files, image_files)

    try:
        result = llm_client.generate_test_cases(
            requirement_text=requirement_text,
            document_contexts=document_contexts,
            image_contexts=image_contexts,
            db_session=db,
        )
    except ValueError as exc:
        failed_record = GenerationRecord(
            requirement_text=requirement_text,
            model_name=profile.model_name,
            prompt_snapshot=requirement_text,
            status="failed",
            error_message=str(exc),
        )
        db.add(failed_record)
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        failed_record = GenerationRecord(
            requirement_text=requirement_text,
            model_name=profile.model_name,
            prompt_snapshot=requirement_text,
            status="failed",
            error_message=str(exc),
        )
        db.add(failed_record)
        db.commit()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="大模型服务调用失败，请稍后重试。") from exc

    generation_record = GenerationRecord(
        requirement_text=requirement_text,
        model_name=result.model_name,
        prompt_snapshot=result.prompt_snapshot,
        output_markdown=result.markdown,
        raw_response=result.raw_response,
        status="succeeded",
    )
    db.add(generation_record)
    db.flush()

    attachments = [
        GenerationAttachment(
            generation_id=generation_record.id,
            file_role="document",
            filename=document.filename,
            content_type=document.content_type,
            extracted_content=document.extracted_text,
        )
        for document in document_contexts
    ]
    attachments.extend(
        GenerationAttachment(
            generation_id=generation_record.id,
            file_role="image",
            filename=image.filename,
            content_type=image.content_type,
            extracted_content=f"[image-data] {image.filename}",
        )
        for image in image_contexts
    )

    db.add_all(attachments)
    db.commit()
    db.refresh(generation_record)

    return GenerateResponse(
        generationId=generation_record.id,
        markdown=result.markdown,
        modelName=result.model_name,
        attachmentCount=len(attachments),
        createdAt=generation_record.created_at,
        cases=result.cases,
        metadata=result.metadata,
    )


@router.post("/generate/async", response_model=TaskSubmitResponse)
async def generate_testcases_async(
    requirement_text: Annotated[str, Form(...)],
    model_key: Annotated[Optional[str], Form(alias="modelKey")] = None,
    document_files: Annotated[Optional[list[UploadFile]], File(alias="documentFiles")] = None,
    image_files: Annotated[Optional[list[UploadFile]], File(alias="imageFiles")] = None,
    db: Session = Depends(get_db_session),
) -> TaskSubmitResponse:
    # 清理超过 30 分钟仍未完成的僵尸 running 任务
    stale_threshold = datetime.now(timezone.utc) - timedelta(minutes=30)
    stale_count = (
        db.query(GenerationRecord)
        .filter(
            GenerationRecord.status == "running",
            GenerationRecord.started_at < stale_threshold,
        )
        .update(
            {
                "status": "failed",
                "error_message": "任务超时未完成（超过 30 分钟），已自动清理。",
                "progress_phase": "failed",
            }
        )
    )
    if stale_count:
        db.commit()
        logger.warning("[async-submit] cleaned %d stale running tasks", stale_count)

    try:
        llm_client = build_llm_client(model_key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    profile = llm_client.profile
    requirement_text = requirement_text.strip()
    if not requirement_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="需求描述不能为空。")

    document_contexts, image_contexts = await _parse_uploads(document_files, image_files)

    generation_record = GenerationRecord(
        requirement_text=requirement_text,
        model_name=profile.model_name,
        prompt_snapshot=requirement_text,
        status="running",
        progress_phase="starting",
        started_at=datetime.now(timezone.utc),
        client_model_key=model_key,
    )
    db.add(generation_record)
    db.flush()

    attachments = [
        GenerationAttachment(
            generation_id=generation_record.id,
            file_role="document",
            filename=document.filename,
            content_type=document.content_type,
            extracted_content=document.extracted_text,
        )
        for document in document_contexts
    ]
    attachments.extend(
        GenerationAttachment(
            generation_id=generation_record.id,
            file_role="image",
            filename=image.filename,
            content_type=image.content_type,
            extracted_content=f"[image-data] {image.filename}",
        )
        for image in image_contexts
    )

    db.add_all(attachments)
    db.commit()

    spawn_generation_thread(
        generation_record.id,
        requirement_text,
        document_contexts,
        image_contexts,
        model_key,
    )

    return TaskSubmitResponse(taskId=generation_record.id, status="running")


@router.get("/generate/tasks/{task_id}", response_model=TaskStatusResponse)
def get_generation_task(task_id: str, db: Session = Depends(get_db_session)) -> TaskStatusResponse:
    record = db.get(GenerationRecord, task_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到该任务。")
    return _task_status_response(record)


@router.get("/generate/tasks", response_model=TaskListResponse)
def list_generation_tasks(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, alias="pageSize")] = 20,
    db: Session = Depends(get_db_session),
) -> TaskListResponse:
    q = db.query(GenerationRecord).order_by(GenerationRecord.created_at.desc())
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    items: list[TaskListItem] = []
    for row in rows:
        items.append(
            TaskListItem(
                taskId=row.id,
                status=row.status,
                requirementPreview=_preview_requirement(row.requirement_text),
                caseCount=_extract_case_count_from_raw(row.raw_response),
                createdAt=row.created_at,
                modelName=row.model_name,
            )
        )
    return TaskListResponse(items=items, total=total, page=page, pageSize=page_size)


@router.post("/generate/tasks/{task_id}/cancel")
def cancel_generation_task(task_id: str, db: Session = Depends(get_db_session)) -> dict[str, bool]:
    record = db.get(GenerationRecord, task_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到该任务。")
    if record.status != "running":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="任务未在运行中，无法取消。")
    record.cancel_requested = True
    db.commit()
    return {"ok": True}


@router.delete("/generate/tasks")
def clear_all_generation_tasks(db: Session = Depends(get_db_session)) -> dict[str, object]:
    """Delete all generation tasks including running ones. Running tasks will have their cancel flag set."""
    # First, set cancel_requested for all running tasks
    running_count = (
        db.query(GenerationRecord)
        .filter(GenerationRecord.status == "running")
        .update({"cancel_requested": True})
    )
    db.commit()

    # Then delete all generation records (cascades to attachments)
    total_count = db.query(GenerationRecord).delete()
    db.commit()

    return {
        "ok": True,
        "deletedCount": total_count,
        "cancelledRunningCount": running_count,
    }


@router.get("/generations/{generation_id}/export")
def export_generation(
    generation_id: str,
    export_format: Annotated[str, Query(alias="format")] = "md",
    db: Session = Depends(get_db_session),
) -> StreamingResponse:
    generation_record = db.get(GenerationRecord, generation_id)
    if not generation_record or not generation_record.output_markdown:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到可导出的生成记录。")

    cases, metadata = load_generation_snapshot(
        raw_response=generation_record.raw_response,
        markdown=generation_record.output_markdown,
    )

    export_format = export_format.lower()
    if export_format == "md":
        md_content = build_skill_template_markdown(
            cases=cases,
            metadata=metadata,
            requirement_text=generation_record.requirement_text,
            document_titles=[att.filename for att in generation_record.attachments],
        )
        content = md_content.encode("utf-8")
        media_type = "text/markdown; charset=utf-8"
        filename = _build_filename(generation_record.requirement_text, "测试用例.md")
    elif export_format == "csv":
        content = build_csv_bytes(cases)
        media_type = "text/csv; charset=utf-8"
        filename = _build_filename(generation_record.requirement_text, "测试用例.csv")
    elif export_format == "xlsx":
        content = build_xlsx_bytes(cases, metadata)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = _build_filename(generation_record.requirement_text, "测试用例.xlsx")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的导出格式。")

    return StreamingResponse(
        BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": _content_disposition(filename)},
    )


# --- WebSocket for real-time task progress ---
_active_ws_connections: dict[str, list[WebSocket]] = {}


@router.websocket("/generate/ws/{task_id}")
async def websocket_task_progress(websocket: WebSocket, task_id: str):
    await websocket.accept()
    if task_id not in _active_ws_connections:
        _active_ws_connections[task_id] = []
    _active_ws_connections[task_id].append(websocket)
    try:
        while True:
            # Wait for a message (client can send pings or nothing)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                pass

            # Read current task status from DB and push
            db_gen = None
            try:
                from app.db.session import SessionLocal
                from app.models.generation import GenerationRecord
                db_gen = SessionLocal()
                record = db_gen.get(GenerationRecord, task_id)
                if not record:
                    await websocket.send_json({"type": "error", "message": "Task not found"})
                    break
                status_resp = _task_status_response(record)
                await websocket.send_json({
                    "type": "status",
                    "data": status_resp.model_dump(by_alias=True),
                })
                if record.status in ("succeeded", "failed", "cancelled"):
                    break
            finally:
                if db_gen:
                    db_gen.close()
    except WebSocketDisconnect:
        pass
    finally:
        _active_ws_connections[task_id] = [
            ws for ws in _active_ws_connections.get(task_id, []) if ws != websocket
        ]
        if not _active_ws_connections.get(task_id):
            _active_ws_connections.pop(task_id, None)

