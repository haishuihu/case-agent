"""Lightweight SQLite column migration for existing deployments (create_all does not ALTER)."""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def ensure_generation_record_columns(engine: Engine) -> None:
    insp = inspect(engine)
    if not insp.has_table("generation_records"):
        return
    existing = {c["name"] for c in insp.get_columns("generation_records")}
    alters: list[str] = []
    if "progress_phase" not in existing:
        alters.append("ALTER TABLE generation_records ADD COLUMN progress_phase VARCHAR NOT NULL DEFAULT ''")
    if "progress_detail" not in existing:
        alters.append("ALTER TABLE generation_records ADD COLUMN progress_detail TEXT")
    if "started_at" not in existing:
        alters.append(
            "ALTER TABLE generation_records ADD COLUMN started_at DATETIME"
        )
    if "client_model_key" not in existing:
        alters.append("ALTER TABLE generation_records ADD COLUMN client_model_key VARCHAR")
    if "cancel_requested" not in existing:
        alters.append(
            "ALTER TABLE generation_records ADD COLUMN cancel_requested BOOLEAN NOT NULL DEFAULT 0"
        )
    if not alters:
        return
    with engine.begin() as conn:
        for stmt in alters:
            conn.execute(text(stmt))
