"""Tests for ingot.dispatcher.AsyncTaskDispatcher."""
from ingot.dispatcher import AsyncTaskDispatcher


async def _succeed(value):
    return value


async def _fail():
    raise ValueError("intentional failure")


async def test_empty_queue():
    d = AsyncTaskDispatcher()
    results = await d.run_all()
    assert results == []


async def test_single_task():
    d = AsyncTaskDispatcher()
    d.enqueue("task1", _succeed, value=42)
    results = await d.run_all()
    assert len(results) == 1
    assert results[0].success
    assert results[0].result == 42
    assert results[0].task_name == "task1"


async def test_multiple_tasks_all_complete():
    d = AsyncTaskDispatcher(max_workers=3)
    for i in range(5):
        d.enqueue(f"task{i}", _succeed, value=i)
    results = await d.run_all()
    assert len(results) == 5
    assert all(r.success for r in results)


async def test_failing_task_isolated():
    d = AsyncTaskDispatcher(max_workers=2)
    d.enqueue("good", _succeed, value="ok")
    d.enqueue("bad", _fail)
    results = await d.run_all()
    assert len(results) == 2
    successes = [r for r in results if r.success]
    failures = [r for r in results if not r.success]
    assert len(successes) == 1
    assert len(failures) == 1
    assert isinstance(failures[0].error, ValueError)
