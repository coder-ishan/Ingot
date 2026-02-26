"""Tests for ingot.llm.schemas — internal LLM request/response envelopes."""
from ingot.llm.schemas import LLMMessage, LLMRequest, LLMResponse


def test_llm_message_construction():
    msg = LLMMessage(role="user", content="hello")
    assert msg.role == "user"
    assert msg.content == "hello"


def test_llm_request_construction():
    req = LLMRequest(
        model="ollama/llama3.1",
        messages=[LLMMessage(role="user", content="test")],
    )
    assert req.model == "ollama/llama3.1"
    assert req.tools is None


def test_llm_request_with_tools():
    req = LLMRequest(
        model="claude-3-5",
        messages=[LLMMessage(role="system", content="sys")],
        tools=[{"type": "function", "function": {"name": "fn"}}],
    )
    assert len(req.tools) == 1


def test_llm_response_construction():
    resp = LLMResponse(content='{"name": "Acme"}', finish_reason="stop")
    assert resp.used_xml_fallback is False
    assert resp.tool_call_args is None


def test_llm_response_with_tool_call():
    resp = LLMResponse(
        content="",
        tool_call_args='{"name": "Beta"}',
        finish_reason="tool_calls",
        used_xml_fallback=False,
    )
    assert resp.tool_call_args is not None


def test_llm_message_roundtrip():
    msg = LLMMessage(role="assistant", content="here is the result")
    dumped = msg.model_dump()
    restored = LLMMessage.model_validate(dumped)
    assert restored.role == "assistant"
    assert restored.content == "here is the result"
