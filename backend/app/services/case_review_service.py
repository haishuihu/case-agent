from __future__ import annotations

import logging
from typing import Optional

from app.services.ai_reviewer import AIReviewInput, AIReviewer

logger = logging.getLogger(__name__)


class CaseReviewService:
    """
    用例评审业务服务。
    负责评审记录的创建、AI 评审执行、状态流转等业务逻辑。
    """

    def run_ai_review(
        self,
        requirement_text: str,
        generated_cases: str,
        model_key: Optional[str] = None,
    ) -> dict:
        """
        执行 AI 评审。

        Args:
            requirement_text: 需求文本
            generated_cases: 生成的用例内容
            model_key: 模型 Key

        Returns:
            AI 评审结果（dict），包含 overall_score, dimensions, issues, suggestions
        """
        reviewer = AIReviewer(model_key=model_key)
        input_data = AIReviewInput(
            requirement_text=requirement_text,
            generated_cases=generated_cases,
            model_key=model_key,
        )
        output = reviewer.review(input_data)
        return {
            "overall_score": output.overall_score,
            "dimensions": output.dimensions,
            "issues": output.issues,
            "suggestions": output.suggestions,
        }
