"""Shared pytest fixtures for INGOT Phase 1 tests."""
from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel


@pytest.fixture
def tmp_config_dir(tmp_path: Path) -> Path:
    """Return a temp dir that acts as the INGOT base_dir (~/.ingot substitute)."""
    config_dir = tmp_path / "ingot"
    config_dir.mkdir()
    return config_dir


@pytest_asyncio.fixture
async def in_memory_engine():
    """In-memory aiosqlite engine with all tables created. Disposed after each test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    # Register all models in SQLModel.metadata
    from ingot.db import models as _  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(in_memory_engine):
    """Yield a single AsyncSession over the in-memory engine."""
    factory = sessionmaker(in_memory_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
