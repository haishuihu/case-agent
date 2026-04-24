from __future__ import annotations

import json
import logging
from typing import Optional

from app.prompts.impact_prompt import (
    SYSTEM_PROMPT_IMPACT,
    build_impact_analysis_prompt,
)
from app.services.code_analyzer import CodeAnalyzer, ParsedDiff
from app.services.dependency_graph import DependencyGraph, get_dependency_graph

logger = logging.getLogger(__name__)


class ImpactAnalyzer:
    """
    影响分析服务：解析代码变更 + 依赖分析 + AI 深度分析
    """

    def __init__(self, model_key: Optional[str] = None):
        self._llm_client = None
        self._model_key = model_key
        self._code_analyzer = CodeAnalyzer()
        self._dep_graph: Optional[DependencyGraph] = None

    @property
    def llm_client(self):
        if self._llm_client is None:
            from app.services.llm_client import build_llm_client

            self._llm_client = build_llm_client(self._model_key)
        return self._llm_client

    @property
    def dep_graph(self) -> DependencyGraph:
        if self._dep_graph is None:
            self._dep_graph = get_dependency_graph()
        return self._dep_graph

    def analyze(
        self,
        git_diff: str,
        affected_modules: list[str],
        submission_id: Optional[str] = None,
        recent_defects: list[str] = None,
    ) -> dict:
        """
        执行完整的影响分析。

        Args:
            git_diff: Git Diff 内容
            affected_modules: 用户指定的影响模块
            submission_id: 关联的提测申请ID
            recent_defects: 最近相关缺陷列表

        Returns:
            影响分析结果（dict）
        """
        # 1. 解析 Git Diff
        parsed: ParsedDiff = self._code_analyzer.parse_diff(git_diff)

        changed_files = [
            {
                "filename": f.filename,
                "status": f.status,
                "additions": f.additions,
                "deletions": f.deletions,
            }
            for f in parsed.changed_files
        ]

        changed_modules = self._code_analyzer.get_changed_modules(parsed)
        api_changes = self._code_analyzer.extract_api_changes(git_diff)

        # 2. 依赖图扩展影响范围
        dep_impact = self.dep_graph.get_impacted_modules(changed_modules, max_depth=3)
        dep_modules = [
            {"module_name": p.module, "module_type": p.path_type, "risk_level": "medium"}
            for p in dep_impact if p.module not in changed_modules
        ]

        # 3. AI 深度分析
        try:
            prompt = build_impact_analysis_prompt(
                git_diff=git_diff,
                affected_modules=affected_modules,
                changed_files=changed_files,
            )
            response = self.llm_client.create_chat_completion(
                system_prompt=SYSTEM_PROMPT_IMPACT,
                user_content=prompt,
                max_tokens=4000,
                response_format={"type": "json_object"},
            )
            ai_result = json.loads(response.content)
        except ValueError:
            logger.warning("[impact] LLM not available, using fallback")
            ai_result = self._fallback_impact(affected_modules, changed_modules)
        except json.JSONDecodeError:
            logger.warning("[impact] JSON parse failed: %s", response.content[:500])
            ai_result = self._fallback_impact(affected_modules, changed_modules)

        # 4. 合并结果
        impacted_modules = ai_result.get("impacted_modules", [])

        # 补充依赖图发现的高频被依赖模块
        key_modules = self.dep_graph.get_key_path_modules()
        for km in key_modules[:3]:
            if not any(m["module_name"] == km for m in impacted_modules):
                impacted_modules.append({
                    "module_name": km,
                    "module_type": "indirect",
                    "risk_level": "medium",
                    "impact_description": f"关键路径模块，被多个模块依赖",
                })

        # 5. 构建最终结果
        return {
            "submission_id": submission_id,
            "changed_files": changed_files,
            "added_lines": parsed.added_lines,
            "deleted_lines": parsed.deleted_lines,
            "modified_functions": parsed.modified_functions,
            "impacted_modules": impacted_modules,
            "indirect_impacts": ai_result.get("indirect_impacts", []),
            "api_breaking_changes": ai_result.get("api_breaking_changes", api_changes),
            "risk_points": ai_result.get("risk_points", []),
            "confidence_level": ai_result.get("confidence_level", "low"),
            "summary": ai_result.get("summary", self._generate_summary(changed_files, impacted_modules)),
        }

    def _fallback_impact(
        self,
        user_modules: list[str],
        changed_modules: list[str],
    ) -> dict:
        """无 LLM 时的降级分析"""
        all_modules = list(dict.fromkeys(user_modules + changed_modules))
        impacted = [
            {
                "module_name": m,
                "module_type": "direct" if m in changed_modules else "indirect",
                "risk_level": "high" if m in changed_modules else "medium",
                "impact_description": f"模块 {m} 涉及代码变更",
            }
            for m in all_modules
        ]
        return {
            "impacted_modules": impacted,
            "indirect_impacts": [],
            "data_flow_impacts": [],
            "api_breaking_changes": [],
            "risk_points": ["请配置 LLM API Key 以获取详细影响分析"],
            "confidence_level": "low",
            "summary": f"检测到 {len(changed_modules)} 个模块发生变更，建议进行针对性回归测试",
        }

    def _generate_summary(self, changed_files: list[dict], impacted_modules: list[dict]) -> str:
        """生成摘要描述"""
        count = len(changed_files)
        high_risk = sum(1 for m in impacted_modules if m.get("risk_level") == "high")
        return f"变更涉及 {count} 个文件，{len(impacted_modules)} 个模块受影响，其中 {high_risk} 个高风险模块。"
