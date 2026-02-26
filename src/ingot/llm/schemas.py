"""Pydantic models for LLM request/response envelopes (internal use)."""
# NOTE: These models are not yet wired into LLMClient (which accepts list[dict] for
# compatibility with litellm's interface). They serve as planned typed contracts for
# a future refactor — keep them in sync with the client's actual behaviour.
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
