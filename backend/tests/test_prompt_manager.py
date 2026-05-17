"""Tests for PromptManager."""

import pytest

from app.prompts.manager import PromptManager, get_prompt_manager, reset_prompt_manager


@pytest.fixture(autouse=True)
def _reset_manager() -> None:
    reset_prompt_manager()


def test_manager_loads_template() -> None:
    pm = PromptManager()
    version = pm.get_version("phase4_module_detail")
    assert version == "1.0.0"


def test_manager_lists_templates() -> None:
    pm = PromptManager()
    templates = pm.list_templates()
    names = {t["name"] for t in templates}
    assert "phase4_module_detail" in names
    assert "phase1_requirement_review" in names
    assert "phase3_smoke" in names
    assert "phase5_review" in names
    for t in templates:
        assert "version" in t
        assert "description" in t


def test_render_phase4_default_system_prompt() -> None:
    pm = PromptManager()
    sys_prompt, user_prompt = pm.render(
        "phase4_module_detail",
        {"module_name": "登录模块", "module_id": "M01"},
    )
    assert "资深测试设计专家" in sys_prompt
    assert "穷尽式" in sys_prompt
    assert "等价类划分" in sys_prompt


def test_render_phase4_user_prompt_no_cot() -> None:
    pm = PromptManager()
    _sys, user = pm.render(
        "phase4_module_detail",
        {"module_name": "登录模块", "module_id": "M01", "requirement_context": "测试需求"},
    )
    assert "<thinking>" not in user
    assert "</thinking>" not in user
    assert "功能理解" not in user
    assert "维度映射" not in user


def test_render_phase4_user_prompt_has_output_instruction() -> None:
    pm = PromptManager()
    _sys, user = pm.render(
        "phase4_module_detail",
        {"module_name": "登录", "module_id": "M01"},
    )
    assert "输出要求" in user
    assert "JSON" in user


def test_render_phase4_model_override() -> None:
    pm = PromptManager()
    sys_default, _ = pm.render(
        "phase4_module_detail",
        {"module_name": "登录", "module_id": "M01"},
        model_provider=None,
    )
    sys_deepseek, _ = pm.render(
        "phase4_module_detail",
        {"module_name": "登录", "module_id": "M01"},
        model_provider="deepseek",
    )
    sys_minimax, _ = pm.render(
        "phase4_module_detail",
        {"module_name": "登录", "module_id": "M01"},
        model_provider="minimax",
    )
    # Default and deepseek are different
    assert sys_default != sys_deepseek
    # Minimax override mentions "只输出 JSON"
    assert "只输出 JSON" in sys_minimax


def test_render_phase1_no_cot() -> None:
    pm = PromptManager()
    _sys, user = pm.render(
        "phase1_requirement_review",
        {"requirement_context": "测试需求"},
    )
    assert "<thinking>" not in user
    assert "通读理解" not in user
    assert "模块识别" not in user
    assert "问题发现" not in user


def test_render_phase3_no_cot() -> None:
    pm = PromptManager()
    _sys, user = pm.render(
        "phase3_smoke",
        {"requirement_context": "测试需求"},
    )
    assert "<thinking>" not in user
    assert "核心路径识别" not in user


def test_render_phase5_no_cot() -> None:
    pm = PromptManager()
    _sys, user = pm.render(
        "phase5_review",
        {"requirement_context": "测试需求"},
    )
    assert "<thinking>" not in user
    assert "理解已有覆盖" not in user
    assert "逐视角检查" not in user


def test_render_phase2_no_cot() -> None:
    pm = PromptManager()
    _sys, user = pm.render(
        "phase2_batch_generation",
        {"requirement_context": "测试需求"},
    )
    assert "<thinking>" not in user
    assert "全局分析" not in user
    assert "冒烟测试设计" not in user
    assert "模块详情设计" not in user


def test_render_unknown_template_raises() -> None:
    pm = PromptManager()
    with pytest.raises(FileNotFoundError):
        pm.render("nonexistent_template", {})


def test_get_prompt_manager_singleton() -> None:
    pm1 = get_prompt_manager()
    pm2 = get_prompt_manager()
    assert pm1 is pm2


def test_render_injects_context_variables() -> None:
    pm = PromptManager()
    _sys, user = pm.render(
        "phase4_module_detail",
        {
            "module_name": "自定义模块名",
            "module_id": "M99",
        },
    )
    assert "自定义模块名" in user
    assert "M99" in user
