from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timezone
from uuid import uuid4

from app.db.session import SessionLocal
from app.models.auto_test import (
    ExecutionStatus,
    TestExecution,
    TestPlan,
    TestSuite,
)

logger = logging.getLogger(__name__)


class TestScheduler:
    """测试调度器

    后台线程定时扫描 auto_execute=True 的 TestPlan，
    按 cron 或 interval 配置定时创建并启动 TestExecution。
    """

    def __init__(self):
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_run: dict[str, datetime] = {}  # plan_id -> last trigger time

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="test-scheduler")
        self._thread.start()
        logger.info("TestScheduler started")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("TestScheduler stopped")

    def _run(self):
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception:
                logger.exception("TestScheduler tick error")
            self._stop_event.wait(30)  # Check every 30 seconds

    def _tick(self):
        db = SessionLocal()
        try:
            plans = (
                db.query(TestPlan)
                .filter(
                    TestPlan.auto_execute == True,
                    TestPlan.is_active == True,
                )
                .all()
            )

            now = datetime.now(timezone.utc)
            for plan in plans:
                if not self._should_run(plan, now):
                    continue

                self._create_execution(db, plan)
                self._last_run[plan.id] = now

        finally:
            db.close()

    def _should_run(self, plan: TestPlan, now: datetime) -> bool:
        last_run = self._last_run.get(plan.id)
        config = json.loads(plan.schedule_config) if plan.schedule_config else {}

        if plan.schedule_type == "manual":
            return False

        if plan.schedule_type == "cron":
            cron_expr = config.get("cron", "")
            if cron_expr and not self._cron_matches(cron_expr, now, last_run):
                return False
            return True

        if plan.schedule_type == "event":
            return False  # Event triggers are external

        # Fallback: interval-based
        interval_minutes = config.get("interval_minutes", 60)
        if last_run and (now - last_run).total_seconds() < interval_minutes * 60:
            return False
        return True

    def _cron_matches(self, cron_expr: str, now: datetime, last_run: datetime | None) -> bool:
        """Simple cron expression matcher (minute hour day-of-month month day-of-week)."""
        try:
            parts = cron_expr.strip().split()
            if len(parts) != 5:
                return True  # Invalid cron, run anyway

            minute, hour, dom, month, dow = parts
            if not self._field_matches(minute, now.minute):
                return False
            if not self._field_matches(hour, now.hour):
                return False
            if not self._field_matches(dom, now.day):
                return False
            if not self._field_matches(month, now.month):
                return False
            if not self._field_matches(dow, now.weekday()):
                return False

            # Avoid re-running within the same minute
            if last_run and (now - last_run).total_seconds() < 60:
                return False

            return True
        except Exception:
            return True

    def _field_matches(self, expr: str, value: int) -> bool:
        if expr == "*":
            return True
        for part in expr.split(","):
            part = part.strip()
            if "-" in part:
                lo, hi = part.split("-")
                if int(lo) <= value <= int(hi):
                    return True
            elif "/" in part:
                step = int(part.split("/")[1])
                if value % step == 0:
                    return True
            else:
                try:
                    if int(part) == value:
                        return True
                except ValueError:
                    pass
        return False

    def _create_execution(self, db, plan: TestPlan):
        from app.services.auto_test.ai_recommender import AIRecommender

        # Determine cases to run based on case_filter
        case_ids, name_suffix = self._resolve_case_ids(db, plan)
        if not case_ids:
            logger.info(f"Scheduler: plan '{plan.name}' has no matching cases")
            return

        execution = TestExecution(
            id=str(uuid4()),
            plan_id=plan.id,
            suite_id=plan.suite_id,
            name=f"[定时] {plan.name} {name_suffix}",
            status=ExecutionStatus.PENDING.value,
            case_ids=json.dumps(case_ids),
            triggered_by="scheduler",
            trigger_source="schedule",
            started_at=datetime.now(timezone.utc),
        )
        db.add(execution)
        db.commit()

        logger.info(f"Scheduler created execution '{execution.name}' from plan '{plan.name}'")

    def _resolve_case_ids(self, db, plan: TestPlan) -> tuple[list[str], str]:
        from app.models.auto_test import TestCase

        case_filter = json.loads(plan.case_filter) if plan.case_filter else {}
        query = db.query(TestCase).filter(
            TestCase.suite_id == plan.suite_id,
            TestCase.status == "active",
        )

        priority = case_filter.get("priority")
        if priority:
            query = query.filter(TestCase.priority >= priority)

        case_type = case_filter.get("case_type")
        if case_type:
            query = query.filter(TestCase.case_type == case_type)

        limit = case_filter.get("limit", 50)
        cases = query.order_by(TestCase.priority.desc()).limit(limit).all()
        case_ids = [c.id for c in cases]

        return case_ids, f"({len(case_ids)} cases)"


# Module-level singleton
scheduler = TestScheduler()
