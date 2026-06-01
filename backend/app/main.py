import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.db.migrate import (
    ensure_append_generate_table,
    ensure_auto_test_soft_delete_columns,
    ensure_case_review_tables,
    ensure_test_case_items_table,
    ensure_defect_table,
    ensure_generation_record_columns,
    ensure_impact_tables,
    ensure_quick_generate_table,
    ensure_regression_execution_table,
    ensure_submission_tables,
)
from app.db.session import Base, engine, SessionLocal
from app.models import generation  # noqa: F401
from app.models import test_case  # noqa: F401 - ensure model is registered
from app.models import case_review  # noqa: F401 - ensure models are registered
from app.models import defect  # noqa: F401 - ensure models are registered
from app.models import impact  # noqa: F401 - ensure models are registered
from app.models import quick_generate  # noqa: F401 - ensure models are registered
from app.models import regression_execution  # noqa: F401 - ensure models are registered
from app.models import submission  # noqa: F401 - ensure models are registered
from app.services.generation_worker import fail_stale_running_task

settings = get_settings()
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.on_event("startup")
def on_startup() -> None:
    # Ensure we always pick up the latest .env on startup, even when running with --reload
    get_settings.cache_clear()

    Base.metadata.create_all(bind=engine)
    ensure_generation_record_columns(engine)
    ensure_submission_tables(engine)
    ensure_impact_tables(engine)
    ensure_regression_execution_table(engine)
    ensure_quick_generate_table(engine)
    ensure_case_review_tables(engine)
    ensure_append_generate_table(engine)
    ensure_defect_table(engine)
    ensure_auto_test_soft_delete_columns(engine)
    ensure_test_case_items_table(engine)

    # 启动时清理历史遗留的超时僵尸 running 任务
    db = SessionLocal()
    try:
        settings = get_settings()
        stale_threshold = datetime.now(timezone.utc) - timedelta(minutes=settings.generation_max_runtime_minutes)
        stale_count = 0
        for record in (
            db.query(generation.GenerationRecord)
            .filter(
                generation.GenerationRecord.status == "running",
                generation.GenerationRecord.started_at < stale_threshold,
            )
            .all()
        ):
            if fail_stale_running_task(db, record):
                stale_count += 1
        if stale_count > 0:
            logger.warning("[startup] cleaned %d stale running tasks from previous sessions", stale_count)
    except Exception:
        db.rollback()
        logger.exception("[startup] failed to clean stale tasks")
    finally:
        db.close()


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


frontend_dist = Path(settings.frontend_dist_path)
assets_dir = frontend_dist / "assets"
index_file = frontend_dist / "index.html"

if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


if index_file.exists():

    @app.get("/", include_in_schema=False)
    def serve_index() -> FileResponse:
        return FileResponse(index_file)


    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str) -> FileResponse:
        candidate = frontend_dist / full_path
        if candidate.exists() and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index_file)
