from __future__ import annotations

import logging
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.llm_config import EmbeddingConfig, LLMConfig
from app.schemas.llm_config import (
    EmbeddingConfigCreate,
    EmbeddingConfigResponse,
    EmbeddingConfigUpdate,
    LLMConfigCreate,
    LLMConfigResponse,
    LLMConfigUpdate,
    TestConnectionRequest,
    TestConnectionResponse,
)

logger = logging.getLogger(__name__)

# ---- LLM Config CRUD ----


def list_llm_configs(db: Session) -> list[LLMConfigResponse]:
    configs = db.query(LLMConfig).order_by(LLMConfig.display_order, LLMConfig.created_at).all()
    return [LLMConfigResponse.model_validate(c) for c in configs]


def create_llm_config(db: Session, payload: LLMConfigCreate) -> LLMConfigResponse:
    if payload.is_default:
        _clear_default_flags(db, LLMConfig)

    config = LLMConfig(
        name=payload.name,
        provider=payload.provider,
        api_format=payload.api_format,
        base_url=payload.base_url,
        api_key=payload.api_key,
        model_name=payload.model_name,
        max_output_tokens=payload.max_output_tokens,
        timeout_seconds=payload.timeout_seconds,
        supports_vision=payload.supports_vision,
        supports_structured_output=payload.supports_structured_output,
        extra_config=payload.extra_config,
        is_default=payload.is_default,
        is_active=payload.is_active,
        display_order=payload.display_order,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    logger.info("[llm_config] created id=%s name=%s", config.id, config.name)
    return LLMConfigResponse.model_validate(config)


def get_llm_config(db: Session, config_id: str) -> Optional[LLMConfig]:
    return db.query(LLMConfig).filter(LLMConfig.id == config_id).first()


def update_llm_config(
    db: Session, config_id: str, payload: LLMConfigUpdate
) -> Optional[LLMConfigResponse]:
    config = get_llm_config(db, config_id)
    if not config:
        return None

    if payload.is_default is True:
        _clear_default_flags(db, LLMConfig)

    update_data = payload.model_dump(exclude_unset=True, exclude_none=True)
    # api_key: 空字符串也不更新（排除 "api_key": "" 的情况）
    if "api_key" in update_data and update_data["api_key"] == "":
        del update_data["api_key"]

    for field, value in update_data.items():
        setattr(config, field, value)

    db.commit()
    db.refresh(config)
    logger.info("[llm_config] updated id=%s", config.id)
    return LLMConfigResponse.model_validate(config)


def delete_llm_config(db: Session, config_id: str) -> bool:
    config = get_llm_config(db, config_id)
    if not config:
        return False
    db.delete(config)
    db.commit()
    logger.info("[llm_config] deleted id=%s", config_id)
    return True


def set_default_llm_config(db: Session, config_id: str) -> Optional[LLMConfigResponse]:
    config = get_llm_config(db, config_id)
    if not config:
        return None
    _clear_default_flags(db, LLMConfig)
    config.is_default = True
    db.commit()
    db.refresh(config)
    logger.info("[llm_config] set default id=%s", config.id)
    return LLMConfigResponse.model_validate(config)


def _clear_default_flags(db: Session, model_class: type) -> None:
    """清除某模型的所有 is_default 标志。"""
    db.query(model_class).filter(model_class.is_default == True).update(
        {"is_default": False}
    )


# ---- Embedding Config CRUD ----


def list_embedding_configs(db: Session) -> list[EmbeddingConfigResponse]:
    configs = db.query(EmbeddingConfig).order_by(EmbeddingConfig.created_at).all()
    return [EmbeddingConfigResponse.model_validate(c) for c in configs]


def create_embedding_config(
    db: Session, payload: EmbeddingConfigCreate
) -> EmbeddingConfigResponse:
    config = EmbeddingConfig(
        name=payload.name,
        provider=payload.provider,
        api_format=payload.api_format,
        base_url=payload.base_url,
        api_key=payload.api_key,
        model_name=payload.model_name,
        dimensions=payload.dimensions,
        extra_config=payload.extra_config,
        is_active=payload.is_active,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    logger.info("[embedding_config] created id=%s name=%s", config.id, config.name)
    return EmbeddingConfigResponse.model_validate(config)


def get_embedding_config(db: Session, config_id: str) -> Optional[EmbeddingConfig]:
    return db.query(EmbeddingConfig).filter(EmbeddingConfig.id == config_id).first()


def update_embedding_config(
    db: Session, config_id: str, payload: EmbeddingConfigUpdate
) -> Optional[EmbeddingConfigResponse]:
    config = get_embedding_config(db, config_id)
    if not config:
        return None

    update_data = payload.model_dump(exclude_unset=True, exclude_none=True)
    if "api_key" in update_data and update_data["api_key"] == "":
        del update_data["api_key"]

    for field, value in update_data.items():
        setattr(config, field, value)

    db.commit()
    db.refresh(config)
    logger.info("[embedding_config] updated id=%s", config.id)
    return EmbeddingConfigResponse.model_validate(config)


def delete_embedding_config(db: Session, config_id: str) -> bool:
    config = get_embedding_config(db, config_id)
    if not config:
        return False
    db.delete(config)
    db.commit()
    logger.info("[embedding_config] deleted id=%s", config_id)
    return True


# ---- Connection Test ----


def test_connection(payload: TestConnectionRequest) -> TestConnectionResponse:
    try:
        headers: dict[str, str] = {"Authorization": f"Bearer {payload.api_key}"}
        timeout = min(payload.timeout_seconds, 60)

        if payload.api_format == "openai_compatible":
            url = f"{payload.base_url.rstrip('/')}/chat/completions"
            data = {
                "model": payload.model_name,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 5,
            }
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=data, headers=headers)

        elif payload.api_format == "anthropic":
            url = "https://api.anthropic.com/v1/messages"
            headers["x-api-key"] = headers.pop("Authorization", "").replace("Bearer ", "")
            headers["anthropic-version"] = "2023-06-01"
            data = {
                "model": payload.model_name,
                "max_tokens": 5,
                "messages": [{"role": "user", "content": "ping"}],
            }
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=data, headers=headers)

        elif payload.api_format == "google_ai":
            url = f"{payload.base_url.rstrip('/')}/models/{payload.model_name}:generateContent?key={payload.api_key}"
            data = {"contents": [{"parts": [{"text": "ping"}]}]}
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=data)

        else:
            return TestConnectionResponse(ok=False, message=f"不支持的 API 格式：{payload.api_format}")

        if resp.status_code == 200:
            return TestConnectionResponse(ok=True, message="连接成功，API 密钥有效。")
        else:
            try:
                err_body = resp.json()
                err_msg = err_body.get("error", {}).get("message", "") or err_body.get("error", "") or resp.text[:200]
            except Exception:
                err_msg = resp.text[:200]
            return TestConnectionResponse(
                ok=False,
                message=f"连接失败（HTTP {resp.status_code}）：{err_msg}",
            )

    except httpx.TimeoutException:
        return TestConnectionResponse(ok=False, message=f"连接超时（{payload.timeout_seconds}s），请检查 base_url 是否正确。")
    except httpx.ConnectError as e:
        return TestConnectionResponse(ok=False, message=f"无法连接到服务器：{e}")
    except Exception as e:
        logger.exception("[llm_config] test_connection error")
        return TestConnectionResponse(ok=False, message=f"测试失败：{str(e)}")


