"""测试 Sprint 4: /generate/quick 极简用例模式 API（TC-001 ~ TC-005）"""

from fastapi.testclient import TestClient

from app.api.routes import generate as generate_routes
from app.main import app
from app.prompts.quick_prompt import SYSTEM_PROMPT_QUICK, build_quick_prompt
from app.services.llm_client import ChatCompletionResult


class StubQuickLLMClient:
    """Stub LLM client for /generate/quick endpoint tests."""

    profile = type("Profile", (), {
        "model_name": "stub-quick-model",
    })()

    def create_chat_completion(
        self,
        system_prompt: str,
        user_content: str,
        max_tokens: int = 2048,
    ) -> ChatCompletionResult:
        return ChatCompletionResult(
            content=(
                "### 核心流程\n"
                "- 用户使用手机号+验证码登录成功\n"
                "### 边界条件\n"
                "- 验证码错误 3 次后锁定\n"
                "### 异常场景\n"
                "- 网络超时 → 提示重试\n"
                "### 关键检查\n"
                "⚠️ 验证码有效期: 60 秒内有效\n"
            ),
            raw_response=(
                "### 核心流程\n"
                "- 用户使用手机号+验证码登录成功\n"
                "### 边界条件\n"
                "- 验证码错误 3 次后锁定\n"
            ),
            model_name="stub-quick-model",
            finish_reason="stop",
        )


original_builder = generate_routes.build_llm_client


def test_quick_generate_normal_call() -> None:
    """TC-001: POST /api/v1/generate/quick 正常调用"""
    generate_routes.build_llm_client = lambda model_key=None: StubQuickLLMClient()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/generate/quick",
                data={"requirement_text": "用户登录功能，支持手机号+验证码"},
            )
        assert response.status_code == 200
        payload = response.json()
        assert "content" in payload
        assert payload["modelName"] == "stub-quick-model"
        assert "generatedAt" in payload
        assert "核心流程" in payload["content"]
    finally:
        generate_routes.build_llm_client = original_builder


def test_quick_generate_empty_requirement_returns_400() -> None:
    """TC-002: 空需求文本返回 400"""
    generate_routes.build_llm_client = lambda model_key=None: StubQuickLLMClient()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/generate/quick",
                data={"requirement_text": ""},
            )
        assert response.status_code == 400
        assert "需求描述不能为空" in response.json()["detail"]
    finally:
        generate_routes.build_llm_client = original_builder


def test_quick_generate_whitespace_only_returns_400() -> None:
    """TC-002 (边界): 仅空白字符也返回 400"""
    generate_routes.build_llm_client = lambda model_key=None: StubQuickLLMClient()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/generate/quick",
                data={"requirement_text": "   "},
            )
        assert response.status_code == 400
        assert "需求描述不能为空" in response.json()["detail"]
    finally:
        generate_routes.build_llm_client = original_builder


def test_quick_generate_returns_markdown_bullet_format() -> None:
    """TC-003: 返回 content 为 markdown bullet point 格式"""
    generate_routes.build_llm_client = lambda model_key=None: StubQuickLLMClient()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/generate/quick",
                data={"requirement_text": "用户登录"},
            )
        assert response.status_code == 200
        payload = response.json()
        assert payload["content"]
        assert "\n- " in payload["content"] or "###" in payload["content"]
    finally:
        generate_routes.build_llm_client = original_builder


def test_quick_prompt_builder_includes_all_sections() -> None:
    """TC-004: build_quick_prompt() 输出包含四个维度"""
    prompt = build_quick_prompt("用户登录功能")
    assert "核心流程" in prompt
    assert "边界条件" in prompt
    assert "异常场景" in prompt
    assert "关键检查" in prompt


def test_quick_prompt_builder_injects_requirement_text() -> None:
    """TC-004 (补充): 需求文本正确注入 prompt"""
    requirement = "用户登录功能，支持手机号+验证码"
    prompt = build_quick_prompt(requirement)
    assert requirement in prompt


def test_system_prompt_quick_bullet_format_instruction() -> None:
    """TC-005: SYSTEM_PROMPT_QUICK 包含 Bullet Point 输出指令"""
    assert "Bullet Point" in SYSTEM_PROMPT_QUICK
    assert "精简" in SYSTEM_PROMPT_QUICK


def test_system_prompt_quick_forbids_full_testcase_format() -> None:
    """TC-005: SYSTEM_PROMPT_QUICK 不要求完整用例格式"""
    # 明确禁止完整用例格式
    assert "禁止输出完整用例格式" in SYSTEM_PROMPT_QUICK
    assert "步骤/预期结果表格" in SYSTEM_PROMPT_QUICK


def test_system_prompt_quick_includes_four_dimensions() -> None:
    """TC-005: SYSTEM_PROMPT_QUICK 包含四个输出维度"""
    assert "核心流程" in SYSTEM_PROMPT_QUICK
    assert "边界条件" in SYSTEM_PROMPT_QUICK
    assert "异常场景" in SYSTEM_PROMPT_QUICK
    assert "关键检查" in SYSTEM_PROMPT_QUICK


def test_system_prompt_quick_warns_high_risk() -> None:
    """TC-005: SYSTEM_PROMPT_QUICK 要求高风险项用 ⚠️ 标记"""
    assert "⚠️" in SYSTEM_PROMPT_QUICK
    assert "高风险" in SYSTEM_PROMPT_QUICK


def test_quick_generate_model_key_param() -> None:
    """TC-001 (补充): 可接受 modelKey 参数"""
    generate_routes.build_llm_client = lambda model_key=None: StubQuickLLMClient()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/generate/quick",
                data={"requirement_text": "用户登录", "modelKey": "deepseek"},
            )
        assert response.status_code == 200
        payload = response.json()
        assert "content" in payload
    finally:
        generate_routes.build_llm_client = original_builder
