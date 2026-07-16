from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.copy import active_copy
from bot.db.database import Database
from bot.services.openrouter import FileStorage

router = Router(name="privacy")


async def purge_inactive_users(db: Database, storage: FileStorage) -> None:
    rows = await db.fetch_users_inactive_since(days=90)
    for row in rows:
        storage.delete_user_dir(row["telegram_id"])
        await db.delete_user_completely(row["telegram_id"])


@router.message(Command("delete_my_data"))
async def delete_my_data(
    message: Message,
    db: Database,
    storage: FileStorage,
) -> None:
    user = await db.fetch_user(message.from_user.id)
    if not user:
        return

    storage.delete_user_dir(message.from_user.id)
    await db.delete_user_completely(message.from_user.id)
    await message.answer(active_copy().delete_confirmation)
