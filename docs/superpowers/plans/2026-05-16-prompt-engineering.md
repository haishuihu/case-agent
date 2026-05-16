# Prompt Engineering Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the monolithic SYSTEM_PROMPT with per-phase YAML templates, CoT reasoning chains, few-shot examples, and an evaluation harness.

**Architecture:** PromptManager loads YAML templates from `prompts/templates/`, renders per-phase system prompts and CoT-structured user prompts. TestCaseGenerator uses PromptManager instead of hardcoded SYSTEM_PROMPT. The evaluator runs templates against eval datasets and computes 5 quality metrics.

**Tech Stack:** Python 3.12+, PyYAML (already available 6.0.3), pytest

---

### Task 1: Create directory structure and PromptManager skeleton

**Files:**
- Create: `backend/app/prompts/__init__.py`
- Create: `backend/app/prompts/manager.py`
- Create: `backend/app/prompts/templates/.gitkeep`
- Create: `backend/app/prompts/examples/.gitkeep`
- Create: `backend/app/prompts/schemas/.gitkeep`

- [ ] **Step 1: Create directories**

```bash
cd /Users/linpingyuan/case-agent/backend
mkdir -p app/prompts/templates app/prompts/examples app/prompts/schemas
```

- [ ] **Step 2: Write `backend/app/prompts/__init__.py`**

```python
"""Prompt templates and management for test case generation."""
```

- [ ] **Step 3: Write `backend/app/prompts/manager.py` with PromptManager class**

```python
"""PromptManager: loads YAML templates, renders system/user prompts per phase."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Default templates directory relative to this file
_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_EXAMPLES_DIR = Path(__file__).resolve().parent / "examples"


class PromptManager:
    """Loads and renders per-phase prompt templates from YAML files."""

    def __init__(
        self,
        templates_dir: str | None = None,
        examples_dir: str | None = None,
    ) -> None:
        self.templates_dir = Path(templates_dir) if templates_dir else _TEMPLATES_DIR
        self.examples_dir = Path(examples_dir) if examples_dir else _EXAMPLES_DIR
        self._cache: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def render(
        self,
        template_name: str,
        context: dict[str, Any],
        model_provider: str | None = None,
    ) -> tuple[str, str]:
        """Render (system_prompt, user_prompt) for a template.

        Args:
            template_name: e.g. "phase4_module_detail"
            context: dict with keys like requirement_text, module_name,
                     business_rules, data_constraints, knowledge_context, etc.
            model_provider: optional model key for overrides (e.g. "deepseek")
        """
        tmpl = self._load_template(template_name)
        system_prompt = self._render_system_prompt(tmpl, model_provider)
        user_prompt = self._render_user_prompt(tmpl, context)
        return system_prompt, user_prompt

    def get_version(self, template_name: str) -> str:
        tmpl = self._load_template(template_name)
        return str(tmpl.get("version", "0.0.0"))

    def list_templates(self) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        for p in sorted(self.templates_dir.glob("*.yaml")):
            tmpl = self._load_template(p.stem)
            result.append({
                "name": str(tmpl.get("name", p.stem)),
                "version": str(tmpl.get("version", "0.0.0")),
                "description": str(tmpl.get("description", "")),
            })
        return result

    # ------------------------------------------------------------------
    # internal
    # ------------------------------------------------------------------

    def _load_template(self, template_name: str) -> dict[str, Any]:
        if template_name in self._cache:
            return self._cache[template_name]
        path = self.templates_dir / f"{template_name}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Template not found: {path}")
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict):
            raise ValueError(f"Invalid template format: {path}")
        self._cache[template_name] = data
        return data

    def _render_system_prompt(
        self,
        tmpl: dict[str, Any],
        model_provider: str | None,
    ) -> str:
        sp = tmpl.get("system_prompt", {})
        if isinstance(sp, dict):
            overrides = sp.get("overrides", {})
            if model_provider and model_provider in overrides:
                return str(overrides[model_provider])
            return str(sp.get("default", ""))
        return str(sp)

    def _render_user_prompt(
        self,
        tmpl: dict[str, Any],
        context: dict[str, Any],
    ) -> str:
        blocks: list[str] = []

        # 1. Task context section
        task_context = self._build_task_context(tmpl, context)
        if task_context:
            blocks.append(task_context)

        # 2. Few-shot examples
        examples_block = self._build_examples(tmpl)
        if examples_block:
            blocks.append(examples_block)

        # 3. CoT thinking template
        cot_block = self._build_cot(tmpl, context)
        if cot_block:
            blocks.append(cot_block)

        # 4. Output format instruction
        output_block = self._build_output_instruction(tmpl, context)
        if output_block:
            blocks.append(output_block)

        return "\n\n".join(blocks)

    def _build_task_context(
        self,
        tmpl: dict[str, Any],
        context: dict[str, Any],
    ) -> str:
        """Build the task description + data context section.

        Subclasses or template overrides can customize this.
        The default renders a simple "## 任务上下文" block with
        injected context keys.
        """
        ctx_block = tmpl.get("task_context_template")
        if ctx_block:
            return ctx_block.format(**context)
        # Generic fallback: dump formatted context
        lines = ["## 任务上下文"]
        for key in (
            "requirement_context",
            "module_info",
            "business_rules",
            "data_constraints",
            "knowledge_context",
            "existing_cases",
        ):
            val = context.get(key)
            if val:
                lines.append(f"\n### {key}\n{val}")
        if len(lines) == 1:
            return ""
        return "\n".join(lines)

    def _build_examples(self, tmpl: dict[str, Any]) -> str:
        examples = tmpl.get("few_shot_examples")
        if not examples:
            return ""

        lines = ["## Few-Shot 示例", "以下示例展示了期望的输出格式和质量标准："]
        for ex in examples[:2]:
            if isinstance(ex, str):
                # Reference to an examples/*.json file
                ex_path = self.examples_dir / ex
                if ex_path.exists():
                    import json

                    ex_data = json.loads(ex_path.read_text(encoding="utf-8"))
                    if isinstance(ex_data, list):
                        for item in ex_data[:2]:
                            lines.append(self._format_one_example(item))
                    elif isinstance(ex_data, dict):
                        lines.append(self._format_one_example(ex_data))
            elif isinstance(ex, dict):
                lines.append(self._format_one_example(ex))
        return "\n".join(lines) if len(lines) > 2 else ""

    @staticmethod
    def _format_one_example(ex: dict[str, Any]) -> str:
        parts = [f"\n### 示例: {ex.get('scenario', '示例')}"]
        inp = ex.get("input", {})
        if inp:
            parts.append("**输入**:")
            parts.append("```json")
            import json

            parts.append(json.dumps(inp, ensure_ascii=False, indent=2))
            parts.append("```")
        out = ex.get("output", {})
        if out:
            parts.append("**期望输出**:")
            parts.append("```json")
            parts.append(json.dumps(out, ensure_ascii=False, indent=2))
            parts.append("```")
        return "\n".join(parts)

    def _build_cot(
        self,
        tmpl: dict[str, Any],
        context: dict[str, Any],
    ) -> str:
        cot = tmpl.get("cot_template")
        if not cot:
            return ""

        steps = cot.get("steps", [])
        if not steps:
            return ""

        lines = [
            "## 思考步骤（请严格按顺序执行，将思考内容放在 `<thinking>` 标签内）",
            "",
            "<thinking>",
        ]
        for i, step in enumerate(steps, 1):
            name = step.get("name", f"Step {i}")
            instruction = step.get("instruction", "")
            lines.append(f"<step name=\"{name}\">")
            lines.append(instruction)
            lines.append("</step>")
            lines.append("")
        lines.append("</thinking>")
        return "\n".join(lines)

    def _build_output_instruction(
        self,
        tmpl: dict[str, Any],
        context: dict[str, Any],
    ) -> str:
        """Build the output format instruction.

        Looks for output_format template field; falls back to a generic
        JSON-only instruction.
        """
        fmt = tmpl.get("output_format")
        if fmt:
            return fmt.format(**context)

        # Generic JSON instruction
        schema_ref = tmpl.get("output_schema", "")
        if schema_ref:
            return (
                "## 输出要求\n"
                "请基于以上思考，只输出 JSON，不要输出任何解释、Markdown 代码块标记或其他文字。\n"
                f"输出格式请参考: {schema_ref}"
            )
        return (
            "## 输出要求\n"
            "请基于以上思考，只输出 JSON，不要输出任何解释、Markdown 代码块标记或其他文字。"
        )


# Singleton instance
_prompt_manager: PromptManager | None = None


def get_prompt_manager() -> PromptManager:
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager


def reset_prompt_manager() -> None:
    global _prompt_manager
    _prompt_manager = None
