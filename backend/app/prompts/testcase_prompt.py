from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from app.services.file_parser import DocumentContext


@dataclass
class KnowledgeContextItem:
    title: str
    doc_type: str
    summary: str
    module_tags: list[str]

COVERAGE_DIMENSIONS = [
    "正常流程",
    "异常与错误处理",
    "边界值与输入校验",
    "数据组合与等价类",
    "状态流转与时序约束",
    "权限与角色控制",
    "兼容性与环境依赖",
    "性能与并发",
    "安全与数据保护",
    "用户体验与界面",
]

SYSTEM_PROMPT = """\
你是一个拥有 20 年互联网软件工程经验的复合型专家，同时具备以下四重视角：

1. **资深产品架构师**：深刻理解业务目标、用户场景和产品逻辑，能识别需求中的模糊点和遗漏。
2. **资深测试工程师**：精通等价类划分、边界值分析、因果图、状态迁移图、错误推测等经典测试设计方法，追求高覆盖率。
3. **资深开发工程师**：了解技术实现边界、数据校验逻辑、并发风险和异常处理机制。
4. **资深产品设计师**：关注用户体验、交互反馈、空状态/加载态/错误态的处理。

## 设计原则

| 原则 | 说明 |
|------|------|
| 功能点优先 | 从功能模块 -> 子功能 -> 测试点逐级分解 |
| 等价类划分 | 有效/无效等价类，避免重复场景 |
| 边界值覆盖 | 最小值、最大值、相邻值 |
| 异常场景发散 | 基于行业经验推测潜在异常 |
| 简洁明了 | 减少冗余文字，直击要点 |

## 优先级定义

| 优先级 | 定义 | 覆盖率要求 |
|--------|------|-----------|
| P0 | 冒烟测试，核心功能 | 100% 覆盖 |
| P1 | 主要业务流程 | 100% 覆盖 |
| P2 | 重要功能点 | 80%+ 覆盖 |
| P3 | 边缘场景 | 尽力覆盖 |

## 覆盖维度清单

- **正常流程**：所有主要业务路径的完整操作流，包括每个分支流程
- **异常与错误处理**：无效输入、超时、网络中断、服务不可用、数据冲突
- **边界值与输入校验**：每个输入字段的最小值/最大值/临界值、空值、超长、特殊字符
- **数据组合与等价类**：多输入字段的有效/无效组合，等价类划分后的代表值
- **状态流转与时序约束**：对象状态的合法/非法跃迁、操作顺序依赖
- **权限与角色控制**：不同角色的操作权限、越权访问、未登录访问
- **兼容性与环境依赖**：不同浏览器/设备/系统版本
- **性能与并发**：批量操作、高并发、超时处理
- **安全与数据保护**：注入攻击、XSS、敏感信息泄露
- **用户体验与界面**：提示信息准确性、交互反馈、加载/空状态显示

## 输出规范

- 当要求输出 JSON 时，只输出纯 JSON，不附加任何解释文字。
- 当要求输出 Markdown 表格时，只输出表格，不附加解释文字。
- 测试用例粒度：一个用例验证一个明确的测试点。
- 步骤可执行：测试步骤必须具体到操作级别。
- 预期可验证：预期结果必须是可观测、可验证的具体行为。
- 不编造能力：需求未明确的内容可合理假设并用「待确认：xxx」标注，不凭空编造。
"""


def build_requirement_context(
    requirement_text: str, document_contexts: list[DocumentContext]
) -> str:
    requirement_block = requirement_text.strip() or "未提供单独的文字需求描述，请以参考文档中的功能说明、业务规则与约束为准。"
    document_sections: list[str] = []
    for index, document in enumerate(document_contexts, start=1):
        document_sections.append(
            "\n".join(
                [
                    f"### 参考文档 {index}",
                    f"- 文件名：{document.filename}",
                    f"- 类型：{document.content_type}",
                    "- 内容摘录：",
                    document.extracted_text or "(无可提取文本)",
                ]
            )
        )
    documents_block = (
        "\n\n".join(document_sections) if document_sections else "无额外参考文档。"
    )
    return "\n\n".join(
        ["## 功能需求", requirement_block, "## 参考文档", documents_block]
    )


