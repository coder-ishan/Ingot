"""Generic async repository providing CRUD operations over any SQLModel table."""
from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Generic async repository providing CRUD operations over any SQLModel table."""

    def __init__(self, session: AsyncSession, model: type[T]):
        self.session = session
        self.model = model

    async def add(self, obj: T) -> T:
        """Persist a new object and return it refreshed from the database."""
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def get(self, id: int) -> T | None:
        """Fetch a single record by primary key, or None if not found."""
        return await self.session.get(self.model, id)

    async def list(self, limit: int = 100, offset: int = 0) -> list[T]:
        """Return a paginated list of all records for this model."""
        result = await self.session.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def delete(self, id: int) -> bool:
        """Delete a record by primary key. Returns True if deleted, False if not found."""
        obj = await self.get(id)
        if obj is None:
            return False
        self.session.delete(obj)
        await self.session.commit()
        return True
