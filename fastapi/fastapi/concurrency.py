import asyncio
from collections.abc import AsyncGenerator, Coroutine, Sequence
from contextlib import AbstractContextManager
from contextlib import asynccontextmanager as asynccontextmanager
from typing import TypeVar

import anyio.to_thread
from anyio import CapacityLimiter
from fastapi.exceptions import ConcurrencyError
from starlette.concurrency import iterate_in_threadpool as iterate_in_threadpool  # noqa
from starlette.concurrency import run_in_threadpool as run_in_threadpool  # noqa
from starlette.concurrency import (  # noqa
    run_until_first_complete as run_until_first_complete,
)

_T = TypeVar("_T")


async def run_concurrently(
    coroutines: Sequence[Coroutine[None, None, _T]],
    max_concurrency: int,
    *,
    timeout: float | None = None,
) -> list[_T]:
    semaphore = asyncio.Semaphore(max_concurrency)
    results: list[_T | Exception] = [None] * len(coroutines)  # type: ignore
    cancelled = False

    async def run_one(index: int, coro: Coroutine[None, None, _T]) -> None:
        nonlocal cancelled
        if cancelled:
            coro.close()
            return
        async with semaphore:
            if cancelled:
                coro.close()
                return
            try:
                results[index] = await coro
            except Exception as e:
                results[index] = e

    tasks = [asyncio.create_task(run_one(i, c)) for i, c in enumerate(coroutines)]

    try:
        done, pending = await asyncio.wait(
            tasks,
            timeout=timeout,
            return_when=asyncio.ALL_COMPLETED,
        )
    except Exception:
        for t in tasks:
            t.cancel()
        raise

    if timeout is not None and len(done) < len(tasks):
        cancelled = True
        for t in pending:
            t.cancel()
        for i, t in enumerate(tasks):
            if t in pending:
                results[i] = asyncio.TimeoutError(
                    f"Task {i} timed out after {timeout}s"
                )

    errors = [r for r in results if isinstance(r, Exception)]
    if errors:
        raise ConcurrencyError(errors)  # type: ignore

    return results  # type: ignore


@asynccontextmanager
async def contextmanager_in_threadpool(
    cm: AbstractContextManager[_T],
) -> AsyncGenerator[_T, None]:
    # blocking __exit__ from running waiting on a free thread
    # can create race conditions/deadlocks if the context manager itself
    # has its own internal pool (e.g. a database connection pool)
    # to avoid this we let __exit__ run without a capacity limit
    # since we're creating a new limiter for each call, any non-zero limit
    # works (1 is arbitrary)
    exit_limiter = CapacityLimiter(1)
    try:
        yield await run_in_threadpool(cm.__enter__)
    except Exception as e:
        ok = bool(
            await anyio.to_thread.run_sync(
                cm.__exit__, type(e), e, e.__traceback__, limiter=exit_limiter
            )
        )
        if not ok:
            raise e
    else:
        await anyio.to_thread.run_sync(
            cm.__exit__, None, None, None, limiter=exit_limiter
        )
