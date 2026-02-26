---
plan: 01-03
phase: 01-foundation-and-core-infrastructure
status: complete
completed: 2026-02-26
---

# Plan 01-03 Summary: LLMClient, XML Fallback, Exception Hierarchy

## What Was Built

Typed exception hierarchy, LiteLLM-backed LLMClient with tenacity retry, and XML tag fallback — the single LLM abstraction all 7 agents use.

## Key Files Created

- `src/ingot/agents/exceptions.py` — `IngotError → LLMError, LLMValidationError, DBError, ConfigError, ValidationError, AgentError`; cause chaining; agent name in `AgentError`
- `src/ingot/llm/fallback.py` — `xml_extract(content, schema)`: regex per field name, list fields split on newlines, raises `LLMValidationError` on Pydantic failure
- `src/ingot/llm/schemas.py` — `LLMMessage`, `LLMRequest`, `LLMResponse` Pydantic envelopes
- `src/ingot/llm/client.py` — `LLMClient(model, max_retries=3)` with `complete(messages, response_schema, tools, use_xml_fallback)`

## LLMClient Interface

```python
from ingot.llm.client import LLMClient
from pydantic import BaseModel

class MySchema(BaseModel):
    field: str

client = LLMClient("anthropic/claude-3-5-sonnet-20241022")
result: MySchema = await client.complete(
    messages=[{"role": "user", "content": "..."}],
    response_schema=MySchema,
    tools=[...],          # optional — enables tool-call path
    use_xml_fallback=True # default True — needed for Ollama
)
```

## Response Path Priority

1. Native tool call → `model_validate_json(args)`
2. Content as JSON (strips ` ```json ``` ` fences) → `model_validate_json`
3. XML tag extraction → `xml_extract()` → `model_validate`
4. Raises `LLMValidationError` if all paths fail

## Retry Config (tenacity)

- `stop_after_attempt(3)` — 3 total attempts
- `wait_exponential(multiplier=1, min=2, max=30)` — 2s, 4s, 8s backoff
- Retries on `LLMError` only — `LLMValidationError` is NOT retried (it's a schema mismatch, not a transient error)

## XML Fallback Limitations

- Flat schemas only — nested objects not supported via XML path
- List fields: values split on newlines inside the tag
- Use flat Pydantic schemas for all Ollama agent outputs

## Verification

- Exception hierarchy correct (`issubclass` checks) ✓
- `xml_extract` scalar and list fields ✓
- LLMClient tool-call path ✓
- LLMClient XML fallback path ✓
- `LLMValidationError` raised on garbage response ✓
- Zero direct `anthropic`/`openai` imports in `src/ingot/` ✓

## Commits

- `aaa98bc` feat(01-03): LLMClient, XML fallback, and typed exception hierarchy

## Self-Check: PASSED
