from io import BytesIO
import json

from fastapi.testclient import TestClient

from app.api.routes import generate as generate_routes
from app.core.config import ModelProfile
from app.main import app
from app.services import generation_worker as generation_worker_mod
from app.schemas.testcase import GenerationMetadata, TestCaseItem
from app.services.llm_client import ChatCompletionResult, LLMGenerationResult


class StubProfile:
    def __init__(self):
        self.key = "stub"
        self.label = "Stub Model"
        self.provider = "stub"
        self.base_url = "https://example.invalid/v1"
        self.api_key = "stub-key"
        self.model_name = "stub-model"
        self.max_output_tokens = 4096
        self.timeout = 60


class StubSettings:
    llm_cache_enabled = False


class StubLLMClient:
    profile = StubProfile()
    settings = StubSettings()

    def generate_test_cases(
        self,
        requirement_text,
        document_contexts,
        image_contexts,
        db_session=None,
        progress_callback=None,
        cancel_check=None,
    ):
        return LLMGenerationResult(
            markdown=(
                "| 用例ID | 优先级 | 模块 | 分类 | 测试标题 | 前置条件 | 测试步骤 | 预期结果 |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
                "| TC-001 | P0 | 登录模块 | 正常流程 | 登录成功 | 用户已注册 | 输入正确手机号和验证码 | 登录成功并进入首页 |"
            ),
            prompt_snapshot=requirement_text,
            raw_response=(
                '{"cases":[{"caseId":"TC-001","title":"登录成功","preconditions":["用户已注册"],'
                '"steps":["输入正确手机号和验证码"],"expectedResult":"登录成功并进入首页",'
                '"category":"正常流程","priority":"P0","module":"登录模块","moduleId":"M01",'
                '"confirmationNote":null,"sourceBatch":"冒烟测试"}],'
                '"metadata":{"caseCount":1,"categoryCounts":{"正常流程":1},'
                '"moduleCounts":{"登录模块":1},"priorityCounts":{"P0":1},'
                '"reviewQuestions":[],"warnings":[],"truncated":false,'
                '"incompleteCategories":[]}}'
            ),
            model_name="stub-model",
            cases=[
                TestCaseItem(
                    caseId="TC-001",
                    title="登录成功",
                    preconditions=["用户已注册"],
                    steps=["输入正确手机号和验证码"],
                    expectedResult="登录成功并进入首页",
                    category="正常流程",
                    priority="P0",
                    module="登录模块",
                    moduleId="M01",
                    sourceBatch="冒烟测试",
                )
            ],
            metadata=GenerationMetadata(
                caseCount=1,
                categoryCounts={"正常流程": 1},
                moduleCounts={"登录模块": 1},
                priorityCounts={"P0": 1},
                reviewQuestions=[],
                warnings=[],
                truncated=False,
                incompleteCategories=[],
            ),
        )

    def create_chat_completion(self, system_prompt: str, user_content: str, **kwargs) -> ChatCompletionResult:
        """Stub for /generate/review and other single-call LLM endpoints."""
        return ChatCompletionResult(
            content=json.dumps({
                "modules": [
                    {"id": "M01", "name": "登录模块", "description": "用户登录核心功能",
                     "sub_features": ["手机号输入", "验证码发送"]}
                ],
                "questions": [],
                "business_rules": ["验证码 60 秒有效"],
                "data_constraints": [{"type": "phone", "description": "手机号格式"}],
            }),
            raw_response="",
            model_name="stub-model",
            finish_reason="stop",
        )

    def summarize_requirement_from_files(self, requirement_text, document_contexts, image_contexts):
        if not requirement_text and not document_contexts and not image_contexts:
            raise ValueError("请至少填写需求摘要或上传参考文件。")
        return {
            "summary_text": "- 功能目标：用户通过手机号验证码登录\n- 业务规则：验证码 60 秒有效",
            "modules": ["登录模块", "验证码模块"],
            "business_rules": ["验证码 60 秒有效"],
            "data_constraints": ["手机号格式合法", "验证码 6 位"],
            "open_questions": ["待确认：验证码是否限制错误次数"],
            "model_name": "stub-model",
        }


