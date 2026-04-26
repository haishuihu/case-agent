from __future__ import annotations

import logging
import time
from typing import Optional, Union

from openai import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, OpenAI, RateLimitError

from app.core.config import ModelProfile, Settings
from app.services.llm_clients.base import BaseLLMClient, ChatCompletionResult

logger = logging.getLogger(__name__)


def _strip_markdown_fence(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return stripped


class OpenAIClient(BaseLLMClient):
    """OpenAI 兼容格式的 LLM 客户端（支持 OpenAI / DeepSeek / MiniMax / 通义等所有兼容 base_url 的 API）。"""

    def __init__(self, settings: Settings, profile: ModelProfile):
        self.settings = settings
        self.profile = profile
        self.client = OpenAI(
            api_key=profile.api_key,
            base_url=profile.base_url,
            timeout=profile.timeout_seconds,
        )

    def create_chat_completion(
        self,
        system_prompt: str,
        user_content: Union[str, list[dict[str, object]]],
        max_tokens: Optional[int] = None,
    ) -> ChatCompletionResult:
        effective_max_tokens = max_tokens or self.profile.max_output_tokens

        request_payload: dict[str, object] = {
            "model": self.profile.model_name,
            "max_tokens": effective_max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        }
        if self.profile.provider != "deepseek" or self.profile.model_name != "deepseek-reasoner":
            request_payload["temperature"] = self.settings.llm_temperature
        if self.profile.extra_body:
            request_payload["extra_body"] = self.profile.extra_body

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = self.client.chat.completions.create(**request_payload)
                break
            except AuthenticationError as exc:
                raise ValueError(f"{self.profile.label} API Key 无效或未开通接口权限。") from exc
            except RateLimitError as exc:
                raise ValueError(f"{self.profile.label} 请求频率超限或额度不足，请稍后重试。") from exc
            except APIStatusError as exc:
                raise ValueError(f"{self.profile.label} 接口返回错误：{exc.status_code}") from exc
            except (APIConnectionError, APITimeoutError) as exc:
                last_error = exc
                if attempt == 2:
                    raise ValueError(f"{self.profile.label} 服务连接失败，请稍后重试。") from exc
                time.sleep(1.5 * (attempt + 1))
        else:
            raise ValueError(f"{self.profile.label} 服务连接失败，请稍后重试。") from last_error

        content = response.choices[0].message.content or ""
        return ChatCompletionResult(
            content=_strip_markdown_fence(content),
            finish_reason=response.choices[0].finish_reason,
            model_name=response.model or self.profile.model_name,
        )
