from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.config import Settings
from bot.db.database import Database
from bot.services.drip import DripService
from bot.services.model_catalog import ModelCatalog
from bot.services.openrouter import FileStorage, OpenRouterClient
from bot.services.premium_offer import consume_ignore_if_pending


class AppMiddleware(BaseMiddleware):
    def __init__(
        self,
        db: Database,
        settings: Settings,
        storage: FileStorage,
        openrouter: OpenRouterClient,
        drip: DripService,
        model_catalog: ModelCatalog,
    ) -> None:
        self.db = db
        self.settings = settings
        self.storage = storage
        self.openrouter = openrouter
        self.drip = drip
        self.model_catalog = model_catalog

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["db"] = self.db
        data["settings"] = self.settings
        data["storage"] = self.storage
        data["openrouter"] = self.openrouter
        data["drip"] = self.drip
        data["model_catalog"] = self.model_catalog
        return await handler(event, data)


class ActivityMiddleware(BaseMiddleware):
    def __init__(self, db: Database, drip: DripService) -> None:
        self.db = db
        self.drip = drip

    def _telegram_id(self, event: TelegramObject) -> int | None:
        user = getattr(event, "from_user", None)
        return user.id if user else None

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        telegram_id = self._telegram_id(event)
        if telegram_id is not None:
            await self.db.update_user_activity(telegram_id)
            await self.drip.cancel_all(telegram_id)
            if consume_ignore_if_pending(telegram_id):
                is_premium_click = isinstance(event, CallbackQuery) and (
                    event.data or ""
                ).startswith("styleguide:")
                if not is_premium_click:
                    await self.db.increment_premium_offer_ignored(telegram_id)
        return await handler(event, data)
