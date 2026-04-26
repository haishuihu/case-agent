from __future__ import annotations

import logging
from typing import Optional, Union

import httpx

from app.core.config import ModelProfile
from app.services.llm_clients.base import BaseLLMClient, ChatCompletionResult

logger = logging.getLogger(__name__)

_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_API_VERSION = "2023-06-01"


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude API 客户端，使用 Anthropic 专属接口格式。"""

    def __init__(self, profile: ModelProfile):
        self.profile = profile

    def create_chat_completion(
        self,
        system_prompt: str,
        user_content: Union[str, list[dict[str, object]]],
        max_tokens: Optional[int] = None,
    ) -> ChatCompletionResult:
        effective_max_tokens = max_tokens or self.profile.max_output_tokens

        # Build messages list — handle both string and structured content
        if isinstance(user_content, str):
            messages = [{"role": "user", "content": user_content}]
        else:
            messages = [{"role": "user", "content": user_content}]

        # Anthropic uses system in top-level, not as a message
        payload = {
            "model": self.profile.model_name,
            "max_tokens": min(effective_max_tokens, 8192),
            "system": system_prompt,
            "messages": messages,
        }

        headers = {
            "x-api-key": self.profile.api_key,
            "anthropic-version": _ANTHROPIC_API_VERSION,
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=self.profile.timeout_seconds) as client:
                resp = client.post(_ANTHROPIC_API_URL, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise ValueError(f"{self.profile.label} 请求超时。") from exc
        except httpx.ConnectError as exc:
            raise ValueError(f"{self.profile.label} 无法连接到服务器。") from exc

        if resp.status_code == 401:
            raise ValueError(f"{self.profile.label} API Key 无效或未开通接口权限。")
        if resp.status_code == 429:
            raise ValueError(f"{self.profile.label} 请求频率超限或额度不足，请稍后重试。")
        if resp.status_code != 200:
            try:
                err = resp.json()
                msg = err.get("error", {}).get("message", "") or resp.text[:200]
            except Exception:
                msg = resp.text[:200]
            raise ValueError(f"{self.profile.label} 接口返回错误（{resp.status_code}）：{msg}")

        data = resp.json()
        content_blocks = data.get("content", [])
        if content_blocks and content_blocks[0].get("type") == "text":
            text = content_blocks[0].get("text", "")
        else:
            text = ""

        return ChatCompletionResult(
            content=text,
            finish_reason=data.get("stop_reason"),
            model_name=data.get("model", self.profile.model_name),
        )
