from __future__ import annotations

from datetime import datetime, timezone

from bot.db.database import Database

MAX_REFERRAL_CREDITS_PER_MONTH = 10


def parse_start_payload(text: str) -> int | None:
    parts = text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].startswith("ref_"):
        return None
    try:
        referrer_id = int(parts[1].removeprefix("ref_"))
    except ValueError:
        return None
    return referrer_id if referrer_id > 0 else None


class ReferralService:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def attach_referral(self, referee_id: int, referrer_id: int) -> None:
        if referee_id == referrer_id:
            return

        referrer = await self.db.fetch_user(referrer_id)
        if not referrer:
            return

        await self.db.record_referral(referrer_id, referee_id)
        await self.db.set_referred_by(referee_id, referrer_id)

    async def on_first_tryon(self, referee_id: int) -> bool:
        cursor = await self.db.conn.execute(
            """
            SELECT referrer_id
            FROM referrals
            WHERE referee_id = ? AND converted_at IS NULL
            """,
            (referee_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return False

        referrer_id = int(row["referrer_id"])
        if not await self._can_reward_referrer(referrer_id):
            await self.db.convert_referral(referee_id)
            return False

        await self.db.add_credits(referrer_id, 1)
        await self._increment_referral_credits(referrer_id)
        await self.db.convert_referral(referee_id)
        return True

    async def _can_reward_referrer(self, referrer_id: int) -> bool:
        referrer = await self.db.fetch_user(referrer_id)
        if not referrer:
            return False

        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        month = referrer["referral_credits_month"]
        count = int(referrer["referral_credits_count"] or 0)

        if month != current_month:
            count = 0

        return count < MAX_REFERRAL_CREDITS_PER_MONTH

    async def _increment_referral_credits(self, referrer_id: int) -> None:
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        referrer = await self.db.fetch_user(referrer_id)
        if not referrer:
            return

        month = referrer["referral_credits_month"]
        count = int(referrer["referral_credits_count"] or 0)
        if month != current_month:
            count = 0

        await self.db.conn.execute(
            """
            UPDATE users
            SET referral_credits_month = ?, referral_credits_count = ?
            WHERE telegram_id = ?
            """,
            (current_month, count + 1, referrer_id),
        )
        await self.db.conn.commit()