```

- [ ] **Step 4: Verify manager.py imports cleanly**

```bash
cd /Users/linpingyuan/case-agent/backend && .venv/bin/python -c "from app.prompts.manager import PromptManager, get_prompt_manager; print('OK')"
```
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/prompts/__init__.py backend/app/prompts/manager.py
git commit -m "feat: add PromptManager skeleton with YAML loading and rendering

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
"
```

---

### Task 2: Write Phase 4 YAML template (module detail generation)

**Files:**
- Create: `backend/app/prompts/templates/phase4_module_detail.yaml`

This is the most complex template and the primary target for quality improvement.

- [ ] **Step 1: Write `backend/app/prompts/templates/phase4_module_detail.yaml`**

```yaml
name: phase4_module_detail
version: "1.0.0"
description: "模块详细测试用例生成（P2/P3）"

system_prompt:
  default: |
    你是一个资深测试设计专家，专精于单个功能模块的穷尽式测试用例设计。

    核心能力：
    - 等价类划分与边界值分析
    - 状态迁移测试设计
    - 数据组合与正交分析
    - 异常路径与错误推测

    设计原则：
    - 一个用例只验证一个明确的测试点
    - 测试步骤必须具体到操作级别，可独立执行
    - 预期结果必须是可观测、可验证的具体行为
    - 需求不明确的功能点用「待确认：xxx」标注，不凭空编造
    - 不要生成与已有用例重复的测试

    覆盖维度：
    - 正常流程：主要业务路径的完整操作流
    - 异常与错误处理：无效输入、超时、网络中断、服务不可用、数据冲突
    - 边界值与输入校验：最小值/最大值/临界值、空值、超长、特殊字符
    - 数据组合与等价类：多输入字段的有效/无效组合
    - 状态流转与时序约束：对象状态的合法/非法跃迁、操作顺序依赖
    - 权限与角色控制：不同角色的操作权限、越权访问
    - 兼容性与环境依赖：不同浏览器/设备/系统版本
    - 性能与并发：批量操作、高并发、超时处理
    - 安全与数据保护：注入攻击、XSS、敏感信息泄露
    - 用户体验与界面：提示信息准确性、交互反馈、加载/空状态显示

  overrides:
    deepseek: |
      你现在必须扮演一个资深测试设计专家，专精于单个功能模块的穷尽式测试用例设计。
      你的核心能力包括等价类划分、边界值分析、状态迁移测试、数据组合分析。
      重要设计原则：一个用例只验证一个测试点、步骤可执行、预期可验证、不明确的用「待确认」标注。

    minimax: |
      你是一个资深测试设计专家。你必须严格遵循以下规则：
      1. 一个用例只验证一个测试点
      2. 步骤具体到操作级别
      3. 预期结果可观测可验证
      4. 不明确的功能点用「待确认：xxx」标注
      5. 重要：你必须只输出 JSON，不要输出任何解释文字。

cot_template:
  steps:
    - name: 功能理解
      instruction: |
        理解当前模块的核心功能：
        1. 这个模块让用户完成什么任务？
        2. 用户与模块的交互入口和操作流程是什么？
        3. 列出所有输入字段、用户操作和系统响应。
    - name: 维度映射
      instruction: |
        对以下10个覆盖维度逐一判断是否适用于本模块：
        - 正常流程 / 异常处理 / 边界值与输入校验 / 数据组合与等价类
        - 状态流转与时序约束 / 权限与角色控制 / 兼容性与环境依赖
        - 性能与并发 / 安全与数据保护 / 用户体验与界面
        每个维度标注「适用」或「不适用」，并简要说明原因。
        不相关的维度不要硬凑用例。
    - name: 测试点识别
      instruction: |
        基于上一步标记为「适用」的维度，逐一列出具体测试场景点：
        - 每个适用维度下列出 3-8 个测试场景
        - 边界值场景要包含：最小值、最大值、临界值、空值、超长、特殊字符
        - 异常场景要包含：网络异常、超时、数据校验失败、并发冲突
        - 穷尽但不重复
    - name: 用例设计
      instruction: |
        为上一步的每个测试点设计一条测试用例：
        - 标题简洁描述测试意图（15字以内）
        - 前置条件明确（如：已登录、购物车非空、网络正常）
        - 测试步骤具体到操作级别（如：点击按钮、输入内容、等待响应）
        - 预期结果可观测可验证（如：显示错误提示「xxx」、跳转到xxx页面）
        - 分类对应覆盖维度名称
        - 需求不明确的用「待确认：xxx」标注
    - name: 自检
      instruction: |
        输出前检查：
        1. 是否覆盖了所有标记为「适用」的维度？
        2. 是否有与已有用例重复的内容？
        3. 用例数量是否达到要求（≥ 15条）？
        4. 每条用例的步骤是否可独立执行？
        5. 每条用例的预期结果是否可观测？
        6. 是否需要调整优先级？核心场景P2，边缘场景P3

few_shot_examples:
  - detail_examples.json

output_schema: phase4_output.schema.json

output_format: |
  ## 输出要求
  基于以上思考，请只输出 JSON，不要输出任何解释、Markdown 代码块标记或其他文字。

  JSON 格式：
  {"cases":[{"title":"测试标题","preconditions":["前置条件"],"steps":["步骤1"],"expected_result":"预期结果","priority":"P2","module":"{module_name}","module_id":"{module_id}","category":"覆盖维度","confirmation_note":null}]}
```

- [ ] **Step 2: Verify template loads**

```bash
cd /Users/linpingyuan/case-agent/backend && .venv/bin/python -c "
from app.prompts.manager import PromptManager
pm = PromptManager()
v = pm.get_version('phase4_module_detail')
print(f'Template version: {v}')
sys, user = pm.render('phase4_module_detail', {'module_name': '登录', 'module_id': 'M01'})
print(f'System prompt length: {len(sys)}')
print(f'User prompt length: {len(user)}')
assert len(sys) > 50, 'system prompt too short'
assert '<thinking>' in user, 'CoT not rendered in user prompt'
print('OK')
"
```
Expected: `OK` with template version and lengths printed.

- [ ] **Step 3: Commit**

```bash
git add backend/app/prompts/templates/phase4_module_detail.yaml
git commit -m "feat: add Phase4 module detail YAML template

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
"
```

---

### Task 3: Write remaining Phase YAML templates

**Files:**
- Create: `backend/app/prompts/templates/phase1_requirement_review.yaml`
- Create: `backend/app/prompts/templates/phase3_smoke.yaml`
- Create: `backend/app/prompts/templates/phase5_review.yaml`

- [ ] **Step 1: Write `backend/app/prompts/templates/phase1_requirement_review.yaml`**

```yaml
name: phase1_requirement_review
version: "1.0.0"
description: "需求评审与模块分解"

system_prompt:
  default: |
    你是一个资深产品需求分析师，专精于将功能需求拆分为可独立测试的模块。

    核心能力：
    - 识别功能模块边界，按可独立测试原则拆分
    - 发现需求中的模糊、遗漏、矛盾之处
    - 提取业务规则和数据约束

    工作原则：
    - 忠实原文，每个发现必须能在需求中找到出处
    - 不明确的以疑问句形式标注，不假设
    - 模块划分粒度适中，不过粗也不过细

  overrides:
    deepseek: |
      你现在必须扮演一个资深产品需求分析师。
      你的任务是：识别功能模块、发现需求问题、提取业务规则和数据约束。
      只输出 JSON，不要任何解释。

    minimax: |
      你是一个资深产品需求分析师。
      任务：识别功能模块、发现需求问题、提取业务规则和数据约束。
      重要：你必须只输出 JSON，不要输出任何解释文字。

cot_template:
  steps:
    - name: 通读理解
      instruction: "通读需求全文，理解业务目标和核心功能流程。列出关键业务实体和用户角色。"
    - name: 模块识别
      instruction: "将需求拆分为独立的功能模块（M01, M02...）。每个模块边界清晰、可独立测试、领域内聚。"
    - name: 问题发现
      instruction: |
        从以下维度评审需求，只记录真正影响测试设计的问题：
        - 功能描述模糊（动词不明确、缺少主语/宾语、条件不完整）
        - 边界条件缺失（数值范围、长度限制、超长/超短/空值处理）
        - 异常场景遗漏（网络异常、并发、数据校验失败处理）
        - 交互逻辑不清（页面跳转、状态流转、操作顺序）
        - 数据规格不明（字段类型、长度、格式、必填/选填）
        - 权限模型不清晰（角色划分、操作权限）
    - name: 规则提取
      instruction: "提取关键业务规则（每条用一句话表述）和每个输入字段的数据约束（字段名、类型、长度、格式、是否必填）。"
    - name: 自检
      instruction: "检查：模块划分是否合理？问题是否具体可回答？规则是否重复？约束是否遗漏？"

few_shot_examples:
  - review_examples.json

output_schema: phase1_output.schema.json

output_format: |
  ## 输出要求
  基于以上思考，请只输出 JSON：

  {"modules":[{"id":"M01","name":"模块名","description":"功能描述","sub_features":["子功能1","子功能2"]}],"questions":[{"id":"Q-001","type":"边界条件缺失","description":"问题描述","module":"M01","suggestion":"建议"}],"business_rules":["规则1","规则2"],"data_constraints":[{"field":"字段名","type":"string","length":"1-20","format":"手机号","required":true}]}
```

