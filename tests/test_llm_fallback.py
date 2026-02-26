"""Tests for ingot.llm.fallback.xml_extract."""
from typing import Optional

import pytest
from pydantic import BaseModel

from ingot.agents.exceptions import LLMValidationError
from ingot.llm.fallback import xml_extract


class SimpleSchema(BaseModel):
    company_name: str
    industry: str


class ListSchema(BaseModel):
    skills: list[str]


class OptionalListSchema(BaseModel):
    tags: Optional[list[str]] = None


class RequiredSchema(BaseModel):
    required_field: str  # no default — must be present


def test_flat_schema_extraction():
    content = "<company_name>Acme Corp</company_name><industry>SaaS</industry>"
    result = xml_extract(content, SimpleSchema)
    assert result.company_name == "Acme Corp"
    assert result.industry == "SaaS"


def test_list_field_newline_split():
    content = "<skills>Python\nGo\nRust</skills>"
    result = xml_extract(content, ListSchema)
    assert result.skills == ["Python", "Go", "Rust"]


def test_optional_list_unwrapped():
    content = "<tags>alpha\nbeta</tags>"
    result = xml_extract(content, OptionalListSchema)
    assert result.tags == ["alpha", "beta"]


def test_missing_required_field_raises():
    content = "<industry>SaaS</industry>"  # company_name missing
    with pytest.raises(LLMValidationError):
        xml_extract(content, SimpleSchema)


def test_empty_content_raises_for_required_schema():
    with pytest.raises(LLMValidationError):
        xml_extract("", RequiredSchema)
