from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from bot.copy import active_copy
from bot.db.database import Database
from bot.filters import TextIs
from bot.keyboards import (
    deficit_keyboard,
    main_keyboard,
    result_keyboard,
    shop_keyboard,
)
from bot.services.analytics import Analytics
from bot.services.drip import DripService

router = Router(name="tryon")


async def _user_ready(db: Database, telegram_id: int) -> tuple[bool, str | None]:
    copy = active_copy()
    user = await db.fetch_user(telegram_id)
    if not user:
        return False, copy.send_start_first
    if not user["onboarding_complete"]:
        return False, copy.upload_photos_first
    photo_path = await db.get_primary_photo_path(user["id"])
    if not photo_path:
        return False, copy.no_saved_photos
    return True, None


def build_result_message(
    remaining: int,
    total_purchases: int,
    generation_id: int = 0,
) -> tuple[str, InlineKeyboardMarkup]:
    copy = active_copy()
    caption = copy.result_caption

    if remaining > 3:
        caption = f"{caption}\n\n{copy.try_another}"
        keyboard = result_keyboard(remaining, generation_id)
    elif 1 <= remaining <= 3:
        caption = f"{caption}\n\n{copy.low_balance.format(count=remaining)}"
        keyboard = result_keyboard(remaining, generation_id)
    elif remaining == 0 and total_purchases == 0:
        caption = f"{caption}\n\n{copy.paywall}"
        keyboard = shop_keyboard()
    elif remaining == 0 and total_purchases > 0:
        caption = f"{caption}\n\n{copy.deficit}"
        keyboard = deficit_keyboard()
    else:
        keyboard = result_keyboard(remaining, generation_id)

    return caption, keyboard


async def _track_paywall_if_needed(
    message: Message,
    db: Database,
    analytics: Analytics,
    remaining: int,
    total_purchases: int,
) -> None:
    if remaining == 0 and total_purchases == 0:
        await analytics.track(message.from_user.id, "paywall_shown")
        await db.set_paywall_shown_at(message.from_user.id)


async def _handle_drip_triggers(
    drip: DripService,
    db: Database,
    analytics: Analytics,
    telegram_id: int,
    user_id: int,
    remaining: int,
    total_purchases: int,
    gen_count: int,
) -> None:
    if gen_count == 1:
        await db.set_first_tryon_at(telegram_id)
        await analytics.track(telegram_id, "first_tryon")
        await drip.schedule(telegram_id, "T1", delay_seconds=30 * 60)
    elif gen_count == 2:
        await analytics.track(telegram_id, "second_tryon")

    if gen_count == 2 and remaining == 0 and total_purchases == 0:
        await drip.cancel_all(telegram_id)
        await drip.schedule(telegram_id, "T2", delay_seconds=60 * 60)
    elif remaining == 0 and total_purchases > 0:
        await drip.schedule(telegram_id, "T5", delay_seconds=0)


@router.callback_query(F.data == "action:try_another")
async def try_another(callback: CallbackQuery, db: Database) -> None:
    ok, error = await _user_ready(db, callback.from_user.id)
    if not ok:
        await callback.answer(error, show_alert=True)
        return
    balance = await db.get_balance(callback.from_user.id)
    await callback.message.answer(
        active_copy().try_on_hint.format(balance=balance),
        reply_markup=main_keyboard(),
    )
    await callback.answer()


@router.message(TextIs("btn_try_on"))
async def try_on_hint(message: Message, db: Database) -> None:
    ok, error = await _user_ready(db, message.from_user.id)
    if not ok:
        await message.answer(error)
        return
    balance = await db.get_balance(message.from_user.id)
    await message.answer(
        active_copy().try_on_hint.format(balance=balance),
        reply_markup=main_keyboard(),
    )