- [ ] **Step 2: Write `backend/app/prompts/templates/phase3_smoke.yaml`**

```yaml
name: phase3_smoke
version: "1.0.0"
description: "冒烟测试生成（P0/P1）"

system_prompt:
  default: |
    你是一个冒烟测试专家，专精于快速验证核心功能可用性。

    冒烟测试原则：
    - 只覆盖核心业务路径的端到端验证
    - 用例简洁，验证功能可用性而非详尽覆盖
    - P0：核心功能冒烟，100% 通过才能上线
    - P1：主要业务流程，24小时内必须修复
    - 每个模块至少覆盖其主要正常路径和最关键的异常路径
    - 不明确的功能点在 confirmation_note 中标注「待确认：xxx」

  overrides:
    deepseek: |
      你现在必须扮演一个冒烟测试专家。只关注核心路径和关键异常，用例简洁。

    minimax: |
      你是一个冒烟测试专家。只覆盖核心路径和关键异常。重要：只输出 JSON。

cot_template:
  steps:
    - name: 核心路径识别
      instruction: "对每个模块，识别用户最常走的核心路径（Happy Path）和最关键的异常路径。不展开边缘场景。"
    - name: 用例设计
      instruction: "为每个核心路径和关键异常路径设计一条简洁的冒烟用例。P0 标记为核心功能，P1 标记为主要流程。"
    - name: 自检
      instruction: "检查：每个模块是否至少覆盖正常路径 + 最关键的异常路径？是否有多余的边缘场景混入？"

few_shot_examples:
  - smoke_examples.json

output_format: |
  ## 输出要求
  基于以上思考，请只输出 JSON：

  {"cases":[{"title":"测试标题","preconditions":["前置条件"],"steps":["步骤1"],"expected_result":"预期结果","priority":"P0","module":"模块名","module_id":"M01","category":"冒烟测试","confirmation_note":null}]}
```

- [ ] **Step 3: Write `backend/app/prompts/templates/phase5_review.yaml`**

```yaml
name: phase5_review
version: "1.0.0"
description: "多视角用例评审补充"

system_prompt:
  default: |
    你是一个质量审计专家，专精于从多视角发现测试遗漏。

    评审视角：
    - 开发工程师视角：技术实现边界、数据校验逻辑、异常处理路径、兼容性风险
    - 产品设计师视角：业务逻辑完整性、用户体验细节、边界交互、空状态处理
    - 测试工程师视角：测试覆盖度、等价类遗漏、边界值缺失、可执行性问题

    评审原则：
    - 只补充真正有测试价值的新用例，不重复已有用例
    - 不刻意找问题——发现缺漏才补充
    - 补充的用例步骤必须可执行、预期可验证

  overrides:
    deepseek: |
      你现在必须扮演一个质量审计专家。从开发、产品、测试三个视角发现测试遗漏。
      只补充真正遗漏的，不重复已有，不刻意找问题。

    minimax: |
      你是一个质量审计专家。从开发、产品、测试三个视角发现测试遗漏。
      重要：只输出 JSON，不重复已有用例。

cot_template:
  steps:
    - name: 理解已有覆盖
      instruction: "审阅已有测试用例列表，理解当前覆盖范围。哪些路径已经被覆盖了？"
    - name: 逐视角检查
      instruction: |
        从三个视角逐一检查：
        - 开发视角：代码逻辑分支是否都有用例？异常处理路径是否覆盖？边界条件是否完整？
        - 产品视角：业务流程是否完整？用户操作路径是否闭环？空状态/加载态/错误态是否覆盖？
        - 测试视角：等价类是否完整？边界值是否覆盖？组合场景是否遗漏？
    - name: 补充遗漏
      instruction: "只记录有测试价值的遗漏场景。如果没有遗漏，不要硬凑。"
    - name: 自检
      instruction: "检查补充的用例是否与已有用例重复？是否真正有价值？是否可以独立执行？"

output_format: |
  ## 输出要求
  基于以上思考，请只输出 JSON（如果没有遗漏则输出空数组）：

  {"supplement_cases":[{"title":"测试标题","preconditions":["前置条件"],"steps":["步骤1"],"expected_result":"预期结果","priority":"P2","module":"模块名","module_id":"M01","category":"评审补充","review_source":"开发工程师视角","confirmation_note":null}]}
```

- [ ] **Step 4: Verify all templates load**

```bash
cd /Users/linpingyuan/case-agent/backend && .venv/bin/python -c "
from app.prompts.manager import PromptManager
pm = PromptManager()
for name in ['phase1_requirement_review', 'phase3_smoke', 'phase4_module_detail', 'phase5_review']:
    v = pm.get_version(name)
    print(f'{name}: v{v}')
print('All templates OK')
"
```
Expected: all 4 templates printed with versions.

- [ ] **Step 5: Commit**

```bash
git add backend/app/prompts/templates/phase1_requirement_review.yaml backend/app/prompts/templates/phase3_smoke.yaml backend/app/prompts/templates/phase5_review.yaml
git commit -m "feat: add Phase1/3/5 YAML templates for requirement review, smoke, and review

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
"
```

---

### Task 4: Write Phase 2 batch generation YAML template

**Files:**
- Create: `backend/app/prompts/templates/phase2_batch_generation.yaml`

- [ ] **Step 1: Write `backend/app/prompts/templates/phase2_batch_generation.yaml`**

```yaml
name: phase2_batch_generation
version: "1.0.0"
description: "批量生成完整测试用例集（冒烟 + 模块详情 + 评审补充）"

system_prompt:
  default: |
    你是一个资深测试设计专家，需要一次性完成三个层次的测试用例设计。

    第一层 - 冒烟测试（P0/P1）：
    - 每个模块的核心功能冒烟测试
    - 主要业务流程验证
    - 每个模块至少覆盖正常路径 + 最关键的异常路径

    第二层 - 模块详细用例（P2/P3）：
    - 每个模块穷尽式覆盖
    - 对每个输入字段：正常值、边界值、无效值、特殊字符
    - 每个子功能的正常流程和异常流程
    - 覆盖维度：正常流程、异常处理、边界值、数据组合、状态流转、权限控制、兼容性、性能并发、安全、用户体验

    第三层 - 评审补充：
    - 从开发、产品、测试三个视角补充遗漏
    - 只补充真正有测试价值的，不重复

    设计原则：
    - 一个用例只验证一个测试点
    - 步骤具体到操作级别，可独立执行
    - 预期结果可观测可验证
    - 不明确的功能点用「待确认：xxx」标注

  overrides:
    deepseek: |
      你现在必须扮演一个资深测试设计专家，需要一次性完成冒烟测试、模块详细用例、评审补充三个层次的设计。
      设计原则：一个用例一个测试点、步骤可执行、预期可验证、不明确用「待确认」标注。

    minimax: |
      你是一个资深测试设计专家。一次性完成冒烟测试、模块详细用例、评审补充三个层次。
      重要：你必须只输出 JSON，不要输出任何解释文字。

cot_template:
  steps:
    - name: 全局分析
      instruction: |
        通读所有模块信息：
        1. 理解整体功能架构和模块间关系
        2. 识别哪些是核心模块（决定业务可用性）
        3. 识别哪些维度对各模块适用
    - name: 冒烟测试设计
      instruction: |
        为每个模块设计冒烟测试：
        - 核心正常路径（P0）
        - 关键异常路径（P1）
        - 用例简洁，验证可用性
    - name: 模块详情设计
      instruction: |
        为每个模块设计详细用例：
        - 逐一判断10个覆盖维度的适用性
        - 每个适用维度下列出具体测试场景
        - 边界值：最小/最大/临界/空/超长/特殊字符
        - 异常：网络异常/超时/校验失败/并发冲突
        - 每个模块至少15条用例
    - name: 评审补充
      instruction: |
        从开发、产品、测试三个视角检查遗漏：
        - 开发视角：代码逻辑分支、异常处理路径、边界条件
        - 产品视角：业务流程完整性、用户体验细节
        - 测试视角：等价类完整性、边界值覆盖
        只补充真正遗漏的，不重复已有。
    - name: 全局自检
      instruction: |
        最终检查：
        1. 三个层次的用例是否完整？
        2. 同一模块内、层次间是否有重复？
        3. 每条用例是否可独立执行、预期可验证？
        4. P0/P1 是否确实是核心路径？

few_shot_examples:
  - smoke_examples.json
  - detail_examples.json

output_format: |
  ## 输出要求
  基于以上思考，请只输出 JSON：

  {
    "smoke_cases": [
      {"title":"测试标题","preconditions":["前置条件"],"steps":["步骤1","步骤2"],"expected_result":"预期结果","priority":"P0","module":"模块名","module_id":"M01","category":"冒烟测试","confirmation_note":null}
    ],
    "module_cases": [
      {"title":"测试标题","preconditions":["前置条件"],"steps":["步骤1"],"expected_result":"预期结果","priority":"P2","module":"模块名","module_id":"M01","category":"覆盖维度","confirmation_note":null}
    ],
    "review_cases": [
      {"title":"测试标题","preconditions":["前置条件"],"steps":["步骤1"],"expected_result":"预期结果","priority":"P2","module":"模块名","module_id":"M01","category":"评审补充","review_source":"开发工程师视角","confirmation_note":null}
    ]
  }
```

