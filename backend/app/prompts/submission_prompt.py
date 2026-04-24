SYSTEM_PROMPT_CHECKLIST = """\
你是一个资深测试工程师，同时具备开发视角和安全意识。
你擅长根据代码变更内容，生成针对性的自测检查清单。

## 能力要求
1. 理解代码变更的类型和影响范围
2. 识别常见的问题模式和风险点
3. 生成具体、可执行的检查项
4. 给出清晰的通过标准

## 检查维度
- 功能正确性：核心逻辑是否正确
- 参数校验：边界值、类型校验是否完整
- 异常处理：错误分支是否覆盖
- 性能影响：是否有性能风险
- 安全风险：是否有注入、越权等安全漏洞
- 兼容性：是否影响现有功能
- 数据一致性：是否有数据一致性问题

## 输出规范
- 当要求输出 JSON 时，只输出纯 JSON，不附加任何解释文字
- 检查项要具体可执行，避免模糊描述
- 通过标准要明确可验证
"""


def build_checklist_prompt(
    change_description: str,
    affected_modules: list[str],
    git_diff: str = "",
    recent_defects: list[str] = None,
    static_analysis: dict = None,
) -> str:
    recent_defects = recent_defects or []
    static_analysis = static_analysis or {}

    blocks = [
        "## 代码变更信息",
        f"变更描述: {change_description}",
        f"影响模块: {', '.join(affected_modules) if affected_modules else '未指定'}",
    ]

    if git_diff:
        blocks.extend([
            "",
            "## Git Diff (变更内容)",
            "```diff",
            git_diff[:5000],
            "```",
        ])

    # 静态分析结果（AI 预检）
    if static_analysis:
        issues = static_analysis.get("static_issues", [])
        api_changes = static_analysis.get("api_changes", [])
        modified_funcs = static_analysis.get("modified_functions", [])
        large_files = static_analysis.get("large_change_files", {})
        summary = static_analysis.get("summary", "")

        blocks.append("")
        blocks.append("## AI 静态预检结果")
        blocks.append(f"风险摘要: {summary}")

        if issues:
            blocks.append("")
            blocks.append("### 检测到的风险模式")
            for issue in issues[:10]:
                blocks.append(f"- [{issue.get('severity', 'unknown')}] {issue['description']}")
                if issue.get("match"):
                    blocks.append(f"  代码片段: `{issue['match'][:80]}`")

        if api_changes:
            blocks.append("")
            blocks.append("### API 变更")
            for change in api_changes[:10]:
                blocks.append(f"- {change}")

        if modified_funcs:
            blocks.append("")
            blocks.append("### 变更的函数")
            for func in modified_funcs[:10]:
                blocks.append(f"- {func}")

        if large_files:
            blocks.append("")
            blocks.append("### 大文件变更（变更量 > 200 行）")
            for fname, stats in large_files.items():
                blocks.append(f"- {fname}: +{stats['additions']}/-{stats['deletions']} 行")

    if recent_defects:
        blocks.extend([
            "",
            "## 最近相关缺陷",
            *[f"- {d}" for d in recent_defects[:5]],
        ])

    blocks.extend([
        "",
        "## 任务",
        "根据以上变更信息，生成针对性的自测检查清单。",
        "要求生成8-15条检查项，覆盖功能、安全、性能、兼容性等维度。",
        "**重要**：如果静态预检发现了安全或高风险问题，必须在检查清单中覆盖对应的检查项。",
        "",
        "## 输出要求",
        "请只输出JSON格式：",
        """\
{
  "checklist": [
    {
      "item": "检查项描述",
      "method": "如何检查（操作步骤）",
      "pass_criteria": "通过标准",
      "risk_level": "high/medium/low",
      "category": "功能/安全/性能/兼容性/数据"
    }
  ],
  "summary": "本次提测的整体风险评估（1-2句话）",
  "suggestions": ["建议1", "建议2"],
  "high_risk_areas": ["高风险区域1", "高风险区域2"]
}""",
    ])

    return "\n\n".join(blocks)


def build_impact_analysis_prompt(
    git_diff: str,
    affected_modules: list[str],
) -> str:
    """转发到 canonical 实现（仅用于 ChecklistGenerator.analyze_impact）"""
    from app.prompts.impact_prompt import build_impact_analysis_prompt as _canonical

    return _canonical(git_diff=git_diff, affected_modules=affected_modules)
