from __future__ import annotations

import logging
from typing import Optional, Union

import httpx

from app.core.config import ModelProfile
from app.services.llm_clients.base import BaseLLMClient, ChatCompletionResult

logger = logging.getLogger(__name__)


class GoogleAIClient(BaseLLMClient):
    """Google AI Gemini API 客户端。"""

    def __init__(self, profile: ModelProfile):
        self.profile = profile

    def _build_url(self, method: str = "generateContent") -> str:
        base = self.profile.base_url.rstrip("/")
        return f"{base}/models/{self.profile.model_name}:{method}?key={self.profile.api_key}"

    def create_chat_completion(
        self,
        system_prompt: str,
        user_content: Union[str, list[dict[str, object]]],
        max_tokens: Optional[int] = None,
    ) -> ChatCompletionResult:
        effective_max_tokens = max_tokens or self.profile.max_output_tokens

        # Build contents
        if isinstance(user_content, str):
            contents = [{"parts": [{"text": user_content}]}]
        else:
            contents = [{"parts": [{"text": str(user_content)}]}]

        payload: dict[str, object] = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": min(effective_max_tokens, 8192),
            },
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        try:
            with httpx.Client(timeout=self.profile.timeout_seconds) as client:
                resp = client.post(self._build_url(), json=payload)
        except httpx.TimeoutException as exc:
            raise ValueError(f"{self.profile.label} 请求超时。") from exc
        except httpx.ConnectError as exc:
            raise ValueError(f"{self.profile.label} 无法连接到服务器。") from exc

        if resp.status_code == 401:
            raise ValueError(f"{self.profile.label} API Key 无效。")
        if resp.status_code == 429:
            raise ValueError(f"{self.profile.label} 请求频率超限，请稍后重试。")
        if resp.status_code != 200:
            try:
                err = resp.json()
                msg = err.get("error", {}).get("message", "") or resp.text[:200]
            except Exception:
                msg = resp.text[:200]
            raise ValueError(f"{self.profile.label} 接口返回错误（{resp.status_code}）：{msg}")

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError(f"{self.profile.label} 未返回有效内容。")

        first = candidates[0]
        parts = first.get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts)

        return ChatCompletionResult(
            content=text,
            finish_reason=first.get("finishReason"),
            model_name=self.profile.model_name,
        )
