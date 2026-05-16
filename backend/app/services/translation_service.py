from __future__ import annotations

import logging

from app.prompts.requirement_translation_prompt import (
    SYSTEM_PROMPT_REQUIREMENT_TRANSLATION,
    build_requirement_translation_prompt,
)
from app.services.file_parser import DocumentContext
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


def translate_requirements(
    llm_client: LLMClient,
    requirement_text: str,
    document_contexts: list[DocumentContext] | None = None,
) -> str:
    """Call LLM to translate raw requirements into structured markdown."""
    user_prompt = build_requirement_translation_prompt(
        requirement_text, document_contexts or []
    )

    result = llm_client.create_chat_completion(
        system_prompt=SYSTEM_PROMPT_REQUIREMENT_TRANSLATION,
        user_content=user_prompt,
        max_tokens=8192,
    )

    logger.info(
        "[translation] completed model=%s content_length=%d",
        result.model_name,
        len(result.content),
    )
    return result.content
