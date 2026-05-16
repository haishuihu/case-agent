"""PromptManager: loads YAML templates, renders system/user prompts per phase."""

from __future__ import annotations

import json
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
        """Build the task description + data context section."""
        ctx_block = tmpl.get("task_context_template")
        if ctx_block:
            try:
                return ctx_block.format(**context)
            except KeyError as e:
                logger.warning("task_context_template references missing key: %s", e)
                # fall through to generic rendering
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
                    ex_data = json.loads(ex_path.read_text(encoding="utf-8"))
                    if isinstance(ex_data, list):
                        for item in ex_data[:2]:
                            lines.append(self._format_one_example(item))
                    elif isinstance(ex_data, dict):
                        lines.append(self._format_one_example(ex_data))
            elif isinstance(ex, dict):
                lines.append(self._format_one_example(ex))
        if len(examples) > 2:
            logger.debug("few_shot_examples has %d entries, only using first 2", len(examples))
        return "\n".join(lines) if len(lines) > 2 else ""

    @staticmethod
    def _format_one_example(ex: dict[str, Any]) -> str:
        parts = [f"\n### 示例: {ex.get('scenario', '示例')}"]
        inp = ex.get("input", {})
        if inp:
            parts.append("**输入**:")
            parts.append("```json")
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
        """Build the output format instruction."""
        fmt = tmpl.get("output_format")
        if fmt:
            try:
                return fmt.format(**context)
            except KeyError as e:
                logger.warning("output_format references missing key: %s", e)
                # fall through to generic JSON instruction

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
