from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.types import BufferedInputFile, CallbackQuery

from bot.copy import active_copy
from bot.db.database import Database
from bot.keyboards import (
    deficit_keyboard,
    result_keyboard,
    shop_keyboard,
    style_guide_offer_keyboard,
)
from bot.services.analytics import Analytics
from bot.services.generation_guard import GenerationGuard
from bot.services.openrouter import FileStorage, OpenRouterClient, TryOnError

logger = logging.getLogger(__name__)

router = Router(name="styleguide")

STYLE_GUIDE_OFFER_DELAY_SECONDS = 30


@router.callback_query(F.data.startswith("styleguide:"))
async def style_guide_callback(
    callback: CallbackQuery,
    db: Database,
    storage: FileStorage,
    openrouter: OpenRouterClient,
) -> None:
    copy = active_copy()
    telegram_id = callback.from_user.id

    try:
        generation_id = int(callback.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await callback.answer(copy.style_guide_not_found, show_alert=True)
        return

    generation = await db.get_generation_for_user_by_id(generation_id, telegram_id)
    if generation is None:
        await callback.answer(copy.style_guide_not_found, show_alert=True)
        return

    analytics = Analytics(db)
    await analytics.track(telegram_id, "style_guide_clicked")

    if generation["style_guide_path"]:
        style_bytes = storage.read(generation["style_guide_path"])
        await callback.message.answer_photo(
            BufferedInputFile(style_bytes, filename="style_guide.jpg"),
            caption=copy.style_guide_already,
        )
        await callback.answer()
        return

    balance = await db.get_balance(telegram_id)
    if balance < 1:
        user = await db.fetch_user(telegram_id)
        total_purchases = int(user["total_purchases"]) if user else 0
        if total_purchases == 0:
            await callback.message.answer(copy.paywall, reply_markup=shop_keyboard())
        else:
            await callback.message.answer(
                copy.deficit,
                parse_mode="Markdown",
                reply_markup=deficit_keyboard(),
            )
        await callback.answer()
        return

    if not await db.deduct_credit(telegram_id):
        await callback.answer(copy.not_enough_credits, show_alert=True)
        return

    guard = GenerationGuard(db)
    if not await guard.acquire(telegram_id):
        await callback.answer(copy.concurrent, show_alert=True)
        return

    try:
        if guard.circuit_breaker.is_open():
            await db.add_credits(telegram_id, 1)
            await callback.message.answer(copy.circuit_open)
            await callback.answer()
            return

        status = await callback.message.answer(copy.style_guide_generating)
        await callback.answer()

        try:
            result_bytes = storage.read(generation["result_path"])
            guide_bytes = await openrouter.generate_style_guide(result_bytes)
            guard.circuit_breaker.record_success()

            user = await db.fetch_user(telegram_id)
            assert user is not None
            user_id = user["id"]
            guide_path = storage.save_style_guide_photo(
                telegram_id, generation_id, guide_bytes
            )
            await db.set_style_guide_path(generation_id, user_id, str(guide_path))

            remaining = await db.get_balance(telegram_id)
            await analytics.track(telegram_id, "style_guide_generated")

            await status.delete()
            await callback.message.answer_photo(
                BufferedInputFile(guide_bytes, filename="style_guide.jpg"),
                caption=copy.style_guide_caption,
                reply_markup=result_keyboard(remaining, generation_id),
            )
        except TryOnError:
            guard.circuit_breaker.record_failure()
            await db.add_credits(telegram_id, 1)
            await analytics.track(telegram_id, "style_guide_failed")
            try:
                await status.delete()
            except Exception:
                pass
            await callback.message.answer(copy.style_guide_failed)
    finally:
        await guard.release(telegram_id)


async def schedule_style_guide_offer(
    bot: Bot,
    db: Database,
    telegram_id: int,
    generation_id: int,
    balance: int,
) -> None:
    try:
        await asyncio.sleep(STYLE_GUIDE_OFFER_DELAY_SECONDS)

        generation = await db.get_generation_for_user_by_id(generation_id, telegram_id)
        if generation is None or generation["style_guide_path"]:
            return

        balance = await db.get_balance(telegram_id)
        if balance < 1:
            return

        copy = active_copy()
        await bot.send_message(
            telegram_id,
            copy.style_guide_offer,
            parse_mode="Markdown",
            reply_markup=style_guide_offer_keyboard(generation_id),
        )
        await Analytics(db).track(telegram_id, "style_guide_offered")
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception(
            "Failed to send style guide offer for user %s gen %s",
            telegram_id,
            generation_id,
        )