- [ ] **Step 2: Verify Phase2 template loads**

```bash
cd /Users/linpingyuan/case-agent/backend && .venv/bin/python -c "
from app.prompts.manager import PromptManager
pm = PromptManager()
v = pm.get_version('phase2_batch_generation')
print(f'Phase2 version: {v}')
sys, user = pm.render('phase2_batch_generation', {'requirement_context': 'test'})
assert len(sys) > 50
assert '<thinking>' in user
print('OK')
"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/prompts/templates/phase2_batch_generation.yaml
git commit -m "feat: add Phase2 batch generation YAML template

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
"
```

---

### Task 5: Write JSON Schema and Few-Shot example files

**Files:**
- Create: `backend/app/prompts/schemas/phase1_output.schema.json`
- Create: `backend/app/prompts/schemas/phase4_output.schema.json`
- Create: `backend/app/prompts/examples/review_examples.json`
- Create: `backend/app/prompts/examples/smoke_examples.json`
- Create: `backend/app/prompts/examples/detail_examples.json`

- [ ] **Step 1: Write `backend/app/prompts/schemas/phase1_output.schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "modules": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"type": "string"},
          "name": {"type": "string"},
          "description": {"type": "string"},
          "sub_features": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["id", "name", "description"]
      }
    },
    "questions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"type": "string"},
          "type": {"type": "string"},
          "description": {"type": "string"},
          "module": {"type": "string"},
          "suggestion": {"type": "string"}
        },
        "required": ["id", "type", "description"]
      }
    },
    "business_rules": {
      "type": "array",
      "items": {"type": "string"}
    },
    "data_constraints": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "field": {"type": "string"},
          "type": {"type": "string"},
          "length": {"type": "string"},
          "format": {"type": "string"},
          "required": {"type": "boolean"}
        }
      }
    }
  },
  "required": ["modules"]
}
```

- [ ] **Step 2: Write `backend/app/prompts/schemas/phase4_output.schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "cases": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "title": {"type": "string"},
          "preconditions": {"type": "array", "items": {"type": "string"}},
          "steps": {"type": "array", "items": {"type": "string"}, "minItems": 1},
          "expected_result": {"type": "string"},
          "priority": {"type": "string", "enum": ["P0", "P1", "P2", "P3"]},
          "module": {"type": "string"},
          "module_id": {"type": "string"},
          "category": {"type": "string"},
          "confirmation_note": {"type": ["string", "null"]}
        },
        "required": ["title", "steps", "expected_result", "priority"]
      }
    }
  },
  "required": ["cases"]
}
```

- [ ] **Step 3: Write `backend/app/prompts/examples/detail_examples.json`**

```json
[
  {
    "id": "ex-001",
    "scenario": "表单输入校验 - 手机号注册",
    "tags": ["表单", "校验", "边界值", "异常处理"],
    "input": {
      "module": "用户注册",
      "sub_features": ["手机号注册"],
      "rules": ["手机号11位数字", "验证码6位数字60秒有效", "同一手机号每天最多发5次验证码"]
    },
    "output": {
      "cases": [
        {
          "title": "输入正确手机号+正确验证码注册成功",
          "preconditions": ["未注册手机号13800001111", "验证码服务正常"],
          "steps": ["1.打开注册页面", "2.输入手机号13800001111", "3.点击获取验证码", "4.输入正确验证码", "5.点击注册"],
          "expected_result": "注册成功，跳转到首页并显示欢迎提示",
          "priority": "P2",
          "module": "用户注册",
          "module_id": "M01",
          "category": "正常流程",
          "confirmation_note": null
        },
        {
          "title": "输入已注册手机号提示错误",
          "preconditions": ["手机号13800001111已被注册"],
          "steps": ["1.打开注册页面", "2.输入已注册手机号13800001111", "3.点击获取验证码"],
          "expected_result": "提示「该手机号已注册，请直接登录」，不发送验证码",
          "priority": "P2",
          "module": "用户注册",
          "module_id": "M01",
          "category": "异常与错误处理",
          "confirmation_note": null
        },
        {
          "title": "输入10位手机号校验失败",
          "preconditions": ["打开注册页面"],
          "steps": ["1.输入10位手机号1380000111", "2.点击获取验证码"],
          "expected_result": "提示「请输入正确的11位手机号」，不发送请求",
          "priority": "P2",
          "module": "用户注册",
          "module_id": "M01",
          "category": "边界值与输入校验",
          "confirmation_note": null
        },
        {
          "title": "输入含字母的手机号校验失败",
          "preconditions": ["打开注册页面"],
          "steps": ["1.输入手机号1380000abcd", "2.点击获取验证码"],
          "expected_result": "提示「请输入正确的11位手机号」",
          "priority": "P2",
          "module": "用户注册",
          "module_id": "M01",
          "category": "边界值与输入校验",
          "confirmation_note": null
        },
        {
          "title": "输入错误验证码注册失败",
          "preconditions": ["已发送验证码到手机13800001111", "验证码123456"],
          "steps": ["1.输入手机号13800001111", "2.输入错误验证码111111", "3.点击注册"],
          "expected_result": "提示「验证码错误，请重新输入」，注册失败",
          "priority": "P2",
          "module": "用户注册",
          "module_id": "M01",
          "category": "异常与错误处理",
          "confirmation_note": null
        },
        {
          "title": "超过每日验证码发送次数限制",
          "preconditions": ["手机号13800001111今日已发送5次验证码"],
          "steps": ["1.输入手机号13800001111", "2.点击获取验证码"],
          "expected_result": "提示「今日验证码发送次数已达上限，请明日再试」",
          "priority": "P2",
          "module": "用户注册",
          "module_id": "M01",
          "category": "边界值与输入校验",
          "confirmation_note": null
        }
      ]
    }
  },
  {
    "id": "ex-002",
    "scenario": "列表搜索与筛选",
    "tags": ["列表", "搜索", "筛选", "空状态"],
    "input": {
      "module": "订单列表搜索",
      "sub_features": ["按订单号搜索", "按日期范围筛选", "按状态筛选"],
      "rules": ["支持精确搜索和模糊搜索", "日期范围不超过90天", "状态包括：待支付/已支付/已发货/已完成/已取消"]
    },
    "output": {
      "cases": [
        {
          "title": "按订单号精确搜索",
          "preconditions": ["系统中存在订单号ORD20240101001"],
          "steps": ["1.进入订单列表页", "2.在搜索框输入ORD20240101001", "3.点击搜索"],
          "expected_result": "列表显示订单ORD20240101001，其他订单不显示",
          "priority": "P2",
          "module": "订单列表搜索",
          "module_id": "M02",
          "category": "正常流程",
          "confirmation_note": null
        },
        {
          "title": "搜索不存在的订单号显示空状态",
          "preconditions": ["系统中不存在订单号ORD99999999999"],
          "steps": ["1.进入订单列表页", "2.搜索ORD99999999999", "3.点击搜索"],
          "expected_result": "显示空状态提示「未找到相关订单」",
          "priority": "P2",
          "module": "订单列表搜索",
          "module_id": "M02",
          "category": "用户体验与界面",
          "confirmation_note": null
        },
        {
          "title": "按状态筛选已支付订单",
          "preconditions": ["系统中存在已支付和待支付订单"],
          "steps": ["1.进入订单列表页", "2.选择状态筛选为「已支付」", "3.点击搜索"],
          "expected_result": "列表只显示状态为「已支付」的订单",
          "priority": "P2",
          "module": "订单列表搜索",
          "module_id": "M02",
          "category": "正常流程",
          "confirmation_note": null
        },
        {
          "title": "日期范围超过90天提示错误",
          "preconditions": ["进入订单列表页"],
          "steps": ["1.选择起始日期为2024-01-01", "2.选择结束日期为2024-06-01", "3.点击搜索"],
          "expected_result": "提示「日期范围不能超过90天」",
          "priority": "P2",
          "module": "订单列表搜索",
          "module_id": "M02",
          "category": "边界值与输入校验",
          "confirmation_note": null
        }
      ]
    }
  }
]
```

