from __future__ import annotations

import json
import logging
from typing import Optional

from app.prompts.impact_prompt import (
    SYSTEM_PROMPT_REGRESSION,
    build_regression_prompt,
)

logger = logging.getLogger(__name__)


class RegressionRecommender:
    """
    智能回归推荐服务：根据影响分析结果推荐最小回归集
    """

    def __init__(self, model_key: Optional[str] = None):
        self._llm_client = None
        self._model_key = model_key

    @property
    def llm_client(self):
        if self._llm_client is None:
            from app.services.llm_client import build_llm_client

            self._llm_client = build_llm_client(self._model_key)
        return self._llm_client

    def recommend(
        self,
        impacted_modules: list[dict],
        summary: str,
        recent_defects: list[str] = None,
    ) -> list[dict]:
        """
        根据影响分析结果，推荐回归用例。

        Args:
            impacted_modules: 受影响模块列表（来自 ImpactAnalyzer）
            summary: 影响分析摘要
            recent_defects: 最近相关缺陷

        Returns:
            推荐回归用例列表
        """
        try:
            prompt = build_regression_prompt(
                impacted_modules=impacted_modules,
                summary=summary,
                recent_defects=recent_defects,
            )
            response = self.llm_client.create_chat_completion(
                system_prompt=SYSTEM_PROMPT_REGRESSION,
                user_content=prompt,
                max_tokens=4000,
                response_format={"type": "json_object"},
            )
            result = json.loads(response.content)
            recommendations = result.get("recommendations", [])
        except ValueError:
            logger.warning("[regression] LLM not available, using fallback")
            recommendations = self._fallback_recommend(impacted_modules)
        except json.JSONDecodeError:
            logger.warning("[regression] JSON parse failed: %s", response.content[:500])
            recommendations = self._fallback_recommend(impacted_modules)

        return recommendations

    def _fallback_recommend(self, impacted_modules: list[dict]) -> list[dict]:
        """无 LLM 时的基础回归推荐"""
        recommendations: list[dict] = []
        priority_map = {"high": "must", "medium": "should", "low": "could"}

        for module in impacted_modules:
            name = module.get("module_name", "")
            risk = module.get("risk_level", "medium")
            priority = priority_map.get(risk, "should")
            desc = module.get("impact_description", "")

            recommendations.append({
                "case_title": f"{name} 核心功能验证",
                "case_id": None,
                "priority": priority,
                "risk_level": risk,
                "reason": f"模块 {name} 受到变更影响，{desc}" if desc else f"模块 {name} 受到变更影响",
                "estimated_minutes": 15 if priority == "must" else 10 if priority == "should" else 5,
                "category": "功能测试",
            })

            if risk == "high":
                recommendations.append({
                    "case_title": f"{name} 异常场景验证",
                    "case_id": None,
                    "priority": "should",
                    "risk_level": "medium",
                    "reason": f"高风险模块 {name} 的异常分支也需要验证",
                    "estimated_minutes": 10,
                    "category": "异常测试",
                })

        return recommendations

    def prioritize(self, recommendations: list[dict]) -> dict:
        """
        将推荐结果按优先级分组。

        Returns:
            {
                "must": [...],
                "should": [...],
                "could": [...],
                "total_must_minutes": int,
                "total_should_minutes": int,
                "total_could_minutes": int,
            }
        """
        must: list[dict] = []
        should: list[dict] = []
        could: list[dict] = []

        for rec in recommendations:
            priority = rec.get("priority", "should")
            if priority == "must":
                must.append(rec)
            elif priority == "should":
                should.append(rec)
            else:
                could.append(rec)

        def total_minutes(items: list[dict]) -> int:
            return sum(
                (r.get("estimated_minutes") or 0) for r in items
            )

        return {
            "must": must,
            "should": should,
            "could": could,
            "total_must_minutes": total_minutes(must),
            "total_should_minutes": total_minutes(should),
            "total_could_minutes": total_minutes(could),
        }
