"""Tests for ingot.db.engine functions."""
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ingot.db.engine import _get_database_url, init_db, create_engine


def test_get_database_url_with_base_dir(tmp_path):
    url = _get_database_url(base_dir=tmp_path)
    assert "outreach.db" in url
    assert tmp_path.as_posix() in url


async def test_init_db_creates_tables(in_memory_engine):
    # Tables were created in conftest; verify 'lead' table exists
    async with in_memory_engine.connect() as conn:
        result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='lead'")
        )
        row = result.fetchone()
    assert row is not None, "lead table not created"


async def test_session_yields_async_session(async_session):
    assert isinstance(async_session, AsyncSession)