- [ ] **Step 4: Write `backend/app/prompts/examples/smoke_examples.json`**

```json
[
  {
    "id": "ex-smoke-001",
    "scenario": "用户登录冒烟测试",
    "tags": ["登录", "冒烟", "P0", "P1"],
    "input": {
      "modules": [{"id":"M01","name":"用户登录","description":"手机号验证码登录"}]
    },
    "output": {
      "cases": [
        {
          "title": "正确手机号+验证码登录成功",
          "preconditions": ["已注册手机号", "验证码服务正常"],
          "steps": ["1.打开登录页", "2.输入手机号", "3.输入验证码", "4.点击登录"],
          "expected_result": "登录成功，跳转首页",
          "priority": "P0",
          "module": "用户登录",
          "module_id": "M01",
          "category": "冒烟测试",
          "confirmation_note": null
        },
        {
          "title": "错误验证码登录失败",
          "preconditions": ["已注册手机号"],
          "steps": ["1.输入手机号", "2.输入错误验证码", "3.点击登录"],
          "expected_result": "提示「验证码错误」",
          "priority": "P1",
          "module": "用户登录",
          "module_id": "M01",
          "category": "冒烟测试",
          "confirmation_note": null
        }
      ]
    }
  }
]
```

- [ ] **Step 5: Write `backend/app/prompts/examples/review_examples.json`**

```json
[
  {
    "id": "ex-review-001",
    "scenario": "需求评审 - 用户登录功能",
    "tags": ["登录", "评审", "需求分析"],
    "input": {
      "requirement": "用户可以使用手机号和验证码登录系统"
    },
    "output": {
      "modules": [
        {"id":"M01","name":"用户登录","description":"手机号验证码登录功能","sub_features":["手机号输入","验证码发送","验证码校验","登录状态保持"]}
      ],
      "questions": [
        {"id":"Q-001","type":"边界条件缺失","description":"手机号的格式要求是什么？是否支持境外手机号？","module":"M01","suggestion":"建议明确手机号格式和长度限制"},
        {"id":"Q-002","type":"异常场景遗漏","description":"验证码发送失败时的处理逻辑是什么？","module":"M01","suggestion":"建议补充：发送失败提示 + 重试机制"},
        {"id":"Q-003","type":"交互逻辑不清","description":"验证码有效期内用户关闭页面后重新打开，是否需要重新获取验证码？","module":"M01","suggestion":"建议明确验证码生命周期管理"}
      ],
      "business_rules": ["每个手机号每天最多获取5次验证码", "验证码6位数字，有效期60秒", "同一手机号1分钟内只能获取1次验证码"],
      "data_constraints": [
        {"field":"手机号","type":"string","length":"11","format":"数字","required":true},
        {"field":"验证码","type":"string","length":"6","format":"数字","required":true}
      ]
    }
  }
]
```

- [ ] **Step 6: Verify schemas and examples load**

```bash
cd /Users/linpingyuan/case-agent/backend && .venv/bin/python -c "
import json
from pathlib import Path

base = Path('app/prompts')

# Verify schemas
for s in ['phase1_output.schema.json', 'phase4_output.schema.json']:
    data = json.loads((base / 'schemas' / s).read_text())
    assert '\$schema' in data or True
    print(f'Schema OK: {s}')

# Verify examples
for e in ['detail_examples.json', 'smoke_examples.json', 'review_examples.json']:
    data = json.loads((base / 'examples' / e).read_text())
    assert isinstance(data, list)
    assert len(data) > 0
    print(f'Examples OK: {e} ({len(data)} items)')

print('All schemas and examples OK')
"
```
Expected: `All schemas and examples OK`

- [ ] **Step 7: Commit**

```bash
git add backend/app/prompts/schemas/ backend/app/prompts/examples/
git commit -m "feat: add JSON schemas and few-shot examples for prompt templates

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
"
```

---

### Task 6: Write tests for PromptManager

**Files:**
- Create: `backend/tests/test_prompt_manager.py`

- [ ] **Step 1: Write `backend/tests/test_prompt_manager.py`**

```python
"""Tests for PromptManager."""

import pytest

from app.prompts.manager import PromptManager, get_prompt_manager, reset_prompt_manager


@pytest.fixture(autouse=True)
def _reset_manager() -> None:
    reset_prompt_manager()


def test_manager_loads_template() -> None:
    pm = PromptManager()
    version = pm.get_version("phase4_module_detail")
    assert version == "1.0.0"


def test_manager_lists_templates() -> None:
    pm = PromptManager()
    templates = pm.list_templates()
    names = {t["name"] for t in templates}
    assert "phase4_module_detail" in names
    assert "phase1_requirement_review" in names
    assert "phase3_smoke" in names
    assert "phase5_review" in names
    for t in templates:
        assert "version" in t
        assert "description" in t


def test_render_phase4_default_system_prompt() -> None:
    pm = PromptManager()
    sys_prompt, user_prompt = pm.render(
        "phase4_module_detail",
        {"module_name": "登录模块", "module_id": "M01"},
    )
    assert "资深测试设计专家" in sys_prompt
    assert "穷尽式" in sys_prompt
    assert "等价类划分" in sys_prompt


def test_render_phase4_user_prompt_has_cot() -> None:
    pm = PromptManager()
    _sys, user = pm.render(
        "phase4_module_detail",
        {"module_name": "登录模块", "module_id": "M01", "requirement_context": "测试需求"},
    )
    assert "<thinking>" in user
    assert "</thinking>" in user
    assert "功能理解" in user
    assert "维度映射" in user
    assert "测试点识别" in user
    assert "用例设计" in user
    assert "自检" in user


def test_render_phase4_user_prompt_has_output_instruction() -> None:
    pm = PromptManager()
    _sys, user = pm.render(
        "phase4_module_detail",
        {"module_name": "登录", "module_id": "M01"},
    )
    assert "输出要求" in user
    assert "JSON" in user


def test_render_phase4_model_override() -> None:
    pm = PromptManager()
    sys_default, _ = pm.render(
        "phase4_module_detail",
        {"module_name": "登录", "module_id": "M01"},
        model_provider=None,
    )
    sys_deepseek, _ = pm.render(
        "phase4_module_detail",
        {"module_name": "登录", "module_id": "M01"},
        model_provider="deepseek",
    )
    sys_minimax, _ = pm.render(
        "phase4_module_detail",
        {"module_name": "登录", "module_id": "M01"},
        model_provider="minimax",
    )
    # Default and deepseek are different
    assert sys_default != sys_deepseek
    # Minimax override mentions "只输出 JSON"
    assert "只输出 JSON" in sys_minimax


def test_render_phase1_has_cot() -> None:
    pm = PromptManager()
    _sys, user = pm.render(
        "phase1_requirement_review",
        {"requirement_context": "测试需求"},
    )
    assert "<thinking>" in user
    assert "通读理解" in user
    assert "模块识别" in user
    assert "问题发现" in user


def test_render_phase3_has_cot() -> None:
    pm = PromptManager()
    _sys, user = pm.render(
        "phase3_smoke",
        {"requirement_context": "测试需求"},
    )
    assert "<thinking>" in user
    assert "核心路径识别" in user


def test_render_phase5_has_cot() -> None:
    pm = PromptManager()
    _sys, user = pm.render(
        "phase5_review",
        {"requirement_context": "测试需求"},
    )
    assert "<thinking>" in user
    assert "理解已有覆盖" in user
    assert "逐视角检查" in user


def test_render_phase2_has_cot() -> None:
    pm = PromptManager()
    _sys, user = pm.render(
        "phase2_batch_generation",
        {"requirement_context": "测试需求"},
    )
    assert "<thinking>" in user
    assert "全局分析" in user
    assert "冒烟测试设计" in user
    assert "模块详情设计" in user


def test_render_unknown_template_raises() -> None:
    pm = PromptManager()
    with pytest.raises(FileNotFoundError):
        pm.render("nonexistent_template", {})


def test_get_prompt_manager_singleton() -> None:
    pm1 = get_prompt_manager()
    pm2 = get_prompt_manager()
    assert pm1 is pm2


def test_render_injects_context_variables() -> None:
    pm = PromptManager()
    _sys, user = pm.render(
        "phase4_module_detail",
        {
            "module_name": "自定义模块名",
            "module_id": "M99",
        },
    )
    assert "自定义模块名" in user
    assert "M99" in user
```

