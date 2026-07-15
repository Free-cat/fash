from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.config import Settings
from bot.copy import active_copy
from bot.db.database import Database
from bot.filters import TextIs
from bot.keyboards import guide_button_keyboard, main_keyboard, photo_gallery_keyboard
from bot.services.image_processor import PhotoValidationError, validate_and_process_person_photo
from bot.services.openrouter import FileStorage

router = Router(name="photos")


class Onboarding(StatesGroup):
    collecting_photos = State()


class PhotosAdding(StatesGroup):
    adding = State()


async def show_gallery(message: Message, db: Database, settings: Settings) -> None:
    copy = active_copy()
    user = await db.fetch_user(message.from_user.id)
    photos = await db.list_user_photos(user["id"])
    active = await db.get_active_photo(user["id"])
    active_slot = active["slot_index"] if active else 0
    await message.answer(
        copy.gallery_header.format(count=len(photos), active_slot=active_slot),
        parse_mode="Markdown",
        reply_markup=photo_gallery_keyboard(photos, max_photos=settings.max_user_photos),
    )


async def _save_person_photo(
    message: Message,
    bot: Bot,
    db: Database,
    settings: Settings,
    storage: FileStorage,
) -> None:
    copy = active_copy()
    user = await db.get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        settings.free_credits,
    )
    current_count = await db.count_user_photos(user["id"])

    if current_count >= settings.max_user_photos:
        await message.answer(
            copy.photo_limit_reached.format(limit=settings.max_user_photos)
        )
        return

    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    raw = await bot.download_file(file.file_path)
    data = raw.read()

    try:
        processed = validate_and_process_person_photo(data)
    except PhotoValidationError as exc:
        await message.answer(str(exc), reply_markup=guide_button_keyboard())
        return

    index = current_count + 1
    path = storage.save_person_photo(message.from_user.id, index, processed)
    await db.add_user_photo(user["id"], str(path))

    new_count = await db.count_user_photos(user["id"])
    remaining = settings.max_user_photos - new_count

    if new_count >= 1 and not user["onboarding_complete"]:
        await db.set_onboarding_complete(user["id"])
        balance = await db.get_balance(message.from_user.id)
        await message.answer(
            copy.photo_ready.format(free_credits=balance),
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )
        await message.answer(copy.privacy_note)
        return

    if remaining > 0:
        await message.answer(
            copy.photo_progress_optional.format(
                count=new_count, limit=settings.max_user_photos
            )
        )
    else:
        await message.answer(copy.photo_limit_reached.format(limit=settings.max_user_photos))


@router.message(F.photo, Onboarding.collecting_photos)
@router.message(F.photo, PhotosAdding.adding)
async def receive_person_photo(
    message: Message,
    bot: Bot,
    db: Database,
    settings: Settings,
    storage: FileStorage,
    state: FSMContext,
) -> None:
    await _save_person_photo(message, bot, db, settings, storage)
    user = await db.fetch_user(message.from_user.id)
    if user and user["onboarding_complete"]:
        await state.clear()


@router.message(TextIs("btn_my_photos"))
async def my_photos(message: Message, db: Database, settings: Settings) -> None:
    await show_gallery(message, db, settings)


@router.message(Command("photos"))
async def cmd_photos(message: Message, db: Database, settings: Settings) -> None:
    await show_gallery(message, db, settings)


@router.callback_query(F.data.startswith("photo:"))
async def photo_gallery_callback(
    callback: CallbackQuery,
    db: Database,
    settings: Settings,
    state: FSMContext,
) -> None:
    copy = active_copy()
    action = callback.data.split(":", 1)[1]

    if action == "add":
        user = await db.fetch_user(callback.from_user.id)
        if not user:
            await callback.answer()
            return
        count = await db.count_user_photos(user["id"])
        if count >= settings.max_user_photos:
            await callback.answer(
                copy.photo_limit_reached.format(limit=settings.max_user_photos),
                show_alert=True,
            )
            return
        await state.set_state(PhotosAdding.adding)
        await callback.message.answer(
            copy.reupload_prompt.format(limit=settings.max_user_photos)
        )
        await callback.answer()
        return

    try:
        photo_id = int(action)
    except ValueError:
        await callback.answer()
        return

    user = await db.fetch_user(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    if not await db.set_active_photo(photo_id, user["id"]):
        await callback.answer()
        return

    active = await db.get_active_photo(user["id"])
    slot = active["slot_index"] if active else photo_id
    await callback.answer(copy.photo_switched.format(slot=slot))
