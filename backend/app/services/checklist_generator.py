from __future__ import annotations

import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class ChecklistGenerator:
    """AI生成提测Checklist服务"""

    def __init__(self, model_key: Optional[str] = None):
        self._llm_client = None
        self._model_key = model_key

    @property
    def llm_client(self):
        if self._llm_client is None:
            try:
                from app.services.llm_client import build_llm_client
                self._llm_client = build_llm_client(self._model_key)
            except ValueError:
                self._llm_client = None
        return self._llm_client

    def _has_llm(self) -> bool:
        return self.llm_client is not None

    def generate(
        self,
        change_description: str,
        affected_modules: list[str],
        git_diff: str = "",
        recent_defects: list[str] = None,
    ) -> dict:
        """
        生成提测Checklist

        Args:
            change_description: 变更描述
            affected_modules: 影响模块列表
            git_diff: Git Diff内容（可选，提供时将进行静态分析预检）
            recent_defects: 最近相关缺陷列表

        Returns:
            {
                "checklists": [...],
                "summary": "...",
                "suggestions": [...],
                "high_risk_areas": [...],
                "static_analysis": {...},  # 静态分析结果
            }
        """
        from app.prompts.submission_prompt import (
            SYSTEM_PROMPT_CHECKLIST,
            build_checklist_prompt,
        )

        static_result = {}
        static_summary = ""

        # 静态分析预检（当提供 git_diff 时）
        if git_diff:
            try:
                static_result = self.detect_risks(git_diff)
                static_summary = static_result.get("summary", "")
            except Exception as exc:
                logger.warning("[checklist] static analysis failed: %s", exc)
                static_result = {}

        prompt = build_checklist_prompt(
            change_description=change_description,
            affected_modules=affected_modules,
            git_diff=git_diff,
            recent_defects=recent_defects,
            static_analysis=static_result,
        )

        if not self._has_llm():
            logger.warning("[checklist] LLM not available, returning fallback")
            return self._generate_fallback_checklist(change_description, affected_modules)

        try:
            response = self.llm_client.create_chat_completion(
                system_prompt=SYSTEM_PROMPT_CHECKLIST,
                user_content=prompt,
                max_tokens=4000,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.content)

            checklists = result.get("checklist", [])

            # 如果静态分析发现了高风险项，自动追加到 checklist
            if static_result.get("static_issues"):
                for issue in static_result["static_issues"][:5]:
                    checklists.append({
                        "item": f"[静态检查] {issue['description']}",
                        "method": f"检查代码中是否包含: {issue.get('match', '问题模式')}",
                        "pass_criteria": "确认无安全/质量问题，或已添加防护措施",
                        "risk_level": "high",
                        "category": "静态检查",
                    })

            return {
                "checklists": checklists,
                "summary": result.get("summary", ""),
                "suggestions": result.get("suggestions", []),
                "high_risk_areas": result.get("high_risk_areas", []),
                "static_analysis": static_result,
                "static_summary": static_summary,
            }
        except (json.JSONDecodeError, AttributeError) as exc:
            logger.warning("[checklist] Response parse failed: %s", exc)
            return self._generate_fallback_checklist(change_description, affected_modules)
        except Exception as exc:
            logger.error("[checklist] generation failed: %s", exc)
            return self._generate_fallback_checklist(change_description, affected_modules)

    def _generate_fallback_checklist(self, change_description: str, affected_modules: list[str]) -> dict:
        """当LLM不可用时，生成基础Checklist"""
        modules = ", ".join(affected_modules) if affected_modules else "通用"
        return {
            "checklists": [
                {
                    "item": "功能正确性验证",
                    "method": f"针对{modules}进行功能测试",
                    "pass_criteria": "核心功能正常运行，无明显错误",
                    "risk_level": "high",
                    "category": "功能",
                },
                {
                    "item": "边界值测试",
                    "method": "测试空值、最大值、特殊字符等边界情况",
                    "pass_criteria": "边界情况处理正确",
                    "risk_level": "medium",
                    "category": "功能",
                },
                {
                    "item": "异常处理验证",
                    "method": "模拟异常场景，验证错误处理",
                    "pass_criteria": "异常被正确捕获和处理",
                    "risk_level": "medium",
                    "category": "功能",
                },
                {
                    "item": "回归测试",
                    "method": "执行相关模块的历史用例",
                    "pass_criteria": "历史功能未被影响",
                    "risk_level": "high",
                    "category": "功能",
                },
            ],
            "summary": f"变更涉及{modules}，建议进行功能、边界、异常和回归测试",
            "suggestions": ["建议先进行冒烟测试", "高风险用例优先执行"],
            "high_risk_areas": ["核心功能路径", "数据处理逻辑"],
            "static_analysis": {},
            "static_summary": "",
        }

    def detect_risks(self, git_diff: str) -> dict:
        """
        使用 CodeAnalyzer 对 Git Diff 进行静态分析，生成风险点列表。

        Args:
            git_diff: Git Diff 内容

        Returns:
            {
                "static_issues": [...],
                "file_stats": {...},
                "api_changes": [...],
                "modified_functions": [...],
            }
        """
        from app.services.code_analyzer import CodeAnalyzer

        analyzer = CodeAnalyzer()
        parsed = analyzer.parse_diff(git_diff)
        api_changes = analyzer.extract_api_changes(git_diff)

        static_issues: list[dict] = []

        # 检测常见风险模式
        risk_patterns = [
            (r"\bexec\s*\(", "代码执行风险：发现 exec() 调用，可能导致注入漏洞"),
            (r"\beval\s*\(", "代码执行风险：发现 eval() 调用，可能导致注入漏洞"),
            (r"\bpickle\.loads?\s*\(", "反序列化风险：发现 pickle.load/loads，可能导致代码执行"),
            (r"\.format\s*\(\s*%", "格式化字符串风险：混用 .format() 和 % 格式化可能导致崩溃"),
            (r"os\.system\s*\(", "系统命令风险：发现 os.system()，建议替换为 subprocess"),
            (r"subprocess\.call\s*\(\s*shell\s*=\s*True", "命令注入风险：subprocess shell=True 可能导致注入"),
            (r"password\s*=\s*['\"][^'\"]*['\"]", "敏感信息泄露：代码中可能硬编码了密码"),
            (r"api[_-]?key\s*=\s*['\"][^'\"]*['\"]", "密钥泄露风险：代码中可能硬编码了 API Key"),
            (r"secret\s*=\s*['\"][^'\"]*['\"]", "密钥泄露风险：代码中可能硬编码了 Secret"),
            (r"SQL\s*\+", "SQL 注入风险：发现字符串拼接 SQL，应使用参数化查询"),
            (r"cursor\.execute\s*\([^,]+\+", "SQL 注入风险：SQL 语句拼接参数"),
            (r"html\s*\+", "XSS 风险：使用字符串拼接 HTML，应使用模板转义"),
            (r"innerHTML\s*=", "XSS 风险：直接赋值 innerHTML 可能导致 XSS"),
            (r"\.text\s*=\s*[^;]*\+", "XSS 风险：直接赋值文本内容可能包含未转义 HTML"),
            (r"await\s+\w+\(.*request\.", "异步请求风险：异步 HTTP 请求需确保超时和错误处理"),
            (r"session\.(get|post)\([^)]*timeout", "网络请求风险：HTTP 请求应配置合理的超时时间"),
            (r"threading\.Thread\s*\(", "并发风险：多线程需注意线程安全问题"),
            (r"Lock\s*\(", "并发风险：使用锁需确保锁粒度适当，避免死锁"),
            (r"delete\s*\(\s*id\s*=", "数据删除风险：删除操作需确保有适当的权限校验和备份"),
            (r"drop\s+table", "数据库风险：发现 DROP TABLE 操作，数据将被永久删除"),
            (r"TRUNCATE", "数据库风险：发现 TRUNCATE 操作，数据将被清空"),
            (r"open\([^)]*['\"]w['\"]", "文件操作风险：文件写入需注意路径遍历和权限问题"),
            (r"shutil\.rmtree\s*\(", "文件删除风险：递归删除操作不可逆"),
            (r"@staticmethod", "方法设计：发现静态方法，可能表示设计问题或应改为类方法"),
        ]

        for pattern, description in risk_patterns:
            matches = re.finditer(pattern, git_diff, re.IGNORECASE)
            for m in matches:
                static_issues.append({
                    "type": "static_analysis",
                    "severity": "high",
                    "description": description,
                    "match": m.group(0),
                    "line_hint": git_diff[:m.start()].count("\n") + 1,
                })

        # 检测高变更频率文件（可能有较高风险）
        file_change_summary = {}
        for f in parsed.changed_files:
            file_change_summary[f.filename] = {
                "status": f.status,
                "additions": f.additions,
                "deletions": f.deletions,
                "total_changes": f.additions + f.deletions,
            }

        # 检测大文件变更（可能引入回归风险）
        large_changes = {
            fname: stats for fname, stats in file_change_summary.items()
            if stats["total_changes"] > 200
        }

        return {
            "static_issues": static_issues[:20],  # 最多返回 20 个
            "file_stats": file_change_summary,
            "api_changes": api_changes,
            "modified_functions": parsed.modified_functions,
            "large_change_files": large_changes,
            "summary": self._summarize_risks(parsed, static_issues, large_changes),
        }

    def _summarize_risks(self, parsed, static_issues: list, large_changes: dict) -> str:
        """生成风险摘要"""
        parts = []
        if static_issues:
            high = [i for i in static_issues if i.get("severity") == "high"]
            if high:
                parts.append(f"检测到 {len(high)} 个高风险静态问题")
        if large_changes:
            parts.append(f"有 {len(large_changes)} 个文件变更量超过 200 行，可能引入回归风险")
        if parsed.added_lines > 500:
            parts.append(f"变更量较大（+{parsed.added_lines} 行），建议重点测试")
        if not parts:
            parts.append("静态分析未发现明显高风险模式")
        return "；".join(parts)

    def analyze_impact(
        self,
        git_diff: str,
        affected_modules: list[str],
    ) -> dict:
        """
        分析代码变更影响

        Args:
            git_diff: Git Diff内容
            affected_modules: 影响模块列表

        Returns:
            影响分析结果
        """
        from app.prompts.impact_prompt import SYSTEM_PROMPT_IMPACT
        from app.prompts.submission_prompt import build_impact_analysis_prompt

        prompt = build_impact_analysis_prompt(
            git_diff=git_diff,
            affected_modules=affected_modules,
        )

        if not self._has_llm():
            logger.warning("[impact] LLM not available, returning fallback")
            return {
                "impacted_modules": affected_modules,
                "indirect_impacts": [],
                "data_flow_impacts": [],
                "api_breaking_changes": [],
                "risk_points": ["请配置LLM API Key以获取详细影响分析"],
                "confidence_level": "low",
            }

        try:
            response = self.llm_client.create_chat_completion(
                system_prompt=SYSTEM_PROMPT_IMPACT,
                user_content=prompt,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )

            return json.loads(response.content)
        except (json.JSONDecodeError, AttributeError) as exc:
            logger.warning("[impact] Response parse failed: %s", exc)
            return {
                "impacted_modules": affected_modules,
                "indirect_impacts": [],
                "data_flow_impacts": [],
                "api_breaking_changes": [],
                "risk_points": [],
                "confidence_level": "low",
            }
        except Exception as exc:
            logger.error("[impact] analysis failed: %s", exc)
            return {
                "impacted_modules": affected_modules,
                "indirect_impacts": [],
                "data_flow_impacts": [],
                "api_breaking_changes": [],
                "risk_points": [],
                "confidence_level": "low",
            }
