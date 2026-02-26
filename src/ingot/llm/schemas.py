"""Pydantic models for LLM request/response envelopes (internal use)."""
from __future__ import annotations

from pydantic import BaseModel


class LLMMessage(BaseModel):
    role: str   # "system" | "user" | "assistant"
    content: str


class LLMRequest(BaseModel):
    model: str
    messages: list[LLMMessage]
    tools: list[dict] | None = None


class LLMResponse(BaseModel):
    """Internal envelope — callers receive the validated schema instance, not this."""
    content: str
    tool_call_args: str | None = None   # JSON string if tool call
    finish_reason: str
    used_xml_fallback: bool = False
