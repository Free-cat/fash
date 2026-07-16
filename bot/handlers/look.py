from __future__ import annotations

import asyncio
import json
import time

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from bot.config import Settings
from bot.copy import active_copy
from bot.db.database import Database
from bot.handlers.photos import Onboarding, PhotosAdding
from bot.handlers.styleguide import schedule_style_guide_offer_task
from bot.handlers.tryon import (
    _handle_drip_triggers,
    _track_paywall_if_needed,
    _user_ready,
    build_result_message,
)
from bot.keyboards import (
    deficit_keyboard,
    guide_button_keyboard,
    look_cart_keyboard,
    paywall_keyboard,
    shop_keyboard,
)
from bot.services.analytics import Analytics
from bot.services.drip import DripService
from bot.services.generation_guard import GenerationGuard
from bot.services.image_processor import PhotoValidationError
from bot.services.look_cart import LookCartService
from bot.services.openrouter import FileStorage, OpenRouterClient, TryOnError
from bot.services.proactive_guard import ProactiveGuard
from bot.services.referrals import ReferralService

router = Router(name="look")


@router.message(
    F.photo,
    ~StateFilter(Onboarding.collecting_photos),
    ~StateFilter(PhotosAdding.adding),
)
async def add_garment_to_cart(
    message: Message,
    bot: Bot,
    db: Database,
    storage: FileStorage,
) -> None:
    ok, error = await _user_ready(db, message.from_user.id)
    if not ok:
        await message.answer(error)
        return

    user = await db.fetch_user(message.from_user.id)
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    raw = (await bot.download_file(file.file_path)).read()

    svc = LookCartService(db, storage)
    try:
        count, at_limit = await svc.add_garment(
            user["id"], message.from_user.id, raw, int(time.time())
        )
    except PhotoValidationError as exc:
        await message.answer(str(exc), reply_markup=guide_button_keyboard())
        return

    copy = active_copy()
    active = await db.get_active_photo(user["id"])
    slot = active["slot_index"] if active else 1
    text = copy.look_item_added.format(count=count, active_slot=slot)
    if count == 1:
        text += f"\n\n{copy.look_one_item_hint}"
    if at_limit:
        text = copy.look_full
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=look_cart_keyboard(count, at_limit=at_limit),
    )
    await Analytics(db).track(
        message.from_user.id,
        "look_item_added",
        json.dumps({"count": count}),
    )


@router.callback_query(F.data == "look:clear")
async def look_clear(callback: CallbackQuery, db: Database) -> None:
    user = await db.fetch_user(callback.from_user.id)
    if not user:
        await callback.answer()
        return
    await db.clear_look_cart(user["id"])
    await callback.message.answer(active_copy().look_cleared)
    await callback.answer()


@router.callback_query(F.data == "look:add_hint")
async def look_add_hint(callback: CallbackQuery) -> None:
    await callback.message.answer("Send another clothing photo 👗")
    await callback.answer()


@router.callback_query(F.data == "look:generate")
async def look_generate(
    callback: CallbackQuery,
    bot: Bot,
    db: Database,
    settings: Settings,
    storage: FileStorage,
    openrouter: OpenRouterClient,
    drip: DripService,
    proactive_guard: ProactiveGuard,
) -> None:
    copy = active_copy()
    telegram_id = callback.from_user.id
    analytics = Analytics(db)

    user = await db.fetch_user(telegram_id)
    if not user:
        await callback.answer(copy.send_start_first, show_alert=True)
        return

    svc = LookCartService(db, storage)
    paths = await svc.paths(user["id"])
    if not paths:
        await callback.answer("Add at least one item first.", show_alert=True)
        return

    person_path = await db.get_active_photo_path(user["id"])
    if not person_path:
        await callback.answer(copy.no_saved_photos, show_alert=True)
        return

    balance = await db.get_balance(telegram_id)
    total_purchases = int(user["total_purchases"])
    if balance < 1:
        if total_purchases == 0:
            await callback.message.answer(copy.paywall, reply_markup=paywall_keyboard())
        else:
            await callback.message.answer(
                copy.deficit,
                parse_mode="Markdown",
                reply_markup=deficit_keyboard(),
            )
        await callback.answer()
        return

    guard = GenerationGuard(db)
    if guard.circuit_breaker.is_open():
        await callback.message.answer(copy.circuit_open)
        await callback.answer()
        return

    garment_count = len(paths)
    generating = (
        copy.look_generating_one
        if garment_count == 1
        else copy.look_generating_many
    )

    if not await db.deduct_credit(telegram_id):
        await callback.answer(copy.not_enough_credits, show_alert=True)
        return

    generation_id = int(time.time())
    person_bytes = storage.read(person_path)
    garment_bytes_list = [storage.read(p) for p in paths]
    garment_path = paths[0] if len(paths) == 1 else ",".join(paths)

    status = await callback.message.answer(generating)
    await callback.answer()

    try:
        result_bytes = await openrouter.generate_outfit_tryon(
            person_bytes, garment_bytes_list
        )
    except TryOnError as exc:
        guard.circuit_breaker.record_failure()
        await db.add_credits(telegram_id, 1)
        await status.edit_text(copy.generation_failed.format(error=exc))
        await analytics.track(
            telegram_id,
            "look_failed",
            json.dumps({"garment_count": garment_count}),
        )
        return

    guard.circuit_breaker.record_success()
    result_path = storage.save_result_photo(
        telegram_id, generation_id, result_bytes
    )
    gen_id = await db.record_generation(
        user["id"],
        garment_path,
        str(result_path),
        garment_count=garment_count,
        mode="cart",
    )
    await svc.clear(user["id"])

    referrals = ReferralService(db)
    await referrals.on_first_tryon(telegram_id)

    remaining = await db.get_balance(telegram_id)
    gen_count = await db.count_generations(user["id"])

    await _handle_drip_triggers(
        drip,
        db,
        analytics,
        telegram_id,
        user["id"],
        remaining,
        total_purchases,
        gen_count,
    )

    await status.delete()
    caption, keyboard = build_result_message(
        remaining, total_purchases, gen_id, cost=await db.get_style_guide_cost(telegram_id)
    )
    await _track_paywall_if_needed(
        callback.message, db, analytics, remaining, total_purchases
    )
    await callback.message.answer_photo(
        BufferedInputFile(result_bytes, filename="tryon.jpg"),
        caption=caption,
        parse_mode="Markdown",
        reply_markup=keyboard,
    )
    await analytics.track(
        telegram_id,
        "look_generated",
        json.dumps({"garment_count": garment_count}),
    )
    schedule_style_guide_offer_task(
        bot, db, proactive_guard, settings, telegram_id, gen_id, remaining
    )
