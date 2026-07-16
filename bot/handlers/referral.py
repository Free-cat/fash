from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.copy import active_copy
from bot.filters import TextIs

router = Router(name="referral")


async def _referral_link(bot_username: str, user_id: int) -> str:
    return f"https://t.me/{bot_username}?start=ref_{user_id}"


@router.callback_query(F.data == "action:invite")
async def invite_friends(callback: CallbackQuery) -> None:
    copy = active_copy()
    bot = callback.bot
    me = await bot.get_me()
    link = await _referral_link(me.username, callback.from_user.id)
    await callback.message.answer(
        f"{copy.invite_text}\n\n{link}",
    )
    await callback.answer()


@router.message(TextIs("btn_invite"))
async def invite_friends_message(message: Message) -> None:
    copy = active_copy()
    me = await message.bot.get_me()
    link = await _referral_link(me.username, message.from_user.id)
    await message.answer(f"{copy.invite_text}\n\n{link}")
