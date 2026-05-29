from __future__ import annotations

import csv
import re
from datetime import date
from functools import partial
from io import BytesIO, StringIO
from typing import List, Optional, Tuple
from urllib.parse import quote

from openpyxl import Workbook

from app.schemas.testcase import GenerationMetadata, TestCaseItem

HEADER_COLUMNS = ["优先级", "模块", "分类", "测试标题", "测试摘要"]


def _escape_markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")


def _extract_title(summary: str) -> str:
    """Extract title part before '：' in summary."""
    if "：" in summary:
        return summary.split("：", 1)[0]
    return summary[:60]


def _case_title_display(case: TestCaseItem) -> str:
    title = _extract_title(case.summary)
    if case.confirmation_note:
        title = f"{title} ⚠️待确认：{case.confirmation_note}"
    return title


def _sanitize_filename(text: str) -> str:
    """Remove characters illegal in filenames (Windows/macOS safe)."""
    return re.sub(r'[\\/:*?"<>|＋，。；：""''【】（）、]', "", text).strip()


def _build_filename(title: str | None, suffix: str) -> str:
    """Build a clean filename from task title, e.g. '商品营销视频生成测试用例.md'."""
    if title:
        clean = _sanitize_filename(title)
        # Strip any existing file extension the title might carry (e.g. ".md" from document titles)
        clean = re.sub(r"\.(md|csv|xlsx|pdf|docx?|txt)$", "", clean, flags=re.IGNORECASE)
        if clean:
            return f"{clean}{suffix}"
    return f"测试用例{suffix}"


def _content_disposition(filename: str) -> str:
    """RFC 5987-compatible Content-Disposition with encoded fallback."""
    safe = _sanitize_filename(filename)
    utf8_encoded = quote(safe, safe="")
    # filename*= carries the UTF-8 percent-encoded name (RFC 5987)
    # filename= carries the same value (URL-encoded ASCII) as fallback for older clients
    return f"attachment; filename*=UTF-8''{utf8_encoded}; filename=\"{utf8_encoded}\""


def _case_row(case: TestCaseItem) -> list[str]:
    return [
        case.priority,
        case.module or "-",
        case.category,
        _extract_title(case.summary),
        case.summary,
    ]


def _id_prefix(case: TestCaseItem) -> str:
    """Return the alphabetic prefix for a case: M, E, S, P, U, or I."""
    cat = case.category or ""
    if "异常" in cat or "错误" in cat or "边界" in cat:
        return "E"
    if "安全" in cat:
        return "S"
    if "性能" in cat or "压力" in cat:
        return "P"
    if "UI" in cat or "界面" in cat or "交互" in cat:
        return "U"
    if "国际化" in cat or "i18n" in cat.lower():
        return "I"
    return "M"



def build_markdown_table(cases: list[TestCaseItem]) -> str:
    columns = ["优先级", "模块", "分类", "测试标题", "测试摘要"]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for case in cases:
        cells = [
            _escape_markdown_cell(case.priority),
            _escape_markdown_cell(case.module or "-"),
            _escape_markdown_cell(case.category),
            _escape_markdown_cell(_extract_title(case.summary)),
            _escape_markdown_cell(case.summary),
        ]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)



