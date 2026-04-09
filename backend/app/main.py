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
from app.db.migrate import ensure_generation_record_columns
from app.db.session import Base, engine, SessionLocal
from app.models import generation  # noqa: F401
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
    Base.metadata.create_all(bind=engine)
    ensure_generation_record_columns(engine)

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
