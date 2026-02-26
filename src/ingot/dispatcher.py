"""
Async task dispatcher using asyncio.Queue.

Redis upgrade path is isolated here — swap queue internals in v2 without
touching any agent or orchestrator code.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class TaskResult:
    task_name: str
    success: bool
    result: Any = None
    error: Exception | None = None


class AsyncTaskDispatcher:
    """
    Worker pool over asyncio.Queue.

    Usage::

        dispatcher = AsyncTaskDispatcher(max_workers=3)
        dispatcher.enqueue("scout", scout_fn, deps=deps, batch=companies)
        results = await dispatcher.run_all()

    All enqueued tasks run concurrently up to ``max_workers``.
    Failed tasks record the exception in TaskResult.error instead of propagating.
    """

    def __init__(self, max_workers: int = 3) -> None:
        self.max_workers = max_workers
        self._queue: asyncio.Queue[tuple[str, Callable, dict]] = asyncio.Queue()
        self._results: list[TaskResult] = []

    def enqueue(self, task_name: str, coro_fn: Callable, **kwargs: Any) -> None:
        """Add a coroutine task to the queue. coro_fn must be an async callable."""
        self._queue.put_nowait((task_name, coro_fn, kwargs))

    async def run_all(self) -> list[TaskResult]:
        """
        Drain the queue using ``max_workers`` concurrent workers.

        Returns all TaskResults (successes and failures) in completion order.
        Safe to call on an empty queue — returns [] immediately.
        """
        self._results = []
        workers = [asyncio.create_task(self._worker()) for _ in range(self.max_workers)]
        await asyncio.gather(*workers)
        return self._results

    async def _worker(self) -> None:
        while True:
            try:
                task_name, coro_fn, kwargs = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            try:
                result = await coro_fn(**kwargs)
                self._results.append(
                    TaskResult(task_name=task_name, success=True, result=result)
                )
            except Exception as exc:  # noqa: BLE001
                self._results.append(
                    TaskResult(task_name=task_name, success=False, error=exc)
                )
            finally:
                self._queue.task_done()
