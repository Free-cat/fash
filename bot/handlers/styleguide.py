from __future__ import annotations

import asyncio
import logging

from datetime import datetime, timezone

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
from bot.services.generation_status import send_generation_status
from bot.services.openrouter import FileStorage, OpenRouterClient, TryOnError
from bot.services.premium_offer import (
    PREMIUM_OFFER_DELAY_SECONDS,
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
    idle_since = datetime.now(timezone.utc)
    task = asyncio.create_task(
        schedule_style_guide_offer(
            bot,
            db,
            guard,
            settings,
            telegram_id,
            generation_id,
            balance,
            idle_since=idle_since,
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


def _premium_offer_text(copy, variant: int, *, showcase: bool) -> str:
    if showcase:
        return (
            copy.premium_showcase_offer_v1
            if variant == 1
            else copy.premium_showcase_offer_v2
        )
    return copy.premium_offer_v1 if variant == 1 else copy.premium_offer_v2


def _premium_analytics_event(*, showcase: bool, action: str, variant: int) -> str:
    prefix = "premium_showcase" if showcase else "premium_offer"
    if showcase and action == "shown":
        return f"{prefix}_offer_shown_v{variant}"
    return f"{prefix}_{action}_v{variant}"


def _premium_cross_sell(copy, balance: int, cost: int) -> str:
    if copy.locale == "ru":
        need = "нужна 1 примерка" if cost == 1 else f"нужно {cost} примерки"
        return (
            f"Для полного стайлинга {need}, у тебя {balance}. "
            "Докупи или позови друга — и попробуй 👇"
        )
    unit = "try-on" if cost == 1 else "try-ons"
    return (
        f"Full styling takes {cost} {unit} — you have {balance}. "
        "Grab a pack or invite a friend, then give it a go 👇"
    )


@router.callback_query(F.data.startswith("styleguide:"))
async def style_guide_callback(
    callback: CallbackQuery,
    settings: Settings,
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
    cost = await db.get_style_guide_cost(telegram_id)
    showcase = cost == 1
    await analytics.track(
        telegram_id,
        _premium_analytics_event(showcase=showcase, action="purchased", variant=variant),
    )

    if generation["style_guide_path"]:
        style_bytes = storage.read(generation["style_guide_path"])
        await callback.message.answer_photo(
            BufferedInputFile(style_bytes, filename="style_guide.jpg"),
            caption=copy.style_guide_already,
        )
        await callback.answer()
        return

    balance = await db.get_balance(telegram_id)
    if balance < cost:
        user = await db.fetch_user(telegram_id)
        total_purchases = int(user["total_purchases"]) if user else 0
        cross_sell = _premium_cross_sell(copy, balance, cost)
        # Paywall/deficit: only packs + invite — no Full styling CTA.
        if total_purchases == 0:
            await callback.message.answer(
                cross_sell,
                reply_markup=paywall_keyboard(),
            )
        else:
            await callback.message.answer(
                cross_sell,
                reply_markup=deficit_keyboard(),
            )
        await callback.answer()
        return

    if not await db.deduct_credits(telegram_id, cost):
        await callback.answer(copy.not_enough_credits, show_alert=True)
        return

    guard = GenerationGuard(db)
    if guard.circuit_breaker.is_open():
        await db.add_credits(telegram_id, cost)
        await callback.message.answer(copy.circuit_open)
        await callback.answer()
        return

    in_progress_key = (telegram_id, generation_id)
    _style_guide_in_progress.add(in_progress_key)
    try:
        generation_status = await send_generation_status(
            callback.message,
            sticker_id=settings.generating_sticker_id,
            text=copy.style_guide_generating,
        )
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
            if showcase:
                await db.mark_premium_showcase_used(telegram_id)

            remaining = await db.get_balance(telegram_id)
            await analytics.track(telegram_id, "style_guide_generated")

            await generation_status.complete()
            await callback.message.answer_photo(
                BufferedInputFile(guide_bytes, filename="style_guide.jpg"),
                caption=copy.style_guide_caption,
                reply_markup=result_keyboard(remaining, generation_id, cost=None),
            )
        except TryOnError as exc:
            guard.circuit_breaker.record_failure()
            await db.add_credits(telegram_id, cost)
            await analytics.track(telegram_id, "style_guide_failed")
            logger.error(
                "Style guide generation failed for user %s gen %s: %s",
                telegram_id,
                generation_id,
                exc,
            )
            failed_copy = (
                copy.premium_showcase_failed if showcase else copy.premium_style_guide_failed
            )
            await generation_status.fail(failed_copy)
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
    *,
    idle_since: datetime | None = None,
) -> None:
    try:
        await asyncio.sleep(PREMIUM_OFFER_DELAY_SECONDS)

        generation = await db.get_generation_for_user_by_id(generation_id, telegram_id)
        if generation is None or generation["style_guide_path"]:
            return

        if (telegram_id, generation_id) in _style_guide_in_progress:
            return

        if not await guard.can_send(
            telegram_id,
            TOUCHPOINT_PREMIUM,
            generation_id=generation_id,
            idle_since=idle_since,
        ):
            await Analytics(db).track(
                telegram_id, "proactive_suppressed", TOUCHPOINT_PREMIUM
            )
            return

        balance = await db.get_balance(telegram_id)
        copy = active_copy()
        analytics = Analytics(db)
        cost = await db.get_style_guide_cost(telegram_id)
        showcase = cost == 1

        if balance < cost:
            # Not enough credits — sell packs only, no Full styling button.
            await bot.send_message(
                telegram_id,
                _premium_cross_sell(copy, balance, cost),
                reply_markup=paywall_keyboard(),
            )
            return

        variant = await _resolve_variant(db, telegram_id)
        offer_text = _premium_offer_text(copy, variant, showcase=showcase)
        state = await db.get_premium_offer_state(telegram_id)
        keyboard = style_guide_offer_keyboard(generation_id, cost=cost)

        if not state.get("premium_offer_shown_once"):
            if settings.premium_preview_path.exists():
                await bot.send_photo(
                    telegram_id,
                    FSInputFile(settings.premium_preview_path),
                    caption=f"{copy.premium_offer_preview_caption}\n\n{offer_text}",
                    reply_markup=keyboard,
                    parse_mode="Markdown",
                )
            else:
                await bot.send_message(
                    telegram_id,
                    offer_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown",
                )
        else:
            await bot.send_message(
                telegram_id,
                offer_text,
                reply_markup=keyboard,
                parse_mode="Markdown",
            )

        await db.mark_premium_offer_shown(telegram_id)
        register_pending(telegram_id, generation_id)
        await analytics.track(
            telegram_id,
            _premium_analytics_event(showcase=showcase, action="shown", variant=variant),
        )
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception(
            "Failed to send style guide offer for user %s gen %s",
            telegram_id,
            generation_id,
        )
