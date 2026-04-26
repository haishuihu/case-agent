from __future__ import annotations

from app.core.config import ModelProfile, get_settings


def list_model_profiles() -> list[ModelProfile]:
    """供 UI 选择器展示的全部模型；是否已配置 Key 不影响出现在列表中。"""
    settings = get_settings()
    profiles = list(settings.get_model_profiles().values())
    # 若用户配置了全局 llm_max_tokens，覆盖各 profile 的默认值
    if settings.llm_max_tokens:
        for p in profiles:
            p.max_output_tokens = settings.llm_max_tokens
    return profiles


def get_model_profile(model_key: str | None = None) -> ModelProfile:
    settings = get_settings()
    profiles = settings.get_model_profiles()
    resolved_key = model_key or settings.default_model_key

    if resolved_key not in profiles:
        raise ValueError(f"不支持的模型标识：{resolved_key}")

    profile = profiles[resolved_key]
    if settings.llm_max_tokens:
        profile.max_output_tokens = settings.llm_max_tokens
    if not profile.api_key.strip():
        raise ValueError(f"模型 {profile.label} 未配置 API Key。")

    return profile
