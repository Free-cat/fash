from __future__ import annotations

import time

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardMarkup, Message

from bot.copy import active_copy
from bot.db.database import Database
from bot.handlers.photos import Onboarding, Reupload
from bot.filters import TextIs
from bot.keyboards import (
    deficit_keyboard,
    guide_button_keyboard,
    main_keyboard,
    result_keyboard,
    shop_keyboard,
)
from bot.services.analytics import Analytics
from bot.services.drip import DripService
from bot.services.generation_guard import GenerationGuard
from bot.services.image_processor import PhotoValidationError, validate_and_process_garment_photo
from bot.services.openrouter import FileStorage, OpenRouterClient, TryOnError
from bot.services.referrals import ReferralService

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


@router.message(
    F.photo,
    ~StateFilter(Onboarding.collecting_photos),
    ~StateFilter(Reupload.collecting_photos),
)
async def try_on_garment(
    message: Message,
    bot: Bot,
    db: Database,
    storage: FileStorage,
    openrouter: OpenRouterClient,
    drip: DripService,
) -> None:
    copy = active_copy()
    ok, error = await _user_ready(db, message.from_user.id)
    if not ok:
        await message.answer(error)
        return

    balance = await db.get_balance(message.from_user.id)
    if balance < 1:
        user = await db.fetch_user(message.from_user.id)
        total_purchases = int(user["total_purchases"]) if user else 0
        if total_purchases == 0:
            await message.answer(copy.paywall, reply_markup=shop_keyboard())
        else:
            await message.answer(
                copy.deficit,
                parse_mode="Markdown",
                reply_markup=deficit_keyboard(),
            )
        return

    user = await db.fetch_user(message.from_user.id)
    person_path = await db.get_primary_photo_path(user["id"])

    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    raw = await bot.download_file(file.file_path)
    garment_raw = raw.read()

    try:
        garment_processed = validate_and_process_garment_photo(garment_raw)
    except PhotoValidationError as exc:
        await message.answer(str(exc), reply_markup=guide_button_keyboard())
        return

    guard = GenerationGuard(db)
    if guard.circuit_breaker.is_open():
        await message.answer(copy.circuit_open, reply_markup=main_keyboard())
        return

    if not await guard.acquire(message.from_user.id):
        await message.answer(copy.concurrent, reply_markup=main_keyboard())
        return

    analytics = Analytics(db)
    total_purchases = int(user["total_purchases"])

    try:
        if not await db.deduct_credit(message.from_user.id):
            await message.answer(copy.not_enough_credits)
            return

        generation_id = int(time.time())
        garment_path = storage.save_garment_photo(
            message.from_user.id, generation_id, garment_processed
        )
        person_bytes = storage.read(person_path)

        status = await message.answer(copy.generating)

        try:
            result_bytes = await openrouter.generate_tryon(person_bytes, garment_processed)
        except TryOnError as exc:
            guard.circuit_breaker.record_failure()
            await db.add_credits(message.from_user.id, 1)
            await status.edit_text(copy.generation_failed.format(error=exc))
            return

        guard.circuit_breaker.record_success()
        result_path = storage.save_result_photo(
            message.from_user.id, generation_id, result_bytes
        )
        gen_id = await db.record_generation(user["id"], str(garment_path), str(result_path))

        referrals = ReferralService(db)
        await referrals.on_first_tryon(message.from_user.id)

        remaining = await db.get_balance(message.from_user.id)
        gen_count = await db.count_generations(user["id"])

        await _handle_drip_triggers(
            drip,
            db,
            analytics,
            message.from_user.id,
            user["id"],
            remaining,
            total_purchases,
            gen_count,
        )

        await status.delete()
        caption, keyboard = build_result_message(remaining, total_purchases, gen_id)
        await _track_paywall_if_needed(
            message, db, analytics, remaining, total_purchases
        )
        await message.answer_photo(
            BufferedInputFile(result_bytes, filename="tryon.jpg"),
            caption=caption,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
    finally:
        await guard.release(message.from_user.id)
