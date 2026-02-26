"""Async SQLite engine with WAL mode, session factory, and table initialisation."""
from pathlib import Path

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel


def _get_database_url(base_dir: Path | None = None) -> str:
    if base_dir:
        return f"sqlite+aiosqlite:///{base_dir}/outreach.db"
    from ingot.config.manager import ConfigManager
    cm = ConfigManager()
    return f"sqlite+aiosqlite:///{cm.get_db_path()}"


def create_engine(database_url: str):
    """Create an async SQLite engine with WAL mode and performance PRAGMAs."""
    eng = create_async_engine(
        database_url,
        echo=False,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(eng.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=-64000")   # 64 MB page cache
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return eng


# Module-level engine (overridable in tests via dependency injection)
engine = create_engine(_get_database_url())

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_session():
    """Async context manager yielding an AsyncSession."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db(eng=None):
    """Create all tables from SQLModel metadata. Used for fresh installs and tests."""
    # Import all models so they are registered in SQLModel.metadata
    from ingot.db import models as _  # noqa: F401
    target_engine = eng or engine
    async with target_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
