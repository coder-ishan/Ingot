"""XML tag extraction fallback for LLM models without structured tool-call support."""
from __future__ import annotations

import re
import types
import typing
from typing import Type, TypeVar

from pydantic import BaseModel

from ingot.agents.exceptions import LLMValidationError

T = TypeVar("T", bound=BaseModel)


def xml_extract(content: str, schema: Type[T]) -> T:
    """
    Extract field values from XML-like tags in LLM text output and validate
    against a Pydantic schema.

    Flat schemas only — nested objects are not supported.
    List fields are populated by splitting on newlines inside the tag.

    Example input:
        <company_name>Acme Corp</company_name>
        <skills>Python
        Go
        Rust</skills>
    """
    data: dict = {}
    for field_name, field_info in schema.model_fields.items():
        pattern = rf"<{field_name}>(.*?)</{field_name}>"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            raw_value = match.group(1).strip()
            annotation = field_info.annotation
            # Unwrap Optional / Union (e.g. list[str] | None → list[str])
            # Handles both typing.Union (Optional[X]) and PEP-604 X | None syntax
            origin = typing.get_origin(annotation)
            if origin is typing.Union or isinstance(annotation, types.UnionType):
                args = [a for a in typing.get_args(annotation) if a is not types.NoneType]
                annotation = args[0] if args else annotation
                origin = typing.get_origin(annotation)
            if origin is list:
                data[field_name] = [
                    line.strip() for line in raw_value.splitlines() if line.strip()
                ]
            else:
                data[field_name] = raw_value
    try:
        return schema.model_validate(data)
    except Exception as e:
        raise LLMValidationError(
            f"XML fallback validation failed for {schema.__name__}: {e}",
            raw_content=content,
            cause=e,
        ) from e