def build_knowledge_context(
    knowledge_items: list[KnowledgeContextItem],
    max_chars: int = 3000,
) -> str:
    if not knowledge_items:
        return ""

    type_groups: dict[str, list[str]] = {}
    for item in knowledge_items:
        label = {
            "requirement": "相关需求文档",
            "defect": "相关缺陷模式",
            "testcase": "相关历史测试用例",
        }.get(item.doc_type, "其他相关知识")

        tags = f" (模块: {', '.join(item.module_tags)})" if item.module_tags else ""
        line = f"- **[{item.title}]**{tags} {item.summary}"
        type_groups.setdefault(label, []).append(line)

    sections = ["## 历史知识参考（仅供参考，不替代当前需求分析）"]
    char_count = len(sections[0])
    for group_name, lines in type_groups.items():
        section_header = f"### {group_name}"
        char_count += len(section_header) + 1
        if char_count > max_chars:
            break
        sections.append(section_header)
        for line in lines:
            char_count += len(line) + 1
            if char_count > max_chars:
                break
            sections.append(line)

    sections.append("> 请参考以上历史知识补充当前需求分析中可能遗漏的场景，但以当前需求为准。")
    return "\n".join(sections)


def build_requirement_summary_prompt(
    requirement_text: str, document_contexts: list[DocumentContext]
) -> str:
    return "\n\n".join(
        [
            build_requirement_context(requirement_text, document_contexts),
            "## 任务：提炼可确认的需求摘要",
            "请基于现有文字需求和参考文档，整理出一份供用户确认的精炼需求摘要。",
            "要求：",
            "1. summary_text 用 5~10 条简洁要点概括功能目标、关键流程、主要规则、边界约束和待确认点。",
            "2. modules 只列出适合单独设计测试用例的主要模块名称。",
            "3. business_rules 提炼最关键的业务规则，避免重复文档原文。",
            "4. data_constraints 提炼字段格式、长度、阈值、次数限制、时效等约束。",
            "5. open_questions 只保留真正影响测试设计的待确认问题。",
            "6. 只输出 JSON，不要输出任何解释、Markdown 代码块标记或其他文字。",
            "## 格式约束（必须严格遵守）",
            "- 使用双引号包裹所有字符串值。",
            "- 字符串值内部若出现英文双引号（\"），必须写成反斜杠转义（\\\"）。禁止出现未转义的英文双引号。",
            "  正确示例：\"将\\\"爆款复刻\\\"改为\\\"视频复刻\\\"\"",
            "  错误示例：\"将\"爆款复刻\"改为\"视频复刻\"\"",
            "- 字符串值内部换行符必须写成 \\n（反斜杠+n），禁止使用实际换行符。",
            "- 所有数组元素必须是字符串，禁止嵌套对象。",
            "",
            "请只输出以下 JSON，不要加任何前缀或后缀：",
            (
                "{\n"
                '  "summaryText": "- 功能目标：...\\n- 关键流程：...\\n- 业务规则：...\\n- 待确认：...",\n'
                '  "modules": ["模块1", "模块2"],\n'
                '  "businessRules": ["规则1", "规则2"],\n'
                '  "dataConstraints": ["约束1", "约束2"],\n'
                '  "openQuestions": ["问题1", "问题2"]\n'
                "}"
            ),
        ]
    )


# ---------------------------------------------------------------------------
# Phase 1: Requirements Review + Module Decomposition (merged)
# ---------------------------------------------------------------------------


