from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.types import BufferedInputFile, CallbackQuery, FSInputFile

from bot.config import Settings
from bot.copy import active_copy
from bot.db.database import Database
from bot.keyboards import (
    deficit_keyboard,
    paywall_keyboard,
    result_keyboard,
    style_guide_offer_keyboard,
)
from bot.services.analytics import Analytics
from bot.services.generation_guard import GenerationGuard
from bot.services.openrouter import FileStorage, OpenRouterClient, TryOnError
from bot.services.premium_offer import (
    PREMIUM_OFFER_DELAY_SECONDS,
    PREMIUM_STYLE_GUIDE_COST,
    assign_variant,
    clear_pending,
    register_pending,
)
from bot.services.proactive_guard import ProactiveGuard, TOUCHPOINT_PREMIUM

logger = logging.getLogger(__name__)

router = Router(name="styleguide")

_pending_offers: dict[tuple[int, int], asyncio.Task[None]] = {}
_style_guide_in_progress: set[tuple[int, int]] = set()


def cancel_style_guide_offer(telegram_id: int, generation_id: int) -> None:
    task = _pending_offers.pop((telegram_id, generation_id), None)
    if task and not task.done():
        task.cancel()


def schedule_style_guide_offer_task(
    bot: Bot,
    db: Database,
    guard: ProactiveGuard,
    settings: Settings,
    telegram_id: int,
    generation_id: int,
    balance: int,
) -> None:
    key = (telegram_id, generation_id)
    cancel_style_guide_offer(telegram_id, generation_id)
    task = asyncio.create_task(
        schedule_style_guide_offer(
            bot, db, guard, settings, telegram_id, generation_id, balance
        )
    )
    _pending_offers[key] = task

    def _cleanup(done: asyncio.Task[None]) -> None:
        current = _pending_offers.get(key)
        if current is done:
            _pending_offers.pop(key, None)
        if done.cancelled():
            return
        exc = done.exception()
        if exc:
            logger.error("Style guide offer task failed: %s", exc)

    task.add_done_callback(_cleanup)


async def _resolve_variant(db: Database, telegram_id: int) -> int:
    state = await db.get_premium_offer_state(telegram_id)
    variant = state.get("premium_offer_variant")
    if variant is not None:
        return int(variant)
    variant = assign_variant(telegram_id)
    await db.assign_premium_offer_variant(telegram_id, variant)
    return variant


def _premium_offer_text(copy, variant: int) -> str:
    return copy.premium_offer_v1 if variant == 1 else copy.premium_offer_v2


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

    cancel_style_guide_offer(telegram_id, generation_id)
    clear_pending(telegram_id)
    await db.reset_premium_offer_ignored(telegram_id)

    generation = await db.get_generation_for_user_by_id(generation_id, telegram_id)
    if generation is None:
        await callback.answer(copy.style_guide_not_found, show_alert=True)
        return

    analytics = Analytics(db)
    variant = await _resolve_variant(db, telegram_id)
    await analytics.track(telegram_id, f"premium_offer_purchased_v{variant}")

    if generation["style_guide_path"]:
        style_bytes = storage.read(generation["style_guide_path"])
        await callback.message.answer_photo(
            BufferedInputFile(style_bytes, filename="style_guide.jpg"),
            caption=copy.style_guide_already,
        )
        await callback.answer()
        return

    balance = await db.get_balance(telegram_id)
    if balance < PREMIUM_STYLE_GUIDE_COST:
        user = await db.fetch_user(telegram_id)
        total_purchases = int(user["total_purchases"]) if user else 0
        if total_purchases == 0:
            await callback.message.answer(
                copy.premium_offer_cross_sell.format(balance=balance),
                reply_markup=paywall_keyboard(),
            )
        else:
            await callback.message.answer(
                copy.premium_offer_cross_sell.format(balance=balance),
                reply_markup=deficit_keyboard(),
            )
        await callback.answer()
        return

    if not await db.deduct_credits(telegram_id, PREMIUM_STYLE_GUIDE_COST):
        await callback.answer(copy.not_enough_credits, show_alert=True)
        return

    guard = GenerationGuard(db)
    if guard.circuit_breaker.is_open():
        await db.add_credits(telegram_id, PREMIUM_STYLE_GUIDE_COST)
        await callback.message.answer(copy.circuit_open)
        await callback.answer()
        return

    in_progress_key = (telegram_id, generation_id)
    _style_guide_in_progress.add(in_progress_key)
    try:
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
        except TryOnError as exc:
            guard.circuit_breaker.record_failure()
            await db.add_credits(telegram_id, PREMIUM_STYLE_GUIDE_COST)
            await analytics.track(telegram_id, "style_guide_failed")
            logger.error(
                "Style guide generation failed for user %s gen %s: %s",
                telegram_id,
                generation_id,
                exc,
            )
            try:
                await status.delete()
            except Exception:
                pass
            await callback.message.answer(copy.premium_style_guide_failed)
    finally:
        _style_guide_in_progress.discard(in_progress_key)


async def schedule_style_guide_offer(
    bot: Bot,
    db: Database,
    guard: ProactiveGuard,
    settings: Settings,
    telegram_id: int,
    generation_id: int,
    balance: int,
) -> None:
    try:
        await asyncio.sleep(PREMIUM_OFFER_DELAY_SECONDS)

        generation = await db.get_generation_for_user_by_id(generation_id, telegram_id)
        if generation is None or generation["style_guide_path"]:
            return

        if (telegram_id, generation_id) in _style_guide_in_progress:
            return

        if not await guard.can_send(
            telegram_id, TOUCHPOINT_PREMIUM, generation_id=generation_id
        ):
            await Analytics(db).track(
                telegram_id, "proactive_suppressed", TOUCHPOINT_PREMIUM
            )
            return

        balance = await db.get_balance(telegram_id)
        copy = active_copy()
        analytics = Analytics(db)

        if balance < PREMIUM_STYLE_GUIDE_COST:
            await bot.send_message(
                telegram_id,
                copy.premium_offer_cross_sell.format(balance=balance),
                reply_markup=paywall_keyboard(),
            )
            return

        variant = await _resolve_variant(db, telegram_id)
        offer_text = _premium_offer_text(copy, variant)
        state = await db.get_premium_offer_state(telegram_id)
        keyboard = style_guide_offer_keyboard(generation_id)

        if not state.get("premium_offer_shown_once"):
            if settings.premium_preview_path.exists():
                await bot.send_photo(
                    telegram_id,
                    FSInputFile(settings.premium_preview_path),
                    caption=f"{copy.premium_offer_preview_caption}\n\n{offer_text}",
                    reply_markup=keyboard,
                )
            else:
                await bot.send_message(
                    telegram_id,
                    offer_text,
                    reply_markup=keyboard,
                )
        else:
            await bot.send_message(
                telegram_id,
                offer_text,
                reply_markup=keyboard,
            )

        await db.mark_premium_offer_shown(telegram_id)
        register_pending(telegram_id, generation_id)
        await analytics.track(telegram_id, f"premium_offer_shown_v{variant}")
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception(
            "Failed to send style guide offer for user %s gen %s",
            telegram_id,
            generation_id,
        )
