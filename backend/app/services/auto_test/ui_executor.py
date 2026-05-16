from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.models.auto_test import ResultStatus
from app.services.auto_test.execution_engine import (
    BaseTestExecutor,
    TestContext,
    TestOutput,
)

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent.parent / "uploads" / "screenshots"


class UIExecutor(BaseTestExecutor):
    """UI 自动化测试执行器

    支持 Playwright 驱动的浏览器自动化测试。
    解析 TestCase 的 ui_selector、ui_action、ui_expected 字段。
    """

    def supports_case_type(self) -> str:
        return "ui"

    async def execute(self, ctx: TestContext) -> TestOutput:
        case = ctx.case
        start_time = datetime.now(timezone.utc)
        screenshot_path: Optional[str] = None

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return TestOutput(
                case_id=case.id,
                result=ResultStatus.FAIL.value,
                response_status=0,
                response_data={},
                request_data={"ui_selector": case.ui_selector, "ui_action": case.ui_action},
                duration_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000),
                error_message="Playwright 未安装。请运行: pip install playwright && playwright install",
            )

        ui_action = case.ui_action or "click"
        ui_expected = case.ui_expected or ""

        # base_url 优先级: ctx.config > case.test_data > case.extra_metadata
        base_url = ctx.config.get("base_url", "")
        if not base_url and case.test_data:
            try:
                td = json.loads(case.test_data) if isinstance(case.test_data, str) else case.test_data
                base_url = td.get("base_url", "") or ""
            except (json.JSONDecodeError, TypeError):
                pass
        if not base_url and case.extra_metadata:
            try:
                em = json.loads(case.extra_metadata) if isinstance(case.extra_metadata, str) else case.extra_metadata
                base_url = em.get("base_url", "") or ""
            except (json.JSONDecodeError, TypeError):
                pass

        request_data = {
            "ui_selector": case.ui_selector,
            "ui_action": ui_action,
            "ui_expected": ui_expected,
        }

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                target_url = base_url + (case.endpoint or "")
                if target_url:
                    await page.goto(target_url, timeout=ctx.config.get("timeout", 30000))

                selector = case.ui_selector
                if not selector:
                    await browser.close()
                    return TestOutput(
                        case_id=case.id,
                        result=ResultStatus.FAIL.value,
                        response_status=0,
                        response_data={},
                        request_data=request_data,
                        duration_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000),
                        error_message="ui_selector 不能为空",
                    )

                await page.wait_for_selector(selector, timeout=ctx.config.get("timeout", 30000))

                if ui_action == "click":
                    await page.click(selector)
                elif ui_action == "fill":
                    input_text = ctx.config.get("input_text", "")
                    await page.fill(selector, input_text)
                elif ui_action == "check":
                    await page.check(selector)
                elif ui_action == "select":
                    value = ctx.config.get("select_value", "")
                    await page.select_option(selector, value)
                elif ui_action == "hover":
                    await page.hover(selector)
                elif ui_action == "assert_visible":
                    pass  # wait_for_selector already confirms visibility

                # Take screenshot
                UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
                screenshot_filename = f"{ctx.case_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.png"
                screenshot_path = str(UPLOAD_DIR / screenshot_filename)
                await page.screenshot(path=screenshot_path, full_page=True)

                result = ResultStatus.PASS.value
                error_message = None

                if ui_expected:
                    page_text = await page.inner_text("body")
                    if ui_expected not in page_text:
                        result = ResultStatus.FAIL.value
                        error_message = f"页面中未找到预期文本: {ui_expected}"

                await browser.close()

                duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
                return TestOutput(
                    case_id=case.id,
                    result=result,
                    response_status=200 if result == ResultStatus.PASS.value else 500,
                    response_data={"screenshot": screenshot_path, "result": result},
                    request_data=request_data,
                    duration_ms=duration_ms,
                    error_message=error_message,
                )

        except Exception as e:
            logger.exception(f"UI test error for case {case.id}")
            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            return TestOutput(
                case_id=case.id,
                result=ResultStatus.FAIL.value,
                response_status=0,
                response_data={},
                request_data=request_data,
                duration_ms=duration_ms,
                error_message=str(e),
            )