def build_requirement_review_prompt(
    requirement_text: str,
    document_contexts: list[DocumentContext],
    knowledge_context: str = "",
) -> str:
    blocks = [build_requirement_context(requirement_text, document_contexts)]
    if knowledge_context:
        blocks.append(knowledge_context)
    blocks.extend([
        "## 任务：需求评审与模块分解",
        "请以资深产品架构师和测试工程师的双重视角，对上述需求执行以下分析：",
        "### 第一步：识别功能模块",
        "将需求拆分为独立的功能模块，每个模块应是一个可独立测试的功能单元。",
        "### 第二步：发现问题",
        "从以下维度评审需求文档，识别不明确、不清晰的内容：",
        "- 功能描述模糊（动词不明确、缺少主语、条件不完整）",
        "- 边界条件缺失（数值范围、数据长度、超长/超短处理）",
        "- 异常场景遗漏（网络异常、并发、数据校验失败处理）",
        "- 交互逻辑不清（多角色权限、状态流转、返回行为）",
        "- 数据规格不明（字段类型、长度限制、格式要求）",
        "### 第三步：提取业务规则与数据约束",
        "从需求中提取关键业务规则和每个输入字段的数据约束。",
        "",
        "请只输出 JSON，格式如下：",
        (
            "{"
            '"modules":[{"id":"M01","name":"模块名","description":"功能描述","sub_features":["子功能1","子功能2"]}],'
            '"questions":[{"id":"Q-001","type":"边界条件缺失","description":"问题描述","module":"M01","suggestion":"建议"}],'
            '"business_rules":["规则1","规则2"],'
            '"data_constraints":[{"field":"字段名","type":"string","length":"1-20","format":"手机号","required":true}]'
            "}"
        ),
    ])
    return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# Phase 3: Smoke Tests (P0/P1)
# ---------------------------------------------------------------------------


def build_smoke_test_prompt(
    requirement_text: str,
    document_contexts: list[DocumentContext],
    modules_json: str,
    business_rules: str,
) -> str:
    return "\n\n".join(
        [
            build_requirement_context(requirement_text, document_contexts),
            "## 模块信息",
            modules_json,
            "## 关键业务规则",
            business_rules,
            "## 任务：生成冒烟测试用例（P0/P1）",
            "请针对所有模块生成冒烟测试用例，覆盖核心业务路径的端到端验证。",
            "冒烟测试要求：",
            "- P0：核心功能冒烟测试，必须 100% 通过才能上线",
            "- P1：主要业务流程验证，24小时内必须修复",
            "- 每个模块至少覆盖其主要正常路径和最关键的异常路径",
            "- 用例应简洁，验证功能可用性而非详尽覆盖",
            "",
            "对于需求中未明确的功能点，在 confirmation_note 中标注，格式为「待确认：问题简述」。",
            "",
            "请只输出 JSON，格式如下：",
            (
                '{"cases":[{"title":"测试标题","preconditions":["前置条件"],'
                '"steps":["步骤1","步骤2"],"expected_result":"预期结果",'
                '"priority":"P0","module":"模块名","module_id":"M01",'
                '"category":"正常流程","confirmation_note":null}]}'
            ),
        ]
    )


# ---------------------------------------------------------------------------
# Phase 4: Module Detail Generation (P2/P3, replaces category-based)
# ---------------------------------------------------------------------------


def build_module_detail_prompt(
    requirement_text: str,
    document_contexts: list[DocumentContext],
    module_id: str,
    module_name: str,
    sub_features: list[str],
    business_rules: str,
    data_constraints: str,
    existing_case_titles: Optional[list[str]] = None,
    min_cases: int = 15,
    knowledge_context: str = "",
) -> str:
    sub_features_block = "\n".join(f"  - {sf}" for sf in sub_features) if sub_features else "  - (未细分)"
    existing_block = ""
    if existing_case_titles:
        existing_block = "\n\n".join(
            [
                "## 已有用例（不要重复生成）",
                "\n".join(f"  - {t}" for t in existing_case_titles[:50]),
            ]
        )

    dimensions = "\n".join(f"  - {d}" for d in COVERAGE_DIMENSIONS)
    blocks = [
        build_requirement_context(requirement_text, document_contexts),
        "## 关键业务规则",
        business_rules,
        "## 数据约束",
        data_constraints,
    ]
    if knowledge_context:
        blocks.append(knowledge_context)
    if existing_block:
        blocks.append(existing_block)
    blocks.extend([
        f"## 任务：为模块「{module_id} {module_name}」生成详细测试用例",
        "子功能点：",
        sub_features_block,
        f"要求生成不少于 {min_cases} 条详细测试用例（优先级 P2/P3），覆盖以下维度中所有相关项：",
        dimensions,
        "",
        "具体要求：",
        f"1. 必须生成不少于 {min_cases} 条用例，穷尽该模块下所有有测试价值的场景。",
        "2. 对每个输入字段：正常值、边界值（最小/最大/临界）、无效值、特殊字符。",
        "3. 每个子功能的正常流程和异常流程都要覆盖。",
        "4. category 填写具体的覆盖维度名称（如「正常流程」「边界值与输入校验」等）。",
        "5. priority 填写 P2 或 P3。",
        "6. 需求不明确的功能点在 confirmation_note 中标注「待确认：xxx」。",
        "7. 不要输出解释，只输出 JSON。",
        "",
        "请只输出 JSON：",
        (
            '{"cases":[{"title":"测试标题","preconditions":["前置条件"],'
            '"steps":["步骤1"],"expected_result":"预期结果",'
            f'"priority":"P2","module":"{module_name}","module_id":"{module_id}",'
            '"category":"覆盖维度","confirmation_note":null}]}'
        ),
    ])
    return "\n\n".join(blocks)


