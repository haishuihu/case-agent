"""极简用例模式 Prompt 模板 - Sprint 4"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.services.file_parser import DocumentContext, ImageContext

SYSTEM_PROMPT_QUICK = """你是一个资深测试工程师，需要快速从需求描述中提炼出测试要点。
输出格式要求：精简、实用、可直接用于自测或评审。

## 输出规范
1. 使用 Bullet Point 格式，每条不超过 30 字
2. 按以下四个维度组织：核心流程、边界条件、异常场景、关键检查
3. 高风险项用 ⚠️ 标记，并简要说明风险原因
4. 禁止输出完整用例格式（步骤/预期结果表格），只输出要点

## 输出格式模板
### 核心流程
- ✅ [场景] → [预期]

### 边界条件
- [边界值场景]

### 异常场景
- ❌ [异常场景] → [处理结果]

### 关键检查
⚠️ [高风险检查项]: [风险原因]
"""

def build_quick_prompt(
    requirement_text: str,
    document_contexts: Optional[list["DocumentContext"]] = None,
    image_contexts: Optional[list["ImageContext"]] = None,
) -> str:
    """构建极简模式的 prompt，可选附加文档/图片上下文"""
    refs_parts: list[str] = []
    if document_contexts:
        for i, doc in enumerate(document_contexts, 1):
            if doc.extracted_text.strip():
                refs_parts.append(f"【文档{i}】{doc.extracted_text[:4000]}")
    if image_contexts:
        for i, img in enumerate(image_contexts, 1):
            if img.extracted_text.strip():
                refs_parts.append(f"【图片{i}描述】{img.extracted_text}")

    body = f"""## 任务
分析以下需求，快速输出测试要点。

## 需求
{requirement_text}"""
    if refs_parts:
        body += "\n\n## 参考材料\n" + "\n\n".join(refs_parts)

    body += """

## 要求
1. 输出格式：Bullet Point（精简要点，非完整用例）
2. 覆盖：核心流程、边界条件、异常场景、关键检查
3. 高风险项用 ⚠️ 标记
4. 每条要点不超过 30 字
5. 优先关注：用户最常走的路径、容易出错的地方、与现有系统交互的地方

## 输出
"""
    return body
