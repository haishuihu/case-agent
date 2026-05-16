from __future__ import annotations

import json
import logging
import re

from app.schemas.testcase import TestCaseItem
from app.services.llm_client import build_llm_client

logger = logging.getLogger(__name__)

CONVERT_PROMPT = """你是一个测试自动化工程师。请将以下自然语言描述的测试用例转换为结构化的 UI 自动化测试步骤。

对于每个用例，分析其步骤和预期结果，生成：
1. `ui_action_steps`: 一个步骤数组，每个步骤包含：
   - `action`: 动作类型 (navigate/fill/click/check/select/hover/wait/assert/scrolling)
   - `selector`: CSS 选择器或 XPath (根据元素描述推断，如"登录按钮"→"button:has-text('登录')", "用户名输入框"→"input[name='username']")
   - `value`: 输入值 (仅 fill/select 需要)
   - `description`: 该步骤的中文描述
2. `ui_expected`: 预期结果描述

## 推断选择器规则
- 按钮文字 → `button:has-text('X')` 或 `[data-testid='X-btn']`
- 输入框 → 根据标签推断 name 属性，如"用户名"→`input[name='username']`
- 链接 → `a:has-text('X')`
- 表单区域 → `.form-X` 或 `#X-form`
- 页面区域 → 用语义化选择器如 `.header`、`.sidebar`、`.content`
- 优先使用 data-testid、aria-label、placeholder 等属性

## 示例

输入:
{
  "title": "用户登录",
  "steps": ["打开登录页面", "输入用户名 test@example.com", "输入密码 123456", "点击登录按钮"],
  "expectedResult": "页面跳转到首页，显示用户昵称"
}

输出:
{
  "case_type": "ui",
  "ui_selector": "button:has-text('登录')",
  "ui_action": "click",
  "ui_expected": "跳转到首页，显示用户昵称",
  "ui_action_steps": [
    {"action": "navigate", "selector": "/login", "value": null, "description": "打开登录页面"},
    {"action": "fill", "selector": "input[name='username']", "value": "test@example.com", "description": "输入用户名 test@example.com"},
    {"action": "fill", "selector": "input[name='password']", "value": "123456", "description": "输入密码 123456"},
    {"action": "click", "selector": "button:has-text('登录')", "value": null, "description": "点击登录按钮"},
    {"action": "assert", "selector": ".user-nickname", "value": null, "description": "验证显示用户昵称"}
  ]
}

现在请转换以下用例，只返回 JSON 数组，不要包含 markdown 代码块:
"""


def convert_cases_to_ui(cases: list[TestCaseItem], model_key: str | None = None) -> list[dict]:
    """将自然语言用例转换为 UI 自动化用例结构。

    返回 list[dict]，每个 dict 包含 case_type, ui_selector, ui_action, ui_expected, ui_action_steps。
    """
    if not cases:
        return []

    case_texts = []
    for c in cases:
        case_texts.append(json.dumps({
            "title": c.title,
            "steps": c.steps,
            "expectedResult": c.expectedResult,
        }, ensure_ascii=False))

    user_content = "[\n" + ",\n".join(case_texts) + "\n]"

    try:
        client = build_llm_client(model_key)
        result = client.create_chat_completion(
            system_prompt=CONVERT_PROMPT,
            user_content=user_content,
        )

        content = result.content.strip()
        # Remove markdown code fences if present
        content = re.sub(r'^```(?:json)?\s*', '', content)
        content = re.sub(r'\s*```$', '', content)

        return json.loads(content)
    except Exception:
        logger.exception("Failed to convert cases to UI format")
        raise


def build_case_from_ui_step(converted: dict, suite_id: str, original: TestCaseItem, base_url: str | None = None) -> dict:
    """将 AI 转换结果 + 原始用例合并为创建 TestCase 的 dict。"""
    return {
        "suite_id": suite_id,
        "title": original.title,
        "description": original.expectedResult,
        "case_type": "ui",
        "priority": _priority_to_int(original.priority),
        "ui_selector": converted.get("ui_selector", ""),
        "ui_action": converted.get("ui_action", "click"),
        "ui_expected": converted.get("ui_expected", original.expectedResult),
        "tags": [original.module, original.category],
        "test_data": {
            "original_case_id": original.caseId,
            "preconditions": original.preconditions,
            "original_steps": original.steps,
            "base_url": base_url,
            "ui_steps": converted.get("ui_action_steps", []),
        },
        "extra_metadata": {
            "source": "ai_conversion",
            "source_module": original.module,
            "source_category": original.category,
            "base_url": base_url,
        },
    }


def _priority_to_int(priority: str) -> int:
    mapping = {"P0": 5, "P1": 4, "P2": 3, "P3": 2}
    return mapping.get(priority, 3)