def build_module_detail_markdown_prompt(
    requirement_text: str,
    document_contexts: list[DocumentContext],
    module_id: str,
    module_name: str,
    sub_features: list[str],
    min_cases: int = 15,
) -> str:
    sub_features_block = "\n".join(f"  - {sf}" for sf in sub_features) if sub_features else "  - (未细分)"
    return "\n\n".join(
        [
            build_requirement_context(requirement_text, document_contexts),
            f"## 任务：为模块「{module_id} {module_name}」生成详细测试用例",
            "子功能点：",
            sub_features_block,
            "要求：",
            f"1. 生成不少于 {min_cases} 条用例，覆盖正常流程/异常/边界/组合等所有相关维度。",
            "2. 只返回 Markdown 表格，不要输出解释。",
            f"3. 表格列固定为：用例ID、优先级、模块、分类、测试标题、前置条件、测试步骤、预期结果。",
            f"4. 模块列统一填写：{module_name}。",
            "5. 优先级填写 P2 或 P3。",
        ]
    )


# ---------------------------------------------------------------------------
# Phase 5: Multi-Perspective Review
# ---------------------------------------------------------------------------


def build_review_prompt(
    requirement_text: str,
    document_contexts: list[DocumentContext],
    existing_cases_summary: str,
) -> str:
    return "\n\n".join(
        [
            build_requirement_context(requirement_text, document_contexts),
            "## 已生成的测试用例摘要",
            existing_cases_summary,
            "## 任务：多视角用例评审",
            "请结合三重视角对上述已有用例进行全面评审，找出遗漏的测试场景：",
            "",
            "**开发工程师视角**：技术实现边界、数据校验逻辑、异常处理路径、兼容性风险",
            "**产品设计师视角**：业务逻辑完整性、用户体验细节、边界交互、空状态处理",
            "**测试工程师视角**：测试覆盖度、等价类遗漏、边界值缺失、可执行性问题",
            "",
            "评审标准：",
            "- 步骤完整性：每个步骤可独立执行",
            "- 结果可验证：预期结果明确可判断",
            "- 核心路径 100% 覆盖、一般路径 80%+ 覆盖",
            "- 发现缺漏才补充，不重复已有用例，不刻意找问题",
            "",
            "请只输出补充的新用例（如果没有遗漏则输出空数组），JSON 格式：",
            (
                '{"supplement_cases":[{"title":"测试标题","preconditions":["前置条件"],'
                '"steps":["步骤1"],"expected_result":"预期结果",'
                '"priority":"P2","module":"模块名","module_id":"M01",'
                '"category":"覆盖维度","review_source":"开发工程师视角"}]}'
            ),
        ]
    )


# ---------------------------------------------------------------------------
# Batch Generation Prompt (Phase 2: 合并 Phase3/4/5 为单次调用)
# ---------------------------------------------------------------------------


