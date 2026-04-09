from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Union

from openai import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, OpenAI, RateLimitError

from app.core.config import ModelProfile, Settings, get_settings
from app.services.model_registry import get_model_profile
from app.schemas.testcase import GenerationMetadata, TestCaseItem
from app.services.file_parser import DocumentContext, ImageContext
from app.prompts.testcase_prompt import SYSTEM_PROMPT, build_requirement_summary_prompt
from app.services.testcase_parser import parse_requirement_summary_response

logger = logging.getLogger(__name__)


@dataclass
class ChatCompletionResult:
    content: str
    finish_reason: Optional[str]
    model_name: str
    raw_response: str


@dataclass
class LLMGenerationResult:
    markdown: str
    prompt_snapshot: str
    raw_response: str
    model_name: str
    cases: list[TestCaseItem] = field(default_factory=list)
    metadata: Optional[GenerationMetadata] = None


def _strip_markdown_fence(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return stripped


class LLMClient:
    def __init__(self, settings: Settings, profile: ModelProfile):
        self.settings = settings
        self.profile = profile
        if not profile.api_key:
            raise ValueError("未配置 LLM_API_KEY，无法调用大模型接口。")

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
        response_format: Optional[dict[str, object]] = None,
    ) -> ChatCompletionResult:
        effective_max_tokens = max_tokens or self.profile.max_output_tokens

        # Try cache first
        try:
            from app.services.llm_cache import get_llm_cache
            cached = get_llm_cache().get(
                f"SYS:{system_prompt}\nUSER:{user_content}",
                self.profile.model_name,
            )
            if cached is not None:
                logger.info("[llm-cache] HIT model=%s", self.profile.model_name)
                return ChatCompletionResult(
                    content=cached,
                    finish_reason="cache_hit",
                    model_name=self.profile.model_name,
                    raw_response="",
                )
        except Exception as exc:
            logger.warning("[llm-cache] lookup failed: %s", exc)

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
        if response_format is not None and self.profile.supports_structured_output:
            request_payload["response_format"] = response_format
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
        stripped = _strip_markdown_fence(content)
        result = ChatCompletionResult(
            content=stripped,
            finish_reason=response.choices[0].finish_reason,
            model_name=response.model or self.profile.model_name,
            raw_response=response.model_dump_json(indent=2),
        )

        # Write to cache on success
        try:
            from app.services.llm_cache import get_llm_cache
            get_llm_cache().set(
                f"SYS:{system_prompt}\nUSER:{user_content}",
                self.profile.model_name,
                stripped,
            )
            logger.info("[llm-cache] stored model=%s", self.profile.model_name)
        except Exception as exc:
            logger.warning("[llm-cache] write failed: %s", exc)

        return result

    def generate_test_cases(
        self,
        requirement_text: str,
        document_contexts: list[DocumentContext],
        image_contexts: list[ImageContext],
        db_session=None,
        progress_callback=None,
        cancel_check=None,
    ) -> LLMGenerationResult:
        from app.services.testcase_generator import TestCaseGenerator

        result = TestCaseGenerator(self, db_session=db_session).generate(
            requirement_text=requirement_text,
            document_contexts=document_contexts,
            image_contexts=image_contexts,
            progress_callback=progress_callback,
            cancel_check=cancel_check,
        )
        return LLMGenerationResult(
            markdown=result.markdown,
            prompt_snapshot=result.prompt_snapshot,
            raw_response=result.raw_response,
            model_name=result.model_name,
            cases=result.cases,
            metadata=result.metadata,
        )

    def summarize_requirement_from_files(
        self,
        requirement_text: str,
        document_contexts: list[DocumentContext],
        image_contexts: list[ImageContext],
    ) -> dict[str, object]:
        if not requirement_text.strip() and not document_contexts and not image_contexts:
            raise ValueError("请至少填写需求摘要或上传参考文件。")
        if image_contexts and not self.profile.supports_vision:
            raise ValueError("当前模型不支持图片理解，请上传文档或切换为支持视觉的模型。")

        prompt = build_requirement_summary_prompt(requirement_text, document_contexts)
        response = self.create_chat_completion(
            system_prompt=SYSTEM_PROMPT,
            user_content=prompt,
            max_tokens=self.profile.max_output_tokens,
            response_format={"type": "json_object"},
        )
        parsed = parse_requirement_summary_response(response.content)
        has_any_field = bool(
            parsed.summary_text
            or parsed.modules
            or parsed.business_rules
            or parsed.data_constraints
            or parsed.open_questions
        )
        if not has_any_field:
            raise ValueError("未能从上传材料中提炼出有效摘要，请补充文字需求或更换材料后重试。")

        return {
            "summary_text": parsed.summary_text,
            "modules": parsed.modules,
            "business_rules": parsed.business_rules,
            "data_constraints": parsed.data_constraints,
            "open_questions": parsed.open_questions,
            "model_name": response.model_name,
        }


    def create_chat_completion_with_fallback(
        self,
        system_prompt: str,
        user_content: Union[str, list[dict[str, object]]],
        max_tokens: Optional[int] = None,
        response_format: Optional[dict[str, object]] = None,
    ) -> ChatCompletionResult:
        """Try primary model first, fall back to configured fallback model on connection errors."""
        primary_exc: Exception | None = None

        # Try primary
        try:
            return self.create_chat_completion(
                system_prompt, user_content, max_tokens, response_format
            )
        except (APIConnectionError, APITimeoutError) as exc:
            primary_exc = exc
            logger.warning("[llm-client] primary model failed (conn), trying fallback: %s", exc)
        except ValueError as exc:
            if "服务连接失败" in str(exc):
                primary_exc = exc
                logger.warning("[llm-client] primary model failed (ValueError), trying fallback: %s", exc)
            else:
                raise

        # Fall back to alternative model if configured
        settings = get_settings()
        fallback_profile_key: str | None = None
        if self.profile.key == "deepseek" and settings.minimax_api_key:
            fallback_profile_key = "minimax"
        elif self.profile.key == "minimax" and settings.deepseek_api_key:
            fallback_profile_key = "deepseek"

        if fallback_profile_key:
            from app.services.model_registry import get_model_profile
            try:
                fallback_profile = get_model_profile(fallback_profile_key)
                fallback_client = LLMClient(self.settings, fallback_profile)
                logger.info("[llm-client] attempting fallback to %s", fallback_profile_key)
                return fallback_client.create_chat_completion(
                    system_prompt, user_content, max_tokens, response_format
                )
            except Exception as fallback_exc:
                logger.error("[llm-client] fallback model also failed: %s", fallback_exc)

        # Re-raise original error if no fallback available
        raise ValueError(f"{self.profile.label} 服务连接失败，请稍后重试。") from primary_exc


def build_llm_client(model_key: str | None = None) -> LLMClient:
    settings = get_settings()
    profile = get_model_profile(model_key)
    return LLMClient(settings, profile)
