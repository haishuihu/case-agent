from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import ModelProfile, get_settings

if TYPE_CHECKING:
    from app.models.llm_config import LLMConfig

logger = logging.getLogger(__name__)

# Lazy DB session (avoids import-time side-effects before tables exist)
_settings = get_settings()
_db_url = _settings.database_url
_db_connect_args = {"check_same_thread": False} if _db_url.startswith("sqlite") else {}
_engine = create_engine(_db_url, future=True, pool_pre_ping=True, connect_args=_db_connect_args)
_DBSession = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)


def _get_db_session() -> Session:
    return _DBSession()


def _db_has_llm_configs(session: Session) -> bool:
    from sqlalchemy import text
    try:
        session.execute(text("SELECT 1 FROM llm_configs LIMIT 1"))
        return True
    except Exception:
        return False


def _build_profile_from_db_config(cfg: "LLMConfig") -> ModelProfile:
    return ModelProfile(
        key=cfg.id,
        label=f"{cfg.name} ({cfg.model_name})",
        provider=cfg.provider,
        base_url=cfg.base_url,
        api_key=cfg.api_key,
        model_name=cfg.model_name,
        max_output_tokens=cfg.max_output_tokens,
        timeout_seconds=cfg.timeout_seconds,
        supports_vision=cfg.supports_vision,
        supports_structured_output=cfg.supports_structured_output,
        extra_body=cfg.extra_config or {},
    )


def list_model_profiles() -> list[ModelProfile]:
    """供 UI 选择器展示的全部模型。

    优先从数据库返回 is_active=True 的配置；若数据库为空则回退到 .env 配置。
    已配置 API Key 的排在最前。
    """
    settings = get_settings()

    try:
        db = _get_db_session()
        try:
            from app.models.llm_config import LLMConfig
            configs = (
                db.query(LLMConfig)
                .filter(LLMConfig.is_active == True)  # noqa: E712
                .order_by(LLMConfig.is_default.desc(), LLMConfig.display_order, LLMConfig.created_at)
                .all()
            )
            if configs:
                profiles = [_build_profile_from_db_config(c) for c in configs]
                if settings.llm_max_tokens:
                    for p in profiles:
                        p.max_output_tokens = settings.llm_max_tokens
                return profiles
        finally:
            db.close()
    except Exception as e:
        logger.warning("[model_registry] DB query failed, falling back to env: %s", e)

    # Fallback: env profiles (all, regardless of API key)
    profiles = list(settings.get_model_profiles().values())
    if settings.llm_max_tokens:
        for p in profiles:
            p.max_output_tokens = settings.llm_max_tokens
    return profiles


def get_model_profile(model_key: str | None = None) -> ModelProfile:
    """获取单个模型配置。

    优先级：DB 中 is_default=True 的配置 > .env default > DB 指定 key > env 指定 key
    未配置 API Key 时抛出 ValueError。
    """
    settings = get_settings()

    # Try DB first
    try:
        db = _get_db_session()
        try:
            from app.models.llm_config import LLMConfig

            # If model_key is provided, try exact match in DB
            if model_key:
                cfg = (
                    db.query(LLMConfig)
                    .filter(LLMConfig.id == model_key, LLMConfig.is_active == True)  # noqa: E712
                    .first()
                )
                if cfg:
                    profile = _build_profile_from_db_config(cfg)
                    if settings.llm_max_tokens:
                        profile.max_output_tokens = settings.llm_max_tokens
                    if not profile.api_key.strip():
                        raise ValueError(f"模型 {profile.label} 未配置 API Key。")
                    return profile

            # No key or not found in DB — try default
            cfg = (
                db.query(LLMConfig)
                .filter(LLMConfig.is_default == True, LLMConfig.is_active == True)  # noqa: E712
                .first()
            )
            if cfg:
                profile = _build_profile_from_db_config(cfg)
                if settings.llm_max_tokens:
                    profile.max_output_tokens = settings.llm_max_tokens
                if not profile.api_key.strip():
                    raise ValueError(f"模型 {profile.label} 未配置 API Key。")
                return profile
        finally:
            db.close()
    except ValueError:
        raise
    except Exception as e:
        logger.warning("[model_registry] DB get_model_profile failed: %s", e)

    # Fallback: env profiles
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
