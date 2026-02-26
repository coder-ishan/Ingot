import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

# Ensure the package is importable without requiring an editable install.
# `alembic` is typically run from the project root; src/ may not be on sys.path.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
from sqlmodel import SQLModel

# MUST import all models to register them in SQLModel.metadata before autogenerate
from ingot.db.models import (  # noqa: F401
    UserProfile, Lead, LeadContact, IntelBrief, Match, Email, FollowUp,
    Campaign, AgentLog, Venue, OutreachMetric, UnsubscribedEmail,
)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def get_url() -> str:
    from ingot.config.manager import ConfigManager
    cm = ConfigManager()
    return f"sqlite+aiosqlite:///{cm.get_db_path()}"


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    url = get_url()
    connectable = create_async_engine(url, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
