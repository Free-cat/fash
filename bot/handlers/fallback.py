from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.copy import active_copy
from bot.db.database import Database
from bot.handlers.photos import Onboarding, PhotosAdding
from bot.keyboards import look_cart_keyboard, main_keyboard, welcome_keyboard

router = Router(name="fallback")


@router.message()
async def unhandled_message(
    message: Message,
    state: FSMContext,
    db: Database,
) -> None:
    copy = active_copy()
    current = await state.get_state()

    if current == Onboarding.collecting_photos.state:
        await message.answer(
            copy.fallback_onboarding_person,
            parse_mode="Markdown",
            reply_markup=welcome_keyboard(),
        )
        return

    if current == PhotosAdding.adding.state:
        await message.answer(
            copy.fallback_add_person_photo,
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )
        return

    user = await db.fetch_user(message.from_user.id)
    if not user or not user["onboarding_complete"]:
        await message.answer(copy.send_start_first, reply_markup=main_keyboard())
        return

    balance = await db.get_balance(message.from_user.id)
    cart_count = len(await db.get_look_cart(user["id"]))
    if cart_count > 0:
        text = copy.fallback_unknown_with_cart.format(
            balance=balance,
            count=cart_count,
        )
        await message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=look_cart_keyboard(cart_count, at_limit=cart_count >= 5),
        )
        return

    await message.answer(
        copy.fallback_unknown.format(balance=balance),
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )
