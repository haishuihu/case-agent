from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Union


@dataclass
class ChatCompletionResult:
    content: str
    finish_reason: Optional[str]
    model_name: str


class BaseLLMClient(ABC):
    """LLM Client 基类，定义统一的调用接口。"""

    @abstractmethod
    def create_chat_completion(
        self,
        system_prompt: str,
        user_content: Union[str, list[dict[str, object]]],
        max_tokens: Optional[int] = None,
    ) -> ChatCompletionResult:
        raise NotImplementedError
