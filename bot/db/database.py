from __future__ import annotations

import aiosqlite
from pathlib import Path

from bot.db.migrations import MIGRATIONS, NEW_TABLES

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL UNIQUE,
    username TEXT,
    balance INTEGER NOT NULL DEFAULT 0,
    onboarding_complete INTEGER NOT NULL DEFAULT 0,
    primary_photo_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS user_photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    path TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    charge_id TEXT NOT NULL UNIQUE,
    stars INTEGER NOT NULL,
    credits INTEGER NOT NULL,
    pack_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS generations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    garment_path TEXT,
    result_path TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
"""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA)
        for migration in MIGRATIONS:
            try:
                await self._conn.execute(migration)
            except aiosqlite.OperationalError:
                pass
        await self._conn.executescript(NEW_TABLES)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database is not connected")
        return self._conn

    async def get_or_create_user(
        self, telegram_id: int, username: str | None, free_credits: int
    ) -> aiosqlite.Row:
        row = await self.fetch_user(telegram_id)
        if row:
            return row

        await self.conn.execute(
            """
            INSERT INTO users (telegram_id, username, balance)
            VALUES (?, ?, ?)
            """,
            (telegram_id, username, free_credits),
        )
        await self.conn.commit()
        row = await self.fetch_user(telegram_id)
        assert row is not None
        return row

    async def fetch_user(self, telegram_id: int) -> aiosqlite.Row | None:
        cursor = await self.conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        return await cursor.fetchone()

    async def count_user_photos(self, user_id: int) -> int:
        cursor = await self.conn.execute(
            "SELECT COUNT(*) AS cnt FROM user_photos WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        return int(row["cnt"])

    async def add_user_photo(self, user_id: int, path: str) -> int:
        cursor = await self.conn.execute(
            "INSERT INTO user_photos (user_id, path) VALUES (?, ?)",
            (user_id, path),
        )
        photo_id = cursor.lastrowid
        await self.conn.execute(
            "UPDATE users SET primary_photo_id = ? WHERE id = ?",
            (photo_id, user_id),
        )
        await self.conn.commit()
        return int(photo_id)

    async def get_primary_photo_path(self, user_id: int) -> str | None:
        cursor = await self.conn.execute(
            """
            SELECT p.path
            FROM users u
            JOIN user_photos p ON p.id = u.primary_photo_id
            WHERE u.id = ?
            """,
            (user_id,),
        )
        row = await cursor.fetchone()
        return row["path"] if row else None

    async def set_onboarding_complete(self, user_id: int) -> None:
        await self.conn.execute(
            "UPDATE users SET onboarding_complete = 1 WHERE id = ?",
            (user_id,),
        )
        await self.conn.commit()

    async def get_balance(self, telegram_id: int) -> int:
        row = await self.fetch_user(telegram_id)
        return int(row["balance"]) if row else 0

    async def deduct_credit(self, telegram_id: int) -> bool:
        cursor = await self.conn.execute(
            """
            UPDATE users
            SET balance = balance - 1
            WHERE telegram_id = ? AND balance > 0
            """,
            (telegram_id,),
        )
        await self.conn.commit()
        return cursor.rowcount > 0

    async def add_credits(self, telegram_id: int, credits: int) -> None:
        await self.conn.execute(
            "UPDATE users SET balance = balance + ? WHERE telegram_id = ?",
            (credits, telegram_id),
        )
        await self.conn.commit()

    async def record_payment(
        self,
        telegram_id: int,
        charge_id: str,
        stars: int,
        credits: int,
        pack_id: str,
    ) -> bool:
        try:
            await self.conn.execute(
                """
                INSERT INTO payments (telegram_id, charge_id, stars, credits, pack_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (telegram_id, charge_id, stars, credits, pack_id),
            )
            await self.conn.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

    async def record_generation(
        self, user_id: int, garment_path: str, result_path: str
    ) -> int:
        cursor = await self.conn.execute(
            """
            INSERT INTO generations (user_id, garment_path, result_path)
            VALUES (?, ?, ?)
            """,
            (user_id, garment_path, result_path),
        )
        await self.conn.commit()
        return int(cursor.lastrowid)

    async def get_generation(
        self, generation_id: int, user_id: int
    ) -> aiosqlite.Row | None:
        cursor = await self.conn.execute(
            "SELECT * FROM generations WHERE id = ? AND user_id = ?",
            (generation_id, user_id),
        )
        return await cursor.fetchone()

    async def set_style_guide_path(
        self, generation_id: int, user_id: int, path: str
    ) -> bool:
        cursor = await self.conn.execute(
            """
            UPDATE generations
            SET style_guide_path = ?, style_guide_at = datetime('now')
            WHERE id = ? AND user_id = ?
            """,
            (path, generation_id, user_id),
        )
        await self.conn.commit()
        return cursor.rowcount > 0

    async def get_generation_for_user_by_id(
        self, generation_id: int, telegram_id: int
    ) -> aiosqlite.Row | None:
        cursor = await self.conn.execute(
            """
            SELECT g.*
            FROM generations g
            JOIN users u ON u.id = g.user_id
            WHERE g.id = ? AND u.telegram_id = ?
            """,
            (generation_id, telegram_id),
        )
        return await cursor.fetchone()

    async def update_user_activity(self, telegram_id: int) -> None:
        await self.conn.execute(
            "UPDATE users SET last_active_at = datetime('now') WHERE telegram_id = ?",
            (telegram_id,),
        )
        await self.conn.commit()

    async def set_referred_by(self, telegram_id: int, referrer_id: int) -> None:
        await self.conn.execute(
            "UPDATE users SET referred_by = ? WHERE telegram_id = ?",
            (referrer_id, telegram_id),
        )
        await self.conn.commit()

    async def increment_total_purchases(self, telegram_id: int) -> None:
        await self.conn.execute(
            """
            UPDATE users
            SET total_purchases = total_purchases + 1
            WHERE telegram_id = ?
            """,
            (telegram_id,),
        )
        await self.conn.commit()

    async def schedule_drip(
        self, telegram_id: int, drip_id: str, scheduled_at: str
    ) -> None:
        await self.conn.execute(
            """
            INSERT OR IGNORE INTO drip_jobs (telegram_id, drip_id, scheduled_at)
            VALUES (?, ?, ?)
            """,
            (telegram_id, drip_id, scheduled_at),
        )
        await self.conn.commit()

    async def fetch_due_drips(self, limit: int = 10) -> list[aiosqlite.Row]:
        cursor = await self.conn.execute(
            """
            SELECT * FROM drip_jobs
            WHERE scheduled_at <= datetime('now')
              AND sent_at IS NULL
              AND cancelled = 0
            ORDER BY scheduled_at
            LIMIT ?
            """,
            (limit,),
        )
        return await cursor.fetchall()

    async def mark_drip_sent(self, drip_job_id: int) -> None:
        await self.conn.execute(
            "UPDATE drip_jobs SET sent_at = datetime('now') WHERE id = ?",
            (drip_job_id,),
        )
        await self.conn.commit()

    async def cancel_drips_for_user(self, telegram_id: int) -> None:
        await self.conn.execute(
            """
            UPDATE drip_jobs
            SET cancelled = 1
            WHERE telegram_id = ? AND sent_at IS NULL
            """,
            (telegram_id,),
        )
        await self.conn.commit()

    async def record_referral(self, referrer_id: int, referee_id: int) -> None:
        await self.conn.execute(
            """
            INSERT OR IGNORE INTO referrals (referrer_id, referee_id)
            VALUES (?, ?)
            """,
            (referrer_id, referee_id),
        )
        await self.conn.commit()

    async def convert_referral(self, referee_id: int) -> None:
        await self.conn.execute(
            """
            UPDATE referrals
            SET converted_at = datetime('now')
            WHERE referee_id = ? AND converted_at IS NULL
            """,
            (referee_id,),
        )
        await self.conn.commit()

    async def delete_user_completely(self, telegram_id: int) -> None:
        user = await self.fetch_user(telegram_id)
        if not user:
            return

        user_id = user["id"]
        await self.conn.execute(
            "DELETE FROM analytics_events WHERE telegram_id = ?", (telegram_id,)
        )
        await self.conn.execute(
            "DELETE FROM drip_jobs WHERE telegram_id = ?", (telegram_id,)
        )
        await self.conn.execute(
            "DELETE FROM generation_locks WHERE telegram_id = ?", (telegram_id,)
        )
        await self.conn.execute(
            "DELETE FROM referrals WHERE referrer_id = ? OR referee_id = ?",
            (telegram_id, telegram_id),
        )
        await self.conn.execute(
            "DELETE FROM payments WHERE telegram_id = ?", (telegram_id,)
        )
        await self.conn.execute(
            "DELETE FROM generations WHERE user_id = ?", (user_id,)
        )
        await self.conn.execute(
            "DELETE FROM user_photos WHERE user_id = ?", (user_id,)
        )
        await self.conn.execute(
            "DELETE FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        await self.conn.commit()

    async def get_admin_stats(self) -> dict[str, int | float]:
        cursor = await self.conn.execute("SELECT COUNT(*) AS cnt FROM users")
        users_row = await cursor.fetchone()
        users = int(users_row["cnt"])

        cursor = await self.conn.execute("SELECT COUNT(*) AS cnt FROM generations")
        generations_row = await cursor.fetchone()
        generations = int(generations_row["cnt"])

        cursor = await self.conn.execute("SELECT COUNT(*) AS cnt FROM payments")
        purchases_row = await cursor.fetchone()
        purchases = int(purchases_row["cnt"])

        cursor = await self.conn.execute("SELECT COALESCE(SUM(stars), 0) AS total FROM payments")
        stars_row = await cursor.fetchone()
        stars = int(stars_row["total"])

        conversion = purchases / users if users > 0 else 0.0

        return {
            "users": users,
            "generations": generations,
            "purchases": purchases,
            "stars": stars,
            "conversion": conversion,
        }

    async def count_generations(self, user_id: int) -> int:
        cursor = await self.conn.execute(
            "SELECT COUNT(*) AS cnt FROM generations WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        return int(row["cnt"])

    async def set_first_tryon_at(self, telegram_id: int) -> None:
        await self.conn.execute(
            """
            UPDATE users
            SET first_tryon_at = datetime('now')
            WHERE telegram_id = ? AND first_tryon_at IS NULL
            """,
            (telegram_id,),
        )
        await self.conn.commit()

    async def set_paywall_shown_at(self, telegram_id: int) -> None:
        await self.conn.execute(
            "UPDATE users SET paywall_shown_at = datetime('now') WHERE telegram_id = ?",
            (telegram_id,),
        )
        await self.conn.commit()

    async def set_drip_opt_out(self, telegram_id: int) -> None:
        await self.conn.execute(
            "UPDATE users SET drip_opt_out = 1 WHERE telegram_id = ?",
            (telegram_id,),
        )
        await self.conn.commit()

    async def fetch_users_inactive_since(self, days: int) -> list[aiosqlite.Row]:
        cursor = await self.conn.execute(
            """
            SELECT telegram_id, last_active_at
            FROM users
            WHERE last_active_at IS NOT NULL
              AND last_active_at < datetime('now', ?)
            """,
            (f"-{days} days",),
        )
        return await cursor.fetchall()