def test_generate_api_returns_markdown_table() -> None:
    original_builder = generate_routes.build_llm_client
    generate_routes.build_llm_client = lambda model_key=None: StubLLMClient()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/generate",
            data={"requirement_text": "用户可以通过手机号验证码登录"},
            files=[
                (
                    "documentFiles",
                    ("rules.txt", BytesIO("验证码 60 秒有效".encode("utf-8")), "text/plain"),
                )
            ],
        )

    generate_routes.build_llm_client = original_builder

    assert response.status_code == 200
    payload = response.json()
    assert payload["modelName"] == "stub-model"
    assert "登录成功" in payload["markdown"]
    assert payload["attachmentCount"] == 1
    assert payload["metadata"]["caseCount"] == 1
    assert payload["cases"][0]["category"] == "正常流程"
    assert payload["cases"][0]["priority"] == "P0"
    assert payload["cases"][0]["module"] == "登录模块"
    assert payload["metadata"]["moduleCounts"]["登录模块"] == 1
    assert payload["metadata"]["priorityCounts"]["P0"] == 1


def test_export_generation_returns_csv() -> None:
    original_builder = generate_routes.build_llm_client
    generate_routes.build_llm_client = lambda model_key=None: StubLLMClient()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/generate",
            data={"requirement_text": "用户可以通过手机号验证码登录"},
        )
        generation_id = response.json()["generationId"]

        export_response = client.get(f"/api/v1/generations/{generation_id}/export?format=csv")

    generate_routes.build_llm_client = original_builder

    assert export_response.status_code == 200
    assert "text/csv" in export_response.headers["content-type"]
    assert "登录成功" in export_response.content.decode("utf-8-sig")


def test_list_models_returns_all_profiles() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/models")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    for option in payload:
        assert "key" in option
        assert "label" in option
        assert "modelName" in option


def test_generate_summary_returns_confirmable_text() -> None:
    original_builder = generate_routes.build_llm_client
    generate_routes.build_llm_client = lambda model_key=None: StubLLMClient()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/generate/summary",
            files=[
                (
                    "documentFiles",
                    ("rules.txt", BytesIO("验证码 60 秒有效".encode("utf-8")), "text/plain"),
                )
            ],
        )

    generate_routes.build_llm_client = original_builder

    assert response.status_code == 200
    payload = response.json()
    assert "功能目标" in payload["summaryText"]
    assert payload["modules"] == ["登录模块", "验证码模块"]
    assert payload["businessRules"] == ["验证码 60 秒有效"]
    assert payload["openQuestions"] == ["待确认：验证码是否限制错误次数"]
    assert payload["modelName"] == "stub-model"


def test_generate_async_completes_and_poll_returns_result() -> None:
    original_spawn = generate_routes.spawn_generation_thread

    def sync_spawn(
        task_id: str,
        requirement_text: str,
        document_contexts: object,
        image_contexts: object,
        model_key,
    ) -> None:
        from app.services.generation_worker import run_generation_task

        run_generation_task(task_id, requirement_text, document_contexts, image_contexts, model_key)

    generate_routes.spawn_generation_thread = sync_spawn
    original_route_builder = generate_routes.build_llm_client
    original_worker_builder = generation_worker_mod.build_llm_client
    generate_routes.build_llm_client = lambda model_key=None: StubLLMClient()
    generation_worker_mod.build_llm_client = lambda model_key=None: StubLLMClient()
    try:
        with TestClient(app) as client:
            submit = client.post(
                "/api/v1/generate/async",
                data={"requirement_text": "用户可以通过手机号验证码登录"},
            )
            assert submit.status_code == 200
            task_id = submit.json()["taskId"]
            assert submit.json()["status"] == "running"

            status = client.get(f"/api/v1/generate/tasks/{task_id}")
            assert status.status_code == 200
            body = status.json()
            assert body["status"] == "succeeded"
            assert body["result"] is not None
            assert body["result"]["metadata"]["caseCount"] == 1
            assert body["result"]["cases"][0]["title"] == "登录成功"

            listed = client.get("/api/v1/generate/tasks?page=1&pageSize=10")
            assert listed.status_code == 200
            lst = listed.json()
            assert lst["total"] >= 1
            assert any(item["taskId"] == task_id for item in lst["items"])
    finally:
        generate_routes.spawn_generation_thread = original_spawn
        generate_routes.build_llm_client = original_route_builder
        generation_worker_mod.build_llm_client = original_worker_builder