# ---- Migration ----

def needs_migration(db: Session) -> tuple[bool, bool, bool, bool]:
    """返回 (needs_llm_migration, needs_embedding_migration, env_has_llm, env_has_embedding)"""
    llm_count = db.query(LLMConfig).count()
    emb_count = db.query(EmbeddingConfig).count()

    settings = get_settings()
    env_has_llm = bool(settings.llm_api_key.strip() or settings.deepseek_api_key.strip() or settings.minimax_api_key.strip())
    env_has_embedding = bool(settings.embedding_api_key.strip())

    needs_llm = llm_count == 0 and env_has_llm
    needs_emb = emb_count == 0 and env_has_embedding

    return needs_llm, needs_emb, env_has_llm, env_has_embedding


def migrate_from_env(db: Session) -> dict:
    """将 .env 中的配置迁移到数据库，返回迁移的模型数量。"""
    settings = get_settings()
    migrated = {"llm": 0, "embedding": 0}

    llm_count = db.query(LLMConfig).count()
    if llm_count == 0:
        profiles: list[tuple] = []
        if settings.deepseek_api_key.strip():
            profiles.append((
                f"DeepSeek ({settings.deepseek_model})",
                "deepseek",
                "openai_compatible",
                settings.deepseek_base_url,
                settings.deepseek_api_key,
                settings.deepseek_model,
                settings.deepseek_max_output_tokens,
                settings.deepseek_timeout_seconds,
                settings.deepseek_supports_vision,
                settings.deepseek_supports_structured_output,
                True,
            ))
        if settings.minimax_api_key.strip():
            profiles.append((
                f"MiniMax ({settings.minimax_model})",
                "minimax",
                "openai_compatible",
                settings.minimax_base_url,
                settings.minimax_api_key,
                settings.minimax_model,
                settings.minimax_max_output_tokens,
                settings.minimax_timeout_seconds,
                settings.minimax_supports_vision,
                settings.minimax_supports_structured_output,
                False,
            ))
        if settings.llm_api_key.strip():
            profiles.append((
                f"OpenAI ({settings.llm_model})",
                "openai",
                "openai_compatible",
                settings.llm_base_url,
                settings.llm_api_key,
                settings.llm_model,
                settings.llm_max_tokens,
                settings.llm_timeout_seconds,
                settings.llm_supports_vision,
                True,
                False,
            ))

        for p in profiles:
            cfg = LLMConfig(
                name=p[0], provider=p[1], api_format=p[2],
                base_url=p[3], api_key=p[4], model_name=p[5],
                max_output_tokens=p[6], timeout_seconds=p[7],
                supports_vision=p[8], supports_structured_output=p[9],
                is_default=p[10], is_active=True,
            )
            db.add(cfg)
            migrated["llm"] += 1

    emb_count = db.query(EmbeddingConfig).count()
    if emb_count == 0 and settings.embedding_api_key.strip():
        cfg = EmbeddingConfig(
            name=f"Embedding ({settings.embedding_model})",
            provider="openai",
            api_format="openai_compatible",
            base_url=settings.embedding_base_url,
            api_key=settings.embedding_api_key,
            model_name=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
            is_active=True,
        )
        db.add(cfg)
        migrated["embedding"] = 1

    db.commit()
    if migrated["llm"] or migrated["embedding"]:
        logger.info("[llm_config] migrated from env: %s", migrated)
    return migrated
