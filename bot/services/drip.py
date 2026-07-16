from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.copy import active_copy
from bot.db.database import Database
from bot.services.analytics import Analytics
from bot.services.proactive_guard import TOUCHPOINT_DRIP, ProactiveGuard

logger = logging.getLogger(__name__)

DRIP_CHAIN: dict[str, tuple[str, int]] = {
    "T2": ("T3", 24 * 3600),
    "T3": ("T4", 72 * 3600),
}


def drip_opt_out_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=active_copy().drip_opt_out,
                    callback_data="drip:opt_out",
                )
            ],
        ],
    )


def _normalize_dt(dt_str: str) -> str:
    return dt_str.replace("T", " ").replace("Z", "")[:19]


class DripService:
    def __init__(self, db: Database, guard: ProactiveGuard | None = None) -> None:
        self.db = db
        self.guard = guard

    async def schedule(
        self, telegram_id: int, drip_id: str, delay_seconds: int
    ) -> None:
        scheduled_at = (
            datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
        ).strftime("%Y-%m-%d %H:%M:%S")
        await self.schedule_at(telegram_id, drip_id, scheduled_at)

    async def schedule_at(
        self, telegram_id: int, drip_id: str, scheduled_at: str
    ) -> None:
        await self.db.schedule_drip(telegram_id, drip_id, _normalize_dt(scheduled_at))

    async def cancel_all(self, telegram_id: int) -> None:
        await self.db.cancel_drips_for_user(telegram_id)

    async def fetch_due(self, limit: int = 10) -> list:
        return await self.db.fetch_due_drips(limit)

    async def _recent_drip_sent(self, telegram_id: int, hours: int = 24) -> bool:
        cursor = await self.db.conn.execute(
            """
            SELECT 1 FROM drip_jobs
            WHERE telegram_id = ?
              AND sent_at IS NOT NULL
              AND sent_at > datetime('now', ?)
            LIMIT 1
            """,
            (telegram_id, f"-{hours} hours"),
        )
        return await cursor.fetchone() is not None

    def _render_message(self, drip_id: str, balance: int) -> str | None:
        template = active_copy().drip_messages.get(drip_id)
        if not template:
            return None
        return template.format(balance=balance)

    async def process_due(self, bot: Bot) -> None:
        due = await self.fetch_due(limit=20)
        analytics = Analytics(self.db)

        for job in due:
            telegram_id = int(job["telegram_id"])
            drip_id = job["drip_id"]
            user = await self.db.fetch_user(telegram_id)
            if not user or user["drip_opt_out"]:
                await self.db.conn.execute(
                    "UPDATE drip_jobs SET cancelled = 1 WHERE id = ?",
                    (job["id"],),
                )
                await self.db.conn.commit()
                continue

            if drip_id != "post_purchase_upsell" and await self._recent_drip_sent(
                telegram_id
            ):
                continue

            balance = await self.db.get_balance(telegram_id)
            text = self._render_message(drip_id, balance)
            if not text:
                await self.db.mark_drip_sent(int(job["id"]))
                continue

            if self.guard and not await self.guard.can_send(
                telegram_id, TOUCHPOINT_DRIP
            ):
                await analytics.track(telegram_id, "proactive_suppressed", drip_id)
                await self.db.conn.execute(
                    "UPDATE drip_jobs SET cancelled = 1 WHERE id = ?",
                    (job["id"],),
                )
                await self.db.conn.commit()
                continue

            try:
                await bot.send_message(
                    telegram_id,
                    text,
                    reply_markup=drip_opt_out_keyboard(),
                )
                await self.db.mark_drip_sent(int(job["id"]))
                await analytics.track(telegram_id, "drip_sent", drip_id)

                next_drip = DRIP_CHAIN.get(drip_id)
                if next_drip:
                    next_id, delay = next_drip
                    await self.schedule(telegram_id, next_id, delay)
            except Exception:
                logger.exception(
                    "Failed to send drip %s to %s", drip_id, telegram_id
                )
