from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import httpx

from app.models.auto_test import ResultStatus
from app.services.auto_test.execution_engine import (
    BaseTestExecutor,
    TestContext,
    TestOutput,
)

logger = logging.getLogger(__name__)


class IntegrationExecutor(BaseTestExecutor):
    """集成测试执行器

    组合多个 API 调用的场景测试。
    利用 test_data 字段中定义的 steps 数组顺序执行多个请求。
    """

    def supports_case_type(self) -> str:
        return "integration"

    async def execute(self, ctx: TestContext) -> TestOutput:
        case = ctx.case
        start_time = datetime.now(timezone.utc)

        # Parse steps from test_data
        steps = []
        if case.test_data:
            try:
                test_data = json.loads(case.test_data) if isinstance(case.test_data, str) else case.test_data
                steps = test_data.get("steps", [])
            except (json.JSONDecodeError, TypeError):
                pass

        # If no steps defined, fall back to single request from case fields
        if not steps:
            steps = [{
                "name": case.title,
                "method": case.method or "GET",
                "endpoint": case.endpoint or "",
                "headers": json.loads(case.headers) if case.headers else {},
                "body": json.loads(case.request_body) if case.request_body else None,
                "expected_status": case.expected_status or 200,
                "expected_response": json.loads(case.expected_response) if case.expected_response else None,
            }]

        timeout = ctx.config.get("timeout", 30)
        base_url = ctx.config.get("base_url", "")
        step_results = []
        overall_result = ResultStatus.PASS.value
        error_message = None
        last_status = 200

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                for i, step in enumerate(steps):
                    step_name = step.get("name", f"Step {i+1}")
                    method = (step.get("method") or "GET").upper()
                    endpoint = step.get("endpoint", "")
                    url = base_url + endpoint if base_url and not endpoint.startswith("http") else endpoint
                    headers = step.get("headers", {})
                    body = step.get("body")
                    expected_status = step.get("expected_status", 200)
                    expected_response = step.get("expected_response")

                    step_start = datetime.now(timezone.utc)
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        json=body,
                    )
                    step_duration = int((datetime.now(timezone.utc) - step_start).total_seconds() * 1000)

                    step_pass = True
                    step_error = None
                    try:
                        resp_data = response.json()
                    except Exception:
                        resp_data = {"raw": response.text}

                    if response.status_code != expected_status:
                        step_pass = False
                        step_error = f"Step '{step_name}': expected status {expected_status}, got {response.status_code}"

                    if step_pass and expected_response:
                        for key, value in expected_response.items():
                            if key not in resp_data or resp_data[key] != value:
                                step_pass = False
                                step_error = f"Step '{step_name}': response key '{key}' mismatch"
                                break

                    step_results.append({
                        "step": step_name,
                        "passed": step_pass,
                        "status": response.status_code,
                        "duration_ms": step_duration,
                        "error": step_error,
                    })
                    last_status = response.status_code

                    if not step_pass:
                        overall_result = ResultStatus.FAIL.value
                        if not error_message:
                            error_message = step_error
                        break

        except httpx.TimeoutException:
            overall_result = ResultStatus.FAIL.value
            error_message = "Integration test timeout"
        except Exception as e:
            logger.exception(f"Integration test error for case {case.id}")
            overall_result = ResultStatus.FAIL.value
            error_message = str(e)

        duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        return TestOutput(
            case_id=case.id,
            result=overall_result,
            response_status=last_status,
            response_data={"steps": step_results},
            request_data={"steps": steps},
            duration_ms=duration_ms,
            error_message=error_message,
        )
