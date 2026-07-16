from __future__ import annotations

from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InputMediaPhoto,
    Message,
)

from bot.config import Settings
from bot.copy import active_copy
from bot.db.database import Database
from bot.filters import TextIs
from bot.keyboards import guide_button_keyboard, main_keyboard
from bot.services.image_processor import PhotoValidationError, validate_and_process_person_photo
from bot.services.openrouter import FileStorage
from bot.services.photo_gallery import (
    empty_gallery_keyboard,
    gallery_caption,
    num_page_for_index,
    photo_by_index,
    photo_gallery_keyboard,
    photo_index,
)

router = Router(name="photos")


class Onboarding(StatesGroup):
    collecting_photos = State()


class PhotosAdding(StatesGroup):
    adding = State()


def _photo_input(storage: FileStorage, path: str, slot: int) -> BufferedInputFile:
    return BufferedInputFile(
        storage.read(path),
        filename=f"photo_{slot}.jpg",
    )


async def _send_gallery(
    message: Message,
    *,
    photos: list,
    view_photo: dict,
    storage: FileStorage,
    num_page: int,
) -> None:
    active = next((photo for photo in photos if photo["is_active"]), None)
    caption = gallery_caption(photos, view_photo, active)
    keyboard = photo_gallery_keyboard(photos, view_photo["id"], num_page)
    slot = view_photo["slot_index"]

    if view_photo["path"] and Path(view_photo["path"]).is_file():
        await message.answer_photo(
            _photo_input(storage, view_photo["path"], slot),
            caption=caption,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
        return

    await message.answer(
        caption,
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


async def _edit_gallery(
    message: Message,
    *,
    photos: list,
    view_photo: dict,
    storage: FileStorage,
    num_page: int,
) -> None:
    active = next((photo for photo in photos if photo["is_active"]), None)
    caption = gallery_caption(photos, view_photo, active)
    keyboard = photo_gallery_keyboard(photos, view_photo["id"], num_page)
    slot = view_photo["slot_index"]

    if view_photo["path"] and Path(view_photo["path"]).is_file():
        media = InputMediaPhoto(
            media=_photo_input(storage, view_photo["path"], slot),
            caption=caption,
            parse_mode="Markdown",
        )
        try:
            await message.edit_media(media=media, reply_markup=keyboard)
            return
        except Exception:
            await message.answer_photo(
                _photo_input(storage, view_photo["path"], slot),
                caption=caption,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
            return

    try:
        await message.edit_caption(
            caption=caption,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
    except Exception:
        await message.edit_reply_markup(reply_markup=keyboard)


async def show_gallery(
    message: Message,
    db: Database,
    storage: FileStorage,
) -> None:
    copy = active_copy()
    user = await db.fetch_user(message.from_user.id)
    if not user:
        return
    photos = await db.list_user_photos(user["id"])
    if not photos:
        await message.answer(
            copy.gallery_empty,
            parse_mode="Markdown",
            reply_markup=empty_gallery_keyboard(),
        )
        return

    active = await db.get_active_photo(user["id"])
    view_photo = active or photos[0]
    num_page = num_page_for_index(photo_index(photos, view_photo["id"]))
    await _send_gallery(
        message,
        photos=photos,
        view_photo=view_photo,
        storage=storage,
        num_page=num_page,
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

    if new_count >= 1 and not user["onboarding_complete"]:
        await db.set_onboarding_complete(user["id"])
        balance = await db.get_balance(message.from_user.id)
        await message.answer(
            copy.photo_ready.format(free_credits=balance),
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )
        return

    await message.answer(copy.photo_progress_optional.format(count=new_count))


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
async def my_photos(message: Message, db: Database, storage: FileStorage) -> None:
    await show_gallery(message, db, storage)


@router.message(Command("photos"))
async def cmd_photos(message: Message, db: Database, storage: FileStorage) -> None:
    await show_gallery(message, db, storage)


@router.callback_query(F.data.startswith("photo:"))
async def photo_gallery_callback(
    callback: CallbackQuery,
    db: Database,
    state: FSMContext,
    storage: FileStorage,
) -> None:
    copy = active_copy()
    parts = callback.data.split(":")
    action = parts[1]

    if action == "noop":
        await callback.answer()
        return

    if action == "add":
        user = await db.fetch_user(callback.from_user.id)
        if not user:
            await callback.answer()
            return
        await state.set_state(PhotosAdding.adding)
        await callback.message.answer(copy.reupload_prompt)
        await callback.answer()
        return

    user = await db.fetch_user(callback.from_user.id)
    if not user:
        await callback.answer()
        return

    photos = await db.list_user_photos(user["id"])
    if not photos:
        await callback.answer(copy.gallery_empty, show_alert=True)
        return

    toast: str | None = None

    if action == "prev":
        view_id = int(parts[2])
        index = photo_index(photos, view_id)
        view_photo = photo_by_index(photos, index - 1)
        num_page = num_page_for_index(photo_index(photos, view_photo["id"]))
    elif action == "next":
        view_id = int(parts[2])
        index = photo_index(photos, view_id)
        view_photo = photo_by_index(photos, index + 1)
        num_page = num_page_for_index(photo_index(photos, view_photo["id"]))
    elif action == "view":
        view_id = int(parts[2])
        view_photo = photos[photo_index(photos, view_id)]
        num_page = num_page_for_index(photo_index(photos, view_id))
    elif action == "npg":
        num_page = int(parts[2])
        view_id = int(parts[3])
        view_photo = photos[photo_index(photos, view_id)]
    elif action == "use":
        view_id = int(parts[2])
        if not await db.set_active_photo(view_id, user["id"]):
            await callback.answer()
            return
        photos = await db.list_user_photos(user["id"])
        view_photo = photos[photo_index(photos, view_id)]
        num_page = num_page_for_index(photo_index(photos, view_id))
        toast = copy.photo_switched.format(slot=view_photo["slot_index"])
    else:
        await callback.answer()
        return

    await _edit_gallery(
        callback.message,
        photos=photos,
        view_photo=view_photo,
        storage=storage,
        num_page=num_page,
    )
    await callback.answer(toast)
