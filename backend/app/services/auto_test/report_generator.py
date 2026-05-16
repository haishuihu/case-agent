from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from app.models.auto_test import TestExecution, TestResult

logger = logging.getLogger(__name__)

# Mapping to Chinese labels
RESULT_LABELS = {
    "pass": "通过",
    "fail": "失败",
    "blocked": "阻塞",
    "skipped": "跳过",
    "pending": "待执行",
}

STATUS_LABELS = {
    "pending": "待执行",
    "running": "执行中",
    "completed": "已完成",
    "failed": "执行失败",
    "cancelled": "已取消",
}


def generate_execution_report(execution: TestExecution, results: list[TestResult]) -> str:
    """Generate an HTML report for a test execution."""

    passed = sum(1 for r in results if r.result == "pass")
    failed = sum(1 for r in results if r.result == "fail")
    blocked = sum(1 for r in results if r.result == "blocked")
    skipped = sum(1 for r in results if r.result == "skipped")
    total = len(results)
    pass_rate = round(passed / total * 100, 2) if total > 0 else 0
    duration_seconds = round((execution.duration_ms or 0) / 1000, 2)

    rows_html = ""
    for r in results:
        result_label = RESULT_LABELS.get(r.result, r.result)
        response_status = r.response_status or 0
        status_color = "#52c41a" if response_status < 400 else "#ff4d4f"
        error = r.error_message or ""
        duration = round((r.duration_ms or 0) / 1000, 2)

        rows_html += f"""
        <tr>
            <td>{r.case_id[:8]}...</td>
            <td>{result_label}</td>
            <td style="color:{status_color}">{response_status}</td>
            <td>{duration}s</td>
            <td style="color:#ff4d4f">{error[:100]}</td>
        </tr>"""

    ai_summary = execution.ai_summary or ""
    ai_recs = ""
    if execution.ai_recommendations:
        try:
            recs = json.loads(execution.ai_recommendations) if isinstance(execution.ai_recommendations, str) else execution.ai_recommendations
            ai_recs = "".join(f"<li>{r}</li>" for r in recs)
        except (json.JSONDecodeError, TypeError):
            ai_recs = ""

    status_label = STATUS_LABELS.get(execution.status, execution.status)

    report = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>测试报告 - {execution.name}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 40px; color: #333; }}
  h1 {{ font-size: 24px; margin-bottom: 8px; }}
  .meta {{ color: #666; font-size: 14px; margin-bottom: 24px; }}
  .summary {{ display: flex; gap: 16px; margin-bottom: 24px; }}
  .card {{ border: 1px solid #e8e8e8; border-radius: 8px; padding: 16px; min-width: 120px; text-align: center; }}
  .card .number {{ font-size: 28px; font-weight: 600; }}
  .card .label {{ font-size: 13px; color: #888; margin-top: 4px; }}
  .pass {{ color: #52c41a; }}
  .fail {{ color: #ff4d4f; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; }}
  th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #f0f0f0; font-size: 13px; }}
  th {{ background: #fafafa; font-weight: 500; }}
  .ai-section {{ background: #f6ffed; border: 1px solid #b7eb8f; border-radius: 8px; padding: 16px; margin-bottom: 16px; }}
  .ai-section h3 {{ margin-top: 0; }}
</style>
</head>
<body>
  <h1>测试执行报告</h1>
  <div class="meta">
    执行名称：{execution.name}<br>
    状态：{status_label} &nbsp;|&nbsp;
    触发方式：{execution.trigger_source or "manual"} &nbsp;|&nbsp;
    耗时：{duration_seconds}s &nbsp;|&nbsp;
    时间：{execution.created_at.strftime("%Y-%m-%d %H:%M:%S") if execution.created_at else ""}
  </div>

  <div class="summary">
    <div class="card"><div class="number">{total}</div><div class="label">总计</div></div>
    <div class="card"><div class="number pass">{passed}</div><div class="label">通过</div></div>
    <div class="card"><div class="number fail">{failed}</div><div class="label">失败</div></div>
    <div class="card"><div class="number">{blocked}</div><div class="label">阻塞</div></div>
    <div class="card"><div class="number">{skipped}</div><div class="label">跳过</div></div>
    <div class="card"><div class="number">{pass_rate}%</div><div class="label">通过率</div></div>
  </div>

  <table>
    <thead><tr>
      <th>用例 ID</th><th>结果</th><th>状态码</th><th>耗时</th><th>错误信息</th>
    </tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
</body>
</html>"""

    return report
