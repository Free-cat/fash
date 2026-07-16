import pytest

from bot.db.database import Database
from bot.services.generation_guard import CircuitBreaker, GenerationGuard


@pytest.mark.asyncio
async def test_clear_all_generation_locks(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.conn.execute(
        "INSERT INTO generation_locks (telegram_id, started_at) VALUES (?, datetime('now'))",
        (111,),
    )
    await db.conn.commit()
    removed = await db.clear_all_generation_locks()
    assert removed == 1
    guard = GenerationGuard(db)
    assert await guard.is_locked(111) is False
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