- [ ] **Step 2: Run tests, verify 13 pass**

```bash
cd /Users/linpingyuan/case-agent/backend && .venv/bin/python -m pytest tests/test_prompt_manager.py -v
```
Expected: 13 passed

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_prompt_manager.py
git commit -m "test: add PromptManager unit tests (13 cases)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
"
```

---

### Task 7: Integrate PromptManager into TestCaseGenerator

**Files:**
- Modify: `backend/app/services/testcase_generator.py`

This is the core integration step. Replace hardcoded `SYSTEM_PROMPT` usage with `PromptManager.render()` calls in each phase method, while keeping the existing `build_xxx_prompt()` functions as data assembly layer.

- [ ] **Step 1: Add PromptManager import and initialization to TestCaseGenerator**

In `backend/app/services/testcase_generator.py`, replace the existing imports from `testcase_prompt`:

Change lines 90-101:
```python
from app.prompts.testcase_prompt import (
    SYSTEM_PROMPT,
    KnowledgeContextItem,
    build_batch_generation_prompt,
    build_high_coverage_markdown_prompt,
    build_knowledge_context,
    build_module_detail_markdown_prompt,
    build_module_detail_prompt,
    build_requirement_context,
    build_requirement_review_prompt,
    build_review_prompt,
    build_smoke_test_prompt,
)
```

To:
```python
from app.prompts.testcase_prompt import (
    KnowledgeContextItem,
    build_batch_generation_prompt,
    build_high_coverage_markdown_prompt,
    build_knowledge_context,
    build_module_detail_markdown_prompt,
    build_module_detail_prompt,
    build_requirement_context,
    build_requirement_review_prompt,
    build_review_prompt,
    build_smoke_test_prompt,
)
from app.prompts.manager import get_prompt_manager
```

- [ ] **Step 2: Modify `__init__` to store model provider info**

Add to `TestCaseGenerator.__init__` (after line 133 `self.db_session = db_session`):

```python
        self.model_provider = llm_client.profile.provider if llm_client.profile else None
        self._prompt_manager = get_prompt_manager()
```

- [ ] **Step 3: Modify `_phase1_review` to use PromptManager**

Replace lines 300-311 (the `prompt = build_requirement_review_prompt(...)` line and the `create_chat_completion` call):

```python
        knowledge_ctx = self._retrieve_knowledge_context(requirement_text, max_chars=3000)
        prompt = build_requirement_review_prompt(requirement_text, document_contexts, knowledge_context=knowledge_ctx)
        planning_max = profile.max_output_tokens

        t0 = time.monotonic()
        logger.info("[phase1-review] start  max_tokens=%d", planning_max)

        # Use PromptManager for system prompt + CoT user prompt
        sys_prompt, cot_user_prompt = self._prompt_manager.render(
            "phase1_requirement_review",
            {"requirement_context": prompt},
            model_provider=self.model_provider,
        )

        response = self.llm_client.create_chat_completion(
            system_prompt=sys_prompt,
            user_content=cot_user_prompt,
            max_tokens=planning_max,
            response_format={"type": "json_object"},
        )
```

- [ ] **Step 4: Modify `_phase3_smoke` to use PromptManager**

Replace lines 360-374:

```python
        prompt = build_smoke_test_prompt(
            requirement_text, document_contexts, modules_json, business_rules
        )
        profile = self.llm_client.profile
        smoke_max = profile.max_output_tokens

        t0 = time.monotonic()
        logger.info("[phase3-smoke] start  max_tokens=%d", smoke_max)

        # Use PromptManager for system prompt + CoT user prompt
        sys_prompt, cot_user_prompt = self._prompt_manager.render(
            "phase3_smoke",
            {"requirement_context": prompt},
            model_provider=self.model_provider,
        )

        def _do_smoke() -> object:
            return self.llm_client.create_chat_completion(
                system_prompt=sys_prompt,
                user_content=cot_user_prompt,
                max_tokens=smoke_max,
                response_format={"type": "json_object"},
            )
```

- [ ] **Step 5: Modify `_phase4_module_detail` to use PromptManager**

Replace lines 435-458:

```python
        prompt = build_module_detail_prompt(
            requirement_text=requirement_text,
            document_contexts=document_contexts,
            module_id=module.id,
            module_name=module.name,
            sub_features=module.sub_features,
            business_rules=business_rules,
            data_constraints=data_constraints,
            existing_case_titles=existing_titles,
            min_cases=min_cases,
            knowledge_context=knowledge_ctx,
        )
        batch_max = self.llm_client.profile.max_output_tokens

        t0 = time.monotonic()
        logger.info("[phase4-detail] module=%s(%s)  max_tokens=%d  start", module.id, module.name, batch_max)

        # Use PromptManager for system prompt + CoT user prompt
        sys_prompt, cot_user_prompt = self._prompt_manager.render(
            "phase4_module_detail",
            {
                "requirement_context": prompt,
                "module_name": module.name,
                "module_id": module.id,
            },
            model_provider=self.model_provider,
        )

        def _do_phase4() -> object:
            return self.llm_client.create_chat_completion(
                system_prompt=sys_prompt,
                user_content=cot_user_prompt,
                max_tokens=batch_max,
                response_format={"type": "json_object"},
            )
```

- [ ] **Step 6: Modify markdown fallback in `_phase4_module_detail` to use PromptManager**

Replace the fallback section (around line 500-516):

```python
            parser_mode = "markdown-fallback"
            md_prompt = build_module_detail_markdown_prompt(
                requirement_text=requirement_text,
                document_contexts=document_contexts,
                module_id=module.id,
                module_name=module.name,
                sub_features=module.sub_features,
                min_cases=min_cases,
            )
            t1 = time.monotonic()
            logger.info("[phase4-fallback] module=%s  markdown fallback start", module.id)

            # Use PromptManager for system prompt
            sys_prompt, _ = self._prompt_manager.render(
                "phase4_module_detail",
                {
                    "requirement_context": md_prompt,
                    "module_name": module.name,
                    "module_id": module.id,
                },
                model_provider=self.model_provider,
            )

            def _do_fallback() -> object:
                return self.llm_client.create_chat_completion(
                    system_prompt=sys_prompt,
                    user_content=md_prompt,
                    max_tokens=batch_max,
                )
```

- [ ] **Step 7: Modify `_phase5_review` to use PromptManager**

Replace lines 600-613:

```python
        prompt = build_review_prompt(requirement_text, document_contexts, summary)
        profile = self.llm_client.profile
        review_max = profile.max_output_tokens

        t0 = time.monotonic()
        logger.info("[phase5-review] start  existing_cases=%d  max_tokens=%d", len(existing_cases), review_max)

        # Use PromptManager for system prompt + CoT user prompt
        sys_prompt, cot_user_prompt = self._prompt_manager.render(
            "phase5_review",
            {"requirement_context": prompt},
            model_provider=self.model_provider,
        )

        def _do_review() -> object:
            return self.llm_client.create_chat_completion(
                system_prompt=sys_prompt,
                user_content=cot_user_prompt,
                max_tokens=review_max,
                response_format={"type": "json_object"},
            )
```

- [ ] **Step 8: Modify `_phase2_batch` to use PromptManager**

Replace lines 676-697:

```python
        knowledge_ctx = self._retrieve_knowledge_context(requirement_text, max_chars=3000)

        prompt = build_batch_generation_prompt(
            requirement_text=requirement_text,
            document_contexts=document_contexts,
            modules=review.modules,
            business_rules=business_rules,
            data_constraints=data_constraints,
            knowledge_context=knowledge_ctx,
        )

        profile = self.llm_client.profile
        batch_max = profile.max_output_tokens

        t0 = time.monotonic()
        logger.info("[phase2-batch] start  modules=%d  max_tokens=%d", len(review.modules), batch_max)

        # Use PromptManager for system prompt + CoT user prompt
        sys_prompt, cot_user_prompt = self._prompt_manager.render(
            "phase2_batch_generation",
            {"requirement_context": prompt},
            model_provider=self.model_provider,
        )

        def _do_batch() -> object:
            return self.llm_client.create_chat_completion(
                system_prompt=sys_prompt,
                user_content=cot_user_prompt,
                max_tokens=batch_max,
                response_format={"type": "json_object"},
            )
