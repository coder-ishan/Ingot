"""Tests for ingot.llm.client.LLMClient.complete()."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from ingot.agents.exceptions import LLMError, LLMValidationError
from ingot.llm.client import LLMClient


class ResponseSchema(BaseModel):
    name: str
    score: int


def _make_response(content=None, tool_args=None):
    """Build a mock acompletion response."""
    msg = MagicMock()
    msg.content = content
    if tool_args:
        tool_call = MagicMock()
        tool_call.function.arguments = tool_args
        msg.tool_calls = [tool_call]
    else:
        msg.tool_calls = None
    choice = MagicMock()
    choice.message = msg
    choice.finish_reason = "stop"
    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.fixture
def client():
    return LLMClient(model="ollama/llama3.1", max_retries=1)


async def test_path1_tool_call(client):
    args = json.dumps({"name": "Acme", "score": 9})
    with patch("ingot.llm.client.acompletion", new_callable=AsyncMock) as mock_ac:
        mock_ac.return_value = _make_response(tool_args=args)
        result = await client.complete(
            messages=[{"role": "user", "content": "test"}],
            response_schema=ResponseSchema,
            tools=[{"type": "function", "function": {"name": "fn"}}],
        )
    assert result.name == "Acme"
    assert result.score == 9


async def test_path2_content_json(client):
    content = '{"name": "Beta", "score": 7}'
    with patch("ingot.llm.client.acompletion", new_callable=AsyncMock) as mock_ac:
        mock_ac.return_value = _make_response(content=content)
        result = await client.complete(
            messages=[{"role": "user", "content": "test"}],
            response_schema=ResponseSchema,
        )
    assert result.name == "Beta"
    assert result.score == 7


async def test_path3_xml_fallback(client):
    content = "<name>Gamma Corp</name><score>5</score>"
    with patch("ingot.llm.client.acompletion", new_callable=AsyncMock) as mock_ac:
        mock_ac.return_value = _make_response(content=content)
        result = await client.complete(
            messages=[{"role": "user", "content": "test"}],
            response_schema=ResponseSchema,
        )
    assert result.name == "Gamma Corp"
    assert result.score == 5


async def test_backend_error_raises_llm_error(client):
    with patch("ingot.llm.client.acompletion", new_callable=AsyncMock) as mock_ac:
        mock_ac.side_effect = RuntimeError("connection refused")
        with pytest.raises(LLMError):
            await client.complete(
                messages=[{"role": "user", "content": "test"}],
                response_schema=ResponseSchema,
            )


async def test_unparseable_raises_llm_validation_error(client):
    content = "not json, not xml"
    with patch("ingot.llm.client.acompletion", new_callable=AsyncMock) as mock_ac:
        mock_ac.return_value = _make_response(content=content)
        with pytest.raises(LLMValidationError):
            await client.complete(
                messages=[{"role": "user", "content": "test"}],
                response_schema=ResponseSchema,
            )


async def test_xml_fallback_disabled_raises_llm_validation_error(client):
    """When use_xml_fallback=False, XML content must raise LLMValidationError."""
    content = "<name>Acme</name><score>5</score>"
    with patch("ingot.llm.client.acompletion", new_callable=AsyncMock) as mock_ac:
        mock_ac.return_value = _make_response(content=content)
        with pytest.raises(LLMValidationError):
            await client.complete(
                messages=[{"role": "user", "content": "test"}],
                response_schema=ResponseSchema,
                use_xml_fallback=False,
            )


async def test_tool_call_invalid_json_falls_back_to_content(client):
    """Invalid tool-call JSON should fall through to the content JSON path."""
    content = '{"name": "Delta", "score": 3}'
    with patch("ingot.llm.client.acompletion", new_callable=AsyncMock) as mock_ac:
        mock_ac.return_value = _make_response(
            content=content,
            tool_args="not-valid-json{{{",  # Malformed JSON triggers fallback
        )
        result = await client.complete(
            messages=[{"role": "user", "content": "test"}],
            response_schema=ResponseSchema,
            tools=[{"type": "function", "function": {"name": "fn"}}],
        )
    assert result.name == "Delta"
    assert result.score == 3