def build_batch_generation_prompt(
    requirement_text: str,
    document_contexts: list[DocumentContext],
    modules: list[PlannedModule],
    business_rules: str,
    data_constraints: str,
    knowledge_context: str = "",
) -> str:
    """构建批量生成提示词，将冒烟测试 + 模块详情 + 评审补充合并为一次调用。

    适用于两阶段模式：Phase1 完成后，Phase2 一次性生成全部用例。
    """
    modules_json = json.dumps(
        [
            {
                "id": m.id,
                "name": m.name,
                "description": m.description,
                "sub_features": m.sub_features,
            }
            for m in modules
        ],
        ensure_ascii=False,
        indent=2,
    )

    dimensions = "\n".join(f"- {d}" for d in COVERAGE_DIMENSIONS)

    blocks = [
        build_requirement_context(requirement_text, document_contexts),
        "## 功能模块清单",
        modules_json,
        "## 关键业务规则",
        business_rules or "无明确业务规则。",
        "## 数据约束",
        data_constraints or "无",
    ]

    if knowledge_context:
        blocks.append(knowledge_context)

    blocks.extend([
        "## 任务：一次性生成完整测试用例集",
        "请针对所有模块一次性生成完整测试用例，包含以下三个层次：",
        "",
        "### 第一层：冒烟测试（P0/P1）",
        "- 每个模块的核心功能冒烟测试，必须 100% 通过才能上线",
        "- 主要业务流程验证，24 小时内必须修复",
        "- 每个模块至少覆盖其主要正常路径和最关键的异常路径",
        "",
        "### 第二层：模块详细用例（P2/P3）",
        f"- 每个模块生成不少于 15 条用例，覆盖以下维度：\n{dimensions}",
        "- 对每个输入字段：正常值、边界值（最小/最大/临界）、无效值、特殊字符",
        "- 每个子功能的正常流程和异常流程都要覆盖",
        "- 需求不明确的功能点在 confirmation_note 中标注「待确认：xxx」",
        "",
        "### 第三层：评审补充（可选）",
        "- 从开发工程师、产品设计师、测试工程师三个视角补充遗漏场景",
        "- 仅补充真正有测试价值的新用例，不重复已有用例",
        "",
        "## 输出要求",
        "请只输出 JSON，格式如下：",
        "{",
        '  "smoke_cases": [',  # P0/P1 冒烟测试
        "    {\"title\":\"测试标题\",\"preconditions\":[\"前置条件\"],\"steps\":[\"步骤1\",\"步骤2\"],\"expected_result\":\"预期结果\",\"priority\":\"P0\",\"module\":\"模块名\",\"module_id\":\"M01\",\"category\":\"正常流程\",\"confirmation_note\":null}",
        "  ],",
        '  "module_cases": [',  # P2/P3 按模块分组
        "    {\"title\":\"测试标题\",\"preconditions\":[\"前置条件\"],\"steps\":[\"步骤1\"],\"expected_result\":\"预期结果\",\"priority\":\"P2\",\"module\":\"模块名\",\"module_id\":\"M01\",\"category\":\"覆盖维度\",\"confirmation_note\":null}",
        "  ],",
        '  "review_cases": [',  # 评审补充
        "    {\"title\":\"测试标题\",\"preconditions\":[\"前置条件\"],\"steps\":[\"步骤1\"],\"expected_result\":\"预期结果\",\"priority\":\"P2\",\"module\":\"模块名\",\"module_id\":\"M01\",\"category\":\"评审补充\",\"review_source\":\"开发工程师视角\",\"confirmation_note\":null}",
        "  ]",
        "}",
    ])
    return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# Fallback: Single-shot high-coverage markdown
# ---------------------------------------------------------------------------


def build_high_coverage_markdown_prompt(
    requirement_text: str, document_contexts: list[DocumentContext]
) -> str:
    categories_str = "、".join(COVERAGE_DIMENSIONS)
    return "\n\n".join(
        [
            build_requirement_context(requirement_text, document_contexts),
            "## 输出要求",
            "请尽可能高覆盖地生成测试用例。",
            f"覆盖维度包括但不限于：{categories_str}。",
            "对于每个功能点和每个输入字段，都要考虑：正常值、边界值、无效值、特殊字符、组合场景。",
            "目标是生成不少于 50 条测试用例，复杂需求应更多。",
            "请只返回 Markdown 表格，不要解释。",
            "表格列固定为：用例ID、优先级、模块、分类、测试标题、前置条件、测试步骤、预期结果。",
        ]
    )
