from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from app.schemas.testcase import GenerationMetadata, ReviewQuestion, TestCaseItem

logger = logging.getLogger(__name__)


@dataclass
class PlannedModule:
    id: str
    name: str
    description: str
    sub_features: list[str] = field(default_factory=list)


@dataclass
class ReviewResult:
    modules: list[PlannedModule] = field(default_factory=list)
    questions: list[ReviewQuestion] = field(default_factory=list)
    business_rules: list[str] = field(default_factory=list)
    data_constraints: list[dict[str, object]] = field(default_factory=list)


@dataclass
class RequirementSummaryResult:
    summary_text: str = ""
    modules: list[str] = field(default_factory=list)
    business_rules: list[str] = field(default_factory=list)
    data_constraints: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)


# Keep for backward compatibility with old snapshots
@dataclass
class PlannedCategory:
    name: str
    focus: str
    min_cases: int = 10
    key_points: Optional[list[str]] = None


def _strip_code_fence(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return stripped


_BRACKET_PAIRS = {"}": "{", "]": "["}


def _find_first_json_object(text: str) -> str | None:
    """Extract the first complete JSON object/array from text (ignoring trailing garbage)."""
    depth = 0
    in_string = False
    escape_next = False
    start_idx = -1

    for i, ch in enumerate(text):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\":
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in ("{", "["):
            if depth == 0:
                start_idx = i
            depth += 1
        elif ch in ("}", "]"):
            depth -= 1
            if depth == 0 and start_idx != -1:
                return text[start_idx : i + 1]

    return None


def _extract_json_text(content: str) -> str:
    stripped = _strip_code_fence(content)

    # Try the classic brace-pair approach first
    for opening, closing in (("{", "}"), ("[", "]")):
        start = stripped.find(opening)
        end = stripped.rfind(closing)
        if start != -1 and end != -1 and end > start:
            candidate = stripped[start : end + 1]
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                pass

    # Fall back to finding the first complete object via bracket matching
    first = _find_first_json_object(stripped)
    if first is not None:
        return first

    return stripped


def _as_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [line.strip("- ").strip() for line in value.splitlines() if line.strip()]
    return []


# ---------------------------------------------------------------------------
# Phase 1: Parse Requirements Review Response
# ---------------------------------------------------------------------------


def parse_review_response(content: str) -> ReviewResult:
    try:
        payload = json.loads(_extract_json_text(content))
    except json.JSONDecodeError:
        return ReviewResult()

    modules: list[PlannedModule] = []
    for item in payload.get("modules", []):
        if not isinstance(item, dict):
            continue
        mod_id = str(item.get("id", "")).strip()
        mod_name = str(item.get("name", "")).strip()
        if not mod_name:
            continue
        modules.append(
            PlannedModule(
                id=mod_id or f"M{len(modules) + 1:02d}",
                name=mod_name,
                description=str(item.get("description", "")).strip(),
                sub_features=_as_list(item.get("sub_features")),
            )
        )

    questions: list[ReviewQuestion] = []
    for item in payload.get("questions", []):
        if not isinstance(item, dict):
            continue
        q_desc = str(item.get("description", "")).strip()
        if not q_desc:
            continue
        questions.append(
            ReviewQuestion(
                id=str(item.get("id", f"Q-{len(questions) + 1:03d}")).strip(),
                questionType=str(item.get("type", "未分类")).strip(),
                description=q_desc,
                module=str(item.get("module", "")).strip(),
                suggestion=str(item.get("suggestion", "")).strip(),
            )
        )

    business_rules = _as_list(payload.get("business_rules"))
    raw_constraints = payload.get("data_constraints", [])
    data_constraints = raw_constraints if isinstance(raw_constraints, list) else []

    return ReviewResult(
        modules=modules,
        questions=questions,
        business_rules=business_rules,
        data_constraints=data_constraints,
    )


def _log_parse_failure(context: str, raw_content: str, exc: Exception) -> None:
    preview = raw_content[:500].replace("\n", " ")
    logger.warning(
        "[parser] %s JSON decode failed: %s | preview: %s",
        context,
        exc,
        preview,
    )


def _extract_json_string_field(raw: str, keys: tuple[str, ...]) -> Optional[str]:
    """在整段（可能不合法的）JSON 文本中，按 JSON 字符串规则解析某键的值。

    解决：兜底正则 `[^"\']+` 会在 summary 正文里出现英文双引号（如 将\"爆款复刻\"改为）时提前截断。
    """
    dec = json.JSONDecoder()
    for key in keys:
        m = re.search(rf'"{re.escape(key)}"\s*:\s*', raw)
        if not m:
            continue
        idx = m.end()
        while idx < len(raw) and raw[idx] in " \t\r\n":
            idx += 1
        if idx >= len(raw) or raw[idx] != '"':
            continue
        try:
            val, _end = dec.raw_decode(raw, idx)
        except json.JSONDecodeError:
            continue
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def _try_extract_fields_from_raw_text(raw: str) -> dict[str, object]:
    """从非 JSON 原始文本中尝试正则提取已知字段，作为解析失败的兜底。"""
    result: dict[str, object] = {}
    # summary_text：必须用 JSON 字符串语义解析，禁止用 [^"\']+（正文里常有 \"爆款复刻\" 等）
    st = _extract_json_string_field(raw, ("summary_text", "summaryText"))
    if st:
        result["summary_text"] = st
    # 匹配 modules / business_rules / data_constraints / open_questions 数组
    for key in ("modules", "business_rules", "data_constraints", "open_questions"):
        pattern = r'["\']?(%s|openQuestions|open_questions|summaryText)["\']?\s*:\s*\[(.*?)\]' % (
            key.replace("_", r"[_\s]?")
        )
        m = re.search(pattern, raw, re.IGNORECASE | re.DOTALL)
        if m:
            items = [s.strip().strip(",").strip('"').strip("'") for s in m.group(2).split("\n") if s.strip()]
            if items:
                result[key] = items
    return result


def parse_requirement_summary_response(content: str) -> RequirementSummaryResult:
    try:
        payload = json.loads(_extract_json_text(content))
    except json.JSONDecodeError as exc:
        _log_parse_failure("requirement_summary", content, exc)
        # 兜底：尝试从原始文本中用正则提取字段
        extracted = _try_extract_fields_from_raw_text(content)
        if extracted:
            logger.info("[parser] requirement_summary fallback extraction succeeded: %s", list(extracted.keys()))
        fallback_result = RequirementSummaryResult(
            summary_text=str(extracted.get("summary_text", "")).strip(),
            modules=_as_list(extracted.get("modules")),
            business_rules=_as_list(extracted.get("business_rules")),
            data_constraints=_as_list(extracted.get("data_constraints")),
            open_questions=_as_list(extracted.get("open_questions")),
        )
        # 如果兜底也没提取到任何实质内容，返回空让其调用方感知
        if not any([fallback_result.summary_text, fallback_result.modules,
                    fallback_result.business_rules, fallback_result.data_constraints,
                    fallback_result.open_questions]):
            return RequirementSummaryResult()
        return fallback_result

    summary_text = str(payload.get("summary_text") or payload.get("summaryText") or "").strip()
    modules = _as_list(payload.get("modules"))
    business_rules = _as_list(payload.get("business_rules") or payload.get("businessRules"))
    data_constraints = _as_list(payload.get("data_constraints") or payload.get("dataConstraints"))
    open_questions = _as_list(payload.get("open_questions") or payload.get("openQuestions"))

    return RequirementSummaryResult(
        summary_text=summary_text,
        modules=modules,
        business_rules=business_rules,
        data_constraints=data_constraints,
        open_questions=open_questions,
    )


# ---------------------------------------------------------------------------
# Parse cases response (unified for smoke/module-detail/review)
# ---------------------------------------------------------------------------


def parse_cases_response(
    content: str,
    default_category: str,
    default_module: str = "",
    default_priority: str = "P2",
) -> list[TestCaseItem]:
    payload = json.loads(_extract_json_text(content))
    raw_cases = (
        payload
        if isinstance(payload, list)
        else payload.get("cases", payload.get("supplement_cases", []))
    )

    cases: list[TestCaseItem] = []
    for item in raw_cases:
        if not isinstance(item, dict):
            continue

        summary = str(item.get("summary") or "").strip()
        if not summary:
            continue

        priority = str(item.get("priority", default_priority)).strip()
        if priority not in ("P0", "P1", "P2", "P3"):
            priority = default_priority

        module = str(item.get("module") or default_module).strip()
        category = str(item.get("category") or default_category).strip() or default_category

        raw_note = item.get("confirmation_note") or item.get("confirmationNote")
        confirmation_note = str(raw_note).strip() if raw_note else None

        cases.append(
            TestCaseItem(
                summary=summary,
                priority=priority,
                module=module,
                category=category,
                confirmationNote=confirmation_note,
            )
        )

    return cases


# ---------------------------------------------------------------------------
# Parse Markdown Table (fallback)
# ---------------------------------------------------------------------------


def parse_markdown_table(markdown: str) -> list[TestCaseItem]:
    return []


# ---------------------------------------------------------------------------
# Legacy: parse planning response (backward compat for old snapshots)
# ---------------------------------------------------------------------------


def parse_planning_response(
    content: str, fallback_categories: list[str]
) -> list[PlannedCategory]:
    try:
        payload = json.loads(_extract_json_text(content))
    except json.JSONDecodeError:
        return [PlannedCategory(name=name, focus=name, min_cases=10) for name in fallback_categories]

    raw_categories = payload.get("categories", [])
    planned: list[PlannedCategory] = []
    for item in raw_categories:
        if isinstance(item, str) and item.strip():
            planned.append(PlannedCategory(name=item.strip(), focus=item.strip(), min_cases=10))
        elif isinstance(item, dict):
            name = str(item.get("name", "")).strip()
            focus = str(item.get("focus", "")).strip() or name
            min_cases = int(item.get("min_cases", 10))
            raw_kp = item.get("key_points")
            key_points = (
                [str(kp).strip() for kp in raw_kp if str(kp).strip()]
                if isinstance(raw_kp, list)
                else None
            )
            if name:
                planned.append(
                    PlannedCategory(
                        name=name,
                        focus=focus,
                        min_cases=max(min_cases, 5),
                        key_points=key_points,
                    )
                )

    return planned or [
        PlannedCategory(name=name, focus=name, min_cases=10) for name in fallback_categories
    ]


def parse_batch_cases_response(
    content: str,
) -> tuple[list[TestCaseItem], list[TestCaseItem], list[TestCaseItem]]:
    """解析批量生成响应，返回 (smoke_cases, module_cases, review_cases) 三元组。

    适用于两阶段模式中的 Phase2 批量生成。
    """
    payload = json.loads(_extract_json_text(content))

    smoke_cases: list[TestCaseItem] = []
    module_cases: list[TestCaseItem] = []
    review_cases: list[TestCaseItem] = []

    raw_smoke = payload.get("smoke_cases", [])
    if isinstance(raw_smoke, list):
        for item in raw_smoke:
            if not isinstance(item, dict):
                continue
            summary = str(item.get("summary") or "").strip()
            if not summary:
                continue

            priority = str(item.get("priority", "P0")).strip()
            if priority not in ("P0", "P1", "P2", "P3"):
                priority = "P0"
            module = str(item.get("module") or "").strip()
            category = str(item.get("category") or "冒烟测试").strip() or "冒烟测试"
            raw_note = item.get("confirmation_note") or item.get("confirmationNote")
            confirmation_note = str(raw_note).strip() if raw_note else None

            smoke_cases.append(
                TestCaseItem(
                    summary=summary,
                    priority=priority,
                    module=module,
                    category=category,
                    confirmationNote=confirmation_note,
                )
            )

    raw_module = payload.get("module_cases", [])
    if isinstance(raw_module, list):
        for item in raw_module:
            if not isinstance(item, dict):
                continue
            summary = str(item.get("summary") or "").strip()
            if not summary:
                continue

            priority = str(item.get("priority", "P2")).strip()
            if priority not in ("P0", "P1", "P2", "P3"):
                priority = "P2"
            module = str(item.get("module") or "").strip()
            category = str(item.get("category") or "正常流程").strip() or "正常流程"
            raw_note = item.get("confirmation_note") or item.get("confirmationNote")
            confirmation_note = str(raw_note).strip() if raw_note else None

            module_cases.append(
                TestCaseItem(
                    summary=summary,
                    priority=priority,
                    module=module,
                    category=category,
                    confirmationNote=confirmation_note,
                )
            )

    raw_review = payload.get("review_cases", [])
    if isinstance(raw_review, list):
        for item in raw_review:
            if not isinstance(item, dict):
                continue
            summary = str(item.get("summary") or "").strip()
            if not summary:
                continue

            priority = str(item.get("priority", "P2")).strip()
            if priority not in ("P0", "P1", "P2", "P3"):
                priority = "P2"
            module = str(item.get("module") or "").strip()
            category = "评审补充"
            raw_note = item.get("confirmation_note") or item.get("confirmationNote")
            confirmation_note = str(raw_note).strip() if raw_note else None

            review_cases.append(
                TestCaseItem(
                    summary=summary,
                    priority=priority,
                    module=module,
                    category=category,
                    confirmationNote=confirmation_note,
                )
            )

    return smoke_cases, module_cases, review_cases


# ---------------------------------------------------------------------------
# Load saved generation snapshot (for export)
# ---------------------------------------------------------------------------


def load_generation_snapshot(
    raw_response: Optional[str], markdown: str
) -> tuple[list[TestCaseItem], GenerationMetadata]:
    if raw_response:
        try:
            payload = json.loads(raw_response)
            raw_cases = payload.get("cases")
            raw_metadata = payload.get("metadata")
            if isinstance(raw_cases, list) and isinstance(raw_metadata, dict):
                validated_cases = []
                for case in raw_cases:
                    try:
                        validated_cases.append(TestCaseItem.model_validate(case))
                    except Exception:
                        pass
                if validated_cases:
                    try:
                        return (
                            validated_cases,
                            GenerationMetadata.model_validate(raw_metadata),
                        )
                    except Exception:
                        pass
        except Exception:
            pass

    fallback_cases = parse_markdown_table(markdown)
    category_counts: dict[str, int] = {}
    module_counts: dict[str, int] = {}
    priority_counts: dict[str, int] = {}
    for case in fallback_cases:
        cat = case.category or "未分类"
        category_counts[cat] = category_counts.get(cat, 0) + 1
        if case.module:
            module_counts[case.module] = module_counts.get(case.module, 0) + 1
        pri = case.priority or "P2"
        priority_counts[pri] = priority_counts.get(pri, 0) + 1

    return (
        fallback_cases,
        GenerationMetadata(
            caseCount=len(fallback_cases),
            categoryCounts=category_counts,
            moduleCounts=module_counts,
            priorityCounts=priority_counts,
            warnings=[],
            truncated=False,
            incompleteCategories=[],
        ),
    )