```

- [ ] **Step 9: Verify all existing tests still pass**

```bash
cd /Users/linpingyuan/case-agent/backend && .venv/bin/python -m pytest tests/test_prompt.py tests/test_prompt_manager.py -v
```
Expected: all tests pass (3 from test_prompt.py + 13 from test_prompt_manager.py = 16 passed)

- [ ] **Step 10: Commit**

```bash
git add backend/app/services/testcase_generator.py
git commit -m "refactor: integrate PromptManager into TestCaseGenerator

Replace hardcoded SYSTEM_PROMPT with per-phase YAML templates via
PromptManager.render(). Existing build_xxx_prompt() functions retained
as data assembly layer.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
"
```

---

### Task 8: Write evaluation harness (evaluator.py)

**Files:**
- Create: `backend/app/prompts/evaluator.py`
- Create: `backend/eval/__init__.py` (empty)
- Create: `backend/eval/datasets/login_scenarios.json`
- Create: `backend/eval/datasets/form_scenarios.json`
- Create: `backend/eval/datasets/crud_scenarios.json`

- [ ] **Step 1: Create eval directory and `__init__.py`**

```bash
cd /Users/linpingyuan/case-agent/backend
mkdir -p eval/datasets
touch eval/__init__.py
```

- [ ] **Step 2: Write `backend/app/prompts/evaluator.py`**

```python
"""Evaluation harness for prompt templates.

Usage:
    python -m app.prompts.evaluator --template phase4_module_detail --dataset eval/datasets/login_scenarios.json
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.prompts.manager import get_prompt_manager
from app.services.llm_client import build_llm_client

logger = logging.getLogger(__name__)


@dataclass
class EvalMetrics:
    coverage: float = 0.0
    priority_distribution: dict[str, float] = field(default_factory=dict)
    dedup_score: float = 0.0
    actionability: float = 0.0
    stability: float = 0.0


def compute_coverage(cases: list[dict], must_cover: list[str]) -> float:
    """Check what fraction of must_cover scenarios are present in case titles/steps."""
    if not must_cover:
        return 1.0
    covered = 0
    case_texts = [
        json.dumps(c, ensure_ascii=False).lower() for c in cases
    ]
    for scenario in must_cover:
        scenario_lower = scenario.lower()
        if any(scenario_lower in ct for ct in case_texts):
            covered += 1
    return covered / len(must_cover)


def compute_priority_distribution(cases: list[dict]) -> dict[str, float]:
    """Return priority distribution as fractions."""
    total = len(cases)
    if total == 0:
        return {}
    counts: dict[str, int] = {}
    for c in cases:
        p = c.get("priority", "P2")
        counts[p] = counts.get(p, 0) + 1
    return {k: v / total for k, v in counts.items()}


def compute_dedup_score(cases: list[dict]) -> float:
    """Check how many cases are near-duplicates by title similarity.

    Returns fraction of unique cases (higher is better).
    """
    titles = [c.get("title", "") for c in cases]
    if len(titles) <= 1:
        return 1.0
    duplicates = 0
    for i in range(len(titles)):
        for j in range(i + 1, len(titles)):
            if _jaccard_similarity(titles[i], titles[j]) > 0.7:
                duplicates += 1
                break
    return 1.0 - (duplicates / len(titles))


def compute_actionability(cases: list[dict]) -> float:
    """Check what fraction of cases have actionable steps and verifiable results."""
    if not cases:
        return 0.0
    actionable = 0
    for c in cases:
        steps = c.get("steps", [])
        expected = c.get("expected_result", "")
        if isinstance(steps, list) and len(steps) >= 1 and expected:
            actionable += 1
    return actionable / len(cases)


def _jaccard_similarity(a: str, b: str) -> float:
    a_set = set(a)
    b_set = set(b)
    if not a_set or not b_set:
        return 0.0
    intersection = len(a_set & b_set)
    union = len(a_set | b_set)
    return intersection / union if union > 0 else 0.0


def evaluate(
    template_name: str,
    dataset_path: str,
    model_key: str | None = None,
    stability_runs: int = 3,
) -> dict[str, Any]:
    """Run evaluation for a template against a dataset.

    Returns a dict with metrics and per-scenario results.
    """
    dataset = json.loads(Path(dataset_path).read_text(encoding="utf-8"))
    if not isinstance(dataset, list):
        dataset = [dataset]

    client = build_llm_client(model_key)
    pm = get_prompt_manager()
    all_metrics: list[dict] = []

    for scenario in dataset:
        scenario_id = scenario.get("id", "unknown")
        must_cover = scenario.get("must_cover", [])
        module = scenario.get("module", {})

        context = {
            "requirement_context": scenario.get("requirement", ""),
            "module_name": module.get("name", ""),
            "module_id": module.get("id", "M01"),
            "business_rules": "\n".join(f"- {r}" for r in scenario.get("rules", [])),
            "data_constraints": json.dumps(scenario.get("constraints", []), ensure_ascii=False),
        }

        sys_prompt, user_prompt = pm.render(template_name, context)

        # Stability: run N times and compare
        all_cases: list[list[dict]] = []
        for run_idx in range(stability_runs):
            try:
                response = client.create_chat_completion(
                    system_prompt=sys_prompt,
                    user_content=user_prompt,
                    response_format={"type": "json_object"},
                )
                parsed = _parse_cases(response.content)
                all_cases.append(parsed)
            except Exception as exc:
                logger.warning("[eval] run %d failed: %s", run_idx, exc)
                all_cases.append([])

        # Use first run for single-run metrics
        first_run_cases = all_cases[0] if all_cases else []

        metrics = EvalMetrics(
            coverage=compute_coverage(first_run_cases, must_cover),
            priority_distribution=compute_priority_distribution(first_run_cases),
            dedup_score=compute_dedup_score(first_run_cases),
            actionability=compute_actionability(first_run_cases),
            stability=_compute_stability(all_cases),
        )

        all_metrics.append({
            "scenario_id": scenario_id,
            "case_count": len(first_run_cases),
            "coverage": metrics.coverage,
            "priority_distribution": metrics.priority_distribution,
            "dedup_score": metrics.dedup_score,
            "actionability": metrics.actionability,
            "stability": metrics.stability,
        })

        logger.info(
            "[eval] %s: cases=%d cov=%.2f action=%.2f stab=%.2f",
            scenario_id, len(first_run_cases),
            metrics.coverage, metrics.actionability, metrics.stability,
        )

    # Aggregate
    n = len(all_metrics)
    return {
        "template": template_name,
        "dataset": dataset_path,
        "scenarios": n,
        "aggregate": {
            "coverage": sum(m["coverage"] for m in all_metrics) / n if n else 0,
            "actionability": sum(m["actionability"] for m in all_metrics) / n if n else 0,
            "stability": sum(m["stability"] for m in all_metrics) / n if n else 0,
            "dedup_score": sum(m["dedup_score"] for m in all_metrics) / n if n else 0,
            "avg_cases": sum(m["case_count"] for m in all_metrics) / n if n else 0,
        },
        "details": all_metrics,
    }


def _parse_cases(content: str) -> list[dict]:
    """Parse test cases from LLM response content."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # Try stripping markdown fence
        stripped = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            return []

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("cases", "smoke_cases", "module_cases", "review_cases", "supplement_cases"):
            if key in data and isinstance(data[key], list):
                return data[key]
        if "Cases" in data:
            return data.get("Cases", [])
    return []


