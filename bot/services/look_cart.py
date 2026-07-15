from __future__ import annotations

from bot.db.database import Database
from bot.services.image_processor import validate_and_process_garment_photo
from bot.services.openrouter import FileStorage

MAX_CART_ITEMS = 5


class LookCartService:
    def __init__(self, db: Database, storage: FileStorage) -> None:
        self.db = db
        self.storage = storage

    async def get_count(self, user_id: int) -> int:
        return len(await self.db.get_look_cart(user_id))

    async def add_garment(
        self,
        user_id: int,
        telegram_id: int,
        raw: bytes,
        generation_id: int,
    ) -> tuple[int, bool]:
        paths = await self.db.get_look_cart(user_id)
        if len(paths) >= MAX_CART_ITEMS:
            return len(paths), True
        processed = validate_and_process_garment_photo(raw)
        path = str(
            self.storage.save_garment_photo(telegram_id, generation_id, processed)
        )
        paths.append(path)
        await self.db.set_look_cart(user_id, paths)
        return len(paths), len(paths) >= MAX_CART_ITEMS

    async def clear(self, user_id: int) -> None:
        await self.db.clear_look_cart(user_id)

    async def paths(self, user_id: int) -> list[str]:
        return await self.db.get_look_cart(user_id)