def build_skill_template_markdown(
    cases: list[TestCaseItem],
    metadata: GenerationMetadata,
    requirement_text: str,
    document_titles: list[str],
    modules_overview: Optional[List[Tuple[str, str, str]]] = None,
) -> str:
    """
    按 test-case-template.md 模板结构输出 Markdown。
    章节编号与模板一致：九、统计 → 十、待确认 → 十一、评审 → 十二、版本。
    """
    today = date.today().isoformat()
    doc_basis = "、".join(document_titles) if document_titles else "（无上传文档，依据需求描述）"

    # --- 模块清单 ---
    if modules_overview:
        mod_rows = modules_overview
    else:
        seen: set[str] = set()
        mod_rows = []
        for c in cases:
            key = _id_prefix(c)
            if key and key not in seen:
                seen.add(key)
                mod_rows.append((key, c.module or key, ""))
        if not mod_rows:
            mod_rows = [("M01", "核心功能", "")]

    # Split cases by category prefix
    smoke = [c for c in cases if c.priority in ("P0", "P1")]
    by_category: dict[str, list[TestCaseItem]] = {}
    for c in cases:
        cat = c.category or "未分类"
        by_category.setdefault(cat, []).append(c)

    def group_by_prefix(case_list: list[TestCaseItem]) -> dict[str, list[TestCaseItem]]:
        groups: dict[str, list[TestCaseItem]] = {}
        for c in case_list:
            prefix = _id_prefix(c)
            groups.setdefault(prefix, []).append(c)
        return groups

    smoke_groups = group_by_prefix(smoke)
    detail_groups = group_by_prefix([c for c in cases if c not in smoke])

    lines: list[str] = []

    # ================================================================
    # 文档头部
    # ================================================================
    first_mod = mod_rows[0][1] if mod_rows else "功能模块"
    lines.extend([
        f"# 【{first_mod}】功能测试用例",
        "",
        f"> 编制人：（AI 自动生成，可替换为测试工程师姓名）",
        f"> 日期：{today}",
        f"> 依据文档：{doc_basis}",
        "> 状态：初版（待评审）",
        "",
        "---",
        "",
    ])

    # ================================================================
    # 一、功能模块概述
    # ================================================================
    lines.append("## 一、功能模块概述")
    lines.append("")
    lines.append("### 2.1 模块清单表格")
    lines.append("")
    lines.append("| 模块编号 | 模块名称 | 功能描述 |")
    lines.append("|---------|---------|---------|")
    for mid, mname, mdesc in mod_rows:
        lines.append(f"| {mid} | {mname} | {_escape_markdown_cell(mdesc or '—')} |")

    lines.append("")
    lines.append("---")
    lines.append("")

    # ================================================================
    # 二、冒烟测试用例（主流程核心验证）
    # ================================================================
    lines.extend([
        "## 二、冒烟测试用例（主流程核心验证）",
        "",
        "> 冒烟测试目的：验证功能主流程是否走得通，确保核心功能可用",
        "",
        "### 2.1 主流程概述",
        "",
    ])
    if len(mod_rows) >= 2:
        flow_line = " → ".join(f"{name}" for _, name, _ in mod_rows)
        arrow_line = " → ".join(f"{mid}" for mid, _, _ in mod_rows)
        lines.append(flow_line)
        lines.append(arrow_line)
    else:
        lines.append(f"{mod_rows[0][1]}({mod_rows[0][0]})")
        lines.append(f"{mod_rows[0][0]}")
    lines.append("")
    lines.append("### 2.2 冒烟测试用例")
    lines.append("")
    lines.append("| 用例名称 | 优先级 | 测试摘要 |")
    lines.append("|---------|-------|---------|")
    for i, c in enumerate(smoke, start=1):
        lines.append(
            "| {title} | {pri} | {summary} |".format(
                title=_escape_markdown_cell(_case_title_display(c)),
                pri=_escape_markdown_cell(c.priority),
                summary=_escape_markdown_cell(c.summary),
            )
        )
    if not smoke:
        lines.append("| — | （暂无 P0/P1 冒烟用例） | — |")

    lines.extend(["", "### 2.3 冒烟测试快速检查清单", ""])
    lines.append("| 步骤 | 检查项 | 测试摘要 |")
    lines.append("|------|-------|---------|")
    for i, c in enumerate(smoke, start=1):
        lines.append(
            f"| {i} | {_escape_markdown_cell(_extract_title(c.summary))} | {_escape_markdown_cell(c.summary[:120] + ('…' if len(c.summary) > 120 else ''))} |"
        )
    if not smoke:
        lines.append("| 1 | （无冒烟用例） | — |")

    p0_n = metadata.priority_counts.get("P0", 0)
    p1_n = metadata.priority_counts.get("P1", 0)
    lines.extend([
        "",
        "### 2.4 冒烟测试统计",
        "",
        "| 类型 | 用例数 | 说明 |",
        "|------|-------|------|",
        f"| P0 核心流程 | {p0_n} | 必须通过，否则阻塞上线 |",
        f"| P1 主流程扩展 | {p1_n} | 重要流程，24小时内修复 |",
        f"| **合计** | **{p0_n + p1_n}** | 覆盖主流程所有关键路径 |",
        "",
        "---",
        "",
    ])

    # ================================================================
    # 三、测试用例明细（M 系列）
    # ================================================================
    lines.append("## 三、测试用例明细")
    lines.append("")
    mod_prefixes = [k for k in detail_groups if k.startswith("M")]
    for prefix in sorted(mod_prefixes, key=lambda x: x):
        group = detail_groups[prefix]
        mod_name = group[0].module or prefix
        lines.append(f"### {prefix} {mod_name}模块")
        lines.append("")
        lines.append("| 用例名称 | 测试摘要 |")
        lines.append("|---------|---------|")
        for j, c in enumerate(group, start=1):
            lines.append(
                "| {title} | {summary} |".format(
                    title=_escape_markdown_cell(_case_title_display(c)),
                    summary=_escape_markdown_cell(c.summary),
                )
            )
        lines.append("")
        lines.append("---")
        lines.append("")

    # ================================================================
    # 四、异常场景测试用例（E 系列）
    # ================================================================
    if "E" in detail_groups:
        lines.append("## 四、异常场景测试用例")
        lines.append("")
        lines.append("| 用例名称 | 测试摘要 |")
        lines.append("|---------|---------|")
        for j, c in enumerate(detail_groups["E"], start=1):
            lines.append(
                "| {title} | {summary} |".format(
                    title=_escape_markdown_cell(_case_title_display(c)),
                    summary=_escape_markdown_cell(c.summary),
                )
            )
        lines.append("")
        lines.append("---")
        lines.append("")

    # ================================================================
    # 五、安全测试用例（S 系列）
    # ================================================================
    if "S" in detail_groups:
        lines.append("## 五、安全测试用例")
        lines.append("")
        lines.append("| 用例名称 | 测试摘要 |")
        lines.append("|---------|---------|")
        for j, c in enumerate(detail_groups["S"], start=1):
            lines.append(
                "| {title} | {summary} |".format(
                    title=_escape_markdown_cell(_case_title_display(c)),
                    summary=_escape_markdown_cell(c.summary),
                )
            )
        lines.append("")
        lines.append("---")
        lines.append("")

    # ================================================================
    # 六、性能测试用例（P 系列）
    # ================================================================
    if "P" in detail_groups:
        lines.append("## 六、性能测试用例")
        lines.append("")
        lines.append("| 用例名称 | 测试摘要 |")
        lines.append("|---------|---------|")
        for j, c in enumerate(detail_groups["P"], start=1):
            lines.append(
                "| {title} | {summary} |".format(
                    title=_escape_markdown_cell(_case_title_display(c)),
                    summary=_escape_markdown_cell(c.summary),
                )
            )
        lines.append("")
        lines.append("---")
        lines.append("")

    # ================================================================
    # 七、UI交互测试用例（U 系列）
    # ================================================================
    if "U" in detail_groups:
        lines.append("## 七、UI交互测试用例")
        lines.append("")
        lines.append("| 用例名称 | 测试摘要 |")
        lines.append("|---------|---------|")
        for j, c in enumerate(detail_groups["U"], start=1):
            lines.append(
                "| {title} | {summary} |".format(
                    title=_escape_markdown_cell(_case_title_display(c)),
                    summary=_escape_markdown_cell(c.summary),
                )
            )
        lines.append("")
        lines.append("---")
        lines.append("")

    # ================================================================
    # 八、国际化测试用例（I 系列）
    # ================================================================
    if "I" in detail_groups:
        lines.append("## 八、国际化测试用例")
        lines.append("")
        lines.append("| 用例名称 | 测试摘要 |")
        lines.append("|---------|---------|")
        for j, c in enumerate(detail_groups["I"], start=1):
            lines.append(
                "| {title} | {summary} |".format(
                    title=_escape_markdown_cell(_case_title_display(c)),
                    summary=_escape_markdown_cell(c.summary),
                )
            )
        lines.append("")
        lines.append("---")
        lines.append("")

    # ================================================================
    # 九、测试用例统计
    # ================================================================
    lines.extend([
        "## 九、测试用例统计",
        "",
        "| 分类 | 用例数量 |",
        "|------|---------|",
    ])
    total = 0
    smoke_n = len(smoke)
    if smoke_n:
        lines.append(f"| 冒烟测试（主流程） | {smoke_n} |")
        total += smoke_n
    for prefix in sorted(mod_prefixes, key=lambda x: x):
        cnt = len(detail_groups[prefix])
        mod_name = detail_groups[prefix][0].module or prefix
        lines.append(f"| {prefix} {mod_name}模块 | {cnt} |")
        total += cnt
    for label, key in [
        ("异常场景测试", "E"),
        ("安全测试", "S"),
        ("性能测试", "P"),
        ("UI交互测试", "U"),
        ("国际化测试", "I"),
    ]:
        if key in detail_groups:
            cnt = len(detail_groups[key])
            lines.append(f"| {label} | {cnt} |")
            total += cnt
    lines.append(f"| **合计** | **{total}** |")
    lines.extend(["", "---", ""])

    # ================================================================
    # 十、待确认问题标记说明
    # ================================================================
    lines.extend([
        "## 十、待确认问题标记说明",
        "",
        "- ⚠️ 标记的测试用例需等待产品经理确认需求后执行",
        "- 高优先级待确认项见 ../to_be_confirmed/待确认需求清单.md",
        "",
        "---",
        "",
    ])

    # ================================================================
    # 十一、评审记录
    # ================================================================
    lines.extend([
        "## 十一、评审记录",
        "",
        "### 产品经理评审",
        "",
        "| 编号 | 补充场景 | 用例编号 |",
        "|------|---------|---------|",
        "| PM-01 | （待评审） | — |",
        "",
        "### 前端开发评审",
        "",
        "| 编号 | 补充场景 | 用例编号 |",
        "|------|---------|---------|",
        "| FE-01 | （待评审） | — |",
        "",
        "### 后端开发评审",
        "",
        "| 编号 | 补充场景 | 用例编号 |",
        "|------|---------|---------|",
        "| BE-01 | （待评审） | — |",
        "",
        "### 测试工程师评审",
        "",
        "| 编号 | 补充场景 | 用例编号 |",
        "|------|---------|---------|",
        "| TE-01 | （待评审） | — |",
        "",
        "---",
        "",
    ])

    # ================================================================
    # 十二、文档版本记录
    # ================================================================
    lines.extend([
        "## 十二、文档版本记录",
        "",
        "| 版本 | 日期 | 说明 |",
        "|------|------|------|",
        f"| v1.0 | {today} | 初始版本，共 {total} 条用例（AI 自动生成） |",
        "",
        "---",
        "",
    ])

    # ================================================================
    # 附录：格式规范
    # ================================================================
    lines.extend([
        "## 附录：格式规范",
        "",
        "### 用例编号规则",
        "",
        "| 类型 | 格式 | 示例 |",
        "|-----|-----|-----|",
        "| 冒烟测试 | SMOKE-XX | SMOKE-01, SMOKE-12 |",
        "| 模块用例 | MXX-XXX | M02-001, M03-015 |",
        "| 异常场景 | E-XX | E01, E14 |",
        "| 安全测试 | S-XX | S01, S06 |",
        "| 性能测试 | P-XX | P01, P05 |",
        "| UI交互测试 | U-XX | U01, U14 |",
        "| 国际化测试 | I-XX | I01, I04 |",
        "",
        "### 优先级定义",
        "",
        "| 优先级 | 定义 | 修复要求 |",
        "|-------|-----|---------|",
        "| P0 | 冒烟测试，核心功能 | 必须通过，阻塞上线 |",
        "| P1 | 主要业务流程 | 24小时内修复 |",
        "| P2 | 重要功能点 | 常规修复 |",
        "| P3 | 边缘场景 | 资源允许时修复 |",
        "",
        "### 待确认标记规范",
        "",
        "- 使用 `⚠️待确认：[问题简述]` 标记在**用例名称**中",
        "- 示例：`⚠️待确认：支持的视频格式`",
        "- 预期结果中也使用：`⚠️待确认：[待确认内容]`",
        "",
        "### 测试步骤编写规范",
        "",
        "1. 每个步骤使用 `1.` 编号（按顺序递增）",
        "2. 步骤之间使用 `<br>` 换行",
        "3. 步骤描述简洁、明确",
        "4. 包含必要的等待或检查点",
        "",
        "### 预期结果编写规范",
        "",
        "1. 明确、具体、可验证",
        "2. 包含界面反馈",
        "3. 包含数据验证（如有）",
        "4. 异常情况需说明处理方式",
        "5. 简洁精炼，避免冗余描述",
        "",
    ])

    if metadata.warnings:
        lines.append("### 生成提示")
        lines.append("")
        for w in metadata.warnings:
            lines.append(f"- {w}")
        lines.append("")

    return "\n".join(lines)



def build_csv_bytes(cases: list[TestCaseItem]) -> bytes:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(HEADER_COLUMNS)
    for case in cases:
        writer.writerow(_case_row(case))
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def build_xlsx_bytes(cases: list[TestCaseItem], metadata: GenerationMetadata) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "测试用例"
    worksheet.append(HEADER_COLUMNS)
    for case in cases:
        worksheet.append(_case_row(case))

    meta_sheet = workbook.create_sheet("生成信息")
    meta_sheet.append(["字段", "值"])
    meta_sheet.append(["总用例数", metadata.case_count])
    meta_sheet.append(["是否存在截断", "是" if metadata.truncated else "否"])
    if metadata.warnings:
        meta_sheet.append(["警告", "\n".join(metadata.warnings)])
    if metadata.incomplete_categories:
        meta_sheet.append(["未完整覆盖类别", "\n".join(metadata.incomplete_categories)])
    for category, count in metadata.category_counts.items():
        meta_sheet.append([f"类别:{category}", count])
    for module, count in metadata.module_counts.items():
        meta_sheet.append([f"模块:{module}", count])
    for priority, count in metadata.priority_counts.items():
        meta_sheet.append([f"优先级:{priority}", count])

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
