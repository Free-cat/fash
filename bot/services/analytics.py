from __future__ import annotations

from bot.db.database import Database


class Analytics:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def track(
        self, telegram_id: int, event_name: str, payload: str | None = None
    ) -> None:
        await self.db.conn.execute(
            "INSERT INTO analytics_events (telegram_id, event_name, payload) VALUES (?, ?, ?)",
            (telegram_id, event_name, payload),
        )
        await self.db.conn.commit()

    async def list_events(self, telegram_id: int) -> list[dict]:
        cursor = await self.db.conn.execute(
            """
            SELECT id, telegram_id, event_name, payload, created_at
            FROM analytics_events
            WHERE telegram_id = ?
            ORDER BY id
            """,
            (telegram_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
