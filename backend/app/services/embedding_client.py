from __future__ import annotations

import logging
from typing import Optional

import httpx
from openai import OpenAI

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_openai_client: Optional[OpenAI] = None
_openai_disabled: bool = False


def _uses_dashscope_multimodal(settings) -> bool:
    """百炼 qwen3-vl-embedding 等走原生多模态接口，不可用 OpenAI /v1/embeddings。"""
    name = settings.embedding_model.lower()
    return "vl-embedding" in name


def _get_openai_client() -> Optional[OpenAI]:
    global _openai_client, _openai_disabled
    if _openai_disabled:
        return None
    if _openai_client is not None:
        return _openai_client

    settings = get_settings()
    api_key = settings.embedding_api_key
    base_url = settings.embedding_base_url

    if not api_key:
        logger.info("[embedding] No embedding API key configured — embedding disabled")
        _openai_disabled = True
        return None

    _openai_client = OpenAI(api_key=api_key, base_url=base_url or None, timeout=60)
    logger.info(
        "[embedding] OpenAI-compatible client initialized base_url=%s model=%s",
        base_url or "(default)",
        settings.embedding_model,
    )
    return _openai_client


def is_embedding_available() -> bool:
    settings = get_settings()
    if not settings.embedding_api_key.strip():
        return False
    if _uses_dashscope_multimodal(settings):
        return True
    return _get_openai_client() is not None


def _generate_dashscope_multimodal(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    url = settings.embedding_dashscope_multimodal_url
    headers = {
        "Authorization": f"Bearer {settings.embedding_api_key}",
        "Content-Type": "application/json",
    }

    results: list[list[float]] = []
    # 百炼单次 contents 上限 20
    batch_size = 20
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        payload: dict[str, object] = {
            "model": settings.embedding_model,
            "input": {"contents": [{"text": t} for t in batch]},
        }
        if settings.embedding_dimensions > 0:
            payload["parameters"] = {"dimension": settings.embedding_dimensions}

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
        settings.embedding_model,
        len(results),
        len(results[0]) if results else 0,
    )
    return results


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    settings = get_settings()
    if not settings.embedding_api_key.strip():
        raise RuntimeError("Embedding API 未配置，无法生成向量。")

    if _uses_dashscope_multimodal(settings):
        return _generate_dashscope_multimodal(texts)

    client = _get_openai_client()
    if client is None:
        raise RuntimeError("Embedding API 未配置，无法生成向量。")

    results: list[list[float]] = []
    batch_size = 32
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        kwargs: dict[str, object] = {
            "model": settings.embedding_model,
            "input": batch,
        }
        if settings.embedding_dimensions > 0:
            kwargs["dimensions"] = settings.embedding_dimensions
        response = client.embeddings.create(**kwargs)
        for item in sorted(response.data, key=lambda x: x.index):
            results.append(item.embedding)

    return results


def generate_single_embedding(text: str) -> list[float]:
    return generate_embeddings([text])[0]
