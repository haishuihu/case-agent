from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from app.models.auto_test import ResultStatus
from app.services.auto_test.execution_engine import (
    BaseTestExecutor,
    TestContext,
    TestOutput,
)

logger = logging.getLogger(__name__)


class UnitExecutor(BaseTestExecutor):
    """单元测试执行器

    通过 subprocess 运行 pytest，解析输出获取 pass/fail 结果。
    """

    def supports_case_type(self) -> str:
        return "unit"

    async def execute(self, ctx: TestContext) -> TestOutput:
        case = ctx.case
        start_time = datetime.now(timezone.utc)
        request_data = {"endpoint": case.endpoint, "test_data": case.test_data}

        test_path = case.endpoint
        if not test_path:
            return TestOutput(
                case_id=case.id,
                result=ResultStatus.FAIL.value,
                response_status=0,
                response_data={},
                request_data=request_data,
                duration_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000),
                error_message="unit 用例的 endpoint 字段必须指定测试文件路径",
            )

        test_file = Path(test_path)
        if not test_file.exists():
            return TestOutput(
                case_id=case.id,
                result=ResultStatus.FAIL.value,
                response_status=0,
                response_data={},
                request_data=request_data,
                duration_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000),
                error_message=f"测试文件不存在: {test_path}",
            )

        try:
            test_filter = None
            if case.test_data:
                test_data = json.loads(case.test_data) if isinstance(case.test_data, str) else case.test_data
                test_filter = test_data.get("test_filter")

            cmd = ["pytest", str(test_file), "-v", "--tb=short", "--no-header"]
            if test_filter:
                cmd.extend(["-k", test_filter])

            timeout = ctx.config.get("timeout", 300)

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return TestOutput(
                    case_id=case.id,
                    result=ResultStatus.FAIL.value,
                    response_status=0,
                    response_data={},
                    request_data=request_data,
                    duration_ms=int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000),
                    error_message="测试执行超时",
                )

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")

            # Parse pytest output
            passed_match = re.search(r"(\d+)\s+passed", stdout)
            failed_match = re.search(r"(\d+)\s+failed", stdout)
            passed = int(passed_match.group(1)) if passed_match else 0
            failed = int(failed_match.group(1)) if failed_match else 0

            result = ResultStatus.PASS.value if failed == 0 and passed > 0 else ResultStatus.FAIL.value
            error_msg = stderr.strip() if failed > 0 else None

            if error_msg:
                # Truncate to first 2000 chars
                error_msg = error_msg[:2000]

            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            return TestOutput(
                case_id=case.id,
                result=result,
                response_status=0 if failed > 0 else 200,
                response_data={
                    "stdout": stdout[-3000:],
                    "passed": passed,
                    "failed": failed,
                },
                request_data=request_data,
                duration_ms=duration_ms,
                error_message=error_msg,
            )

        except Exception as e:
            logger.exception(f"Unit test error for case {case.id}")
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
