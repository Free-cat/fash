from __future__ import annotations

import time
from dataclasses import dataclass, field

from bot.db.database import Database


@dataclass
class CircuitBreaker:
    threshold: int = 3
    window_seconds: int = 600
    _failures: list[float] = field(default_factory=list)

    def record_failure(self) -> None:
        now = time.time()
        self._failures = [t for t in self._failures if now - t < self.window_seconds]
        self._failures.append(now)

    def record_success(self) -> None:
        self._failures.clear()

    def is_open(self) -> bool:
        now = time.time()
        self._failures = [t for t in self._failures if now - t < self.window_seconds]
        return len(self._failures) >= self.threshold


_circuit_breaker: CircuitBreaker | None = None


class GenerationGuard:
    def __init__(self, db: Database | None) -> None:
        self.db = db

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        global _circuit_breaker
        if _circuit_breaker is None:
            _circuit_breaker = CircuitBreaker()
        return _circuit_breaker

    async def acquire(self, telegram_id: int) -> bool:
        if self.db is None:
            raise RuntimeError("Database is required for acquire")
        cursor = await self.db.conn.execute(
            """
            INSERT OR IGNORE INTO generation_locks (telegram_id, started_at)
            VALUES (?, datetime('now'))
            """,
            (telegram_id,),
        )
        await self.db.conn.commit()
        return cursor.rowcount > 0

    async def release(self, telegram_id: int) -> None:
        if self.db is None:
            return
        await self.db.conn.execute(
            "DELETE FROM generation_locks WHERE telegram_id = ?", (telegram_id,)
        )
        await self.db.conn.commit()

    async def is_locked(self, telegram_id: int) -> bool:
        if self.db is None:
            return False
        cursor = await self.db.conn.execute(
            "SELECT 1 FROM generation_locks WHERE telegram_id = ? LIMIT 1",
            (telegram_id,),
        )
        return await cursor.fetchone() is not None