def test_generate_summary_rejects_empty_input() -> None:
    original_builder = generate_routes.build_llm_client
    generate_routes.build_llm_client = lambda model_key=None: StubLLMClient()
    with TestClient(app) as client:
        response = client.post("/api/v1/generate/summary")

    generate_routes.build_llm_client = original_builder

    assert response.status_code == 400
    assert response.json()["detail"] == "请至少填写需求摘要或上传参考文件。"


def test_stale_running_task_marked_failed_on_get() -> None:
    """GET /api/v1/generate/tasks/{id} 应当在读状态时将超时的 running 任务自动标记为 failed。"""
    from datetime import datetime, timedelta, timezone
    from unittest.mock import patch

    def fake_settings():
        from app.core.config import Settings

        s = Settings()
        s.generation_max_runtime_minutes = 1
        return s

    with TestClient(app) as client:
        from app.db.session import SessionLocal
        from app.models.generation import GenerationRecord

        db = SessionLocal()
        try:
            stale_record = GenerationRecord(
                requirement_text="超时测试任务",
                model_name="stub-model",
                prompt_snapshot="超时测试",
                status="running",
                progress_phase="running",
                started_at=datetime.now(timezone.utc) - timedelta(minutes=2),
            )
            db.add(stale_record)
            db.commit()
            db.refresh(stale_record)
            task_id = stale_record.id
        finally:
            db.close()

        with patch("app.core.config.get_settings", fake_settings):
            resp = client.get(f"/api/v1/generate/tasks/{task_id}")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "failed", f"expected failed, got {body['status']}"
        assert body.get("errorMessage"), f"expected non-empty errorMessage, got {body.get('errorMessage')}"


# ----------------------------------------------------------------------
# TC-014 ~ TC-015: 回归测试 - 确保新增功能未破坏已有 API
# ----------------------------------------------------------------------


def test_existing_generate_summary_still_works() -> None:
    """TC-014: 原有 /generate/summary API 仍然正常"""
    original_builder = generate_routes.build_llm_client
    generate_routes.build_llm_client = lambda model_key=None: StubLLMClient()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/generate/summary",
                data={"requirement_text": "用户登录功能"},
            )
        assert response.status_code == 200
        payload = response.json()
        assert "summaryText" in payload
        assert "modules" in payload
        assert isinstance(payload["modules"], list)
        assert payload["businessRules"] == ["验证码 60 秒有效"]
        assert payload["modelName"] == "stub-model"
    finally:
        generate_routes.build_llm_client = original_builder


def test_existing_generate_review_still_works() -> None:
    """TC-015: 原有 /generate/review API 仍然正常"""
    original_builder = generate_routes.build_llm_client
    generate_routes.build_llm_client = lambda model_key=None: StubLLMClient()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/generate/review",
                data={"requirement_text": "用户登录功能"},
            )
        assert response.status_code == 200
        payload = response.json()
        assert "modules" in payload
        assert "questions" in payload
        assert isinstance(payload["modules"], list)
        assert payload["businessRules"] == ["验证码 60 秒有效"]
        assert payload["dataConstraints"] == [{"type": "phone", "description": "手机号格式"}]
        assert payload["modelName"] == "stub-model"
    finally:
        generate_routes.build_llm_client = original_builder
