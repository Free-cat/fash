import pytest

from bot.db.database import Database
from bot.services.generation_guard import CircuitBreaker, GenerationGuard


@pytest.mark.asyncio
async def test_only_one_concurrent_generation(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    guard = GenerationGuard(db)
    assert await guard.acquire(100) is True
    assert await guard.acquire(100) is False
    await guard.release(100)
    assert await guard.acquire(100) is True
    await db.close()


def test_circuit_breaker_opens_after_failures():
    guard = GenerationGuard(None)
    cb = CircuitBreaker(threshold=3, window_seconds=600)
    cb.record_failure()
    cb.record_failure()
    assert cb.is_open() is False
    cb.record_failure()
    assert cb.is_open() is True
    _ = guard
