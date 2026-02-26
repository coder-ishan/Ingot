"""Tests for ingot.db.repositories.base.BaseRepository using Lead as the test model."""
from ingot.db.repositories.base import BaseRepository
from ingot.db.models import Lead


async def test_add_returns_with_id(async_session):
    repo = BaseRepository(async_session, Lead)
    lead = Lead(company_name="Acme Corp")
    result = await repo.add(lead)
    assert result.id is not None
    assert result.company_name == "Acme Corp"


async def test_get_existing(async_session):
    repo = BaseRepository(async_session, Lead)
    added = await repo.add(Lead(company_name="Beta Inc"))
    fetched = await repo.get(added.id)
    assert fetched is not None
    assert fetched.company_name == "Beta Inc"


async def test_get_missing_returns_none(async_session):
    repo = BaseRepository(async_session, Lead)
    assert await repo.get(99999) is None


async def test_list_all(async_session):
    repo = BaseRepository(async_session, Lead)
    await repo.add(Lead(company_name="A"))
    await repo.add(Lead(company_name="B"))
    results = await repo.list()
    assert len(results) >= 2


async def test_list_limit_offset(async_session):
    repo = BaseRepository(async_session, Lead)
    for i in range(5):
        await repo.add(Lead(company_name=f"Co{i}"))
    page = await repo.list(limit=2, offset=0)
    assert len(page) == 2


async def test_delete_existing(async_session):
    repo = BaseRepository(async_session, Lead)
    added = await repo.add(Lead(company_name="DeleteMe"))
    deleted = await repo.delete(added.id)
    assert deleted is True
    assert await repo.get(added.id) is None


async def test_delete_missing(async_session):
    repo = BaseRepository(async_session, Lead)
    assert await repo.delete(99999) is False