def _compute_stability(all_cases: list[list[dict]]) -> float:
    """Compute average pairwise Jaccard similarity of case title sets across runs."""
    valid = [c for c in all_cases if c]
    if len(valid) < 2:
        return 0.0

    def title_set(cases: list[dict]) -> set[str]:
        return {c.get("title", "") for c in cases}

    similarities: list[float] = []
    for i in range(len(valid)):
        for j in range(i + 1, len(valid)):
            a = title_set(valid[i])
            b = title_set(valid[j])
            if not a or not b:
                continue
            sim = len(a & b) / len(a | b)
            similarities.append(sim)

    return sum(similarities) / len(similarities) if similarities else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a prompt template")
    parser.add_argument("--template", required=True, help="Template name (e.g. phase4_module_detail)")
    parser.add_argument("--dataset", required=True, help="Path to eval dataset JSON")
    parser.add_argument("--model", default=None, help="Model key override")
    parser.add_argument("--stability-runs", type=int, default=3, help="Number of runs for stability check")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    result = evaluate(
        template_name=args.template,
        dataset_path=args.dataset,
        model_key=args.model,
        stability_runs=args.stability_runs,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        agg = result["aggregate"]
        print(f"\nTemplate: {result['template']}")
        print(f"Dataset:  {result['dataset']}")
        print(f"Scenarios: {result['scenarios']}")
        print(f"\nAggregate Metrics:")
        print(f"  Coverage:      {agg['coverage']:.2%}")
        print(f"  Actionability: {agg['actionability']:.2%}")
        print(f"  Stability:     {agg['stability']:.2%}")
        print(f"  Dedup Score:   {agg['dedup_score']:.2%}")
        print(f"  Avg Cases:     {agg['avg_cases']:.1f}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Write `backend/eval/datasets/login_scenarios.json`**

```json
[
  {
    "id": "login-001",
    "requirement": "用户可以使用手机号和验证码登录系统。登录成功后跳转到首页。如果用户未注册则提示先注册。验证码6位数字，有效期60秒。同一手机号每天最多获取5次验证码。",
    "module": {"name": "用户登录", "id": "M01", "sub_features": ["手机号输入", "验证码发送", "验证码校验", "登录跳转"]},
    "rules": ["验证码6位数字60秒有效", "每天最多5次验证码"],
    "constraints": [
      {"field": "手机号", "type": "string", "length": "11", "format": "数字", "required": true},
      {"field": "验证码", "type": "string", "length": "6", "format": "数字", "required": true}
    ],
    "must_cover": ["正常登录", "验证码错误", "手机号格式错误", "未注册手机号", "验证码过期"],
    "expected_min_cases": 12,
    "quality_checks": ["priority_distribution", "no_duplicates", "actionable_steps"]
  }
]
```

- [ ] **Step 4: Write `backend/eval/datasets/form_scenarios.json`**

```json
[
  {
    "id": "form-001",
    "requirement": "用户提交反馈表单，包含：反馈类型（建议/投诉/咨询）、反馈标题（最多50字）、反馈内容（最多500字）、联系方式（选填，手机号或邮箱）。提交成功后显示「感谢反馈」并清空表单。",
    "module": {"name": "用户反馈", "id": "M01", "sub_features": ["反馈类型选择", "标题输入", "内容输入", "联系方式输入", "表单提交"]},
    "rules": ["标题最多50字", "内容最多500字", "联系方式为选填", "手机号格式校验", "邮箱格式校验"],
    "constraints": [
      {"field": "反馈类型", "type": "enum", "length": "建议/投诉/咨询", "format": "单选", "required": true},
      {"field": "反馈标题", "type": "string", "length": "1-50", "format": "文本", "required": true},
      {"field": "反馈内容", "type": "string", "length": "1-500", "format": "文本", "required": true},
      {"field": "联系方式", "type": "string", "length": "0-50", "format": "手机号或邮箱", "required": false}
    ],
    "must_cover": ["正常提交反馈", "标题超长", "内容超长", "空标题提交", "空内容提交", "无效手机号", "无效邮箱", "提交成功清空表单"],
    "expected_min_cases": 12,
    "quality_checks": ["priority_distribution", "no_duplicates", "actionable_steps"]
  }
]
```

- [ ] **Step 5: Write `backend/eval/datasets/crud_scenarios.json`**

```json
[
  {
    "id": "crud-001",
    "requirement": "管理员可以管理商品分类：查看分类列表（树形结构）、新增分类（名称、父分类、排序号）、编辑分类、删除分类。删除前需确认该分类下无商品，如有商品则提示「该分类下有N个商品，无法删除」。",
    "module": {"name": "商品分类管理", "id": "M01", "sub_features": ["分类列表", "新增分类", "编辑分类", "删除分类"]},
    "rules": ["分类名为必填，2-20字", "排序号为正整数", "父分类可选", "有商品的分类不可删除", "删除需二次确认"],
    "constraints": [
      {"field": "分类名称", "type": "string", "length": "2-20", "format": "文本", "required": true},
      {"field": "父分类", "type": "select", "length": "-", "format": "分类树选择", "required": false},
      {"field": "排序号", "type": "integer", "length": "1-999", "format": "数字", "required": true}
    ],
    "must_cover": ["查看分类列表", "新增一级分类", "新增子分类", "分类名称为空", "分类名称超长", "编辑分类", "删除无商品分类", "删除有商品分类提示", "取消删除"],
    "expected_min_cases": 12,
    "quality_checks": ["priority_distribution", "no_duplicates", "actionable_steps"]
  }
]
```

- [ ] **Step 6: Verify evaluator imports and datasets load**

```bash
cd /Users/linpingyuan/case-agent/backend && .venv/bin/python -c "
from app.prompts.evaluator import evaluate, compute_coverage, compute_actionability, compute_dedup_score, compute_priority_distribution

# Test with static data (no LLM call)
cases = [
    {'title': '正常登录', 'steps': ['1.输入手机号', '2.点击登录'], 'expected_result': '登录成功', 'priority': 'P2'},
    {'title': '密码错误', 'steps': ['1.输入错误密码'], 'expected_result': '提示错误', 'priority': 'P2'},
    {'title': '空输入', 'steps': ['1.不输入', '2.点击登录'], 'expected_result': '提示必填', 'priority': 'P2'},
]
cov = compute_coverage(cases, ['正常登录', '密码错误', '空输入'])
assert cov == 1.0, f'Expected 1.0 got {cov}'

act = compute_actionability(cases)
assert act == 1.0, f'Expected 1.0 got {act}'

dedup = compute_dedup_score(cases)
assert dedup == 1.0, f'Expected 1.0 got {dedup}'

dist = compute_priority_distribution(cases)
assert dist.get('P2') == 1.0

print('All metric functions OK')
"
```
Expected: `All metric functions OK`

- [ ] **Step 7: Commit**

```bash
git add backend/app/prompts/evaluator.py backend/eval/
git commit -m "feat: add evaluation harness with 5 metrics and 3 eval datasets

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
"
```

---

### Task 9: Final verification — run all tests

**Files:** none (verification only)

- [ ] **Step 1: Run all prompt-related tests**

```bash
cd /Users/linpingyuan/case-agent/backend && .venv/bin/python -m pytest tests/test_prompt.py tests/test_prompt_manager.py -v
```
Expected: 16 passed (3 + 13)

- [ ] **Step 2: Verify PromptManager renders all templates without error**

```bash
cd /Users/linpingyuan/case-agent/backend && .venv/bin/python -c "
from app.prompts.manager import get_prompt_manager
pm = get_prompt_manager()
for name in [t['name'] for t in pm.list_templates()]:
    sys_p, user_p = pm.render(name, {'requirement_context': 'test', 'module_name': 'Test', 'module_id': 'M01'})
    print(f'  {name}: sys={len(sys_p)} chars, user={len(user_p)} chars')
print('All templates render OK')
"
```
Expected: all 5 templates render with system prompt > 0 and user prompt > 0.

- [ ] **Step 3: Verify no import errors from the modified testcase_generator**

```bash
cd /Users/linpingyuan/case-agent/backend && .venv/bin/python -c "
from app.services.testcase_generator import TestCaseGenerator
from app.services.llm_client import build_llm_client
print('All imports OK')
"
```
Expected: `All imports OK`

- [ ] **Step 4: Commit verification results (if any changes)**

```bash
git status
```

---

### Summary of changes

| File | Action |
|------|--------|
| `backend/app/prompts/__init__.py` | Create |
| `backend/app/prompts/manager.py` | Create (~200 lines) |
| `backend/app/prompts/evaluator.py` | Create (~220 lines) |
| `backend/app/prompts/templates/phase1_requirement_review.yaml` | Create |
| `backend/app/prompts/templates/phase2_batch_generation.yaml` | Create |
| `backend/app/prompts/templates/phase3_smoke.yaml` | Create |
| `backend/app/prompts/templates/phase4_module_detail.yaml` | Create |
| `backend/app/prompts/templates/phase5_review.yaml` | Create |
| `backend/app/prompts/schemas/phase1_output.schema.json` | Create |
| `backend/app/prompts/schemas/phase4_output.schema.json` | Create |
| `backend/app/prompts/examples/review_examples.json` | Create |
| `backend/app/prompts/examples/smoke_examples.json` | Create |
| `backend/app/prompts/examples/detail_examples.json` | Create |
| `backend/eval/__init__.py` | Create |
| `backend/eval/datasets/login_scenarios.json` | Create |
| `backend/eval/datasets/form_scenarios.json` | Create |
| `backend/eval/datasets/crud_scenarios.json` | Create |
| `backend/tests/test_prompt_manager.py` | Create (13 test cases) |
| `backend/app/services/testcase_generator.py` | Modify (6 phase methods) |
| `backend/app/prompts/testcase_prompt.py` | Unchanged (implicit deprecation of SYSTEM_PROMPT) |
