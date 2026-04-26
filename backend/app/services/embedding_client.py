from __future__ import annotations

import logging
from typing import Optional

import httpx
from openai import OpenAI

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_openai_client: Optional[OpenAI] = None
_openai_disabled: bool = False


def _get_db_embedding_config():
    """从数据库查询 active embedding 配置，失败则返回 None。"""
    try:
        from app.core.config import get_settings
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        settings = get_settings()
        db_url = settings.database_url
        connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
        engine = create_engine(db_url, future=True, pool_pre_ping=True, connect_args=connect_args)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
        db = Session()
        try:
            from app.models.llm_config import EmbeddingConfig
            cfg = db.query(EmbeddingConfig).filter(EmbeddingConfig.is_active == True).first()  # noqa: E712
            if cfg:
                return cfg
        finally:
            db.close()
    except Exception as e:
        logger.warning("[embedding] DB lookup failed: %s", e)
    return None


def _uses_dashscope_multimodal(model_name: str) -> bool:
    """百炼 qwen3-vl-embedding 等走原生多模态接口，不可用 OpenAI /v1/embeddings。"""
    return "vl-embedding" in model_name.lower()


def _get_openai_client_from_config(cfg=None, settings=None):
    """从配置对象初始化 OpenAI client。"""
    global _openai_client, _openai_disabled
    if _openai_disabled:
        return None
    if _openai_client is not None:
        return _openai_client

    if cfg:
        api_key = cfg.api_key
        base_url = cfg.base_url
        model_name = cfg.model_name
        dimensions = cfg.dimensions
    else:
        settings = settings or get_settings()
        api_key = settings.embedding_api_key
        base_url = settings.embedding_base_url
        model_name = settings.embedding_model
        dimensions = settings.embedding_dimensions

    if not api_key:
        logger.info("[embedding] No embedding API key configured — embedding disabled")
        _openai_disabled = True
        return None

    _openai_client = OpenAI(api_key=api_key, base_url=base_url or None, timeout=60)
    logger.info(
        "[embedding] OpenAI-compatible client initialized base_url=%s model=%s",
        base_url or "(default)",
        model_name,
    )
    return _openai_client


def _get_embedding_config_values():
    """获取当前有效配置的值，优先从 DB 取，回退到 env。"""
    db_cfg = _get_db_embedding_config()
    if db_cfg:
        return {
            "api_key": db_cfg.api_key,
            "base_url": db_cfg.base_url,
            "model_name": db_cfg.model_name,
            "dimensions": db_cfg.dimensions,
            "from_db": True,
        }

    settings = get_settings()
    return {
        "api_key": settings.embedding_api_key,
        "base_url": settings.embedding_base_url,
        "model_name": settings.embedding_model,
        "dimensions": settings.embedding_dimensions,
        "from_db": False,
    }


def is_embedding_available() -> bool:
    cfg = _get_embedding_config_values()
    if not cfg["api_key"].strip():
        return False
    if _uses_dashscope_multimodal(cfg["model_name"]):
        return True
    return _get_openai_client_from_config() is not None


def _generate_dashscope_multimodal(texts: list[str], model_name: str, api_key: str, dimensions: int) -> list[list[float]]:
    from app.core.config import get_settings

    settings = get_settings()
    url = settings.embedding_dashscope_multimodal_url
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    results: list[list[float]] = []
    batch_size = 20
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        payload: dict[str, object] = {
            "model": model_name,
            "input": {"contents": [{"text": t} for t in batch]},
        }
        if dimensions > 0:
            payload["parameters"] = {"dimension": dimensions}

        with httpx.Client(timeout=120.0) as client:
            response = client.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            raise RuntimeError(
                f"DashScope 多模态 Embedding 失败：HTTP {response.status_code} {response.text[:500]}"
            )

        data = response.json()
        embeddings = data.get("output", {}).get("embeddings", [])
        if len(embeddings) != len(batch):
            raise RuntimeError(
                f"DashScope Embedding 返回数量异常：期望 {len(batch)}，实际 {len(embeddings)}"
            )
        for item in embeddings:
            vec = item.get("embedding")
            if not isinstance(vec, list):
                raise RuntimeError("DashScope Embedding 响应缺少 embedding 向量")
            results.append(vec)

    logger.info(
        "[embedding] dashscope multimodal ok model=%s count=%d dim=%d",
        model_name,
        len(results),
        len(results[0]) if results else 0,
    )
    return results


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    cfg = _get_embedding_config_values()
    if not cfg["api_key"].strip():
        raise RuntimeError("Embedding API 未配置，无法生成向量。")

    if _uses_dashscope_multimodal(cfg["model_name"]):
        return _generate_dashscope_multimodal(texts, cfg["model_name"], cfg["api_key"], cfg["dimensions"])

    client = _get_openai_client_from_config()
    if client is None:
        raise RuntimeError("Embedding API 未配置，无法生成向量。")

    results: list[list[float]] = []
    batch_size = 32
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        kwargs: dict[str, object] = {
            "model": cfg["model_name"],
            "input": batch,
        }
        if cfg["dimensions"] > 0:
            kwargs["dimensions"] = cfg["dimensions"]
        response = client.embeddings.create(**kwargs)
        for item in sorted(response.data, key=lambda x: x.index):
            results.append(item.embedding)

    return results


def generate_single_embedding(text: str) -> list[float]:
    return generate_embeddings([text])[0]
