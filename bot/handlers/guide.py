from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.config import Settings
from bot.copy import active_copy
from bot.db.database import Database
from bot.handlers.photos import Onboarding
from bot.keyboards import main_keyboard
from bot.services.analytics import Analytics
from bot.services.drip import DripService

router = Router(name="guide")


def guide_next_step(
    onboarding_complete: bool,
    balance: int,
) -> tuple[str, InlineKeyboardMarkup]:
    copy = active_copy()
    if onboarding_complete:
        return (
            copy.guide_next_garment,
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=copy.btn_choose_outfit,
                            callback_data="guide:next:garment",
                        )
                    ]
                ]
            ),
        )

    return (
        copy.guide_next_person,
        InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=copy.btn_upload_person,
                        callback_data="guide:next:person",
                    )
                ]
            ]
        ),
    )


async def _show_guide(
    target: Message,
    settings: Settings,
    db: Database,
    state: FSMContext,
    telegram_id: int,
) -> None:
    copy = active_copy()
    analytics = Analytics(db)
    await analytics.track(telegram_id, "guide_viewed")

    user = await db.fetch_user(telegram_id)
    onboarding_complete = bool(user and user["onboarding_complete"])
    balance = await db.get_balance(telegram_id)
    next_text, next_keyboard = guide_next_step(onboarding_complete, balance)

    if not onboarding_complete:
        await state.set_state(Onboarding.collecting_photos)

    guide_path = settings.guide_photo_path
    if not guide_path.exists():
        await target.answer(
            f"{copy.guide_text_fallback}\n\n{next_text}",
            parse_mode="Markdown",
            reply_markup=next_keyboard,
        )
        return

    await target.answer_photo(
        FSInputFile(guide_path),
        caption=f"{copy.guide_caption}\n\n{next_text}",
        parse_mode="Markdown",
        reply_markup=next_keyboard,
    )


@router.callback_query(F.data == "guide:show")
async def show_guide_callback(
    callback: CallbackQuery,
    settings: Settings,
    db: Database,
    state: FSMContext,
) -> None:
    await _show_guide(callback.message, settings, db, state, callback.from_user.id)
    await callback.answer()


@router.message(Command("guide"))
async def show_guide_command(
    message: Message,
    settings: Settings,
    db: Database,
    state: FSMContext,
) -> None:
    await _show_guide(message, settings, db, state, message.from_user.id)


@router.callback_query(F.data == "guide:next:person")
async def guide_next_person(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Onboarding.collecting_photos)
    await callback.message.answer(active_copy().guide_next_person)
    await callback.answer()


@router.callback_query(F.data == "guide:next:garment")
async def guide_next_garment(callback: CallbackQuery, db: Database) -> None:
    balance = await db.get_balance(callback.from_user.id)
    await callback.message.answer(
        active_copy().try_on_hint.format(balance=balance),
        reply_markup=main_keyboard(),
    )
    await callback.answer()


@router.message(Command("stop_reminders"))
async def stop_reminders(message: Message, db: Database, drip: DripService) -> None:
    copy = active_copy()
    await db.set_drip_opt_out(message.from_user.id)
    await drip.cancel_all(message.from_user.id)
    analytics = Analytics(db)
    await analytics.track(message.from_user.id, "drip_opt_out")
    await message.answer(copy.stop_reminders)


@router.callback_query(F.data == "drip:opt_out")
async def drip_opt_out_callback(
    callback: CallbackQuery, db: Database, drip: DripService
) -> None:
    copy = active_copy()
    await db.set_drip_opt_out(callback.from_user.id)
    await drip.cancel_all(callback.from_user.id)
    analytics = Analytics(db)
    await analytics.track(callback.from_user.id, "drip_opt_out")
    await callback.answer(copy.drip_opt_out)
    await callback.message.answer(copy.stop_reminders_done)
