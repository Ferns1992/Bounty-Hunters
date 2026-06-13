import asyncio

import pytest
from fastapi.concurrency import run_concurrently
from fastapi.exceptions import ConcurrencyError


async def noop() -> int:
    return 42


async def slow(value: int, delay: float) -> int:
    await asyncio.sleep(delay)
    return value


async def failing() -> int:
    raise ValueError("task failed")


async def test_basic_concurrency():
    results = await run_concurrently([noop(), noop(), noop()], max_concurrency=2)
    assert results == [42, 42, 42]


async def test_max_concurrency_one():
    results = await run_concurrently([noop(), noop()], max_concurrency=1)
    assert results == [42, 42]


async def test_max_concurrency_greater_than_count():
    results = await run_concurrently([noop()], max_concurrency=10)
    assert results == [42]


async def test_results_in_order():
    coros = [slow(1, 0.1), slow(2, 0.01), slow(3, 0.05)]
    results = await run_concurrently(coros, max_concurrency=3)
    assert results == [1, 2, 3]


async def test_error_collection():
    with pytest.raises(ConcurrencyError) as exc_info:
        await run_concurrently([failing(), noop()], max_concurrency=2)
    assert len(exc_info.value.exceptions) == 1
    assert isinstance(exc_info.value.exceptions[0], ValueError)
    assert "task failed" in str(exc_info.value.exceptions[0])


async def test_multiple_errors():
    with pytest.raises(ConcurrencyError) as exc_info:
        await run_concurrently([failing(), failing()], max_concurrency=2)
    assert len(exc_info.value.exceptions) == 2


async def test_timeout():
    with pytest.raises(ConcurrencyError) as exc_info:
        slow_coros = [slow(1, 0.5), noop()]
        await run_concurrently(slow_coros, max_concurrency=2, timeout=0.1)
    assert any(
        isinstance(e, asyncio.TimeoutError) for e in exc_info.value.exceptions
    )


async def test_empty_coroutines():
    results = await run_concurrently([], max_concurrency=1)
    assert results == []
