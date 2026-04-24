from __future__ import annotations

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ExecutionTracker:
    """
    用例执行追踪器。

    管理回归推荐用例的执行状态，提供：
    - 执行状态流转
    - 失败用例一键创建缺陷
    - 执行历史查询
    """

    def get_execution_summary(self, recommendation_ids: list[str]) -> dict:
        """
        获取一组推荐用例的执行汇总。

        Args:
            recommendation_ids: 推荐用例ID列表

        Returns:
            {
                "total": N,
                "not_started": N,
                "in_progress": N,
                "passed": N,
                "failed": N,
                "blocked": N,
                "pass_rate": 0.0-1.0,
            }
        """
        from app.models.regression_execution import RegressionExecution, ExecutionStatus

        result = {
            "total": len(recommendation_ids),
            "not_started": 0,
            "in_progress": 0,
            "passed": 0,
            "failed": 0,
            "blocked": 0,
            "pass_rate": 0.0,
        }

        for rid in recommendation_ids:
            from app.db.session import SessionLocal
            with SessionLocal() as db:
                from app.models.impact import RegressionRecommendation
                rec = db.get(RegressionRecommendation, rid)
                if rec and rec.execution:
                    status = rec.execution.status.value if hasattr(rec.execution.status, 'value') else str(rec.execution.status)
                    if status == "not_started":
                        result["not_started"] += 1
                    elif status == "in_progress":
                        result["in_progress"] += 1
                    elif status == "passed":
                        result["passed"] += 1
                    elif status == "failed":
                        result["failed"] += 1
                    elif status == "blocked":
                        result["blocked"] += 1

        total_done = result["passed"] + result["failed"] + result["blocked"]
        if total_done > 0:
            result["pass_rate"] = result["passed"] / total_done

        return result

    def create_defect_from_execution(
        self,
        execution_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        severity: str = "medium",
        priority: str = "medium",
        creator: Optional[str] = None,
        db=None,
    ) -> dict:
        """
        从执行失败的用例一键创建缺陷。

        Args:
            execution_id: 执行记录ID
            title: 缺陷标题（不填则自动生成）
            description: 缺陷描述
            severity: 严重程度
            priority: 优先级
            creator: 创建人
            db: 数据库会话（不提供则自动创建）

        Returns:
            创建的缺陷信息
        """
        from app.models.defect import Defect
        from app.models.regression_execution import RegressionExecution
        from app.db.session import SessionLocal

        if db is None:
            db = SessionLocal()
            should_close = True
        else:
            should_close = False

        try:
            execution = db.get(RegressionExecution, execution_id)
            if not execution:
                raise ValueError(f"执行记录 {execution_id} 不存在")

            # 获取关联的推荐信息
            rec = execution.recommendation
            submission_id = None
            recommendation_id = rec.id if rec else None

            if rec and rec.analysis:
                submission_id = rec.analysis.submission_id

            # 生成默认标题
            if not title:
                case_title = rec.case_title if rec else "未知用例"
                title = f"[回归失败] {case_title}"

            # 生成描述
            if not description:
                parts = [f"执行用例: {rec.case_title if rec else '未知'}"]
                if execution.actual_result:
                    parts.append(f"实际结果: {execution.actual_result}")
                if execution.comment:
                    parts.append(f"执行备注: {execution.comment}")
                description = "\n".join(parts)

            defect = Defect(
                submission_id=submission_id,
                recommendation_id=recommendation_id,
                execution_id=execution_id,
                title=title,
                description=description,
                severity=severity,
                priority=priority,
                status="open",
                creator=creator,
                environment="测试环境",
            )
            db.add(defect)
            db.commit()
            db.refresh(defect)

            logger.info("[tracker] created defect id=%s from execution_id=%s", defect.id, execution_id)

            return {
                "id": defect.id,
                "title": defect.title,
                "status": defect.status,
                "submission_id": defect.submission_id,
            }
        finally:
            if should_close:
                db.close()
