"""LLMClient — the single unified LLM abstraction for all INGOT agents.

Routes to any LiteLLM-supported backend (Claude, OpenAI, Ollama, OpenAI-compatible).
Response path priority:
  1. Native tool call  → JSON parse → Pydantic validate
  2. Content as JSON   → Pydantic validate
  3. XML tag fallback  → Pydantic validate
Raises LLMError after all retries; LLMValidationError when response cannot be parsed.
"""
from __future__ import annotations

import logging
import re
from typing import Type, TypeVar

from litellm import acompletion
from pydantic import BaseModel
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ingot.agents.exceptions import LLMError, LLMValidationError
from ingot.llm.fallback import xml_extract

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger("ingot.llm")


class LLMClient:
    def __init__(self, model: str, max_retries: int = 3):
        self.model = model
        self.max_retries = max_retries
        self._retry_decorator = retry(
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=30),
            retry=retry_if_exception_type(LLMError),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )

    async def complete(
        self,
        messages: list[dict],
        response_schema: Type[T],
        tools: list[dict] | None = None,
        *,
        use_xml_fallback: bool = True,
    ) -> T:
        """Call LLM and return a validated Pydantic instance.

        Args:
            messages: List of {"role": ..., "content": ...} dicts.
            response_schema: Pydantic model class to validate the response against.
            tools: Optional list of tool definitions for structured output.
            use_xml_fallback: Fall back to XML tag extraction when JSON parsing fails.

        Returns:
            Validated instance of response_schema.

        Raises:
            LLMError: Backend unreachable or all retries exhausted.
            LLMValidationError: Response received but cannot be parsed/validated.
        """
        inner = self._retry_decorator(self._call_once)
        return await inner(messages, response_schema, tools, use_xml_fallback)

    async def _call_once(
        self,
        messages: list[dict],
        response_schema: Type[T],
        tools: list[dict] | None,
        use_xml_fallback: bool,
    ) -> T:
        try:
            kwargs: dict = {"model": self.model, "messages": messages}
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            response = await acompletion(**kwargs)
            raw = response.choices[0].message
            finish_reason = response.choices[0].finish_reason or ""

            # Path 1: Native tool call
            if raw.tool_calls:
                args_json = raw.tool_calls[0].function.arguments
                try:
                    return response_schema.model_validate_json(args_json)
                except Exception as e:
                    logger.debug(
                        "Tool call JSON validation failed, trying content fallback: %s", e
                    )

            # Path 2: Content as JSON (strip markdown fences if present)
            content = raw.content or ""
            if content:
                json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
                json_str = json_match.group(1).strip() if json_match else content.strip()
                try:
                    return response_schema.model_validate_json(json_str)
                except Exception:
                    pass  # fall through to XML

            # Path 3: XML tag extraction
            if use_xml_fallback and content:
                return xml_extract(content, response_schema)

            raise LLMValidationError(
                f"LLM response could not be parsed for schema {response_schema.__name__}",
                raw_content=content,
            )

        except (LLMValidationError, LLMError):
            raise  # already typed — don't wrap
        except Exception as e:
            raise LLMError(f"LLM backend error: {e}", cause=e) from e
