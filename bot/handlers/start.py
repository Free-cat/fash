from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message

from bot.config import Settings
from bot.copy import active_copy
from bot.db.database import Database
from bot.filters import TextIs
from bot.handlers.photos import Onboarding
from bot.keyboards import draft_look_keyboard, main_keyboard, welcome_keyboard
from bot.services.analytics import Analytics
from bot.services.referrals import ReferralService, parse_start_payload

router = Router(name="start")


async def send_demo_visual(message: Message, settings: Settings, db: Database) -> None:
    if not settings.demo_image_path.exists():
        return

    copy = active_copy()
    await message.answer_photo(
        FSInputFile(settings.demo_image_path),
        caption=copy.demo_caption,
        parse_mode="Markdown",
    )
    analytics = Analytics(db)
    await analytics.track(message.from_user.id, "demo_viewed")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db: Database, settings: Settings) -> None:
    await state.clear()
    copy = active_copy()

    user = await db.get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        settings.free_credits,
    )

    referrer_id = parse_start_payload(message.text or "")
    if referrer_id is not None:
        referrals = ReferralService(db)
        await referrals.attach_referral(
            referee_id=message.from_user.id,
            referrer_id=referrer_id,
        )

    if user["onboarding_complete"]:
        balance = await db.get_balance(message.from_user.id)
        active = await db.get_active_photo(user["id"])
        slot = active["slot_index"] if active else 1
        cart_count = len(await db.get_look_cart(user["id"]))
        if cart_count > 0:
            await message.answer(
                copy.welcome_back_draft_look.format(count=cart_count),
                reply_markup=draft_look_keyboard(),
            )
        else:
            await message.answer(
                copy.welcome_back.format(balance=balance)
                + f"\nActive photo: Photo {slot} ✓",
                reply_markup=main_keyboard(),
            )
        return

    await send_demo_visual(message, settings, db)
    await state.set_state(Onboarding.collecting_photos)
    await message.answer(
        copy.welcome_new,
        parse_mode="Markdown",
        reply_markup=welcome_keyboard(),
    )


@router.message(Command("help"))
@router.message(TextIs("btn_help"))
async def cmd_help(message: Message, settings: Settings, db: Database) -> None:
    await send_demo_visual(message, settings, db)
    await message.answer(active_copy().help_text, reply_markup=main_keyboard())


@router.message(Command("balance"))
@router.message(TextIs("btn_balance"))
async def cmd_balance(message: Message, db: Database) -> None:
    balance = await db.get_balance(message.from_user.id)
    await message.answer(
        active_copy().balance_text.format(balance=balance),
        reply_markup=main_keyboard(),
    )
