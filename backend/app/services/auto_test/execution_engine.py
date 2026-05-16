from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

import httpx
from sqlalchemy.orm import Session

from app.models.auto_test import (
    ExecutionStatus,
    ResultStatus,
    TestCase,
    TestExecution,
    TestResult,
)

logger = logging.getLogger(__name__)


@dataclass
class TestContext:
    """测试执行上下文"""
    execution_id: str
    case_id: str
    case: TestCase
    db: Session
    config: dict


@dataclass
class TestOutput:
    """测试执行输出"""
    case_id: str
    result: str
    response_status: int
    response_data: dict
    request_data: dict
    duration_ms: int
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    validation_details: Optional[dict] = None


class BaseTestExecutor(ABC):
    """测试执行器基类"""
    
    @abstractmethod
    async def execute(self, ctx: TestContext) -> TestOutput:
        """执行测试"""
        pass
    
    @abstractmethod
    def supports_case_type(self) -> str:
        """返回支持的用例类型"""
        pass


class APIExecutor(BaseTestExecutor):
    """API 测试执行器"""
    
    def supports_case_type(self) -> str:
        return "api"
    
    async def execute(self, ctx: TestContext) -> TestOutput:
        case = ctx.case
        start_time = datetime.utcnow()
        
        headers = {}
        if case.headers:
            try:
                headers = json.loads(case.headers)
            except json.JSONDecodeError:
                logger.warning(f"Invalid headers JSON for case {case.id}")
        
        request_body = None
        if case.request_body:
            try:
                request_body = json.loads(case.request_body)
            except json.JSONDecodeError:
                logger.warning(f"Invalid request_body JSON for case {case.id}")
        
        request_data = {
            "method": case.method,
            "endpoint": case.endpoint,
            "headers": headers,
            "body": request_body,
        }
        
        try:
            timeout = 30
            if case.extra_metadata:
                try:
                    meta = json.loads(case.extra_metadata)
                    timeout = meta.get("timeout", 30)
                except json.JSONDecodeError:
                    pass
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                url = case.endpoint or ""
                method = case.method or "GET"
                
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    headers=headers,
                    json=request_body,
                )
                
                duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                try:
                    response_data = response.json()
                except Exception:
                    response_data = {"raw": response.text}
                
                result = ResultStatus.PASS.value
                error_message = None
                validation_details = None
                
                if response.status_code != (case.expected_status or 200):
                    result = ResultStatus.FAIL.value
                    error_message = f"Expected status {case.expected_status}, got {response.status_code}"
                
                if case.expected_response and result == ResultStatus.PASS.value:
                    try:
                        expected = json.loads(case.expected_response)
                        validation = self._validate_response(response_data, expected)
                        if not validation["passed"]:
                            result = ResultStatus.FAIL.value
                            error_message = validation.get("message", "Response validation failed")
                            validation_details = validation
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid expected_response JSON for case {case.id}")
                
                if case.validation_rules and result == ResultStatus.PASS.value:
                    try:
                        rules = json.loads(case.validation_rules)
                        validation = self._validate_rules(response_data, rules)
                        if not validation["passed"]:
                            result = ResultStatus.FAIL.value
                            error_message = validation.get("message", "Validation rules failed")
                            validation_details = validation
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid validation_rules JSON for case {case.id}")
                
                return TestOutput(
                    case_id=case.id,
                    result=result,
                    response_status=response.status_code,
                    response_data=response_data,
                    request_data=request_data,
                    duration_ms=duration_ms,
                    error_message=error_message,
                    validation_details=validation_details,
                )
                
        except httpx.TimeoutException:
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            return TestOutput(
                case_id=case.id,
                result=ResultStatus.FAIL.value,
                response_status=0,
                response_data={},
                request_data=request_data,
                duration_ms=duration_ms,
                error_message="Request timeout",
            )
        except Exception as e:
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            logger.exception(f"Error executing case {case.id}")
            return TestOutput(
                case_id=case.id,
                result=ResultStatus.FAIL.value,
                response_status=0,
                response_data={},
                request_data=request_data,
                duration_ms=duration_ms,
                error_message=str(e),
                stack_trace=getattr(e, "__traceback__", None),
            )
    
    def _validate_response(self, actual: dict, expected: dict) -> dict:
        """验证响应内容"""
        mismatches = []
        for key, value in expected.items():
            if key not in actual:
                mismatches.append(f"Missing key: {key}")
            elif actual[key] != value:
                mismatches.append(f"Key '{key}': expected {value}, got {actual[key]}")
        
        if mismatches:
            return {"passed": False, "message": "; ".join(mismatches)}
        return {"passed": True}
    
    def _validate_rules(self, data: dict, rules: list[dict]) -> dict:
        """验证规则"""
        errors = []
        for rule in rules:
            rule_type = rule.get("type")
            field = rule.get("field")
            condition = rule.get("condition")
            expected_val = rule.get("value")
            
            if rule_type == "exists":
                if field not in data:
                    errors.append(f"Field '{field}' must exist")
            elif rule_type == "equals":
                if data.get(field) != expected_val:
                    errors.append(f"Field '{field}' must equal {expected_val}")
            elif rule_type == "contains":
                if expected_val not in str(data.get(field, "")):
                    errors.append(f"Field '{field}' must contain '{expected_val}'")
        
        if errors:
            return {"passed": False, "message": "; ".join(errors)}
        return {"passed": True}


