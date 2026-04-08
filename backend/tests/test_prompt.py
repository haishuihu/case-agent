from app.prompts.testcase_prompt import (
    SYSTEM_PROMPT,
    build_module_detail_prompt,
    build_requirement_context,
    build_requirement_review_prompt,
    build_smoke_test_prompt,
    build_review_prompt,
)
from app.services.file_parser import DocumentContext


def test_prompt_builders_include_requirement_and_documents() -> None:
    document = DocumentContext(
        filename="login.md",
        content_type="text/markdown",
        extracted_text="登录失败超过 5 次需要锁定 10 分钟。",
    )

    requirement_context = build_requirement_context("用户使用手机号验证码登录。", [document])
    review_prompt = build_requirement_review_prompt("用户使用手机号验证码登录。", [document])
    module_prompt = build_module_detail_prompt(
        "用户使用手机号验证码登录。",
        [document],
        module_id="M01",
        module_name="登录模块",
        sub_features=["手机号输入", "验证码发送", "验证码校验"],
        business_rules="- 验证码60秒有效",
        data_constraints="无",
    )

    assert "用户使用手机号验证码登录。" in requirement_context
    assert "登录失败超过 5 次需要锁定 10 分钟。" in review_prompt
    assert "需求评审与模块分解" in review_prompt
    assert "登录模块" in module_prompt
    assert '"cases"' in module_prompt
    assert "覆盖率优先" not in SYSTEM_PROMPT
    assert "资深产品架构师" in SYSTEM_PROMPT
    assert "等价类划分" in SYSTEM_PROMPT


def test_smoke_test_prompt_includes_modules() -> None:
    smoke_prompt = build_smoke_test_prompt(
        "用户登录",
        [],
        '[{"id":"M01","name":"登录"}]',
        "- 密码长度至少8位",
    )
    assert "冒烟测试" in smoke_prompt
    assert "M01" in smoke_prompt


def test_review_prompt_includes_existing_cases() -> None:
    review_prompt = build_review_prompt(
        "用户登录",
        [],
        "- [P0] [登录模块] 登录成功 → 进入首页",
    )
    assert "多视角" in review_prompt
    assert "开发工程师视角" in review_prompt
    assert "登录成功" in review_prompt
