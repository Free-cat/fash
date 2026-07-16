from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bot.db.database import Database
from bot.services.generation_guard import GenerationGuard

TOUCHPOINT_PREMIUM = "premium_offer"
TOUCHPOINT_DRIP = "drip"

_DRIP_ACTIVITY_MINUTES = 10


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
        idle_since: datetime | None = None,
    ) -> bool:
        if await self._generation_guard.is_locked(telegram_id):
            return False

        user = await self.db.fetch_user(telegram_id)
        if not user:
            return False

        if touchpoint == TOUCHPOINT_PREMIUM:
            return await self._premium_allowed(
                user, generation_id=generation_id, idle_since=idle_since
            )

        if self._recently_active(user["last_active_at"], _DRIP_ACTIVITY_MINUTES):
            return False
        return True

    async def _premium_allowed(
        self,
        user,
        *,
        generation_id: int | None,
        idle_since: datetime | None,
    ) -> bool:
        if user["premium_offer_paused_until"]:
            if self._is_future(user["premium_offer_paused_until"]):
                return False
            await self.db.reset_premium_offer_ignored(user["telegram_id"])

        if idle_since is not None and user["last_active_at"]:
            last_active = self._parse_dt(user["last_active_at"])
            if last_active > idle_since:
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
        return datetime.now(timezone.utc) - self._parse_dt(last_active_at) < timedelta(
            minutes=minutes
        )

    def _is_future(self, value: str) -> bool:
        return self._parse_dt(value) > datetime.now(timezone.utc)
