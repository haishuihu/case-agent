SYSTEM_PROMPT_IMPACT = """\
你是一个代码变更分析专家，擅长深度分析代码变更的影响范围。

## 能力要求
1. 理解代码变更的类型和影响范围
2. 识别直接和间接影响的模块
3. 检测 API 破坏性变更
4. 识别潜在风险点
5. 评估分析置信度

## 分析维度
1. **直接影响**: 变更直接涉及的模块/函数
2. **间接影响**: 通过调用链传递的连锁影响
3. **数据流影响**: 对数据存储、传输、持久化的影响
4. **接口影响**: API 签名、参数、返回值变化
5. **风险点**: 可能引入的 bug、性能、安全问题

## 输出规范
- 当要求输出 JSON 时，只输出纯 JSON，不附加任何解释文字
- 只输出有把握的分析，不要编造不确定的信息
- 影响模块用中文描述
"""


SYSTEM_PROMPT_REGRESSION = """\
你是一个资深测试工程师，擅长根据变更分析结果推荐最小回归集。

## 能力要求
1. 根据影响模块识别必须回归的用例
2. 评估用例优先级（must/should/could）
3. 评估风险等级（high/medium/low）
4. 预估回归时间
5. 给出推荐原因

## 评分权重参考
- 覆盖分 (30%): 代码变更覆盖的用例
- 风险分 (25%): 历史缺陷率 × 变更频率
- 依赖分 (25%): 调用链距离 × 关键路径权重
- 业务分 (20%): 业务关键度评分

## 输出规范
- 当要求输出 JSON 时，只输出纯 JSON，不附加任何解释文字
- 用例标题使用中文
- 预估时间以分钟为单位
"""


def build_impact_analysis_prompt(
    git_diff: str,
    affected_modules: list[str],
    changed_files: list[dict] = None,
) -> str:
    """构建影响分析的 prompt"""
    if changed_files is None:
        changed_files = []
    files_summary = "\n".join(
        f"  - {f['filename']} ({f['status']}, +{f['additions']}/-{f['deletions']})"
        for f in changed_files
    ) if changed_files else "（无文件变更信息）"

    modules = ", ".join(affected_modules) if affected_modules else "未指定"

    return f"""\
## 代码变更信息

### 变更文件列表
{files_summary}

### 影响模块（用户指定）
{modules}

### Git Diff（变更详情）
```diff
{git_diff[:8000]}
```

## 任务
请深度分析以上代码变更的影响范围，输出完整的分析报告。

## 输出要求
请只输出JSON格式：
{{
  "impacted_modules": [
    {{
      "module_name": "模块名称（中文）",
      "module_type": "direct/indirect/api",
      "risk_level": "high/medium/low",
      "impact_description": "影响描述"
    }}
  ],
  "indirect_impacts": ["间接影响1", "间接影响2"],
  "data_flow_impacts": ["数据影响1", "数据影响2"],
  "api_breaking_changes": ["破坏性API变更1", "破坏性API变更2"],
  "risk_points": ["风险点1", "风险点2"],
  "confidence_level": "high/medium/low",
  "summary": "整体影响摘要（2-3句话）"
}}
"""


def build_regression_prompt(
    impacted_modules: list[dict],
    summary: str,
    recent_defects: list[str] = None,
) -> str:
    """构建回归推荐的 prompt"""
    modules_str = "\n".join(
        f"  - {m['module_name']} (风险:{m['risk_level']}, 类型:{m['module_type']})"
        for m in impacted_modules
    )
    defects_str = ""
    if recent_defects:
        defects_str = "\n\n## 最近相关缺陷\n" + "\n".join(f"- {d}" for d in recent_defects[:5])

    return f"""\
## 影响分析结果

### 受影响模块
{modules_str}

### 整体摘要
{summary}
{defects_str}

## 任务
根据以上影响分析，推荐最小回归测试集。请从功能路径、数据处理、接口兼容性、异常处理等维度进行推荐。

## 输出要求
请只输出JSON格式：
{{
  "recommendations": [
    {{
      "case_title": "用例标题（中文）",
      "case_id": null,
      "priority": "must/should/could",
      "risk_level": "high/medium/low",
      "reason": "推荐原因",
      "estimated_minutes": 预估分钟数,
      "category": "用例分类"
    }}
  ]
}}
"""