class TestExecutionEngine:
    """测试执行引擎"""

    def __init__(self):
        from app.services.auto_test.integration_executor import IntegrationExecutor
        from app.services.auto_test.ui_executor import UIExecutor
        from app.services.auto_test.unit_executor import UnitExecutor

        self._executors: dict[str, BaseTestExecutor] = {
            "api": APIExecutor(),
            "ui": UIExecutor(),
            "unit": UnitExecutor(),
            "integration": IntegrationExecutor(),
        }
    
    def register_executor(self, executor: BaseTestExecutor):
        """注册执行器"""
        self._executors[executor.supports_case_type()] = executor
    
    def get_executor(self, case_type: str) -> Optional[BaseTestExecutor]:
        """获取执行器"""
        return self._executors.get(case_type)
    
    async def execute_case(self, ctx: TestContext) -> TestOutput:
        """执行单个用例"""
        executor = self.get_executor(ctx.case.case_type)
        if not executor:
            return TestOutput(
                case_id=ctx.case_id,
                result=ResultStatus.FAIL.value,
                response_status=0,
                response_data={},
                request_data={},
                duration_ms=0,
                error_message=f"No executor for case type: {ctx.case.case_type}",
            )
        
        return await executor.execute(ctx)
    
    async def execute_batch(
        self,
        execution_id: str,
        case_ids: list[str],
        db: Session,
        config: Optional[dict] = None,
        max_concurrency: int = 5,
    ) -> list[TestOutput]:
        """批量执行用例"""
        cases = db.query(TestCase).filter(TestCase.id.in_(case_ids)).all()
        
        outputs = []
        semaphore = asyncio.Semaphore(max_concurrency)
        
        async def execute_with_semaphore(case: TestCase) -> TestOutput:
            async with semaphore:
                ctx = TestContext(
                    execution_id=execution_id,
                    case_id=case.id,
                    case=case,
                    db=db,
                    config=config or {},
                )
                return await self.execute_case(ctx)
        
        tasks = [execute_with_semaphore(case) for case in cases]
        outputs = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_outputs = []
        for output in outputs:
            if isinstance(output, TestOutput):
                valid_outputs.append(output)
            else:
                logger.error(f"Unexpected result during execution: {output}")
        
        return valid_outputs
    
    def save_result(self, db: Session, execution_id: str, output: TestOutput) -> TestResult:
        """保存测试结果"""
        result = TestResult(
            id=str(uuid4()),
            execution_id=execution_id,
            case_id=output.case_id,
            result=output.result,
            request_data=json.dumps(output.request_data) if output.request_data else None,
            response_data=json.dumps(output.response_data) if output.response_data else None,
            response_status=output.response_status,
            validation_details=json.dumps(output.validation_details) if output.validation_details else None,
            error_message=output.error_message,
            stack_trace=str(output.stack_trace) if output.stack_trace else None,
            duration_ms=output.duration_ms,
            executed_at=datetime.utcnow(),
        )
        db.add(result)
        db.commit()
        db.refresh(result)
        return result


execution_engine = TestExecutionEngine()
