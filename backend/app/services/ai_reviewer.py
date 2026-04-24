from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class AIReviewInput:
    """AI 评审输入参数"""
    requirement_text: str
    generated_cases: str
    model_key: Optional[str] = None


@dataclass
class AIReviewOutput:
    """AI 评审输出"""
    overall_score: int
    dimensions: list[dict]
    issues: list[dict]
    suggestions: list[str]


class AIReviewer:
    """
    AI 用例评审引擎。
    负责调用 LLM 执行多维度用例质量评审。
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

    def review(self, input: AIReviewInput) -> AIReviewOutput:
        """
        执行 AI 多维度评审。

        Args:
            input: 评审输入

        Returns:
            AIReviewOutput: 评审结果
        """
        prompt = f"""## 需求描述

{input.requirement_text or "(未提供需求描述)"}

---

## 已有测试用例

{input.generated_cases if input.generated_cases else "(未提供用例)"}

---

## 任务

请对以上测试用例进行多维度 AI 评审，从以下维度评估用例质量并给出 0-100 的评分：

1. **完整性 (completeness)**: 是否覆盖正常流程、异常流程、边界条件
2. **可执行性 (executability)**: 步骤是否清晰、可重复执行
3. **一致性 (consistency)**: 同模块用例风格是否统一
4. **冗余性 (redundancy)**: 是否存在重复用例
5. **覆盖率 (coverage)**: 各维度（功能路径、数据处理、接口兼容、安全等）的覆盖情况

## 输出要求

请只输出JSON格式：
{{
  "overall_score": 综合评分(0-100),
  "dimensions": [
    {{"dimension": "completeness", "label": "完整性", "score": 评分(0-100), "description": "评分说明"}},
    {{"dimension": "executability", "label": "可执行性", "score": 评分(0-100), "description": "评分说明"}},
    {{"dimension": "consistency", "label": "一致性", "score": 评分(0-100), "description": "评分说明"}},
    {{"dimension": "redundancy", "label": "冗余性", "score": 评分(0-100), "description": "评分说明"}},
    {{"dimension": "coverage", "label": "覆盖率", "score": 评分(0-100), "description": "评分说明"}}
  ],
  "issues": [
    {{
      "type": "missing_coverage/executability/consistency/redundancy/coverage",
      "severity": "high/medium/low",
      "description": "问题描述",
      "recommendation": "建议"
    }}
  ],
  "suggestions": ["建议1", "建议2", "建议3"]
}}"""

        system_prompt = """你是一个资深测试工程师，擅长评审测试用例质量。
给出 JSON 格式的多维度评分结果，确保评分客观、有依据。"""

        try:
            response = self.llm_client.create_chat_completion(
                system_prompt=system_prompt,
                user_content=prompt,
                max_tokens=4000,
                response_format={"type": "json_object"},
            )
            result = json.loads(response.content)
            return AIReviewOutput(
                overall_score=result.get("overall_score", 0),
                dimensions=result.get("dimensions", []),
                issues=result.get("issues", []),
                suggestions=result.get("suggestions", []),
            )
        except json.JSONDecodeError as exc:
            logger.warning("[ai-reviewer] JSON parse failed: %s", exc)
            raise ValueError(f"AI 评审响应格式错误: {exc}") from exc
        except Exception as exc:
            logger.error("[ai-reviewer] review failed: %s", exc)
            raise ValueError(f"AI 评审执行失败: {exc}") from exc
