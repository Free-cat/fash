from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bot.db.database import Database
from bot.services.generation_guard import GenerationGuard

TOUCHPOINT_PREMIUM = "premium_offer"
TOUCHPOINT_DRIP = "drip"

_PREMIUM_ACTIVITY_MINUTES = 2
_DRIP_ACTIVITY_MINUTES = 10
_PREMIUM_COOLDOWN_HOURS = 4


class ProactiveGuard:
    def __init__(self, db: Database) -> None:
        self.db = db
        self._generation_guard = GenerationGuard(db)

    async def can_send(
        self,
        telegram_id: int,
        touchpoint: str,
        *,
        generation_id: int | None = None,
    ) -> bool:
        if await self._generation_guard.is_locked(telegram_id):
            return False

        user = await self.db.fetch_user(telegram_id)
        if not user:
            return False

        activity_minutes = (
            _PREMIUM_ACTIVITY_MINUTES
            if touchpoint == TOUCHPOINT_PREMIUM
            else _DRIP_ACTIVITY_MINUTES
        )
        if self._recently_active(user["last_active_at"], activity_minutes):
            return False

        if touchpoint == TOUCHPOINT_PREMIUM:
            return await self._premium_allowed(user, generation_id)
        return True

    async def _premium_allowed(self, user, generation_id: int | None) -> bool:
        if user["premium_offer_paused_until"]:
            if self._is_future(user["premium_offer_paused_until"]):
                return False
            await self.db.reset_premium_offer_ignored(user["telegram_id"])

        if user["premium_offer_last_shown_at"]:
            if self._within_hours(user["premium_offer_last_shown_at"], _PREMIUM_COOLDOWN_HOURS):
                return False

        if generation_id is not None:
            gen = await self.db.get_generation_for_user_by_id(
                generation_id, user["telegram_id"]
            )
            if gen and gen["style_guide_path"]:
                return False
        return True

    @staticmethod
    def _parse_dt(value: str) -> datetime:
        return datetime.fromisoformat(value.replace(" ", "T")).replace(tzinfo=timezone.utc)

    def _recently_active(self, last_active_at: str | None, minutes: int) -> bool:
        if not last_active_at:
            return False
        return datetime.now(timezone.utc) - self._parse_dt(last_active_at) < timedelta(minutes=minutes)

    def _within_hours(self, value: str, hours: int) -> bool:
        return datetime.now(timezone.utc) - self._parse_dt(value) < timedelta(hours=hours)

    def _is_future(self, value: str) -> bool:
        return self._parse_dt(value) > datetime.now(timezone.utc)
